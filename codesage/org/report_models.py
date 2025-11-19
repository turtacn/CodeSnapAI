from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class OrgProjectRow(BaseModel):
    name: str = Field(..., description="Project name.")
    risk_level: str = Field(..., description="Risk level (e.g., 'high', 'medium', 'low').")
    error_issues: int = Field(..., description="Number of error-level issues.")
    has_recent_regression: bool = Field(..., description="Whether a recent regression was detected.")
    open_governance_tasks: int = Field(..., description="Number of open governance tasks.")
    health_score: float = Field(..., description="Calculated project health score.")


class OrgReportSummary(BaseModel):
    total_projects: int = Field(..., description="Total number of projects.")
    projects_by_language: dict[str, int] = Field(..., description="Distribution of projects by primary language.")
    projects_by_risk_level: dict[str, int] = Field(..., description="Distribution of projects by risk level.")
    projects_with_regressions: int = Field(..., description="Number of projects with recent regressions.")
    projects: List[OrgProjectRow] = Field(..., description="List of individual project metrics for the report.")
