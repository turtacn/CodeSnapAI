from codesage.config.history import HistoryConfig
from codesage.history.diff_models import ProjectDiffSummary
from codesage.history.regression_detector import detect_regressions


def test_regression_warning_on_high_risk_delta():
    diff = ProjectDiffSummary(
        project_name="test",
        from_snapshot_id="v1",
        to_snapshot_id="v2",
        high_risk_files_delta=10,
        total_issues_delta=0,
        error_issues_delta=0,
    )
    config = HistoryConfig()
    config.regression_thresholds.max_high_risk_delta = 5

    warnings = detect_regressions(diff, config)
    assert len(warnings) == 1
    assert warnings[0].id == "high_risk_files_increase"
    assert warnings[0].severity == "warning"


def test_regression_warning_on_error_issues_delta():
    diff = ProjectDiffSummary(
        project_name="test",
        from_snapshot_id="v1",
        to_snapshot_id="v2",
        high_risk_files_delta=0,
        total_issues_delta=20,
        error_issues_delta=15,
    )
    config = HistoryConfig()
    config.regression_thresholds.max_error_issues_delta = 10

    warnings = detect_regressions(diff, config)
    assert len(warnings) == 1
    assert warnings[0].id == "error_issues_increase"
    assert warnings[0].severity == "error"
