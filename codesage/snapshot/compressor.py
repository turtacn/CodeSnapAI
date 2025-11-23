from typing import Any, Dict, List, Optional
import os
import tiktoken
from codesage.snapshot.models import ProjectSnapshot, FileSnapshot
from codesage.snapshot.strategies import CompressionStrategyFactory, FullStrategy

class SnapshotCompressor:
    """Compresses a ProjectSnapshot to reduce its token usage for LLM context."""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        # Default budget if not specified
        self.token_budget = self.config.get("token_budget", 8000)
        self.model_name = self.config.get("model_name", "gpt-4")

        try:
            self.encoding = tiktoken.encoding_for_model(self.model_name)
        except KeyError:
            self.encoding = tiktoken.get_encoding("cl100k_base")

    def compress_project(self, snapshot: ProjectSnapshot, project_root: str) -> ProjectSnapshot:
        """
        Compresses the snapshot by assigning compression levels to files based on risk and budget.

        Args:
            snapshot: The project snapshot.
            project_root: The root directory of the project (to read file contents).

        Returns:
            The modified project snapshot with updated compression_level fields.
        """
        # 1. Sort files by Risk Score (Desc)
        # Assuming risk.risk_score exists. If not, default to 0.
        sorted_files = sorted(
            snapshot.files,
            key=lambda f: f.risk.risk_score if f.risk else 0.0,
            reverse=True
        )

        # 2. Initial pass: Estimate costs for different levels
        file_costs = {} # {file_path: {level: token_count}}

        # We need to read files.
        for file in sorted_files:
            file_path = os.path.join(project_root, file.path)
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except Exception:
                content = "" # Should we handle missing files?

            # Calculate costs for all strategies
            costs = {}
            for level in ["full", "skeleton", "signature"]:
                strategy = CompressionStrategyFactory.get_strategy(level)
                compressed_content = strategy.compress(content, file.path, file.language)
                costs[level] = len(self.encoding.encode(compressed_content))

            file_costs[file.path] = costs

        # 3. Budget allocation loop
        # Start with minimal cost (all signature)
        current_total_tokens = sum(file_costs[f.path]["signature"] for f in sorted_files)

        # Assign initial level
        for file in snapshot.files:
            file.compression_level = "signature"

        # If we have budget left, upgrade files based on risk
        # We iterate sorted_files (highest risk first)

        # Upgrades: signature -> skeleton -> full

        # Pass 1: Upgrade to Skeleton
        for file in sorted_files:
            costs = file_costs[file.path]
            cost_increase = costs["skeleton"] - costs["signature"]

            if current_total_tokens + cost_increase <= self.token_budget:
                file.compression_level = "skeleton"
                current_total_tokens += cost_increase
            else:
                # If we can't upgrade this file, maybe we can upgrade smaller files?
                # Greedy approach says: prioritize high risk.
                # If high risk file is huge, it might consume all budget.
                # Standard Knapsack problem.
                # For now, simple greedy: iterate by risk. If fits, upgrade.
                pass

        # Pass 2: Upgrade to Full
        for file in sorted_files:
            if file.compression_level == "skeleton":
                costs = file_costs[file.path]
                cost_increase = costs["full"] - costs["skeleton"]

                if current_total_tokens + cost_increase <= self.token_budget:
                    file.compression_level = "full"
                    current_total_tokens += cost_increase

        return snapshot

    def select_strategy(self, file_risk: float, is_focal_file: bool) -> str:
        """
        Determines the ideal strategy based on risk, ignoring budget.
        Used as a heuristic or upper bound.
        """
        if is_focal_file or file_risk >= 0.7: # High risk
            return "full"
        elif file_risk >= 0.3: # Medium risk
            return "skeleton"
        else:
            return "signature"
