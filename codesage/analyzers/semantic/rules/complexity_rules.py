from typing import List, Dict

from codesage.analyzers.semantic.models import ComplexityMetrics, AnalysisIssue, CodeLocation

class ComplexityRule:
    def __init__(self, function_threshold: int, file_threshold: int, cognitive_threshold: int):
        self.function_threshold = function_threshold
        self.file_threshold = file_threshold
        self.cognitive_threshold = cognitive_threshold

    @staticmethod
    def load_from_config(config: Dict) -> 'ComplexityRule':
        complexity_config = config.get("analyzers", {}).get("complexity", {})
        return ComplexityRule(
            function_threshold=complexity_config.get("function_threshold", 10),
            file_threshold=complexity_config.get("file_threshold", 200),
            cognitive_threshold=complexity_config.get("cognitive_threshold", 15)
        )

    def check(self, metrics: ComplexityMetrics, file_path: str) -> List[AnalysisIssue]:
        issues = []
        if metrics.cyclomatic_complexity > self.file_threshold:
            issues.append(AnalysisIssue(
                severity="warning", category="complexity",
                message=f"File complexity ({metrics.cyclomatic_complexity}) exceeds threshold ({self.file_threshold})",
                location=CodeLocation(file=file_path, start_line=0, end_line=0)
            ))

        # This check requires per-function metrics, which are not yet fully plumbed
        # if metrics.max_function_complexity > self.function_threshold:
        #     issues.append(AnalysisIssue(
        #         severity="warning", category="complexity",
        #         message=f"Max function complexity ({metrics.max_function_complexity}) exceeds threshold ({self.function_threshold})",
        #         location=CodeLocation(file=file_path, start_line=0, end_line=0)
        #     ))

        return issues
