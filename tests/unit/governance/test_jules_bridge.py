import os
from pathlib import Path
import pytest
from codesage.governance.jules_bridge import build_jules_task_view
from codesage.governance.task_models import GovernanceTask
from codesage.snapshot.models import ProjectSnapshot, SnapshotMetadata

@pytest.fixture
def temp_file(tmp_path: Path) -> str:
    file_path = tmp_path / "test.py"
    file_path.write_text("def hello():\n    print('hello')\n")
    return str(file_path)

def test_jules_task_view_contains_minimal_context(temp_file: str):
    task = GovernanceTask(
        id="test_task",
        project_name="test",
        file_path=temp_file,
        language="python",
        rule_id="test_rule",
        description="test issue",
        priority=1,
        risk_level="high",
        llm_hint="test hint",
        metadata={"line": 2, "symbol": "hello"},
    )

    snapshot = ProjectSnapshot(
        metadata=SnapshotMetadata(
            version="1.0",
            timestamp="2023-01-01T00:00:00Z",
            project_name="test",
            file_count=1,
            total_size=1,
            tool_version="1.0",
            config_hash="abc",
        ),
        files=[],
    )

    view = build_jules_task_view(task, snapshot, 10)

    assert view.file_path == temp_file
    assert view.function_name == "hello"
    assert "test issue" in view.issue_message
    assert "test hint" in view.llm_hint
    assert "hello" in view.code_snippet


def test_jules_task_view_respects_context_limit(temp_file: str):
    # Overwrite temp_file with more content
    long_content = "\\n".join([f"line {i}" for i in range(20)])
    Path(temp_file).write_text(long_content)

    task = GovernanceTask(
        id="test_task",
        project_name="test",
        file_path=temp_file,
        language="python",
        rule_id="test_rule",
        description="test issue",
        priority=1,
        risk_level="high",
        metadata={"line": 10},
    )
    snapshot = ProjectSnapshot(
        metadata=SnapshotMetadata(
            version="1.0",
            timestamp="2023-01-01T00:00:00Z",
            project_name="test",
            file_count=1,
            total_size=1,
            tool_version="1.0",
            config_hash="abc",
        ),
        files=[],
    )

    view = build_jules_task_view(task, snapshot, 5)

    # The snippet should be around 5 lines, not 20
    assert len(view.code_snippet.splitlines()) <= 7  # A bit of leeway
