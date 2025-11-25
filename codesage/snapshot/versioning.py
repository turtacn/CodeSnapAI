import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from codesage.snapshot.models import ProjectSnapshot, SnapshotMetadata
from codesage.snapshot.json_generator import JSONGenerator


class SnapshotVersionManager:
    """Manages the versioning and lifecycle of project snapshots."""

    def __init__(self, snapshot_dir: str, config: Dict[str, Any]):
        self.snapshot_dir = snapshot_dir
        self.index_file = os.path.join(snapshot_dir, "index.json")
        versioning_config = config.get("versioning", {})
        self.max_versions = versioning_config.get("max_versions", 10)
        self.retention_days = versioning_config.get("retention_days", 30)
        os.makedirs(self.snapshot_dir, exist_ok=True)

    def _load_index(self) -> List[Dict[str, Any]]:
        """Loads the snapshot index from the index file."""
        if not os.path.exists(self.index_file):
            return []
        with open(self.index_file, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []

    def _save_index(self, index: List[Dict[str, Any]]):
        """Saves the snapshot index to the index file."""
        with open(self.index_file, "w") as f:
            json.dump(index, f, indent=2)

    def _get_next_version(self) -> str:
        """Determines the next snapshot version string."""
        index = self._load_index()
        if not index:
            return "v1"
        latest_version = 0
        for item in index:
            if item["version"].startswith("v"):
                try:
                    version_num = int(item["version"][1:])
                    if version_num > latest_version:
                        latest_version = version_num
                except ValueError:
                    continue
        return f"v{latest_version + 1}"

    def save_snapshot(self, snapshot: ProjectSnapshot, format: str = "json") -> str:
        """Saves a snapshot, assigning a new version and updating the index."""
        version = self._get_next_version()
        snapshot.metadata.version = version

        snapshot_filename = f"{version}.{format}"
        snapshot_path = os.path.join(self.snapshot_dir, snapshot_filename)

        if format == "json":
            generator = JSONGenerator()
            generator.export(snapshot, snapshot_path, pretty=False)
        else:
            raise NotImplementedError(f"Format '{format}' is not supported for saving.")

        self._update_index(snapshot_path, snapshot.metadata)

        return snapshot_path

    def _update_index(self, snapshot_path: str, metadata: SnapshotMetadata):
        """Updates the index with a new snapshot record."""
        index = self._load_index()
        index.append(
            {
                "version": metadata.version,
                "timestamp": metadata.timestamp.isoformat(),
                "path": snapshot_path,
                "git_commit": metadata.git_commit,
            }
        )
        self._save_index(index)

    def cleanup_expired_snapshots(self):
        """Removes expired snapshots based on retention days and max versions."""
        index = self._load_index()
        now = datetime.now(timezone.utc)

        now = datetime.now(timezone.utc)
        valid_snapshots = []
        for s in index:
            timestamp_str = s["timestamp"]
            try:
                # Attempt to parse as timezone-aware datetime
                timestamp = datetime.fromisoformat(timestamp_str)
                if timestamp.tzinfo is None:
                    # If naive, assume local timezone and convert to UTC
                    timestamp = timestamp.astimezone(timezone.utc)
            except ValueError:
                # Fallback for older/invalid formats
                continue

            if now - timestamp <= timedelta(days=self.retention_days):
                valid_snapshots.append(s)

        if len(valid_snapshots) > self.max_versions:
            valid_snapshots = sorted(
                valid_snapshots, key=lambda s: s["timestamp"], reverse=True
            )[:self.max_versions]

        expired_snapshots = [s for s in index if s not in valid_snapshots]

        for snapshot_data in expired_snapshots:
            if os.path.exists(snapshot_data["path"]):
                os.remove(snapshot_data["path"])

        self._save_index(valid_snapshots)

    def list_snapshots(self) -> List[Dict[str, Any]]:
        """Lists all managed snapshots from the index."""
        return self._load_index()

    def load_snapshot(self, version: str) -> Optional[ProjectSnapshot]:
        """Loads a specific version of a snapshot from the index."""
        index = self._load_index()
        snapshot_data = next((s for s in index if s["version"] == version), None)

        if not snapshot_data or not os.path.exists(snapshot_data["path"]):
            return None

        with open(snapshot_data["path"], "r") as f:
            data = json.load(f)
            return ProjectSnapshot.model_validate(data)
