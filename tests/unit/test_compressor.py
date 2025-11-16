import pytest
from codesage.snapshot.compressor import SnapshotCompressor
from codesage.snapshot.models import (
    ProjectSnapshot,
    FileSnapshot,
    ASTSummary,
    ComplexityMetrics,
    SnapshotMetadata,
)
from codesage.analyzers.ast_models import ASTNode, FunctionNode
from datetime import datetime


@pytest.fixture
def project_snapshot():
    """Provides a ProjectSnapshot instance with various files for testing."""
    return ProjectSnapshot(
        metadata=SnapshotMetadata(
            version="v1", timestamp=datetime.now(), tool_version="0.1.0", config_hash="abc"
        ),
        files=[
            FileSnapshot(
                path="src/main.py", language="python", hash="h1", lines=100,
                ast_summary=ASTSummary(function_count=5, class_count=2, import_count=10, comment_lines=20),
                complexity_metrics=ComplexityMetrics(),
            ),
            FileSnapshot(
                path="src/main_test.py", language="python", hash="h2", lines=50,
                ast_summary=ASTSummary(function_count=2, class_count=0, import_count=3, comment_lines=5),
                complexity_metrics=ComplexityMetrics(),
            ),
            FileSnapshot(
                path="data/large_file.py", language="python", hash="h3", lines=1500,
                ast_summary=ASTSummary(function_count=50, class_count=10, import_count=25, comment_lines=100),
                complexity_metrics=ComplexityMetrics(),
            ),
        ],
        global_metrics={}, dependency_graph={}, detected_patterns=[], issues=[]
    )

def test_exclude_test_files(project_snapshot):
    """Tests that test files are correctly excluded based on patterns."""
    config = {"compression": {"exclude_patterns": ["*_test.py"]}}
    compressor = SnapshotCompressor(config)
    compressed_snapshot = compressor.compress(project_snapshot)
    assert len(compressed_snapshot.files) == 2
    assert "src/main_test.py" not in [f.path for f in compressed_snapshot.files]

def test_trim_large_asts(project_snapshot):
    """Tests that the AST of large files is trimmed."""
    # Create a mock AST for the large file
    large_file = next(f for f in project_snapshot.files if f.path == "data/large_file.py")

    # Create a complex AST structure to test trimming
    func_with_body = FunctionNode(node_type="function", name="func1", complexity=5)
    func_with_body.children.append(ASTNode(node_type="statement", value="..."))
    large_file.ast_summary = func_with_body

    config = {"compression": {"trimming_threshold": 1200}}
    compressor = SnapshotCompressor(config)
    compressed_snapshot = compressor.compress(project_snapshot)

    trimmed_file = next(f for f in compressed_snapshot.files if f.path == "data/large_file.py")

    # Assert that the function body (children) has been removed
    assert not trimmed_file.ast_summary.children

def test_no_trimming_for_small_files(project_snapshot):
    """Tests that small files are not trimmed."""
    small_file = next(f for f in project_snapshot.files if f.path == "src/main.py")

    func_with_body = FunctionNode(node_type="function", name="func2", complexity=3)
    func_with_body.children.append(ASTNode(node_type="statement", value="..."))
    small_file.ast_summary = func_with_body

    config = {"compression": {"trimming_threshold": 1200}}
    compressor = SnapshotCompressor(config)
    compressed_snapshot = compressor.compress(project_snapshot)

    untrimmed_file = next(f for f in compressed_snapshot.files if f.path == "src/main.py")
    assert untrimmed_file.ast_summary.children
