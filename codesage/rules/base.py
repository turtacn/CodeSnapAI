from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List

from pydantic import BaseModel

# These imports are needed at runtime for Pydantic's model_rebuild to work.
from codesage.snapshot.models import ProjectSnapshot, FileSnapshot, Issue
from codesage.config.rules_python_baseline import RulesPythonBaselineConfig


class RuleContext(BaseModel):
    """Provides the context in which a rule is executed."""
    project: "ProjectSnapshot"
    file: "FileSnapshot"
    config: "RulesPythonBaselineConfig"

    class Config:
        arbitrary_types_allowed = True


class BaseRule(ABC):
    """Abstract base class for a rule."""
    rule_id: str
    description: str
    default_severity: str = "warning"

    @abstractmethod
    def check(self, ctx: RuleContext) -> List[Issue]:
        """
        Checks the given context for violations of this rule.

        Args:
            ctx: The context containing the file and project snapshots.

        Returns:
            A list of issues found, or an empty list if no issues are found.
        """
        raise NotImplementedError

# Resolve forward references in RuleContext now that all dependent models are imported.
RuleContext.model_rebuild()
