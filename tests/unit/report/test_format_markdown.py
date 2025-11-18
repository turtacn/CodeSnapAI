from __future__ import annotations
from codesage.report.summary_models import ReportProjectSummary, ReportFileSummary
from codesage.report.format_markdown import render_markdown


def test_markdown_contains_key_sections():
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
    )
    file_summaries = [
        ReportFileSummary(
            path="file1.py",
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

    md_report = render_markdown(project_summary, file_summaries)

    assert "# CodeSnapAI Project Analysis Report" in md_report
    assert "## Project Overview" in md_report
    assert "## Top Risky Files" in md_report
    assert "## Top Rules Triggered" in md_report
    assert "file1.py" in md_report
