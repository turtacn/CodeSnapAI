from codesage.snapshot.models import ProjectSnapshot, SnapshotMetadata
from codesage.report.summary_models import ReportProjectSummary
from codesage.web.api_models import ApiProjectSummary
import datetime

def test_project_summary_view_model_from_snapshot():
    snapshot = ProjectSnapshot(
        metadata=SnapshotMetadata(
            project_name="test-project",
            version="1.0",
            timestamp=datetime.datetime.now(),
            file_count=1,
            total_size=100,
            tool_version="0.1.0",
            config_hash="dummy"
        ),
        files=[],
    )
    report_summary = ReportProjectSummary(
        total_files=1,
        high_risk_files=1,
        medium_risk_files=0,
        low_risk_files=0,
        total_issues=5,
        error_issues=1,
        warning_issues=2,
        info_issues=2,
        top_rules=[],
        top_risky_files=[],
        languages=["python"],
        files_per_language={"python": 1}
    )

    api_summary = ApiProjectSummary(
        project_name=snapshot.metadata.project_name,
        total_files=len(snapshot.files),
        languages=snapshot.languages,
        files_per_language=snapshot.language_stats,
        high_risk_files=report_summary.high_risk_files,
        total_issues=report_summary.total_issues,
    )

    assert api_summary.project_name == "test-project"
    assert api_summary.high_risk_files == 1
    assert api_summary.total_issues == 5
