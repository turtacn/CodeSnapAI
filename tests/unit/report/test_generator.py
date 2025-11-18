from __future__ import annotations
import pytest
from codesage.snapshot.models import ProjectSnapshot, FileSnapshot, FileRisk, Issue, IssueLocation, FileMetrics
from codesage.report.generator import ReportGenerator


def test_report_generator_from_snapshot():
    snapshot = ProjectSnapshot(
        metadata={
            "version": "1.0",
            "timestamp": "2023-01-01T00:00:00",
            "project_name": "test",
            "file_count": 2,
            "total_size": 1024,
            "tool_version": "0.1.0",
            "config_hash": "abc"
        },
        files=[
            FileSnapshot(
                path="file1.py",
                language="python",
                metrics=FileMetrics(lines_of_code=100, num_functions=5),
                risk=FileRisk(risk_score=0.8, level="high", factors=[]),
                issues=[
                    Issue(rule_id="E001", severity="error", message="Error 1", location=IssueLocation(file_path="file1.py", line=10)),
                    Issue(rule_id="W001", severity="warning", message="Warning 1", location=IssueLocation(file_path="file1.py", line=20)),
                ],
            ),
            FileSnapshot(
                path="file2.py",
                language="python",
                metrics=FileMetrics(lines_of_code=50, num_functions=2),
                risk=FileRisk(risk_score=0.4, level="low", factors=[]),
                issues=[
                    Issue(rule_id="W002", severity="warning", message="Warning 2", location=IssueLocation(file_path="file2.py", line=30)),
                ],
            ),
        ],
    )

    project_summary, file_summaries = ReportGenerator.from_snapshot(snapshot)

    assert project_summary.total_files == 2
    assert project_summary.high_risk_files == 1
    assert project_summary.low_risk_files == 1
    assert project_summary.total_issues == 3
    assert project_summary.error_issues == 1
    assert project_summary.warning_issues == 2

    assert len(file_summaries) == 2

    assert file_summaries[0].path == "file1.py"
    assert file_summaries[0].risk_level == "high"
    assert file_summaries[0].risk_score == 0.8
    assert file_summaries[0].loc == 100
    assert file_summaries[0].num_functions == 5
    assert file_summaries[0].issues_total == 2
    assert file_summaries[0].issues_error == 1
    assert file_summaries[0].issues_warning == 1

    assert file_summaries[1].path == "file2.py"
    assert file_summaries[1].risk_level == "low"
    assert file_summaries[1].risk_score == 0.4
    assert file_summaries[1].loc == 50
    assert file_summaries[1].num_functions == 2
    assert file_summaries[1].issues_total == 1
    assert file_summaries[1].issues_error == 0
    assert file_summaries[1].issues_warning == 1
