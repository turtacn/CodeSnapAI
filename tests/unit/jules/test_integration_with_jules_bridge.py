import pytest
from codesage.config.jules import JulesPromptConfig
from codesage.governance.task_models import GovernanceTask
from codesage.snapshot.models import ProjectSnapshot, FileSnapshot
from codesage.governance.jules_bridge import build_view_and_template_for_task

@pytest.fixture
def sample_task() -> GovernanceTask:
    """Provides a sample GovernanceTask for testing."""
    return GovernanceTask(
        id="test_task",
        rule_id="PY_HIGH_CYCLOMATIC_FUNCTION",
        language="python",
        description="High complexity",
        file_path="test.py",
        llm_hint="A hint",
        priority=1,
        risk_level="low",
        status="pending",
        metadata={"line": 5, "symbol": "my_func", "start_line": 1, "end_line": 10},
    )

from datetime import datetime
from codesage.snapshot.models import SnapshotMetadata, DependencyGraph

@pytest.fixture
def sample_snapshot(tmp_path) -> ProjectSnapshot:
    """Provides a sample ProjectSnapshot for testing."""
    file_path = tmp_path / "test.py"
    file_path.write_text("def my_func():\n    pass")
    return ProjectSnapshot(
        metadata=SnapshotMetadata(
            version="1.0",
            timestamp=datetime.now(),
            project_name="test_project",
            file_count=1,
            total_size=0,
            tool_version="0.1.0",
            config_hash="abc"
        ),
        files=[FileSnapshot(path=str(file_path), language="python", metrics={})],
        dependencies=DependencyGraph()
    )

def test_jules_prompt_from_task_view(sample_task: GovernanceTask, sample_snapshot: ProjectSnapshot):
    """
    Tests the integration of building a JulesTaskView and selecting a template.
    """
    config = JulesPromptConfig.default()
    view, template = build_view_and_template_for_task(sample_task, sample_snapshot, config)

    assert view is not None
    assert template is not None

    assert view.file_path == "test.py"
    assert view.function_name == "my_func"
    assert view.llm_hint == "A hint"

    assert template.id == "high_complexity_refactor"
