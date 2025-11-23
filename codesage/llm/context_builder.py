import tiktoken
from typing import List, Dict, Any, Optional

from codesage.snapshot.models import ProjectSnapshot, FileSnapshot
from codesage.snapshot.strategies import CompressionStrategyFactory

class ContextBuilder:
    def __init__(self, model_name: str = "gpt-4", max_tokens: int = 8000, reserve_tokens: int = 1000):
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.reserve_tokens = reserve_tokens
        try:
            self.encoding = tiktoken.encoding_for_model(model_name)
        except KeyError:
            self.encoding = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        return len(self.encoding.encode(text))

    def fit_to_window(self,
                      primary_files: List[FileSnapshot],
                      reference_files: List[FileSnapshot],
                      snapshot: ProjectSnapshot) -> str:
        """
        Builds a context string that fits within the token window.
        Uses the compression_level specified in FileSnapshot to determine content.
        """
        available_tokens = self.max_tokens - self.reserve_tokens

        # Guard against zero/negative available tokens
        if available_tokens <= 0:
             if self.max_tokens > 0:
                 available_tokens = self.max_tokens

        context_parts = []
        current_tokens = 0

        # 1. Add System/Project Context (from snapshot metadata)
        project_context = f"Project: {snapshot.metadata.project_name}\nStats: {snapshot.metadata.file_count} files\n"
        tokens = self.count_tokens(project_context)
        if current_tokens + tokens <= available_tokens:
            context_parts.append(project_context)
            current_tokens += tokens

        # Combine primary and reference files for processing
        # Note: In the new logic, the SnapshotCompressor should have already assigned appropriate levels
        # based on global budget. However, ContextBuilder might receive raw snapshots.
        # Here we assume we respect the file.compression_level if set.

        all_files = primary_files + reference_files

        for file in all_files:
            content = self._read_file(file.path)
            if not content: continue

            # Apply compression strategy
            strategy = CompressionStrategyFactory.get_strategy(getattr(file, "compression_level", "full"))
            processed_content = strategy.compress(content, file.path, file.language)

            # Decorate
            file_block = f"<file path=\"{file.path}\">\n{processed_content}\n</file>\n"
            tokens = self.count_tokens(file_block)

            if current_tokens + tokens <= available_tokens:
                context_parts.append(file_block)
                current_tokens += tokens
            else:
                # If even the compressed content doesn't fit, we might need to truncate
                # Or stop adding files.
                remaining = available_tokens - current_tokens
                if remaining > 50:
                    truncated = processed_content[:(remaining * 3)] + "\n...(truncated due to context limit)"
                    context_parts.append(f"<file path=\"{file.path}\">\n{truncated}\n</file>\n")
                    current_tokens += remaining # Approximate
                    break
                else:
                    break

        return "\n".join(context_parts)

    def _read_file(self, path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception:
            return ""
