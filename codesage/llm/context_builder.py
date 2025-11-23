import tiktoken
from typing import List, Dict, Any, Optional

from codesage.snapshot.models import ProjectSnapshot, FileSnapshot

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
        Prioritizes primary files (full content), then reference files (summaries/interfaces),
        then truncates if necessary.
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

        # 2. Add Primary Files
        for file in primary_files:
            content = self._read_file(file.path)
            if not content: continue

            file_block = f"<file path=\"{file.path}\">\n{content}\n</file>\n"
            tokens = self.count_tokens(file_block)

            if current_tokens + tokens <= available_tokens:
                context_parts.append(file_block)
                current_tokens += tokens
            else:
                # Compression needed
                # We try to keep imports and signatures
                compressed = self._compress_file(file, content)
                tokens = self.count_tokens(compressed)
                if current_tokens + tokens <= available_tokens:
                    context_parts.append(compressed)
                    current_tokens += tokens
                else:
                    # Even compressed is too large, hard truncate
                    remaining = available_tokens - current_tokens
                    if remaining > 20: # Ensure at least some chars
                         chars_limit = remaining * 4
                         if chars_limit > len(compressed):
                             chars_limit = len(compressed)

                         truncated = compressed[:chars_limit] + "\n...(truncated)"
                         context_parts.append(truncated)
                         current_tokens += remaining # Stop here
                         break
                    else:
                        break # No space even for truncated

        # 3. Add Reference Files (Summaries) if space permits
        for file in reference_files:
            if current_tokens >= available_tokens: break

            summary = self._summarize_file(file)
            tokens = self.count_tokens(summary)
            if current_tokens + tokens <= available_tokens:
                context_parts.append(summary)
                current_tokens += tokens

        return "\n".join(context_parts)

    def _read_file(self, path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception:
            return ""

    def _compress_file(self, file_snapshot: FileSnapshot, content: str) -> str:
        """
        Retains imports, structs/classes/interfaces, and function signatures.
        Removes function bodies.
        """
        if not file_snapshot.symbols:
             # Fallback: keep first 50 lines
             lines = content.splitlines()
             return f"<file path=\"{file_snapshot.path}\" compressed=\"true\">\n" + "\n".join(lines[:50]) + "\n... (bodies omitted)\n</file>\n"

        lines = content.splitlines()

        # Intervals to exclude (function bodies)
        exclude_intervals = []

        funcs = file_snapshot.symbols.get("functions", [])

        for f in funcs:
            start = f.get("start_line", 0)
            end = f.get("end_line", 0)
            if end > start:
                # To preserve closing brace if it is on end_line, we exclude up to end_line - 1?
                # It depends on where end_line points. Tree-sitter end_point is row/col.
                # If end_line is the line index (0-based) where function ends.
                # Usually closing brace is on end_line.

                # Check if end_line contains ONLY brace.
                # If we exclude start+1 to end-1, we keep start and end line.

                exclude_start = start + 1
                exclude_end = end - 1

                if exclude_end >= exclude_start:
                    exclude_intervals.append((exclude_start, exclude_end)) # inclusive

        # Sort intervals
        exclude_intervals.sort()

        compressed_lines = []
        skipping = False

        for i, line in enumerate(lines):
            is_excluded = False
            for start_idx, end_idx in exclude_intervals:
                if start_idx <= i <= end_idx: # Excluding body
                     is_excluded = True
                     break

            if is_excluded:
                if not skipping:
                    compressed_lines.append("    ... (body omitted)")
                    skipping = True
            else:
                compressed_lines.append(line)
                skipping = False

        return f"<file path=\"{file_snapshot.path}\" compressed=\"true\">\n" + "\n".join(compressed_lines) + "\n</file>\n"

    def _summarize_file(self, file_snapshot: FileSnapshot) -> str:
        lines = [f"File: {file_snapshot.path}"]
        if file_snapshot.symbols:
            if "functions" in file_snapshot.symbols:
                funcs = file_snapshot.symbols["functions"]
                lines.append("Functions: " + ", ".join([f['name'] for f in funcs]))
            if "structs" in file_snapshot.symbols:
                structs = file_snapshot.symbols["structs"]
                lines.append("Structs: " + ", ".join([s['name'] for s in structs]))
            if "external_commands" in file_snapshot.symbols:
                 cmds = file_snapshot.symbols["external_commands"]
                 lines.append("External Commands: " + ", ".join(cmds))

        return "\n".join(lines) + "\n"
