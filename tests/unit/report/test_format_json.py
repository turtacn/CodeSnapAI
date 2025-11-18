from __future__ import annotations
import json
from codesage.report.summary_models import ReportProjectSummary, ReportFileSummary
from codesage.report.format_json import render_json


def test_json_format_structure():
    project_summary = ReportProjectSummary(
        total_files=1,
        high_risk_files=1,
        medium_risk_files=0,
        low_risk_files=0,
        total_issues=1,
        error_issues=1,
        warning_issues=0,
        info_issues=0,
        top_rules=["E001"],
        top_risky_files=["file1.py"],
        languages=["python"],
        files_per_language={"python": 1},
    )
    file_summaries = [
        ReportFileSummary(
            path="file1.py",
            language="python",
            risk_level="high",
            risk_score=0.8,
            loc=100,
            num_functions=5,
            issues_total=1,
            issues_error=1,
            issues_warning=0,
            top_issue_rules=["E001"],
        )
    ]

    json_report = render_json(project_summary, file_summaries)
    report_data = json.loads(json_report)

    assert "project" in report_data
    assert "files" in report_data
    assert report_data["project"]["total_files"] == 1
    assert len(report_data["files"]) == 1
    assert report_data["files"][0]["path"] == "file1.py"
