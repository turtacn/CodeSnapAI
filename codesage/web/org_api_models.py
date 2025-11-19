from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class ApiOrgProjectItem(BaseModel):
    id: str = Field(..., description="Project unique identifier.")
    name: str = Field(..., description="Project name.")
    tags: List[str] = Field(..., description="A list of tags for categorization.")
    health_score: float = Field(..., description="Calculated health score (higher is better).")
    risk_level: str = Field(..., description="Categorized risk level ('low', 'medium', 'high').")
    high_risk_files: int = Field(..., description="Number of high-risk files.")
    total_issues: int = Field(..., description="Total number of open issues.")
    has_recent_regression: bool = Field(..., description="Flag indicating a recent regression.")


class ApiOrgReport(BaseModel):
    total_projects: int = Field(..., description="Total number of projects in the overview.")
    projects_with_regressions: int = Field(..., description="Count of projects with recent regressions.")
    avg_health_score: float = Field(..., description="Average health score across all projects.")
    projects: List[ApiOrgProjectItem] = Field(..., description="A list of project summaries for the API response.")
