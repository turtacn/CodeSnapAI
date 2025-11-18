from datetime import datetime, timedelta, timezone
import yaml
from pathlib import Path

from codesage.config.history import HistoryConfig
from codesage.history.models import HistoricalSnapshot, SnapshotIndex, SnapshotMeta
from codesage.history.store import (
    save_historical_snapshot,
    load_historical_snapshot,
    load_snapshot_index,
    update_snapshot_index
)
from codesage.snapshot.models import ProjectSnapshot, SnapshotMetadata


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


def test_snapshot_meta_and_index_roundtrip(tmp_path: Path):
    project_name = "test-project"
    index_file = tmp_path / project_name / "index.yaml"
    index_file.parent.mkdir()

    metas = [
        SnapshotMeta(project_name=project_name, snapshot_id=f"id_{i}", created_at=datetime.now(timezone.utc) - timedelta(days=i))
        for i in range(3)
    ]

    # Test update_snapshot_index
    for meta in reversed(metas):
        update_snapshot_index(tmp_path, meta, max_snapshots=5)

    # Test load_snapshot_index
    index = load_snapshot_index(tmp_path, project_name)
    assert index.project_name == project_name
    assert len(index.items) == 3
    assert index.items[0].snapshot_id == "id_0"
    assert index.items[2].snapshot_id == "id_2"


def test_save_and_load_historical_snapshot(tmp_path: Path):
    project_name = "test-project"
    snapshot_id = "test-snapshot"
    config = HistoryConfig()

    meta = SnapshotMeta(project_name=project_name, snapshot_id=snapshot_id)
    snapshot = create_test_snapshot(project_name, [])
    hs = HistoricalSnapshot(meta=meta, snapshot=snapshot)

    # Save
    save_historical_snapshot(tmp_path, hs, config)

    # Load
    loaded_hs = load_historical_snapshot(tmp_path, project_name, snapshot_id)

    assert loaded_hs.meta.snapshot_id == snapshot_id
    assert loaded_hs.snapshot.metadata.project_name == project_name
