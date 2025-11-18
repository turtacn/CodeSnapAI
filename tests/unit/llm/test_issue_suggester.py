from codesage.llm.issue_suggester import IssueSuggester
from codesage.llm.client import DummyLLMClient
from codesage.snapshot.models import (
    ProjectSnapshot,
    FileSnapshot,
    Issue,
    IssueLocation,
    SnapshotMetadata,
)
from codesage.config.llm import LLMConfig
import pytest
from datetime import datetime

@pytest.fixture
def mock_project_snapshot_with_issues(tmp_path):
    p = tmp_path / "test.py"
    p.write_text("print('hello')\n" * 20)
    return ProjectSnapshot(
        metadata=SnapshotMetadata(
            project_name="test-project",
            version="1.0",
            timestamp=datetime(2023, 1, 1, 0, 0, 0),
            file_count=1,
            total_size=0,
            tool_version="0.1.0",
            config_hash="abc",
        ),
        files=[
            FileSnapshot(
                path=str(p),
                language="python",
                issues=[
                    Issue(
                        rule_id="test-rule",
                        severity="warning",
                        message="This is a test issue",
                        location=IssueLocation(file_path=str(p), line=10),
                    ),
                    Issue(
                        rule_id="another-rule",
                        severity="info",
                        message="This is another test issue",
                        location=IssueLocation(file_path=str(p), line=20),
                    ),
                ],
            )
        ],
    )

def test_issue_suggester_enriches_snapshot(mock_project_snapshot_with_issues):
    client = DummyLLMClient()
    config = LLMConfig(filter_severity=["warning"])
    suggester = IssueSuggester(client, config)

    enriched_snapshot = suggester.enrich_with_llm_suggestions(
        mock_project_snapshot_with_issues
    )

    warning_issue = enriched_snapshot.files[0].issues[0]
    info_issue = enriched_snapshot.files[0].issues[1]

    assert warning_issue.llm_status == "succeeded"
    assert warning_issue.llm_fix_hint
    assert warning_issue.llm_rationale
    assert info_issue.llm_status == "not_requested"
    assert enriched_snapshot.llm_stats
    assert enriched_snapshot.llm_stats.total_requests == 1
    assert enriched_snapshot.llm_stats.succeeded == 1
