from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class CodeIssue(BaseModel):
    """
    Represents a generic issue found in code.
    """
    file_path: str
    line_number: int
    severity: str  # low, medium, high, error
    description: str
    rule_id: str
    context: Optional[str] = None

class Plugin(ABC):
    """
    Base interface for all plugins.
    """
    @abstractmethod
    def register(self, engine: Any) -> None:
        """
        Registers the plugin components (rules, analyzers) with the engine.
        """
        pass

class Rule(ABC):
    """
    Base interface for a static analysis rule.
    """
    id: str
    description: str
    severity: str = "medium"

    @abstractmethod
    def check(self, file_path: str, content: str, context: Dict[str, Any]) -> List[CodeIssue]:
        """
        Checks the file content for violations of this rule.
        """
        pass

class Analyzer(ABC):
    """
    Base interface for a custom analyzer (e.g., checking broader scope than a single file).
    """
    id: str

    @abstractmethod
    def analyze(self, project_path: str) -> List[CodeIssue]:
        """
        Analyzes the project to find issues.
        """
        pass
