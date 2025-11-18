import pytest
from codesage.config.risk_baseline import RiskBaselineConfig
from codesage.risk.risk_scorer import score_file_risk, summarize_project_risk
from codesage.snapshot.models import FileMetrics, FileRisk

@pytest.fixture
def risk_config():
    return RiskBaselineConfig.from_defaults()

def test_risk_score_low(risk_config):
    metrics = FileMetrics(
        lines_of_code=50,
        language_specific={
            "python": {
                "max_cyclomatic_complexity": 5,
                "avg_cyclomatic_complexity": 2.0,
                "fan_out": 2,
            }
        }
    )
    risk = score_file_risk(metrics, risk_config)
    assert risk.risk_score < risk_config.threshold_risk_medium
    assert risk.level == "low"
    assert "low_risk" in risk.factors

def test_risk_score_high(risk_config):
    metrics = FileMetrics(
        lines_of_code=1500,
        language_specific={
            "python": {
                "max_cyclomatic_complexity": 15,
                "avg_cyclomatic_complexity": 8.0,
                "fan_out": 25,
            }
        }
    )
    risk = score_file_risk(metrics, risk_config)
    assert risk.risk_score >= risk_config.threshold_risk_high
    assert risk.level == "high"
    assert "high_cyclomatic_complexity" in risk.factors
    assert "high_fan_out" in risk.factors
    assert "large_file" in risk.factors

def test_project_risk_summary():
    file_risks = {
        "file1.py": FileRisk(risk_score=0.8, level="high", factors=[]),
        "file2.py": FileRisk(risk_score=0.5, level="medium", factors=[]),
        "file3.py": FileRisk(risk_score=0.2, level="low", factors=[]),
    }
    summary = summarize_project_risk(file_risks)
    assert summary.avg_risk == 0.5
    assert summary.high_risk_files == 1
    assert summary.medium_risk_files == 1
    assert summary.low_risk_files == 1
