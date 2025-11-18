from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field

from codesage.config.history import HistoryConfig
from codesage.history.diff_models import ProjectDiffSummary


class RegressionWarning(BaseModel):
    """Represents a potential regression detected between two snapshots."""
    id: str
    severity: Literal["info", "warning", "error"]
    message: str
    from_snapshot_id: str
    to_snapshot_id: str
    metrics_delta: Dict[str, Any] = Field(default_factory=dict)


def detect_regressions(
    diff: ProjectDiffSummary,
    config: HistoryConfig,
) -> List[RegressionWarning]:
    """Detects regressions based on a project diff and configuration."""
    warnings: List[RegressionWarning] = []
    thresholds = config.regression_thresholds

    if diff.high_risk_files_delta > thresholds.max_high_risk_delta:
        warnings.append(
            RegressionWarning(
                id="high_risk_files_increase",
                severity="warning",
                message=(
                    f"High risk files increased by {diff.high_risk_files_delta} "
                    f"(threshold: >{thresholds.max_high_risk_delta})."
                ),
                from_snapshot_id=diff.from_snapshot_id,
                to_snapshot_id=diff.to_snapshot_id,
                metrics_delta={"high_risk_files_delta": diff.high_risk_files_delta},
            )
        )

    if diff.error_issues_delta > thresholds.max_error_issues_delta:
        warnings.append(
            RegressionWarning(
                id="error_issues_increase",
                severity="error",
                message=(
                    f"Error issues increased by {diff.error_issues_delta} "
                    f"(threshold: >{thresholds.max_error_issues_delta})."
                ),
                from_snapshot_id=diff.from_snapshot_id,
                to_snapshot_id=diff.to_snapshot_id,
                metrics_delta={"error_issues_delta": diff.error_issues_delta},
            )
        )

    # This is an extension point for checking important rules.
    # A more detailed file-level diff would be needed to implement this properly.

    return warnings
