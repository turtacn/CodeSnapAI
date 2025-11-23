from __future__ import annotations

import difflib
import re
import shutil
from pathlib import Path
from typing import Optional, Tuple

import structlog

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
        # Pattern for ```language ... ```
        # We try to match specifically the requested language first
        if language:
            pattern = re.compile(rf"```{language}\s*\n(.*?)\n```", re.DOTALL)
            match = pattern.search(llm_response)
            if match:
                return match.group(1)

        # Fallback: match any code block
        pattern = re.compile(r"```(?:\w+)?\s*\n(.*?)\n```", re.DOTALL)
        match = pattern.search(llm_response)
        if match:
            return match.group(1)

        # If no code block is found, we return None to be safe.
        # Returning the whole response might risk injecting chat text into source code.
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

            # For Phase 1, we assume new_content is the FULL file content
            # or we need to compute diff?
            # The task says "implement extract_code_block and apply_diff".
            # If the LLM returns a full file, we just overwrite.
            # If the LLM returns a diff or snippet, we need to handle it.
            # For now, let's assume the prompt asks for the FULL file content or we do full replacement.
            # If we want to support git-style diffs, we need more complex logic.
            # Based on "AC-2: PatchManager can correct parse LLM returned Markdown code block... and replace it to source file",
            # I will implement full replacement for now as it's safer for "Apply" than trying to merge snippets without line numbers.

            path.write_text(new_content, encoding="utf-8")
            logger.info("Patch applied successfully", file_path=str(path))
            return True

        except Exception as e:
            logger.error("Failed to apply patch", file_path=str(path), error=str(e))
            return False

    def create_diff(self, original: str, new: str, filename: str = "file") -> str:
        """
        Creates a unified diff between original and new content.
        """
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
        )
        return "".join(diff)

    def restore_backup(self, file_path: str | Path) -> bool:
        """
        Restores the file from its backup (.bak).
        """
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
