from __future__ import annotations
import pytest
from codesage.snapshot.models import ProjectSnapshot, FileSnapshot, FileRisk, Issue, IssueLocation
from codesage.report.summary_models import ReportProjectSummary


def test_project_summary_basic_aggregation():
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
                risk=FileRisk(risk_score=0.8, level="high", factors=[]),
                issues=[
                    Issue(rule_id="E001", severity="error", message="Error 1", location=IssueLocation(file_path="file1.py", line=10)),
                    Issue(rule_id="W001", severity="warning", message="Warning 1", location=IssueLocation(file_path="file1.py", line=20)),
                ],
            ),
            FileSnapshot(
                path="file2.py",
                language="python",
                risk=FileRisk(risk_score=0.4, level="low", factors=[]),
                issues=[
                    Issue(rule_id="W002", severity="warning", message="Warning 2", location=IssueLocation(file_path="file2.py", line=30)),
                ],
            ),
        ],
    )

    from codesage.report.generator import ReportGenerator
    project_summary, _ = ReportGenerator.from_snapshot(snapshot)

    assert project_summary.total_files == 2
    assert project_summary.high_risk_files == 1
    assert project_summary.low_risk_files == 1
    assert project_summary.total_issues == 3
    assert project_summary.error_issues == 1
    assert project_summary.warning_issues == 2
