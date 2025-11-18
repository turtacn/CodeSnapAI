from codesage.llm.prompts import build_issue_prompt
from codesage.snapshot.models import (
    Issue,
    IssueLocation,
    FileSnapshot,
    ProjectSnapshot,
    SnapshotMetadata,
)
from codesage.config.llm import LLMConfig
import pytest

@pytest.fixture
def mock_issue():
    return Issue(
        rule_id="test-rule",
        severity="warning",
        message="This is a test issue",
        location=IssueLocation(file_path="test.py", line=10),
    )

@pytest.fixture
def mock_file_snapshot(tmp_path):
    d = tmp_path / "sub"
    d.mkdir()
    p = d / "test.py"
    p.write_text("print('hello')\n" * 20)
    return FileSnapshot(
        path=str(p),
        language="python",
    )

@pytest.fixture
def mock_project_snapshot():
    return ProjectSnapshot(
        metadata=SnapshotMetadata(
            project_name="test-project",
            version="1.0",
            timestamp="2023-01-01T00:00:00",
            file_count=1,
            total_size=0,
            tool_version="0.1.0",
            config_hash="abc",
        ),
        files=[],
    )

@pytest.fixture
def mock_llm_config():
    return LLMConfig(max_code_context_lines=10)


def test_build_issue_prompt_contains_expected_info(
    mock_issue, mock_file_snapshot, mock_project_snapshot, mock_llm_config
):
    prompt = build_issue_prompt(
        mock_issue, mock_file_snapshot, mock_project_snapshot, mock_llm_config
    )

    assert "test-project" in prompt
    assert "test.py" in prompt
    assert "10" in prompt
    assert "test-rule" in prompt
    assert "warning" in prompt
    assert "This is a test issue" in prompt
    assert "print('hello')" in prompt
