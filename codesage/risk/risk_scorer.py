from typing import Dict, List, Optional
import math

from codesage.config.risk_baseline import RiskBaselineConfig
from codesage.snapshot.models import FileMetrics, FileRisk, ProjectRiskSummary, ProjectSnapshot
from codesage.git.miner import GitMiner
from codesage.test.coverage_parser import CoverageParser
from codesage.risk.propagation import RiskPropagator

import logging

logger = logging.getLogger(__name__)

class RiskScorer:
    def __init__(
        self,
        config: RiskBaselineConfig,
        repo_path: Optional[str] = None,
        coverage_report: Optional[str] = None
    ):
        self.config = config
        self.git_miner = GitMiner(repo_path)
        self.coverage_parser = CoverageParser(coverage_report) if coverage_report else None

        # Risk Propagator (Legacy/Existing component usage)
        self.risk_propagator = RiskPropagator(
            attenuation_factor=config.propagation_factor,
            max_iterations=config.propagation_iterations
        )

    def _calculate_static_score(self, metrics: FileMetrics) -> float:
        """
        Calculates static complexity score (0-10).
        """
        # Original logic used specific weights and returned 0-1.
        # We need to adapt it to return 0-10 or use the original 0-1 and scale.

        python_metrics = metrics.language_specific.get("python", {})

        # Extract metrics
        max_cc = python_metrics.get("max_cyclomatic_complexity", 0)
        avg_cc = python_metrics.get("avg_cyclomatic_complexity", 0.0)
        fan_out = python_metrics.get("fan_out", 0)

        # Normalize based on thresholds (simple scaling)
        # Assuming high complexity starts around 10-15
        norm_max_cc = min(max_cc / 15.0, 1.0)
        norm_avg_cc = min(avg_cc / 5.0, 1.0)
        norm_fan_out = min(fan_out / 20.0, 1.0)

        # Weighted sum for complexity
        # Weights: max_cc 50%, avg_cc 30%, fan_out 20%
        complexity_score = (
            0.5 * norm_max_cc +
            0.3 * norm_avg_cc +
            0.2 * norm_fan_out
        )

        return complexity_score * 10.0 # Scale to 0-10

    def _weighted_risk_model(
        self,
        complexity: float,      # 0-10
        churn: float,           # 0-10
        coverage: float,        # 0-10 (Note: this is risk score from lack of coverage, so 10 = no coverage)
        author_count: int,
        file_lines: int
    ) -> Dict:
        """加权风险评分（对齐架构设计第 3.1.2 节）

        公式:
        Risk = w1·Complexity + w2·Churn + w3·(1-Coverage)
               + w4·AuthorDiversity + w5·FileSize
        """
        # Get weights from config
        weights = {
            "complexity": self.config.weight_complexity,
            "churn": self.config.weight_churn,
            "coverage": self.config.weight_coverage,
            "author_diversity": self.config.weight_author_diversity,
            "file_size": self.config.weight_file_size
        }

        # Standardize author_count (0-10)
        # 5+ authors = 10 points
        author_score = min(10.0, author_count * 2.0)

        # Standardize file_lines (0-10)
        # 1000 lines = 10 points
        size_score = min(10.0, file_lines / 100.0)

        # Weighted sum
        weighted_score = (
            weights["complexity"] * complexity +
            weights["churn"] * churn +
            weights["coverage"] * coverage +
            weights["author_diversity"] * author_score +
            weights["file_size"] * size_score
        )

        # Risk Level
        if weighted_score >= 8.0:
            level = "CRITICAL"
        elif weighted_score >= 6.0:
            level = "HIGH"
        elif weighted_score >= 4.0:
            level = "MEDIUM"
        else:
            level = "LOW"

        return {
            "risk_score": round(weighted_score, 2),
            "risk_level": level,
            "breakdown": {
                "complexity": round(complexity, 2),
                "churn": round(churn, 2),
                "coverage": round(coverage, 2),
                "author_diversity": round(author_score, 2),
                "file_size": round(size_score, 2)
            }
        }

    def score_project(self, snapshot: ProjectSnapshot) -> ProjectSnapshot:
        """
        Scores the entire project.
        """
        file_risks: Dict[str, FileRisk] = {}
        base_scores: Dict[str, float] = {}

        for file_snapshot in snapshot.files:
            file_path = file_snapshot.path
            metrics = file_snapshot.metrics or FileMetrics()

            # 1. Complexity (0-10)
            complexity = self._calculate_static_score(metrics)

            # 2. Churn (0-10)
            churn = 0.0
            author_count = 0
            if self.git_miner:
                churn = self.git_miner.get_file_churn_score(file_path)
                author_count = self.git_miner.get_file_author_count(file_path)

            # 3. Coverage (Risk Score 0-10)
            # Coverage Ratio is 0.0-1.0
            # If report provided, use it. If no report provided, neutral risk (0.0).
            # If report provided but file not found, assume 0% coverage (High Risk).
            coverage_risk = 0.0 # Default if no report

            if self.coverage_parser:
                cov_ratio = self.coverage_parser.get_file_coverage(file_path)
                if cov_ratio is not None:
                    # Found in report
                    coverage_risk = (1.0 - cov_ratio) * 10.0
                else:
                    # Not found in report -> Assumed 0% coverage -> Max Risk
                    # BUT only if file is relevant code (not test, etc).
                    # For simplicity, if coverage parser is active but file missing, max risk.
                    # This aligns with "If cov_ratio is None: coverage_score = 10.0" from spec
                    coverage_risk = 10.0

            # 4. File Size (Lines)
            file_lines = metrics.lines_of_code

            # Calculate Risk
            risk_result = self._weighted_risk_model(
                complexity=complexity,
                churn=churn,
                coverage=coverage_risk,
                author_count=author_count,
                file_lines=file_lines
            )

            risk_score = risk_result["risk_score"]
            base_scores[file_path] = risk_score

            # Determine factors
            factors = []
            breakdown = risk_result["breakdown"]
            if breakdown["complexity"] > 6.0: factors.append("high_complexity")
            if breakdown["churn"] > 6.0: factors.append("high_churn")
            if breakdown["coverage"] > 8.0: factors.append("low_coverage")
            if breakdown["author_diversity"] > 6.0: factors.append("many_authors")

            file_risks[file_path] = FileRisk(
                risk_score=risk_score,
                level=risk_result["risk_level"].lower(),
                factors=factors,
                sub_scores=breakdown
            )

        # Propagation (Optional: Apply on top of weighted score or integrate?)
        # Architecture doc says propagation is important.
        # We can apply propagation to the `risk_score`.

        # Build dependency graph
        dep_graph_dict = {}
        if snapshot.dependencies:
             for src, dest in snapshot.dependencies.edges:
                 if src not in dep_graph_dict:
                     dep_graph_dict[src] = []
                 dep_graph_dict[src].append(dest)

        propagated_scores = self.risk_propagator.propagate(dep_graph_dict, base_scores)

        # Update scores with propagation
        for file_snapshot in snapshot.files:
            path = file_snapshot.path
            if path in file_risks:
                original_risk = file_risks[path]
                new_score = propagated_scores.get(path, original_risk.risk_score)

                # Cap at 10.0
                new_score = min(10.0, new_score)

                # Update level if score increased significantly
                # (Simple logic for now)
                if new_score >= 8.0: level = "critical"
                elif new_score >= 6.0: level = "high"
                elif new_score >= 4.0: level = "medium"
                else: level = "low"

                # Add propagation factor
                if new_score > original_risk.risk_score + 0.5:
                    original_risk.factors.append("risk_propagated")

                original_risk.risk_score = round(new_score, 2)
                original_risk.level = level
                original_risk.sub_scores["propagated_score"] = round(new_score, 2)

                file_snapshot.risk = original_risk

        # Summary
        snapshot.risk_summary = summarize_project_risk(file_risks)
        return snapshot

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

    high_risk_files = sum(1 for r in file_risks.values() if r.level in ["high", "critical"])
    medium_risk_files = sum(1 for r in file_risks.values() if r.level == "medium")
    low_risk_files = sum(1 for r in file_risks.values() if r.level == "low")

    return ProjectRiskSummary(
        avg_risk=avg_risk,
        high_risk_files=high_risk_files,
        medium_risk_files=medium_risk_files,
        low_risk_files=low_risk_files,
    )
