from __future__ import annotations
from typing import Tuple, List
from codesage.report.summary_models import ReportProjectSummary
from codesage.config.ci import CIPolicyConfig


def evaluate_ci_policy(project_summary: ReportProjectSummary, config: CIPolicyConfig) -> Tuple[bool, List[str]]:
    should_fail = False
    reasons: List[str] = []

    if not config.enabled:
        return False, reasons

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

    return should_fail, reasons
