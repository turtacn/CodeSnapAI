from pathlib import Path
from codesage.web.loader import load_snapshot, reload_all
from codesage.snapshot.models import ProjectSnapshot

def test_load_snapshot_from_yaml():
    reload_all()
    snapshot_path = Path("tests/fixtures/snapshot.yaml")
    snapshot = load_snapshot(snapshot_path)
    assert isinstance(snapshot, ProjectSnapshot)
    assert snapshot.metadata.project_name == "test-project"
    assert len(snapshot.files) == 1
    assert snapshot.files[0].path == "a/b/c.py"
