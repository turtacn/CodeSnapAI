from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from codesage.snapshot.models import ProjectSnapshot


class SnapshotMeta(BaseModel):
    """Metadata for a single snapshot."""
    project_name: str
    snapshot_id: str  # e.g., commit hash or timestamp
    created_at: datetime = Field(default_factory=datetime.utcnow)
    branch: Optional[str] = None
    commit: Optional[str] = None
    trigger: Optional[str] = None  # e.g., 'ci', 'manual'


class HistoricalSnapshot(BaseModel):
    """A snapshot with its metadata."""
    meta: SnapshotMeta
    snapshot: ProjectSnapshot


class SnapshotIndex(BaseModel):
    """An index of all snapshots for a project."""
    project_name: str
    items: List[SnapshotMeta] = Field(default_factory=list)
