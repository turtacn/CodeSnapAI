from typing import Dict, List, NamedTuple

from codesage.config.risk_baseline import RiskBaselineConfig
from codesage.snapshot.models import FileMetrics, FileRisk, ProjectRiskSummary


def score_file_risk(metrics: FileMetrics, config: RiskBaselineConfig) -> FileRisk:
    """Calculates the risk score for a single file."""

    factors = []

    # Normalize metrics (simple division, can be improved)
    norm_max_cc = min(metrics.max_cyclomatic_complexity / config.threshold_complexity_high, 1.0)
    norm_avg_cc = min(metrics.avg_cyclomatic_complexity / config.threshold_complexity_high, 1.0)
    norm_fan_out = min(metrics.fan_out / 20, 1.0)  # Assuming 20 is a high fan-out
    norm_loc = min(metrics.lines_of_code / 1000, 1.0) # Assuming 1000 is a large file

    risk_score = (
        config.weight_complexity_max * norm_max_cc +
        config.weight_complexity_avg * norm_avg_cc +
        config.weight_fan_out * norm_fan_out +
        config.weight_loc * norm_loc
    )

    risk_score = min(risk_score, 1.0)

    # Determine risk level and factors
    if risk_score >= config.threshold_risk_high:
        level = "high"
    elif risk_score >= config.threshold_risk_medium:
        level = "medium"
    else:
        level = "low"

    if metrics.max_cyclomatic_complexity > config.threshold_complexity_high:
        factors.append("high_cyclomatic_complexity")
    if metrics.fan_out > 20:
        factors.append("high_fan_out")
    if metrics.lines_of_code > 1000:
        factors.append("large_file")

    if not factors:
        factors.append("low_risk")

    return FileRisk(risk_score=risk_score, level=level, factors=factors)


def summarize_project_risk(file_risks: Dict[str, FileRisk]) -> ProjectRiskSummary:
    """Summarizes the risk for the entire project."""
    if not file_risks:
        return ProjectRiskSummary(
            avg_risk=0.0,
            high_risk_files=0,
            medium_risk_files=0,
            low_risk_files=0,
        )

    total_risk = sum(r.risk_score for r in file_risks.values())
    avg_risk = total_risk / len(file_risks)

    high_risk_files = sum(1 for r in file_risks.values() if r.level == "high")
    medium_risk_files = sum(1 for r in file_risks.values() if r.level == "medium")
    low_risk_files = sum(1 for r in file_risks.values() if r.level == "low")

    return ProjectRiskSummary(
        avg_risk=avg_risk,
        high_risk_files=high_risk_files,
        medium_risk_files=medium_risk_files,
        low_risk_files=low_risk_files,
    )
