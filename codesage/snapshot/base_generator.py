from abc import ABC, abstractmethod
from typing import Any, Dict, List

from codesage.snapshot.models import (
    AnalysisIssue,
    AnalysisResult,
    DetectedPattern,
    ProjectSnapshot,
)


class SnapshotGenerator(ABC):
    """Abstract base class for all snapshot generators."""

    @abstractmethod
    def generate(
        self, analysis_results: List[AnalysisResult], config: Dict[str, Any]
    ) -> ProjectSnapshot:
        """
        Generates a project snapshot from analysis results.

        Args:
            analysis_results: A list of analysis results for each file.
            config: The project configuration.

        Returns:
            A ProjectSnapshot object.
        """
        raise NotImplementedError

    def _aggregate_metrics(
        self, results: List[AnalysisResult]
    ) -> Dict[str, Any]:
        """
        Aggregates project-level metrics from a list of file analysis results.
        """
        # This is a placeholder implementation.
        # The actual implementation will depend on the structure of AnalysisResult.
        total_lines = sum(result.get("lines", 0) for result in results)
        total_files = len(results)
        languages = {result.get("language") for result in results if result.get("language")}

        return {
            "total_lines": total_lines,
            "total_files": total_files,
            "language_distribution": {lang: 0 for lang in languages}, # Placeholder
            "avg_complexity": 0, # Placeholder
        }

    def _collect_all_patterns(
        self, results: List[AnalysisResult]
    ) -> List[DetectedPattern]:
        """
        Collects all detected patterns from the analysis results.
        """
        all_patterns = []
        for result in results:
            all_patterns.extend(result.get("detected_patterns", []))
        return all_patterns

    def _collect_all_issues(
        self, results: List[AnalysisResult]
    ) -> List[AnalysisIssue]:
        """
        Collects all issues from the analysis results and sorts them by severity.
        """
        all_issues = []
        for result in results:
            all_issues.extend(result.get("issues", []))
        # Placeholder for sorting by severity
        return all_issues
