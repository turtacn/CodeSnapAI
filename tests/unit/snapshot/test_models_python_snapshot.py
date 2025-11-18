import pytest
from datetime import datetime, timezone
from codesage.snapshot.models import (
    FileMetrics,
    FileSnapshot,
    ProjectSnapshot,
    SnapshotMetadata,
    DependencyGraph,
)

def test_file_metrics_basic_fields():
    metrics = FileMetrics(
        num_classes=2,
        num_functions=3,
        num_methods=5,
        has_async=True,
        uses_type_hints=True,
    )
    assert metrics.num_classes == 2
    assert metrics.num_functions == 3
    assert metrics.num_methods == 5
    assert metrics.has_async is True
    assert metrics.uses_type_hints is True

def test_project_snapshot_structure():
    metadata = SnapshotMetadata(
        version="1.0",
        timestamp=datetime.now(timezone.utc),
        project_name="test-project",
        file_count=2,
        total_size=1024,
        tool_version="0.1.0",
        config_hash="dummy_hash",
    )
    files = [
        FileSnapshot(
            path="test.py",
            language="python",
            metrics=FileMetrics(),
            symbols={},
        ),
        FileSnapshot(
            path="test2.py",
            language="python",
            metrics=FileMetrics(),
            symbols={},
        ),
    ]
    dependencies = DependencyGraph(internal=[], external=[])

    snapshot = ProjectSnapshot(
        metadata=metadata,
        files=files,
        dependencies=dependencies,
    )

    assert snapshot.metadata.version == "1.0"
    assert len(snapshot.files) == 2
    assert snapshot.dependencies.internal == []
    assert snapshot.dependencies.external == []

    snapshot_dict = snapshot.model_dump()
    assert "metadata" in snapshot_dict
    assert "files" in snapshot_dict
    assert "dependencies" in snapshot_dict
