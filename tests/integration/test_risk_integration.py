
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from codesage.risk.risk_scorer import RiskScorer
from codesage.config.risk_baseline import RiskBaselineConfig
from codesage.snapshot.models import ProjectSnapshot, FileSnapshot, FileMetrics, SnapshotMetadata, FileRisk

@pytest.fixture
def mock_snapshot():
    meta = SnapshotMetadata(
        version="v1",
        timestamp=datetime.now(),
        project_name="test_proj",
        file_count=2,
        total_size=100,
        tool_version="1.0",
        config_hash="abc"
    )

    file1 = FileSnapshot(
        path="src/complex.py",
        language="python",
        content="def foo(): pass",
        metrics=FileMetrics(
            lines_of_code=200,
            language_specific={
                "python": {
                    "max_cyclomatic_complexity": 20, # High
                    "avg_cyclomatic_complexity": 10.0,
                    "fan_out": 10
                }
            }
        )
    )

    file2 = FileSnapshot(
        path="src/simple.py",
        language="python",
        content="print('hello')",
        metrics=FileMetrics(
            lines_of_code=10,
            language_specific={
                "python": {
                    "max_cyclomatic_complexity": 1,
                    "avg_cyclomatic_complexity": 1.0,
                    "fan_out": 0
                }
            }
        )
    )

    return ProjectSnapshot(
        metadata=meta,
        files=[file1, file2],
        languages=["python"]
    )

def test_risk_scorer_integration_static_only(mock_snapshot):
    config = RiskBaselineConfig()
    scorer = RiskScorer(config)

    scored_snapshot = scorer.score_project(mock_snapshot)

    f1 = next(f for f in scored_snapshot.files if f.path == "src/complex.py")
    f2 = next(f for f in scored_snapshot.files if f.path == "src/simple.py")

    # Static score for f1 should be high because max_cc=20
    # In my logic: 0.5 * min(20/15, 1) + ...
    # 0.5 * 1 + 0.3 * 1 + 0.2 * 0.5 = 0.9 * 10 = 9.0 complexity

    # Static score only contributed 30% to total risk (weight_complexity=0.3)
    # Risk = 0.3 * 9.0 = 2.7.
    # Plus file_size=200 lines -> 2.0. weight=0.1 -> 0.2
    # Total ~ 2.9 (Low)

    assert f1.risk.risk_score > f2.risk.risk_score
    assert f1.risk.sub_scores["complexity"] > 5.0

    # Ensure churn/coverage is 0 (as not provided)
    assert f1.risk.sub_scores["churn"] == 0.0
    assert f1.risk.sub_scores["coverage"] == 0.0

@patch("codesage.git.miner.GitMiner.get_file_churn_score")
@patch("codesage.git.miner.GitMiner.get_file_author_count")
def test_risk_scorer_integration_with_churn(mock_author, mock_churn, mock_snapshot):
    mock_churn.return_value = 10.0 # Max churn
    mock_author.return_value = 5   # Max authors (5 -> 10 score)

    config = RiskBaselineConfig()
    # Pass repo_path to trigger GitMiner usage (although we mocked methods, init needs path)
    scorer = RiskScorer(config, repo_path=".")

    scored_snapshot = scorer.score_project(mock_snapshot)
    f1 = next(f for f in scored_snapshot.files if f.path == "src/complex.py")

    # Components:
    # Complexity: ~9.0 * 0.3 = 2.7
    # Churn: 10.0 * 0.25 = 2.5
    # Author: 10.0 * 0.1 = 1.0
    # Size: 2.0 * 0.1 = 0.2
    # Coverage: 0.0
    # Total: 2.7 + 2.5 + 1.0 + 0.2 = 6.4 (High)

    assert f1.risk.risk_score >= 6.0
    assert f1.risk.level in ["high", "critical"]
    assert "high_churn" in f1.risk.factors
