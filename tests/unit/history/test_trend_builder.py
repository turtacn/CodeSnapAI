from datetime import datetime, timedelta, timezone
from pathlib import Path
from codesage.config.history import HistoryConfig
from codesage.history.models import HistoricalSnapshot, SnapshotMeta
from codesage.history.store import save_historical_snapshot, update_snapshot_index
from codesage.history.trend_builder import build_trend_series
from codesage.snapshot.models import ProjectSnapshot, SnapshotMetadata, FileSnapshot, FileRisk

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

def test_trend_series_from_multiple_snapshots(tmp_path: Path):
    project_name = "test-project"
    config = HistoryConfig()

    # Create 3 snapshots
    for i in range(3):
        snapshot_id = f"snap_{i}"
        meta = SnapshotMeta(
            project_name=project_name,
            snapshot_id=snapshot_id,
            created_at=datetime.now(timezone.utc) - timedelta(days=2 - i)
        )
        snapshot = create_test_snapshot(project_name,
            [FileSnapshot(path=f"file_{i}.py", language="python", risk=FileRisk(risk_score=0.8, level="high" if i % 2 == 0 else "low"))]
        )
        hs = HistoricalSnapshot(meta=meta, snapshot=snapshot)
        save_historical_snapshot(tmp_path, hs, config)

        # Explicitly update index as save_historical_snapshot doesn't do it automatically anymore?
        # The store.py logic I implemented doesn't update index.
        update_snapshot_index(tmp_path, meta)

    # Build trend series
    series = build_trend_series(tmp_path, project_name)

    assert len(series.points) == 3
    assert series.points[0].snapshot_id == "snap_0"
    assert series.points[0].high_risk_files == 1
    assert series.points[1].snapshot_id == "snap_1"
    assert series.points[1].high_risk_files == 0
    assert series.points[2].snapshot_id == "snap_2"
    assert series.points[2].high_risk_files == 1
