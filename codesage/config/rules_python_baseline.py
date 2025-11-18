from __future__ import annotations
from pydantic import BaseModel, Field


class RulesPythonBaselineConfig(BaseModel):
    """Configuration for the Python baseline ruleset."""
    enabled: bool = Field(True, description="Whether to enable the baseline Python ruleset.")

    # Rule-specific switches
    enable_high_cyclomatic_rule: bool = Field(True, description="Enable the high cyclomatic complexity rule.")
    enable_high_fan_out_rule: bool = Field(True, description="Enable the high fan-out rule.")
    enable_large_file_rule: bool = Field(True, description="Enable the large file (lines of code) rule.")
    enable_missing_type_hints_rule: bool = Field(False, description="Enable the missing type hints rule (experimental).")

    # Thresholds
    max_cyclomatic_threshold: int = Field(10, description="The cyclomatic complexity threshold for the `RuleHighCyclomaticFunction`.")
    fan_out_threshold: int = Field(15, description="The fan-out threshold for the `RuleHighFanOutFile`.")
    loc_threshold: int = Field(500, description="The lines of code threshold for the `RuleLargeFile`.")

    @classmethod
    def default(cls) -> "RulesPythonBaselineConfig":
        return cls()
