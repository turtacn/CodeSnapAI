from __future__ import annotations
from typing import Tuple, List, Optional
from codesage.report.summary_models import ReportProjectSummary, RegressionSummaryView
from codesage.config.ci import CIPolicyConfig


def evaluate_ci_policy(
    project_summary: ReportProjectSummary,
    config: CIPolicyConfig,
    regression_summary: Optional[RegressionSummaryView] = None
) -> Tuple[bool, List[str]]:
    should_fail = False
    reasons: List[str] = []

    if not config.enabled:
        return False, reasons

    # Existing policy checks
    if config.fail_on_error_issues and project_summary.error_issues > config.max_error_issues:
        should_fail = True
        reasons.append(
            f"error issues {project_summary.error_issues} > allowed {config.max_error_issues}"
        )

    if config.max_high_risk_files >= 0 and project_summary.high_risk_files > config.max_high_risk_files:
        should_fail = True
        reasons.append(
            f"high risk files {project_summary.high_risk_files} > allowed {config.max_high_risk_files}"
        )

    # Regression warnings
    if regression_summary and regression_summary.warnings:
        for warning in regression_summary.warnings:
            message = f"Regression warning ({warning.severity}): {warning.message}"
            reasons.append(message)
            # Optionally, fail CI on critical regressions
            # if config.fail_on_regression and warning.severity == 'error':
            #     should_fail = True

    return should_fail, reasons
