import pytest
from unittest.mock import MagicMock, patch
from codesage.risk.risk_scorer import RiskScorer
from codesage.config.risk_baseline import RiskBaselineConfig
from codesage.snapshot.models import ProjectSnapshot, FileSnapshot, FileMetrics, FileRisk, SnapshotMetadata
from datetime import datetime

@pytest.fixture
def mock_snapshot():
    return ProjectSnapshot(
        metadata=SnapshotMetadata(
            version="v1",
            timestamp=datetime.now(),
            project_name="test_project",
            file_count=1,
            total_size=100,
            tool_version="0.1.0",
            config_hash="abc"
        ),
        files=[
            FileSnapshot(
                path="src/complex.py",
                language="python",
                content="def foo(): pass",
                metrics=FileMetrics(
                    lines_of_code=200,
                    language_specific={
                        "python": {
                            "max_cyclomatic_complexity": 9,
                            "avg_cyclomatic_complexity": 5.0,
                            "fan_out": 10,
                        }
                    }
                )
            )
        ]
    )

@pytest.fixture
def mock_churn():
    return MagicMock()

@pytest.fixture
def mock_author():
    return MagicMock()

@patch("codesage.git.miner.GitMiner.get_file_churn_score")
@patch("codesage.git.miner.GitMiner.get_file_author_count")
def test_risk_scorer_integration_with_churn(mock_author, mock_churn, mock_snapshot):
    mock_churn.return_value = 10.0
    mock_author.return_value = 5

    config = RiskBaselineConfig()
    scorer = RiskScorer(config, repo_path=".")

    scored_snapshot = scorer.score_project(mock_snapshot)
    f1 = next(f for f in scored_snapshot.files if f.path == "src/complex.py")

    # Expected score ~0.51 with current logic.
    # We assert it captures risk (Medium/High)
    # 0.5 is Medium threshold in default config usually?
    # Let's assert >= 0.5
    assert f1.risk.risk_score >= 0.5
