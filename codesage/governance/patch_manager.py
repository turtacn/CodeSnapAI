from __future__ import annotations

import difflib
import re
import shutil
import ast
from pathlib import Path
from typing import Optional, Tuple

import structlog

from codesage.analyzers.parser_factory import create_parser

logger = structlog.get_logger()


class PatchManager:
    """
    Manages parsing of code blocks from LLM responses and applying patches to files.
    """

    def extract_code_block(self, llm_response: str, language: str = "") -> Optional[str]:
        """
        Extracts the content of a markdown code block.
        Prioritizes blocks marked with the specific language.
        """
        if language:
            pattern = re.compile(rf"```{language}\s*\n(.*?)\n```", re.DOTALL)
            match = pattern.search(llm_response)
            if match:
                return match.group(1)

        pattern = re.compile(r"```(?:\w+)?\s*\n(.*?)\n```", re.DOTALL)
        match = pattern.search(llm_response)
        if match:
            return match.group(1)

        return None

    def apply_patch(self, file_path: str | Path, new_content: str, create_backup: bool = True) -> bool:
        """
        Replaces the content of file_path with new_content.
        Optionally creates a backup.
        """
        path = Path(file_path)
        if not path.exists():
            logger.error("File not found for patching", file_path=str(path))
            return False

        try:
            if create_backup:
                backup_path = path.with_suffix(path.suffix + ".bak")
                shutil.copy2(path, backup_path)
                logger.info("Backup created", backup_path=str(backup_path))

            path.write_text(new_content, encoding="utf-8")
            logger.info("Patch applied successfully", file_path=str(path))
            return True

        except Exception as e:
            logger.error("Failed to apply patch", file_path=str(path), error=str(e))
            return False

    def apply_fuzzy_patch(self, file_path: str | Path, new_code_block: str, target_symbol: str = None) -> bool:
        """
        Applies a patch using fuzzy matching logic when exact replacement isn't feasible.
        """
        path = Path(file_path)
        if not path.exists():
            logger.error("File not found for fuzzy patching", file_path=str(path))
            return False

        try:
            original_content = path.read_text(encoding="utf-8")
            patched_content = None

            if target_symbol:
                patched_content = self._replace_symbol(file_path, original_content, target_symbol, new_code_block)
                if patched_content:
                    logger.info("Symbol replaced successfully", symbol=target_symbol)

            if not patched_content:
                patched_content = self._apply_context_patch(original_content, new_code_block)
                if patched_content:
                    logger.info("Context patch applied successfully")

            if not patched_content:
                logger.warning("Could not apply fuzzy patch")
                return False

            language = self._get_language_from_extension(path.suffix)
            if language and not self._verify_syntax(patched_content, language):
                logger.error("Patched content failed syntax check", language=language)
                return False

            backup_path = path.with_suffix(path.suffix + ".bak")
            if not backup_path.exists():
                shutil.copy2(path, backup_path)

            path.write_text(patched_content, encoding="utf-8")
            return True

        except Exception as e:
            logger.error("Failed to apply fuzzy patch", file_path=str(path), error=str(e))
            return False

    def _replace_symbol(self, file_path: str | Path, content: str, symbol_name: str, new_block: str) -> Optional[str]:
        """
        Uses simple indentation-based parsing to find and replace a Python function.
        """
        path = Path(file_path)
        if path.suffix != '.py':
             return None # Only Python implemented for P1 regex

        lines = content.splitlines(keepends=True)
        start_idx = -1
        end_idx = -1
        current_indent = 0

        # Regex to find definition
        def_pattern = re.compile(rf"^(\s*)def\s+{re.escape(symbol_name)}\s*\(")

        for i, line in enumerate(lines):
            match = def_pattern.match(line)
            if match:
                start_idx = i
                current_indent = len(match.group(1))
                break

        if start_idx == -1:
            return None

        # Find end: Look for next line with same or less indentation that is NOT empty/comment
        # This is naive but works for standard formatting
        for i in range(start_idx + 1, len(lines)):
            line = lines[i]
            if not line.strip() or line.strip().startswith('#'):
                continue

            # Check indentation
            indent = len(line) - len(line.lstrip())
            if indent <= current_indent:
                end_idx = i
                break
        else:
            end_idx = len(lines) # End of file

        # Replace lines[start_idx:end_idx] with new_block
        # Ensure new_block ends with newline if needed
        if not new_block.endswith('\n'):
            new_block += '\n'

        new_lines = lines[:start_idx] + [new_block] + lines[end_idx:]
        return "".join(new_lines)

    def _apply_context_patch(self, original: str, new_block: str) -> Optional[str]:
        """
        Uses difflib to find a close match for replacement.
        Finds the most similar block in the original content and replaces it.
        """
        # Split into lines
        original_lines = original.splitlines(keepends=True)
        new_lines = new_block.splitlines(keepends=True)

        if not new_lines:
            return None

        # Assumption: The new_block is a modified version of some block in the original.
        # We search for the block in original that has the highest similarity to new_block.

        best_ratio = 0.0
        best_match_start = -1
        best_match_end = -1

        # Try to find header match
        header = new_lines[0].strip()
        # If header is empty or just braces, it's hard.
        if not header:
             return None

        candidates = []
        for i, line in enumerate(original_lines):
            if header in line: # Loose match
                candidates.append(i)

        # For each candidate start, try to find the end of the block (indentation based)
        # and compare similarity.

        for start_idx in candidates:
             # Determine end_idx based on indentation of start_idx
             current_indent = len(original_lines[start_idx]) - len(original_lines[start_idx].lstrip())
             end_idx = len(original_lines)

             for i in range(start_idx + 1, len(original_lines)):
                 line = original_lines[i]
                 if not line.strip() or line.strip().startswith('#'):
                     continue
                 indent = len(line) - len(line.lstrip())
                 if indent <= current_indent:
                     end_idx = i
                     break

             # Check similarity of this block with new_block
             old_block = "".join(original_lines[start_idx:end_idx])
             ratio = difflib.SequenceMatcher(None, old_block, new_block).ratio()

             if ratio > best_ratio:
                 best_ratio = ratio
                 best_match_start = start_idx
                 best_match_end = end_idx

        # Threshold
        if best_ratio > 0.6: # Allow some significant changes but ensure it's roughly the same place
            # Replace
            new_content_lines = original_lines[:best_match_start] + new_lines + original_lines[best_match_end:]

            return "".join(new_content_lines)

        return None

    def _verify_syntax(self, content: str, language: str) -> bool:
        if language == "python":
            try:
                ast.parse(content)
                return True
            except SyntaxError:
                return False
        elif language == "go":
            try:
                parser = create_parser("go")
                parser.parse(content)
                root = parser.tree.root_node
                return not self._has_error_node(root)
            except Exception:
                return False
        return True

    def _has_error_node(self, node) -> bool:
        if node.type == 'ERROR' or node.is_missing:
            return True
        for child in node.children:
            if self._has_error_node(child):
                return True
        return False

    def _get_language_from_extension(self, ext: str) -> Optional[str]:
        if ext in ['.py', '.pyi']:
            return 'python'
        if ext in ['.go']:
            return 'go'
        return None

    def create_diff(self, original: str, new: str, filename: str = "file") -> str:
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
        )
        return "".join(diff)

    def restore_backup(self, file_path: str | Path) -> bool:
        path = Path(file_path)
        backup_path = path.with_suffix(path.suffix + ".bak")

        if not backup_path.exists():
            logger.error("Backup not found", backup_path=str(backup_path))
            return False

        try:
            shutil.move(str(backup_path), str(path))
            logger.info("Backup restored", file_path=str(path))
            return True
        except Exception as e:
            logger.error("Failed to restore backup", file_path=str(path), error=str(e))
            return False

    def revert(self, file_path: str | Path) -> bool:
        return self.restore_backup(file_path)

    def cleanup_backup(self, file_path: str | Path) -> bool:
        path = Path(file_path)
        backup_path = path.with_suffix(path.suffix + ".bak")

        if backup_path.exists():
            try:
                backup_path.unlink()
                logger.info("Backup cleaned up", backup_path=str(backup_path))
                return True
            except Exception as e:
                logger.error("Failed to cleanup backup", backup_path=str(backup_path), error=str(e))
                return False
        return True
