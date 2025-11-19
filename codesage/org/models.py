from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class OrgProjectRef(BaseModel):
    id: str = Field(..., description="Unique identifier for the project.")
    name: str = Field(..., description="The display name of the project.")
    tags: List[str] = Field(default_factory=list, description="A list of tags for categorization.")
    snapshot_path: str = Field(..., description="Path to the project's snapshot artifact.")
    report_path: Optional[str] = Field(None, description="Path to the project's report summary artifact.")
    history_root: Optional[str] = Field(None, description="Path to the root directory for historical snapshots.")
    governance_plan_path: Optional[str] = Field(None, description="Path to the project's governance plan artifact.")


class OrgProjectHealth(BaseModel):
    project: OrgProjectRef = Field(..., description="A reference to the project.")
    health_score: float = Field(..., description="A calculated health score, where higher is better (e.g., 0-100).")
    risk_level: str = Field(..., description="The overall risk level, e.g., 'low', 'medium', 'high'.")
    high_risk_files: int = Field(..., description="The number of files classified as high-risk.")
    total_issues: int = Field(..., description="The total number of open issues.")
    error_issues: int = Field(..., description="The number of issues with 'error' severity.")
    has_recent_regression: bool = Field(..., description="Flag indicating if a recent regression was detected.")
    open_governance_tasks: int = Field(..., description="The number of pending or in-progress governance tasks.")
    governance_completion_ratio: float = Field(
        ..., description="The ratio of completed governance tasks to total tasks (0.0 to 1.0)."
    )


class OrgGovernanceOverview(BaseModel):
    projects: List[OrgProjectHealth] = Field(default_factory=list, description="A list of all project health summaries.")
    total_projects: int = Field(..., description="The total number of projects in the organization.")
    projects_with_regressions: int = Field(..., description="The number of projects that have recent regressions.")
    avg_health_score: float = Field(..., description="The average health score across all projects.")
