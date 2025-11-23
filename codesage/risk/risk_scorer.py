from typing import Dict, List, Optional

from codesage.config.risk_baseline import RiskBaselineConfig
from codesage.snapshot.models import FileMetrics, FileRisk, ProjectRiskSummary, ProjectSnapshot
from codesage.history.git_miner import GitMiner
from codesage.risk.scorers.coverage_scorer import CoverageScorer
from codesage.risk.propagation import RiskPropagator

import logging

logger = logging.getLogger(__name__)

class RiskScorer:
    def __init__(self, config: RiskBaselineConfig):
        self.config = config
        self.git_miner = GitMiner()
        self.coverage_scorer = None # Lazy load or passed in
        self.risk_propagator = RiskPropagator(
            attenuation_factor=config.propagation_factor,
            max_iterations=config.propagation_iterations
        )

    def set_coverage_report(self, coverage_file: str):
        self.coverage_scorer = CoverageScorer(coverage_file)
        self.coverage_scorer.parse()

    def _calculate_static_score(self, metrics: FileMetrics) -> float:
        python_metrics = metrics.language_specific.get("python", {})

        # Use existing logic or simplified logic?
        # Using existing logic for now
        max_cc = python_metrics.get("max_cyclomatic_complexity", 0)
        avg_cc = python_metrics.get("avg_cyclomatic_complexity", 0.0)
        fan_out = python_metrics.get("fan_out", 0)

        norm_max_cc = min(max_cc / self.config.threshold_complexity_high, 1.0)
        norm_avg_cc = min(avg_cc / self.config.threshold_complexity_high, 1.0)
        norm_fan_out = min(fan_out / 20, 1.0)
        norm_loc = min(metrics.lines_of_code / 1000, 1.0)

        static_score = (
            self.config.weight_complexity_max * norm_max_cc +
            self.config.weight_complexity_avg * norm_avg_cc +
            self.config.weight_fan_out * norm_fan_out +
            self.config.weight_loc * norm_loc
        )
        return min(static_score, 1.0)

    def _calculate_churn_score(self, file_path: str) -> float:
        churn = self.git_miner.get_file_churn(file_path, since_days=self.config.churn_since_days)
        # Normalize
        norm_churn = min(churn / self.config.threshold_churn_high, 1.0)
        return norm_churn

    def _calculate_coverage_penalty(self, file_path: str) -> float:
        if not self.coverage_scorer:
            return 0.0 # No penalty if no coverage data

        coverage = self.coverage_scorer.get_coverage(file_path)
        # Penalty is high if coverage is low.
        # coverage is 0.0 to 1.0 (where 1.0 is full coverage)
        return 1.0 - coverage

    def score_project(self, snapshot: ProjectSnapshot) -> ProjectSnapshot:
        """
        Scores the entire project, updating file risks in place (or returning new ones).
        Uses propagation.
        """
        file_risks: Dict[str, FileRisk] = {}
        base_scores: Dict[str, float] = {}

        # 1. Calculate base scores (Static + Churn + Coverage)
        for file_snapshot in snapshot.files:
            file_path = file_snapshot.path
            metrics = file_snapshot.metrics or FileMetrics()

            static_score = self._calculate_static_score(metrics)
            churn_score = self._calculate_churn_score(file_path)
            coverage_penalty = self._calculate_coverage_penalty(file_path)

            # Formula:
            # Score = w_static * static + w_churn * churn + w_cov * (static * (1-Coverage))
            # Note: coverage penalty is applied to static score usually (if complex code is not covered, it's risky).
            # The prompt says: "Score = w1 * Complexity + w2 * Churn + w3 * (1 - Coverage)"
            # Wait, "w3 * (1 - Coverage)" implies standalone risk from lack of coverage regardless of complexity?
            # But the prompt also said: "Coverage penalty amplifies static risk".
            # Let's use the prompt formula: w1 * Complexity + w2 * Churn + w3 * (1 - Coverage)
            # Complexity is static_score.
            # (1-Coverage) is coverage_penalty.

            # Using weights from config
            # But wait, weights in config are summing to > 1.0?
            # weights for static components sum to 1.0 (0.4+0.3+0.2+0.1).
            # So static_score is 0-1.

            # Now we combine them.
            w_static = self.config.weight_static_score
            w_churn = self.config.weight_churn
            w_cov = self.config.weight_coverage_penalty

            # If I follow prompt strictly: w1, w2, w3.
            # I will assume w1=w_static, w2=w_churn, w3=w_cov.

            # However, if code is simple (complexity 0) and not covered, is it risky?
            # Maybe less risky.
            # Let's implement: w1 * static + w2 * churn + w3 * (static * coverage_penalty)
            # This aligns with "amplifies static risk".

            combined_score = (
                w_static * static_score +
                w_churn * churn_score +
                w_cov * (static_score * coverage_penalty)
            )

            # Store for propagation
            base_scores[file_path] = combined_score

            # Store intermediate for detailed output
            sub_scores = {
                "static_score": round(static_score, 3),
                "churn_score": round(churn_score, 3),
                "coverage_penalty": round(coverage_penalty, 3),
                "combined_base_score": round(combined_score, 3)
            }

            # Temporary FileRisk (will be updated after propagation)
            # We don't have level/factors yet fully determined.
            file_risks[file_path] = FileRisk(
                risk_score=combined_score,
                level="low", # placeholder
                factors=[],
                sub_scores=sub_scores
            )

        # 2. Propagation
        # Build dependency graph in format for propagator: Dict[str, List[str]]
        # The snapshot has dependencies.
        dep_graph_dict = {}
        if snapshot.dependencies:
             # dependency_graph.internal is List[Dict[str, str]] e.g. [{"source": "A", "target": "B"}]?
             # Wait, `internal: List[Dict[str, str]]` description says "List of internal dependencies."
             # Need to verify structure. Usually it is [{"source": ..., "target": ...}] or similar.
             # Or maybe it's a list of dicts like [{"path": "...", "imports": [...]}]?
             # Let's check `codesage/snapshot/models.py`.
             # `internal: List[Dict[str, str]]`.
             # Also `edges: List[Tuple[str, str]]`.

             # If edges is populated, use that.
             for src, dest in snapshot.dependencies.edges:
                 if src not in dep_graph_dict:
                     dep_graph_dict[src] = []
                 dep_graph_dict[src].append(dest)

        final_scores = self.risk_propagator.propagate(dep_graph_dict, base_scores)

        # 3. Finalize
        for file_snapshot in snapshot.files:
            path = file_snapshot.path
            score = final_scores.get(path, 0.0)

            # Normalize to 0-1 if it exceeded
            score = min(score, 1.0) # Or should we allow >1? Usually risk is 0-1 or 0-100. Let's cap at 1.0 (100%)

            # Level
            if score >= self.config.threshold_risk_high:
                level = "high"
            elif score >= self.config.threshold_risk_medium:
                level = "medium"
            else:
                level = "low"

            # Factors
            factors = []
            risk_obj = file_risks.get(path)
            sub_scores = risk_obj.sub_scores if risk_obj else {}

            static_s = sub_scores.get("static_score", 0)
            churn_s = sub_scores.get("churn_score", 0)
            cov_p = sub_scores.get("coverage_penalty", 0)
            base_s = sub_scores.get("combined_base_score", 0)

            if static_s > 0.7: factors.append("high_complexity")
            if churn_s > 0.7: factors.append("high_churn")
            if cov_p > 0.5 and static_s > 0.3: factors.append("low_coverage_complex")
            if (score - base_s) > 0.2: factors.append("risk_propagated")

            sub_scores["final_score"] = round(score, 3)
            sub_scores["propagation_impact"] = round(score - base_s, 3)

            file_snapshot.risk = FileRisk(
                risk_score=score,
                level=level,
                factors=factors,
                sub_scores=sub_scores
            )

        # 4. Summarize Project Risk
        snapshot.risk_summary = summarize_project_risk({f.path: f.risk for f in snapshot.files if f.risk})

        return snapshot

# Backwards compatibility wrapper
def score_file_risk(metrics: FileMetrics, config: RiskBaselineConfig) -> FileRisk:
    """Legacy function for single file scoring without context."""
    scorer = RiskScorer(config)
    # Create a dummy score
    static = scorer._calculate_static_score(metrics)
    level = "low"
    if static >= config.threshold_risk_high: level = "high"
    elif static >= config.threshold_risk_medium: level = "medium"

    return FileRisk(
        risk_score=static,
        level=level,
        factors=["static_analysis_only"],
        sub_scores={"static_score": static}
    )

def summarize_project_risk(file_risks: Dict[str, FileRisk]) -> ProjectRiskSummary:
    """Summarizes the risk for the entire project."""
    if not file_risks:
        return ProjectRiskSummary(
            avg_risk=0.0,
            high_risk_files=0,
            medium_risk_files=0,
            low_risk_files=0,
        )

    total_risk = sum(r.risk_score for r in file_risks.values())
    avg_risk = total_risk / len(file_risks)

    high_risk_files = sum(1 for r in file_risks.values() if r.level == "high")
    medium_risk_files = sum(1 for r in file_risks.values() if r.level == "medium")
    low_risk_files = sum(1 for r in file_risks.values() if r.level == "low")

    return ProjectRiskSummary(
        avg_risk=avg_risk,
        high_risk_files=high_risk_files,
        medium_risk_files=medium_risk_files,
        low_risk_files=low_risk_files,
    )
