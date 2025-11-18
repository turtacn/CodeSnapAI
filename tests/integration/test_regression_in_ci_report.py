from datetime import datetime, timezone
from codesage.config.ci import CIPolicyConfig
from codesage.config.history import HistoryConfig
from codesage.ci.policy import evaluate_ci_policy
from codesage.history.diff_engine import diff_project_snapshots
from codesage.history.regression_detector import detect_regressions
from codesage.report.summary_models import RegressionSummaryView, ReportProjectSummary
from codesage.snapshot.models import (
    ProjectSnapshot,
    FileSnapshot,
    SnapshotMetadata,
    FileRisk,
    Issue,
    ProjectRiskSummary,
    ProjectIssuesSummary,
)

def create_test_snapshot(project_name, files):
    """Helper to create a valid ProjectSnapshot for testing."""
    high_risk_files = sum(1 for f in files if f.risk and f.risk.level == 'high')
    return ProjectSnapshot(
        metadata=SnapshotMetadata(
            version="1.0",
            timestamp=datetime.now(timezone.utc),
            project_name=project_name,
            file_count=len(files),
            total_size=100,
            tool_version="0.1.0",
            config_hash="dummy_hash"
        ),
        files=files,
        risk_summary=ProjectRiskSummary(
            avg_risk=0.5,
            high_risk_files=high_risk_files,
            medium_risk_files=0,
            low_risk_files=len(files) - high_risk_files
        ),
        issues_summary=ProjectIssuesSummary(
            total_issues=0, by_severity={}, by_rule={}
        )
    )

def test_regression_warning_appears_in_ci_reasons():
    """
    Verify that a regression warning is included in the CI policy evaluation reasons,
    but does not cause the build to fail by default.
    """
    # 1. Arrange: Create two snapshots where the second one has a clear regression.
    # 0 high risk files
    old_snapshot = create_test_snapshot("ci-regression-test", [
        FileSnapshot(path="a.py", language="python", risk=FileRisk(risk_score=0.2, level="low")),
    ])
    # 3 high risk files
    new_snapshot = create_test_snapshot("ci-regression-test", [
        FileSnapshot(path="a.py", language="python", risk=FileRisk(risk_score=0.9, level="high")),
        FileSnapshot(path="b.py", language="python", risk=FileRisk(risk_score=0.9, level="high")),
        FileSnapshot(path="c.py", language="python", risk=FileRisk(risk_score=0.9, level="high")),
    ])

    # 2. Act: Generate diff, detect regressions, and evaluate CI policy.
    project_diff, _ = diff_project_snapshots(old_snapshot, new_snapshot, "v1", "v2")

    # The number of high risk files went from 0 to 3, so the delta is 3.
    assert project_diff.high_risk_files_delta == 3

    # Configure regression thresholds to be triggered
    history_config = HistoryConfig()
    history_config.regression_thresholds.max_high_risk_delta = 2 # Trigger if delta > 2

    warnings = detect_regressions(project_diff, history_config)
    assert len(warnings) == 1

    regression_summary = RegressionSummaryView(warnings=warnings)

    # Dummy project summary for the *new* snapshot and a non-blocking CI config
    project_summary = ReportProjectSummary(
        total_files=3, high_risk_files=3, medium_risk_files=0, low_risk_files=0,
        total_issues=0, error_issues=0, warning_issues=0, info_issues=0,
        top_rules=[], top_risky_files=[], languages=['python'], files_per_language={'python': 3}
    )
    # Set high thresholds so only the regression warning is triggered
    ci_config = CIPolicyConfig(enabled=True, max_high_risk_files=10, max_error_issues=10)

    should_fail, reasons = evaluate_ci_policy(project_summary, ci_config, regression_summary)

    # 3. Assert: Check the policy evaluation results.
    assert not should_fail, "Regression warning should not fail the build by default."
    assert len(reasons) == 1
    # Check for the correct delta in the message
    assert "High risk files increased by 3" in reasons[0]
    assert "(threshold: >2)" in reasons[0]
