import os
import tempfile
import pytest
from sqlalchemy import create_engine, inspect
from codesage.history.store import StorageEngine
from codesage.history.models import Project, Snapshot, Issue
from codesage.snapshot.models import ProjectSnapshot, ProjectRiskSummary, ProjectIssuesSummary, SnapshotMetadata

@pytest.fixture
def db_url():
    _, path = tempfile.mkstemp()
    url = f"sqlite:///{path}"
    yield url
    os.remove(path)

def test_storage_engine_creation(db_url):
    engine = StorageEngine(db_url)
    assert engine is not None

    # Verify tables exist
    inspector = inspect(engine.engine)
    tables = inspector.get_table_names()
    assert "projects" in tables
    assert "snapshots" in tables
    assert "issues" in tables

def test_save_and_retrieve_snapshot(db_url):
    storage = StorageEngine(db_url)

    # Create a dummy ProjectSnapshot
    metadata = SnapshotMetadata.model_construct(
        project_name="test_project",
        git_commit="abc1234"
    )
    snapshot = ProjectSnapshot.model_construct(
        metadata=metadata,
        files={},
        # risk_summary uses avg_risk now
        risk_summary=ProjectRiskSummary.model_construct(avg_risk=0.5, high_risk_files=1),
        issues_summary=ProjectIssuesSummary.model_construct(total=0, by_severity={})
    )

    # Save
    db_snapshot = storage.save_snapshot("test_project", snapshot)
    assert db_snapshot.id is not None
    assert db_snapshot.project.name == "test_project"

    # Retrieve
    retrieved = storage.get_latest_snapshot("test_project")
    assert retrieved is not None
    assert retrieved.id == db_snapshot.id
    assert retrieved.commit_hash == "abc1234"

def test_save_snapshot_with_issues(db_url):
    storage = StorageEngine(db_url)

    metadata = SnapshotMetadata.model_construct(project_name="issue_project", git_commit="def5678")

    # Mock file with issues
    # We need to mock the structure expected by store.py
    # store.py expects snapshot.files to be a dict where values have 'issues' attribute

    class MockIssue:
        def __init__(self, line, severity, message):
            self.line = line
            self.severity = severity
            self.message = message
            self.category = "test-rule"

    class MockFileSnapshot:
        def __init__(self):
            self.issues = [MockIssue(10, "high", "Fix me")]

    # Use model_construct to bypass validation for missing fields
    snapshot_constructed = ProjectSnapshot.model_construct(
        metadata=metadata,
        files={"main.py": MockFileSnapshot()},
        risk_summary=ProjectRiskSummary.model_construct(avg_risk=0.1, high_risk_files=1),
        issues_summary=ProjectIssuesSummary.model_construct(total=1, by_severity={'high': 1})
    )

    db_snapshot = storage.save_snapshot("issue_project", snapshot_constructed)

    session = storage.get_session()
    issues = session.query(Issue).filter_by(snapshot_id=db_snapshot.id).all()
    assert len(issues) == 1
    assert issues[0].file_path == "main.py"
    assert issues[0].description == "Fix me"
