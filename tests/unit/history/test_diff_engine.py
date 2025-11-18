from datetime import datetime, timezone
from codesage.history.diff_engine import diff_project_snapshots
from codesage.snapshot.models import ProjectSnapshot, FileSnapshot, SnapshotMetadata, FileRisk, Issue

def create_test_snapshot(project_name, files):
    return ProjectSnapshot(
        metadata=SnapshotMetadata(
            version="1.0",
            timestamp=datetime.now(timezone.utc),
            project_name=project_name,
            file_count=len(files),
            total_size=100,
            tool_version="0.1.0",
            config_hash="dummy_hash"
        ),
        files=files
    )

def test_project_diff_metrics_and_risk():
    old_snapshot = create_test_snapshot("test", [
        FileSnapshot(path="a.py", language="python", risk=FileRisk(risk_score=0.2, level="low"), issues=[]),
        FileSnapshot(path="b.py", language="python", risk=FileRisk(risk_score=0.8, level="high"), issues=[]),
        FileSnapshot(path="c.py", language="python", risk=FileRisk(risk_score=0.5, level="medium"), issues=[]),
    ])
    new_snapshot = create_test_snapshot("test", [
        FileSnapshot(path="a.py", language="python", risk=FileRisk(risk_score=0.9, level="high"), issues=[]), # Risk increased
        FileSnapshot(path="b.py", language="python", risk=FileRisk(risk_score=0.1, level="low"), issues=[]),  # Risk decreased
        # c.py removed
        FileSnapshot(path="d.py", language="python", risk=FileRisk(risk_score=0.6, level="medium"), issues=[]), # New file
    ])

    summary, files = diff_project_snapshots(old_snapshot, new_snapshot, "v1", "v2")

    assert summary.high_risk_files_delta == 0  # 1 high risk file in both
    assert files[0].path == "a.py" and files[0].status == "modified"
    assert files[1].path == "b.py" and files[1].status == "modified"
    assert files[2].path == "c.py" and files[2].status == "removed"
    assert files[3].path == "d.py" and files[3].status == "added"


def test_issue_additions_and_removals():
    old_snapshot = create_test_snapshot("test",
        [FileSnapshot(path="a.py", language="python", issues=[Issue(id="123", rule_id="R1", severity="error", message="m", location={"file_path": "a.py", "line": 1})])]
    )
    new_snapshot = create_test_snapshot("test",
        [FileSnapshot(path="a.py", language="python", issues=[Issue(id="456", rule_id="R2", severity="error", message="m", location={"file_path": "a.py", "line": 1})])]
    )

    _, files = diff_project_snapshots(old_snapshot, new_snapshot, "v1", "v2")

    file_diff = files[0]
    assert file_diff.path == "a.py"
    assert file_diff.issues_added == 1
    assert file_diff.issues_resolved == 1
