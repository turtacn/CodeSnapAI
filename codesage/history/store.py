from pathlib import Path
from typing import Optional

import yaml

from codesage.config.history import HistoryConfig
from codesage.history.models import HistoricalSnapshot, SnapshotIndex, SnapshotMeta
from codesage.snapshot.models import ProjectSnapshot


def save_historical_snapshot(root: Path, hs: HistoricalSnapshot, config: HistoryConfig) -> None:
    """Saves a historical snapshot and updates the index."""
    project_dir = root / hs.meta.project_name
    project_dir.mkdir(parents=True, exist_ok=True)

    snapshot_file = project_dir / f"{hs.meta.snapshot_id}.yaml"

    # Use Pydantic's `model_dump` for v2, which is equivalent to `dict` in v1
    data = hs.snapshot.model_dump(mode='json')

    with snapshot_file.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)

    update_snapshot_index(root, hs.meta, config.max_snapshots)


def load_historical_snapshot(root: Path, project: str, snapshot_id: str) -> HistoricalSnapshot:
    """Loads a historical snapshot."""
    snapshot_file = root / project / f"{snapshot_id}.yaml"
    with snapshot_file.open("r", encoding="utf-8") as f:
        raw_snapshot = yaml.safe_load(f)

    snapshot = ProjectSnapshot.model_validate(raw_snapshot)

    index = load_snapshot_index(root, project)
    meta = next((m for m in index.items if m.snapshot_id == snapshot_id), None)

    if not meta:
        raise FileNotFoundError(f"Snapshot metadata for id {snapshot_id} not found in index.")

    return HistoricalSnapshot(meta=meta, snapshot=snapshot)


def load_snapshot_index(root: Path, project: str) -> SnapshotIndex:
    """Loads the snapshot index for a project."""
    index_file = root / project / "index.yaml"
    if not index_file.exists():
        return SnapshotIndex(project_name=project, items=[])

    with index_file.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    return SnapshotIndex.model_validate(raw)


def update_snapshot_index(root: Path, meta: SnapshotMeta, max_snapshots: int) -> None:
    """Updates the snapshot index for a project."""
    index_file = root / meta.project_name / "index.yaml"

    index = load_snapshot_index(root, meta.project_name)

    # Avoid adding duplicate entries
    index.items = [item for item in index.items if item.snapshot_id != meta.snapshot_id]

    index.items.append(meta)
    index.items.sort(key=lambda m: m.created_at, reverse=True)

    if max_snapshots > 0:
        index.items = index.items[:max_snapshots]

    with index_file.open("w", encoding="utf-8") as f:
        yaml.safe_dump(index.model_dump(mode='json'), f, sort_keys=False, allow_unicode=True)
