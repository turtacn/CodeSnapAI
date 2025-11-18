import pytest
from codesage.snapshot.models import Issue, IssueLocation, ProjectIssuesSummary

def test_issue_serialization_roundtrip():
    location = IssueLocation(file_path="a/b.py", line=10)
    issue = Issue(
        id="test-rule:a/b.py:10",
        rule_id="test-rule",
        severity="warning",
        message="This is a test issue",
        location=location,
        symbol="test_func",
        tags=["test"],
    )

    issue_dict = issue.model_dump()
    issue_from_dict = Issue.model_validate(issue_dict)

    assert issue == issue_from_dict

def test_project_issues_summary_aggregation_fields():
    summary = ProjectIssuesSummary(
        total_issues=10,
        by_severity={"warning": 5, "error": 5},
        by_rule={"rule-1": 7, "rule-2": 3},
    )

    assert summary.total_issues == 10
    assert summary.by_severity["warning"] == 5
    assert summary.by_rule["rule-1"] == 7
