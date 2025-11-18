import pytest
from pathlib import Path
from codesage.semantic_digest.python_snapshot_builder import PythonSemanticSnapshotBuilder, SnapshotConfig

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "complex_project"


def test_python_snapshot_builder_with_issues():
    builder = PythonSemanticSnapshotBuilder(FIXTURE_DIR, SnapshotConfig())
    project_snapshot = builder.build()

    assert project_snapshot is not None
    assert project_snapshot.issues_summary is not None
    assert project_snapshot.issues_summary.total_issues > 0

    high_complexity_issue_found = False
    for file in project_snapshot.files:
        for issue in file.issues:
            if issue.rule_id == "PY_HIGH_CYCLOMATIC_FUNCTION":
                high_complexity_issue_found = True
                break
        if high_complexity_issue_found:
            break

    assert high_complexity_issue_found, "Expected to find at least one high complexity issue"
