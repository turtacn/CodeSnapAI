from pathlib import Path
import pytest
from codesage.semantic_digest.python_snapshot_builder import PythonSemanticSnapshotBuilder, SnapshotConfig

@pytest.fixture
def complex_project_path():
    return Path("tests/fixtures/complex_project")

def test_python_builder_collects_files(complex_project_path):
    builder = PythonSemanticSnapshotBuilder(complex_project_path, SnapshotConfig())
    snapshot = builder.build()

    file_paths = {f.path for f in snapshot.files}
    assert "models/user.py" in file_paths
    assert "services/user_service.py" in file_paths

def test_python_builder_metrics_counts(complex_project_path):
    builder = PythonSemanticSnapshotBuilder(complex_project_path, SnapshotConfig())
    snapshot = builder.build()

    user_model_snapshot = next(f for f in snapshot.files if f.path == "models/user.py")
    assert user_model_snapshot.metrics.num_classes == 1
    assert user_model_snapshot.metrics.num_functions == 0
    assert user_model_snapshot.metrics.num_methods == 2 # __init__ and get_name

    user_service_snapshot = next(f for f in snapshot.files if f.path == "services/user_service.py")
    assert user_service_snapshot.metrics.num_classes == 1
    assert user_service_snapshot.metrics.num_functions == 1
    assert user_service_snapshot.metrics.num_methods == 2 # __init__ and add_user
    assert user_service_snapshot.metrics.has_async is True
