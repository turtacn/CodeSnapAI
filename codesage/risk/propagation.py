from typing import Dict, List, Set, Tuple
import logging

logger = logging.getLogger(__name__)

class RiskPropagator:
    def __init__(self, attenuation_factor: float = 0.5, max_iterations: int = 10, epsilon: float = 0.01):
        self.attenuation_factor = attenuation_factor
        self.max_iterations = max_iterations
        self.epsilon = epsilon

    def propagate(self, dependency_graph: Dict[str, List[str]], base_scores: Dict[str, float]) -> Dict[str, float]:
        """
        Propagates risk scores through the dependency graph.
        dependency_graph: Dict[str, List[str]] where key is a file and value is a list of files it depends on (imports).
        base_scores: Dict[str, float] initial risk scores for each file.

        If A depends on B (A -> B), then risk flows from B to A.
        "Calling a high risk component makes you risky."
        """

        final_scores = base_scores.copy()

        # Build reverse graph: who depends on X? (X -> [A, ...])
        # Wait, if A depends on B, risk propagates B -> A.
        # So we iterate through nodes. For a node A, we look at its dependencies (B, C).
        # A's new score = A's base score + sum(B's score * factor)

        # However, B's score might also increase if B depends on D.
        # So this is an iterative process.

        nodes = list(base_scores.keys())

        for _ in range(self.max_iterations):
            changes = 0
            current_scores = final_scores.copy()

            for node in nodes:
                # dependencies: files that 'node' imports
                dependencies = dependency_graph.get(node, [])

                incoming_risk = 0.0
                for dep in dependencies:
                    if dep in current_scores:
                        incoming_risk += current_scores[dep] * self.attenuation_factor

                # Formula: Base + Propagated
                # We should probably dampen it so it doesn't explode, or clamp it?
                # The user formula says: new_score = base_scores[node] + incoming_risk
                # If we want 0-100 or 0-1 scale, this might exceed 1.0.
                # But that's fine, we can normalize later or cap it.

                new_score = base_scores[node] + incoming_risk

                if abs(new_score - final_scores[node]) > self.epsilon:
                    final_scores[node] = new_score
                    changes += 1

            if changes == 0:
                break

        return final_scores
