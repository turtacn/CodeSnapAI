from pydantic import BaseModel, Field
from typing import Literal, Dict


class ValidationConfig(BaseModel):
    # Commands for syntax checking (linting)
    # Use {file} as placeholder
    syntax_commands: Dict[str, str] = Field(
        default_factory=lambda: {
            "python": "python -m py_compile {file}",
            "go": "go vet {file}",
        },
        description="Commands to check syntax for different languages."
    )
    # Commands for running tests
    # Use {scope} as placeholder, which might be a file or a package
    test_commands: Dict[str, str] = Field(
        default_factory=lambda: {
            "python": "pytest {scope}",
            "go": "go test {scope}",
        },
        description="Commands to run tests for different languages."
    )


class GovernanceConfig(BaseModel):
    max_tasks_per_file: int = Field(10, description="Maximum number of governance tasks to create per file.")
    max_tasks_per_rule: int = Field(50, description="Maximum number of governance tasks to create per rule.")
    group_by: Literal["rule", "file", "risk_level"] = Field("rule", description="How to group governance tasks.")
    prioritization_strategy: Literal["risk_first", "issue_count_first"] = Field("risk_first", description="Strategy to prioritize governance tasks.")

    validation: ValidationConfig = Field(default_factory=ValidationConfig, description="Validation settings.")

    @classmethod
    def default(cls) -> "GovernanceConfig":
        return cls()
