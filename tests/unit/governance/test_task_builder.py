from datetime import datetime
from codesage.config.governance import GovernanceConfig
from codesage.governance.task_builder import TaskBuilder
from codesage.snapshot.models import (
    ProjectSnapshot,
    FileSnapshot,
    Issue,
    IssueLocation,
    FileRisk,
    SnapshotMetadata,
)

def create_mock_snapshot() -> ProjectSnapshot:
    return ProjectSnapshot(
        metadata=SnapshotMetadata(
            version="1.0",
            timestamp=datetime.now(),
            project_name="test_project",
            file_count=1,
            total_size=100,
            tool_version="1.0",
            config_hash="abc",
        ),
        files=[
            FileSnapshot(
                path="test.py",
                language="python",
                risk=FileRisk(risk_score=0.8, level="high", factors=[]),
                issues=[
                    Issue(
                        rule_id="rule1",
                        severity="error",
                        message="error message",
                        location=IssueLocation(file_path="test.py", line=10),
                    ),
                    Issue(
                        rule_id="rule2",
                        severity="warning",
                        message="warning message",
                        location=IssueLocation(file_path="test.py", line=20),
                    ),
                ],
            ),
            FileSnapshot(
                path="test2.py",
                language="python",
                risk=FileRisk(risk_score=0.4, level="low", factors=[]),
                issues=[
                    Issue(
                        rule_id="rule1",
                        severity="error",
                        message="error message",
                        location=IssueLocation(file_path="test2.py", line=10),
                    ),
                ],
            )
        ],
    )


def test_build_tasks_from_issues_and_risk():
    snapshot = create_mock_snapshot()
    config = GovernanceConfig.default()
    builder = TaskBuilder(config)
    plan = builder.build_plan(snapshot)

    assert plan.summary["total_tasks"] == 3

    high_priority_task_found = False
    for group in plan.groups:
        for task in group.tasks:
            if task.file_path == "test.py" and task.metadata["severity"] == "error":
                assert task.priority == 1
                high_priority_task_found = True

    assert high_priority_task_found


def test_task_builder_respects_max_tasks_per_file():
    snapshot = create_mock_snapshot()
    # Add more issues to the first file
    for i in range(15):
        snapshot.files[0].issues.append(
            Issue(
                rule_id=f"rule_extra_{i}",
                severity="warning",
                message="another message",
                location=IssueLocation(file_path="test.py", line=30 + i),
            )
        )

    config = GovernanceConfig(max_tasks_per_file=5)
    builder = TaskBuilder(config)
    plan = builder.build_plan(snapshot)

    file_task_count = 0
    for group in plan.groups:
        for task in group.tasks:
            if task.file_path == "test.py":
                file_task_count += 1

    assert file_task_count == 5
