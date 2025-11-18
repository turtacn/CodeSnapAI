from __future__ import annotations
import pytest
from codesage.report.summary_models import ReportProjectSummary
from codesage.config.ci import CIPolicyConfig
from codesage.ci.policy import evaluate_ci_policy


def test_ci_pass_when_under_threshold():
    project_summary = ReportProjectSummary(
        total_files=1,
        high_risk_files=0,
        medium_risk_files=1,
        low_risk_files=0,
        total_issues=1,
        error_issues=0,
        warning_issues=1,
        info_issues=0,
        top_rules=[],
        top_risky_files=[],
        languages=["python"],
        files_per_language={"python": 1},
    )
    config = CIPolicyConfig(enabled=True, max_high_risk_files=1, max_error_issues=1)

    should_fail, reasons = evaluate_ci_policy(project_summary, config)

    assert not should_fail
    assert len(reasons) == 0


def test_ci_fail_on_high_risk_files():
    project_summary = ReportProjectSummary(
        total_files=1,
        high_risk_files=2,
        medium_risk_files=0,
        low_risk_files=0,
        total_issues=0,
        error_issues=0,
        warning_issues=0,
        info_issues=0,
        top_rules=[],
        top_risky_files=[],
        languages=["python"],
        files_per_language={"python": 1},
    )
    config = CIPolicyConfig(enabled=True, max_high_risk_files=1)

    should_fail, reasons = evaluate_ci_policy(project_summary, config)

    assert should_fail
    assert "high risk files 2 > allowed 1" in reasons[0]


def test_ci_fail_on_error_issues():
    project_summary = ReportProjectSummary(
        total_files=1,
        high_risk_files=0,
        medium_risk_files=1,
        low_risk_files=0,
        total_issues=2,
        error_issues=2,
        warning_issues=0,
        info_issues=0,
        top_rules=[],
        top_risky_files=[],
        languages=["python"],
        files_per_language={"python": 1},
    )
    config = CIPolicyConfig(enabled=True, fail_on_error_issues=True, max_error_issues=1)

    should_fail, reasons = evaluate_ci_policy(project_summary, config)

    assert should_fail
    assert "error issues 2 > allowed 1" in reasons[0]
