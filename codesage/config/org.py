from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class OrgProjectRefConfig(BaseModel):
    id: str = Field(..., description="Unique identifier for the project.")
    name: str = Field(..., description="The display name of the project.")
    tags: Optional[List[str]] = Field(None, description="A list of tags for categorization.")
    snapshot_path: str = Field(..., description="Path to the project's snapshot artifact.")
    report_path: Optional[str] = Field(None, description="Path to the project's report summary artifact.")
    history_root: Optional[str] = Field(None, description="Path to the root directory for historical snapshots.")
    governance_plan_path: Optional[str] = Field(None, description="Path to the project's governance plan artifact.")


class OrgConfig(BaseModel):
    projects: List[OrgProjectRefConfig] = Field(
        default_factory=list, description="A list of project configurations for the organization."
    )
    health_weights: Dict[str, float] = Field(
        default_factory=dict,
        description="Weights for calculating the project health score.",
    )

    @classmethod
    def default(cls) -> "OrgConfig":
        return OrgConfig(
            projects=[],
            health_weights={
                "risk_weight": 2.0,
                "issues_weight": 0.1,
                "regression_weight": 15.0,
                "governance_progress_weight": 10.0,
            },
        )
