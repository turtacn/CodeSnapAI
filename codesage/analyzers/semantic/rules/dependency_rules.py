from typing import List, Dict

from codesage.analyzers.semantic.models import DependencyGraph, AnalysisIssue, CodeLocation

class DependencyRule:
    def __init__(self, max_depth: int, detect_cycles: bool):
        self.max_depth = max_depth
        self.detect_cycles = detect_cycles

    @staticmethod
    def load_from_config(config: Dict) -> 'DependencyRule':
        dep_config = config.get("analyzers", {}).get("dependency", {})
        return DependencyRule(
            max_depth=dep_config.get("max_depth", 5),
            detect_cycles=dep_config.get("detect_cycles", True)
        )

    def check(self, graph: DependencyGraph) -> List[AnalysisIssue]:
        issues = []
        if self.detect_cycles and graph.cycles:
            for cycle in graph.cycles:
                issues.append(AnalysisIssue(
                    severity="error", category="dependency",
                    message=f"Circular dependency detected: {' -> '.join(cycle)}",
                    location=CodeLocation(file=cycle[0], start_line=0, end_line=0)
                ))

        if self.max_depth > 0 and graph.max_depth > self.max_depth:
            issues.append(AnalysisIssue(
                severity="warning", category="dependency",
                message=f"Max dependency depth ({graph.max_depth}) exceeds threshold ({self.max_depth})",
                location=CodeLocation(file="", start_line=0, end_line=0)
            ))

        return issues
