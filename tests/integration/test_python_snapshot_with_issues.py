from pathlib import Path
import pytest

from codesage.semantic_digest.python_snapshot_builder import PythonSemanticSnapshotBuilder, SnapshotConfig


@pytest.fixture
def complex_project_path():
    # Assuming this fixture is still available from previous tests
    return Path("tests/fixtures/complex_project")


def test_python_snapshot_with_issues(complex_project_path):
    builder = PythonSemanticSnapshotBuilder(complex_project_path, SnapshotConfig())
    # Manually set a high complexity to trigger the rule
    builder.rules_config.max_cyclomatic_threshold = 5
    snapshot = builder.build()

    assert snapshot.issues_summary is not None
    assert snapshot.issues_summary.total_issues > 0
    assert snapshot.issues_summary.by_rule["PY_HIGH_CYCLOMATIC_FUNCTION"] > 0

    complex_file_snapshot = next(
        (f for f in snapshot.files if "complex.py" in f.path), None
    )

    assert complex_file_snapshot is not None
    assert len(complex_file_snapshot.issues) > 0

    issue_ids = [issue.rule_id for issue in complex_file_snapshot.issues]
    assert "PY_HIGH_CYCLOMATIC_FUNCTION" in issue_ids
