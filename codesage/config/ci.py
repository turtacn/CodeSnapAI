from __future__ import annotations
from pydantic import BaseModel, Field


class CIPolicyConfig(BaseModel):
    enabled: bool = Field(False, description="Whether the CI policy is enabled.")
    fail_on_error_issues: bool = Field(True, description="Whether to fail the build if there are error-level issues.")
    max_error_issues: int = Field(0, description="The maximum number of error-level issues allowed.")
    max_high_risk_files: int = Field(0, description="The maximum number of high-risk files allowed.")

    @classmethod
    def default(cls):
        return cls()
