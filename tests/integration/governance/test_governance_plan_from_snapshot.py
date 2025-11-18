from pathlib import Path
import pytest
from codesage.config.governance import GovernanceConfig
from codesage.governance.task_builder import TaskBuilder
from codesage.snapshot.models import ProjectSnapshot
from codesage.utils.file_utils import read_yaml_file

@pytest.fixture
def snapshot_from_file() -> ProjectSnapshot:
    snapshot_path = Path(__file__).parent.parent.parent / "fixtures" / "snapshot_samples" / "governance_test_snapshot.yaml"
    snapshot_data = read_yaml_file(snapshot_path)
    return ProjectSnapshot.model_validate(snapshot_data)


def test_build_governance_plan_from_snapshot_file(snapshot_from_file: ProjectSnapshot):
    config = GovernanceConfig.default()
    builder = TaskBuilder(config)
    plan = builder.build_plan(snapshot_from_file)

    assert plan.summary["total_tasks"] == 2

    # Check that the high-risk, error-severity issue has the highest priority
    top_priority_task = None
    for group in plan.groups:
        for task in group.tasks:
            if top_priority_task is None or task.priority < top_priority_task.priority:
                top_priority_task = task

    assert top_priority_task is not None
    assert top_priority_task.file_path == 'src/main.py'
    assert top_priority_task.rule_id == 'PY_HIGH_CYCLO'
    assert top_priority_task.priority == 1
