"""Git-based Rollback Manager
Implements the "Automated Rollback" capability from Architecture Design Section 3.2.1
"""
import logging
from typing import List
import time
from git import Repo, GitCommandError, Actor

logger = logging.getLogger(__name__)

class RollbackManager:
    """
    Manages patch application rollbacks using Git.

    Core Capabilities:
    1. Automated patch branch creation (Change Isolation)
    2. Atomic rollback based on Git commits
    3. Rollback history tracking (Audit requirements)
    """

    def __init__(self, repo_path: str):
        self.repo = Repo(repo_path)
        self.patch_branch_prefix = "codesage/patch-"

    def create_patch_branch(self, task_id: str) -> str:
        """
        Creates an isolated branch for a patch task.

        Branch naming: codesage/patch-{task_id}-{timestamp}

        Returns:
            Branch name
        """
        timestamp = int(time.time())
        branch_name = f"{self.patch_branch_prefix}{task_id}-{timestamp}"

        # Ensure we are on a clean slate or handle it.
        # For now, we assume we branch off the current HEAD.
        current_branch = self.repo.active_branch.name

        # Create new branch from current HEAD
        new_branch = self.repo.create_head(branch_name)
        new_branch.checkout()

        logger.info(f"Created patch branch: {branch_name} from {current_branch}")
        return branch_name

    def commit_patch(self, file_paths: List[str], task_id: str, message: str) -> str:
        """
        Commits patch changes (atomic operation).

        Returns:
            Commit SHA
        """
        # Add files to index
        self.repo.index.add(file_paths)

        commit = self.repo.index.commit(
            message=f"[CodeSnapAI] {message}\n\nTask ID: {task_id}",
            author=self._get_bot_author()
        )
        return commit.hexsha

    def rollback_patch(self, commit_sha: str, reason: str) -> bool:
        """
        Rolls back a specific patch (Git revert).

        Args:
            commit_sha: The commit to rollback
            reason: Reason for rollback (logged)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Use git revert to preserve history
            self.repo.git.revert(commit_sha, no_edit=True)

            logger.warning(
                f"Rolled back patch {commit_sha[:8]}: {reason}"
            )
            return True

        except GitCommandError as e:
            logger.error(f"Rollback failed: {e}")
            return False

    def merge_to_main(self, patch_branch: str, target_branch: str = 'main') -> bool:
        """
        Merges the patch branch into the target branch (after verification).

        Strategy: --no-ff (Preserve branch history)
        """
        try:
            # Checkout target branch
            if target_branch not in self.repo.heads:
                 logger.error(f"Target branch {target_branch} does not exist")
                 return False

            main_branch = self.repo.heads[target_branch]
            main_branch.checkout()

            # Merge patch branch
            self.repo.git.merge(patch_branch, no_ff=True, m=f"Merge {patch_branch}")

            # Delete patch branch
            if patch_branch in self.repo.heads:
                 self.repo.delete_head(patch_branch, force=True)

            logger.info(f"Successfully merged {patch_branch} to {target_branch}")
            return True

        except GitCommandError as e:
            logger.error(f"Merge failed: {e}")
            return False

    def _get_bot_author(self):
        """Returns CodeSnapAI Bot's Git Author info"""
        return Actor("CodeSnapAI Bot", "bot@codesnapai.dev")
