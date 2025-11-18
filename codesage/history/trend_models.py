from datetime import datetime
from typing import List

from pydantic import BaseModel


class TrendPoint(BaseModel):
    """A single point in a trend series."""
    snapshot_id: str
    created_at: datetime
    high_risk_files: int
    total_issues: int
    error_issues: int


class TrendSeries(BaseModel):
    """A series of trend points for a project."""
    project_name: str
    points: List[TrendPoint]
