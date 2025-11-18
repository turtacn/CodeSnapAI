from pathlib import Path
import pytest
import yaml

from codesage.semantic_digest.python_snapshot_builder import PythonSemanticSnapshotBuilder, SnapshotConfig


@pytest.fixture
def complex_project_path():
    return Path("tests/fixtures/complex_project")


def test_python_snapshot_with_risk(complex_project_path):
    builder = PythonSemanticSnapshotBuilder(complex_project_path, SnapshotConfig())
    snapshot = builder.build()

    assert snapshot.risk_summary is not None
    assert snapshot.risk_summary.avg_risk > 0
    assert snapshot.risk_summary.high_risk_files >= 1

    complex_file_snapshot = next(
        (f for f in snapshot.files if f.path == "complex.py"), None
    )
    assert complex_file_snapshot is not None
    assert complex_file_snapshot.risk is not None
    assert complex_file_snapshot.risk.level == "high"
    assert "high_cyclomatic_complexity" in complex_file_snapshot.risk.factors
