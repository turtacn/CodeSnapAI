from typing import List
from pydantic import BaseModel, Field


class RegressionThresholds(BaseModel):
    max_high_risk_delta: int = 5
    max_error_issues_delta: int = 10
    important_rules: List[str] = Field(default_factory=list)


class HistoryConfig(BaseModel):
    history_root: str = ".codesage/history"
    max_snapshots: int = 100
    regression_thresholds: RegressionThresholds = Field(default_factory=RegressionThresholds)

    @classmethod
    def default(cls):
        return HistoryConfig()
