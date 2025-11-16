import pytest
from codesage.snapshot.differ import SnapshotDiffer, FileChange
from codesage.snapshot.models import (
    ProjectSnapshot,
    FileSnapshot,
    ASTSummary,
    ComplexityMetrics,
    SnapshotMetadata,
    DependencyGraph,
)
from datetime import datetime

@pytest.fixture
def base_snapshot():
    """Provides a base snapshot with complexity and dependency data."""
    return ProjectSnapshot(
        metadata=SnapshotMetadata(version="v1", timestamp=datetime.now(), tool_version="0.1.0", config_hash="abc",
                                project_name="test", file_count=2, total_size=30),
        files=[
            FileSnapshot(
                path="a.py", hash="hash_a", language="python", lines=10,
                ast_summary=ASTSummary(function_count=1, class_count=0, import_count=1, comment_lines=2),
                complexity_metrics=ComplexityMetrics(cyclomatic=5),
            ),
            FileSnapshot(
                path="b.py", hash="hash_b", language="python", lines=20,
                ast_summary=ASTSummary(function_count=2, class_count=1, import_count=3, comment_lines=5),
                complexity_metrics=ComplexityMetrics(cyclomatic=10),
            ),
        ],
        global_metrics={},
        dependency_graph=DependencyGraph(edges=[("a.py", "b.py")]),
        detected_patterns=[], issues=[]
    )

@pytest.fixture
def modified_snapshot():
    """Provides a modified snapshot with changes to complexity and dependencies."""
    return ProjectSnapshot(
        metadata=SnapshotMetadata(version="v2", timestamp=datetime.now(), tool_version="0.1.0", config_hash="abc",
                                project_name="test", file_count=2, total_size=55),
        files=[
            FileSnapshot( # Modified complexity
                path="b.py", hash="hash_b_new", language="python", lines=25,
                ast_summary=ASTSummary(function_count=2, class_count=1, import_count=4, comment_lines=6),
                complexity_metrics=ComplexityMetrics(cyclomatic=15),
            ),
            FileSnapshot( # Added file
                path="c.py", hash="hash_c", language="python", lines=30,
                ast_summary=ASTSummary(function_count=3, class_count=0, import_count=2, comment_lines=8),
                complexity_metrics=ComplexityMetrics(cyclomatic=8),
            ),
        ],
        global_metrics={},
        dependency_graph=DependencyGraph(edges=[("b.py", "c.py")]), # Changed dependency
        detected_patterns=[], issues=[]
    )

def test_calculate_complexity_delta(base_snapshot, modified_snapshot):
    """Tests that the complexity delta is correctly calculated for modified files."""
    differ = SnapshotDiffer()
    diff = differ.diff(base_snapshot, modified_snapshot)

    modified_file_change = next(f for f in diff.modified_files if f.path == "b.py")
    assert modified_file_change.complexity_delta == 5 # 15 - 10

def test_compare_dependencies(base_snapshot, modified_snapshot):
    """Tests that changes in dependencies are correctly identified."""
    differ = SnapshotDiffer()
    diff = differ.diff(base_snapshot, modified_snapshot)

    assert diff.dependency_changes.added_edges == [("b.py", "c.py")]
    assert diff.dependency_changes.removed_edges == [("a.py", "b.py")]

def test_no_changes(base_snapshot):
    """Tests that no changes are detected when comparing identical snapshots."""
    differ = SnapshotDiffer()
    snapshot_clone = base_snapshot.model_copy(deep=True)
    diff = differ.diff(base_snapshot, snapshot_clone)

    assert not diff.added_files
    assert not diff.removed_files
    assert not diff.modified_files
    assert not diff.dependency_changes.added_edges
    assert not diff.dependency_changes.removed_edges
