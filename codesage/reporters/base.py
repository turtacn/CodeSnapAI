from abc import ABC, abstractmethod
from typing import List, Optional
from codesage.snapshot.models import ProjectSnapshot

class BaseReporter(ABC):
    @abstractmethod
    def report(self, snapshot: ProjectSnapshot) -> None:
        """
        Report the findings of the snapshot.

        Args:
            snapshot: The project snapshot containing analysis results and issues.
        """
        pass
