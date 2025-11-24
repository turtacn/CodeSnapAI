from __future__ import annotations

import difflib
import re
import shutil
import ast
import logging
import time
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List, Union
from dataclasses import dataclass, field

import structlog

from codesage.analyzers.parser_factory import create_parser
from codesage.governance.rollback_manager import RollbackManager
from codesage.sandbox.validator import SandboxValidator

logger = structlog.get_logger()

@dataclass
class Patch:
    new_code: str
    context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PatchResult:
    success: bool
    new_code: str = ""
    error: str = ""
    commit_sha: str = ""
    partial_commit_sha: str = ""

class PatchTransformer(ast.NodeTransformer):
    """AST Transformer to replace a specific node with a new one (parsed from code)."""
    def __init__(self, target_node: ast.AST, new_node: ast.AST):
        self.target_node = target_node
        self.new_node = new_node
        self.replaced = False

    def visit(self, node):
        if node == self.target_node:
            self.replaced = True
            return self.new_node
        return super().visit(node)

class PatchManager:
    """
    Manages parsing of code blocks from LLM responses and applying patches to files.
    """

    def __init__(self, repo_path: str = None, enable_git_rollback: bool = True, enable_sandbox: bool = True):
        self.rollback_mgr = RollbackManager(repo_path) if enable_git_rollback and repo_path else None
        self.sandbox = SandboxValidator() if enable_sandbox else None

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

    def apply_patch_safe(self, task: Any) -> PatchResult:
        """
        Applies a patch with Git rollback protection and Sandbox validation.

        Args:
            task: A task object containing id, file_path, patch (Patch object or code),
                  issue.message, and validation_config.
                  We assume 'task' behaves like FixTask or GovernanceTask wrapper.
        """
        file_path = task.file_path
        patch_obj = task.patch if hasattr(task, 'patch') and isinstance(task.patch, Patch) else Patch(new_code=task.patch if hasattr(task, 'patch') else "")

        # 1. Create isolation branch
        if self.rollback_mgr:
            self.rollback_mgr.create_patch_branch(task.id)

        # 2. Apply patch
        # We assume apply_fuzzy_patch_internal logic here, but returning PatchResult
        result = self._apply_fuzzy_patch_internal(file_path, patch_obj)

        # 3. Validate
        if result.success and self.sandbox:
            validation_config = getattr(task, 'validation_config', {})
            validation = self.sandbox.validate_patch(
                patched_code=result.new_code,
                original_file=Path(file_path),
                validation_config=validation_config
            )

            if not validation.passed:
                result.success = False
                result.error = f"Validation failed: {validation.checks}"
                # If we modified the file on disk, we might want to revert it or the commit.
                # Since we haven't committed yet (just modified file), rollback_patch isn't applicable yet
                # unless we commit first.
                # But Step 2 modified the file on disk.
                # If we are on a branch, we can just checkout the file.
                if self.rollback_mgr:
                     # Revert changes to file
                     try:
                         self.rollback_mgr.repo.git.checkout(file_path)
                     except Exception as e:
                         logger.error(f"Failed to revert file after validation failure: {e}")

        # 4. Commit or Rollback
        if result.success:
            if self.rollback_mgr:
                msg = getattr(task.issue, 'message', 'Fix issue') if hasattr(task, 'issue') else "Applied patch"
                commit_sha = self.rollback_mgr.commit_patch(
                    [file_path],
                    task.id,
                    f"Fix: {msg}"
                )
                result.commit_sha = commit_sha
        else:
            # If we failed (and didn't revert above, or if apply returned failure but left partial state)
            # Revert file changes if any
            pass

        return result

    def apply_fuzzy_patch(self, file_path: str | Path, new_code_block: str, target_symbol: str = None) -> bool:
        """
        Applies a patch using fuzzy matching logic when exact replacement isn't feasible.
        Backward compatible wrapper around _apply_fuzzy_patch_internal.
        """
        patch = Patch(
            new_code=new_code_block,
            context={"function_name": target_symbol} if target_symbol else {}
        )
        result = self._apply_fuzzy_patch_internal(file_path, patch)
        return result.success

    def _apply_fuzzy_patch_internal(self, file_path: str | Path, patch: Patch) -> PatchResult:
        """
        Internal logic for fuzzy patching (Refactored CX < 5).
        """
        path = Path(file_path)
        if not path.exists():
            return PatchResult(False, error=f"File not found: {path}")

        # 1. Parse
        tree = self._parse_file(path)
        if not tree:
             # Fallback to text-based if parse fails (e.g. non-python or syntax error)
             # Mimic old behavior: call _apply_context_patch directly on text
             # But first we need the content
             try:
                 content = path.read_text(encoding="utf-8")
                 res = self._apply_text_fallback(content, patch.new_code)
                 if res:
                     return self._validate_and_save_text(res, path)
                 return PatchResult(False, error="Parse failed and text fallback failed")
             except Exception as e:
                 return PatchResult(False, error=str(e))

        # 2. Find Anchor
        anchor = self._find_fuzzy_anchor(tree, patch.context)

        # Special case: If new code has comments, and we found an anchor via AST,
        # AST replacement will lose comments.
        # We might prefer text-based patch if available.
        if anchor and "#" in patch.new_code:
             # Force text fallback by NOT using the anchor
             anchor = None

        # 3. Apply Replacement
        if anchor:
            modified_tree = self._apply_replacement(tree, anchor, patch.new_code)
            if modified_tree:
                 return self._validate_and_save(modified_tree, path)

        # 4. Fallback if anchor not found or replacement failed
        # Try text-based fuzzy match
        content = path.read_text(encoding="utf-8")
        patched_content = self._apply_context_patch(content, patch.new_code)

        if patched_content:
             return self._validate_and_save_text(patched_content, path)

        return PatchResult(False, error="No matching anchor found and fuzzy text patch failed")

    def _parse_file(self, file_path: Path) -> Optional[ast.AST]:
        try:
            content = file_path.read_text(encoding="utf-8")
            return ast.parse(content)
        except (SyntaxError, Exception) as e:
            logger.warning(f"Failed to parse {file_path}: {e}")
            return None

    def _find_fuzzy_anchor(self, tree: ast.AST, context: Dict[str, Any], similarity_threshold: float = 0.75) -> Optional[ast.AST]:
        """
        Multi-level fuzzy matching for anchor finding.
        """
        if not context:
            return None

        function_name = context.get("function_name")
        if not function_name:
            return None

        # Level 1: Exact Match (Name)
        candidates = self._get_functions_by_name(tree, function_name)
        if len(candidates) == 1:
            return candidates[0]

        # Level 3: Semantic Similarity (Code Snippet)
        snippet = context.get("code_snippet")
        if snippet:
            best_node = None
            best_score = 0.0

            all_funcs = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]

            for func in all_funcs:
                score = self._compute_similarity(func, snippet)
                if score > best_score:
                    best_score = score
                    best_node = func

            if best_score > similarity_threshold:
                logger.info(f"Fuzzy match found: {best_node.name} (score: {best_score:.2f})")
                return best_node

        return None

    def _get_functions_by_name(self, tree: ast.AST, name: str) -> List[ast.AST]:
        found = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name == name:
                    found.append(node)
        return found

    def _compute_similarity(self, node: ast.AST, reference: str) -> float:
        try:
            node_code = ast.unparse(node)
            return difflib.SequenceMatcher(None, node_code, reference).ratio()
        except Exception:
            return 0.0

    def _apply_replacement(self, tree: ast.AST, anchor: ast.AST, new_code: str) -> Optional[ast.AST]:
        """Parses new code and replaces anchor in tree."""
        try:
            new_tree = ast.parse(new_code)
            if not new_tree.body:
                return None

            new_node = new_tree.body[0]

            # Replace
            transformer = PatchTransformer(anchor, new_node)
            modified_tree = transformer.visit(tree)
            ast.fix_missing_locations(modified_tree)
            return modified_tree
        except Exception as e:
            logger.error(f"Replacement failed: {e}")
            return None

    def _validate_and_save(self, tree: ast.AST, file_path: Path) -> PatchResult:
        """Saves AST to file after basic syntax check (implicit in unparse/parse)."""
        try:
            # Check if we lost comments. If we want to support comments,
            # this is not the place, as AST already lost them.
            content = ast.unparse(tree)

            # Backup
            self._create_backup(file_path)

            file_path.write_text(content, encoding="utf-8")
            return PatchResult(True, new_code=content)
        except Exception as e:
            return PatchResult(False, error=str(e))

    def _validate_and_save_text(self, content: str, file_path: Path) -> PatchResult:
        try:
            if file_path.suffix == '.py':
                try:
                    ast.parse(content)
                except SyntaxError as e:
                     return PatchResult(False, error=f"Syntax Error: {e}")

            self._create_backup(file_path)
            file_path.write_text(content, encoding="utf-8")
            return PatchResult(True, new_code=content)
        except Exception as e:
             return PatchResult(False, error=str(e))

    def _create_backup(self, path: Path):
        backup_path = path.with_suffix(path.suffix + ".bak")
        if path.exists():
            shutil.copy2(path, backup_path)

    def _apply_text_fallback(self, original_content: str, new_code: str) -> Optional[str]:
         # Re-use the existing logic for text patch
         return self._apply_context_patch(original_content, new_code)

    def _apply_context_patch(self, original: str, new_block: str) -> Optional[str]:
        """
        Uses difflib to find a close match for replacement.
        Finds the most similar block in the original content and replaces it.
        """
        original_lines = original.splitlines(keepends=True)
        new_lines = new_block.splitlines(keepends=True)

        if not new_lines:
            return None

        best_ratio = 0.0
        best_match_start = -1
        best_match_end = -1

        header = new_lines[0].strip()
        if not header:
             return None

        candidates = []
        for i, line in enumerate(original_lines):
            # Relaxed matching
            if header in line:
                candidates.append(i)
            elif line.strip() and header.startswith(line.strip()):
                candidates.append(i)

        for start_idx in candidates:
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

             old_block = "".join(original_lines[start_idx:end_idx])
             ratio = difflib.SequenceMatcher(None, old_block, new_block).ratio()

             if ratio > best_ratio:
                 best_ratio = ratio
                 best_match_start = start_idx
                 best_match_end = end_idx

        if best_ratio > 0.6:
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
