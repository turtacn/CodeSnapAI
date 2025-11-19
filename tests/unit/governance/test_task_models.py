from datetime import datetime
from codesage.governance.task_models import (
    GovernanceTask,
    GovernanceTaskGroup,
    GovernancePlan,
)


def test_governance_task_minimal_fields():
    task = GovernanceTask(
        id="test",
        project_name="test_project",
        file_path="test.py",
        language="python",
        rule_id="test_rule",
        description="test",
        priority=1,
        risk_level="high",
    )
    assert task.status == "pending"
    assert task.model_dump_json() is not None


def test_governance_plan_grouping():
    task1 = GovernanceTask(
        id="test1",
        project_name="test_project",
        file_path="test.py",
        language="python",
        rule_id="test_rule",
        description="test",
        priority=1,
        risk_level="high",
    )
    task2 = GovernanceTask(
        id="test2",
        project_name="test_project",
        file_path="test.py",
        language="python",
        rule_id="test_rule",
        description="test",
        priority=1,
        risk_level="high",
    )
    group = GovernanceTaskGroup(
        id="test_group",
        name="test_group",
        group_by="rule",
        tasks=[task1, task2],
    )
    plan = GovernancePlan(
        project_name="test_project",
        created_at=datetime.now(),
        summary={},
        groups=[group],
    )
    assert len(plan.groups) == 1
    assert len(plan.groups[0].tasks) == 2
