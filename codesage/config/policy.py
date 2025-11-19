from typing import Optional

from pydantic import BaseModel, Field


class PolicyConfig(BaseModel):
    project_policy_path: Optional[str] = Field(None, description="Path to the project-specific policy file.")
    org_policy_path: Optional[str] = Field(None, description="Path to the organization-level policy file.")
    default_actions: dict = Field(default_factory=dict, description="Default actions to take when no policy is matched.")
