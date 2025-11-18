from typing import Literal, Optional

from pydantic import BaseModel


class FileDiffSummary(BaseModel):
    """A summary of the differences for a single file."""
    path: str
    status: Literal["added", "removed", "modified", "unchanged"]
    risk_before: Optional[str] = None
    risk_after: Optional[str] = None
    risk_score_delta: float
    issues_added: int
    issues_resolved: int


class ProjectDiffSummary(BaseModel):
    """A summary of the differences for the entire project."""
    project_name: str
    from_snapshot_id: str
    to_snapshot_id: str
    high_risk_files_delta: int
    total_issues_delta: int
    error_issues_delta: int
