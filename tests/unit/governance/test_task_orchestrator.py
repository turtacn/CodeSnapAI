from datetime import datetime
from codesage.governance.task_orchestrator import TaskOrchestrator
from codesage.governance.task_models import (
    GovernancePlan,
    GovernanceTask,
    GovernanceTaskGroup,
)

def create_mock_plan() -> GovernancePlan:
    return GovernancePlan(
        project_name="test_project",
        created_at=datetime.now(),
        summary={},
        groups=[
            GovernanceTaskGroup(
                id="group1",
                name="group1",
                group_by="rule",
                tasks=[
                    GovernanceTask(
                        id="task1",
                        file_path="test.py",
                        language="python",
                        rule_id="rule1",
                        description="test",
                        priority=1,
                        risk_level="high",
                    ),
                    GovernanceTask(
                        id="task2",
                        file_path="test.go",
                        language="go",
                        rule_id="rule2",
                        description="test",
                        priority=2,
                        risk_level="medium",
                    ),
                ],
            )
        ],
    )


def test_orchestrator_filter_by_language_and_rule():
    plan = create_mock_plan()
    orchestrator = TaskOrchestrator(plan)

    tasks = orchestrator.select_tasks(language="python", rule_ids=["rule1"])
    assert len(tasks) == 1
    assert tasks[0].id == "task1"


def test_orchestrator_batching():
    plan = create_mock_plan()
    orchestrator = TaskOrchestrator(plan)

    # Add more tasks for batching test
    for i in range(10):
        plan.groups[0].tasks.append(
            GovernanceTask(
                id=f"task_extra_{i}",
                file_path="test.py",
                language="python",
                rule_id="rule_extra",
                description="test",
                priority=3,
                risk_level="low",
            )
        )

    orchestrator = TaskOrchestrator(plan)
    tasks = orchestrator.select_tasks(limit=5)
    assert len(tasks) == 5
