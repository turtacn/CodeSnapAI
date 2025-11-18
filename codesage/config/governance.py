from pydantic import BaseModel, Field
from typing import Literal


class GovernanceConfig(BaseModel):
    max_tasks_per_file: int = Field(10, description="Maximum number of governance tasks to create per file.")
    max_tasks_per_rule: int = Field(50, description="Maximum number of governance tasks to create per rule.")
    group_by: Literal["rule", "file", "risk_level"] = Field("rule", description="How to group governance tasks.")
    prioritization_strategy: Literal["risk_first", "issue_count_first"] = Field("risk_first", description="Strategy to prioritize governance tasks.")

    @classmethod
    def default(cls) -> "GovernanceConfig":
        return cls()
