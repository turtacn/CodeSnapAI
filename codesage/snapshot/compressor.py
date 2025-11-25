from typing import Any, Dict, List, Optional
import os
import tiktoken
import fnmatch
from codesage.snapshot.models import ProjectSnapshot, FileSnapshot
from codesage.snapshot.strategies import CompressionStrategyFactory, FullStrategy
from codesage.analyzers.ast_models import FunctionNode, ClassNode

class SnapshotCompressor:
    """Compresses a ProjectSnapshot to reduce its token usage for LLM context."""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        # Default budget if not specified
        self.token_budget = self.config.get("token_budget", 8000)
        self.model_name = self.config.get("model_name", "gpt-4")
        self.exclude_patterns = self.config.get("compression", {}).get("exclude_patterns", [])
        self.trimming_threshold = self.config.get("compression", {}).get("trimming_threshold", None)

        try:
            self.encoding = tiktoken.encoding_for_model(self.model_name)
        except KeyError:
            self.encoding = tiktoken.get_encoding("cl100k_base")

    def compress(self, snapshot: ProjectSnapshot, project_root: str = ".") -> ProjectSnapshot:
        """Alias for compress_project for backward compatibility."""
        return self.compress_project(snapshot, project_root)

    def compress_project(self, snapshot: ProjectSnapshot, project_root: str) -> ProjectSnapshot:
        """
        Compresses the snapshot by assigning compression levels to files based on risk and budget.
        """
        # 0. Filter files based on exclude_patterns
        if self.exclude_patterns:
            filtered_files = []
            for file in snapshot.files:
                excluded = False
                for pattern in self.exclude_patterns:
                    if fnmatch.fnmatch(file.path, pattern):
                        excluded = True
                        break
                if not excluded:
                    filtered_files.append(file)
            snapshot.files = filtered_files

        # 1. Trimming large ASTs if needed (AST Trimming Logic)
        if self.trimming_threshold:
            for file in snapshot.files:
                if file.lines and file.lines > self.trimming_threshold:
                    if file.ast_summary:
                        # Prune children of FunctionNode/ClassNode
                        if isinstance(file.ast_summary, (FunctionNode, ClassNode)):
                             file.ast_summary.children = [] # Remove body
                        # Also check if ast_summary is ASTSummary wrapper or node
                        # In tests, it seems they assign FunctionNode to ast_summary which is typed as ASTSummary | ASTNode?
                        # Model says: ast_summary: Optional[ASTSummary]
                        # But Python is dynamic. Tests assign FunctionNode.
                        # If it's a FunctionNode, prune children.
                        # If it's ASTSummary, it doesn't have children directly.
                        if hasattr(file.ast_summary, 'children'):
                             file.ast_summary.children = []

        # 2. Sort files by Risk Score (Desc)
        sorted_files = sorted(
            snapshot.files,
            key=lambda f: f.risk.risk_score if f.risk else 0.0,
            reverse=True
        )

        # 3. Initial pass: Estimate costs for different levels
        file_costs = {}

        for file in sorted_files:
            content = file.content
            if content is None:
                file_path = os.path.join(project_root, file.path)
                try:
                    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                except Exception:
                    content = ""

            costs = {}
            for level in ["full", "skeleton", "signature"]:
                strategy = CompressionStrategyFactory.get_strategy(level)
                compressed_content = strategy.compress(content, file.path, file.language)
                costs[level] = len(self.encoding.encode(compressed_content))

            file_costs[file.path] = costs

        # 4. Budget allocation loop
        current_total_tokens = sum(file_costs[f.path]["signature"] for f in sorted_files)

        for file in snapshot.files:
            file.compression_level = "signature"

        # Pass 1: Upgrade to Skeleton
        for file in sorted_files:
            costs = file_costs[file.path]
            cost_increase = costs["skeleton"] - costs["signature"]

            if current_total_tokens + cost_increase <= self.token_budget:
                file.compression_level = "skeleton"
                current_total_tokens += cost_increase
            else:
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
