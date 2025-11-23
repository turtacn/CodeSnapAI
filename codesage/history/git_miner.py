import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class GitMiner:
    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path
        self._churn_cache: Dict[str, int] = {}
        self._last_modified_cache: Dict[str, datetime] = {}
        self._is_initialized = False

    def _run_git_cmd(self, args: List[str]) -> str:
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.warning(f"Git command failed: {e}")
            return ""

    def _initialize_stats(self, since_days: int = 90):
        """
        Parses git log once to populate churn and last modified dates.
        """
        if self._is_initialized:
            return

        since_date = (datetime.now() - timedelta(days=since_days)).strftime("%Y-%m-%d")

        # Get all commits with file changes
        # Format: timestamp|filename
        cmd = [
            "log",
            f"--since={since_date}",
            "--pretty=format:%at", # Timestamp
            "--name-only",         # List changed files
        ]

        output = self._run_git_cmd(cmd)

        current_timestamp = None

        for line in output.split('\n'):
            line = line.strip()
            if not line:
                continue

            # If line is a timestamp (digits)
            if line.isdigit():
                current_timestamp = int(line)
                continue

            # Otherwise it's a filename
            file_path = line
            self._churn_cache[file_path] = self._churn_cache.get(file_path, 0) + 1

            if current_timestamp:
                dt = datetime.fromtimestamp(current_timestamp)
                if file_path not in self._last_modified_cache:
                    self._last_modified_cache[file_path] = dt
                else:
                    # git log is usually newest first, so we keep the first one we see (max)
                    # or if we process in order, the first one is indeed the latest.
                    # Wait, git log default is reverse chronological (newest first).
                    # So the first time we see a file, it's the latest commit.
                    # We only set it if not present.
                    pass

        self._is_initialized = True

    def get_file_churn(self, file_path: str, since_days: int = 90) -> int:
        """
        Returns the number of times a file has been changed in the last `since_days`.
        """
        self._initialize_stats(since_days)
        return self._churn_cache.get(file_path, 0)

    def get_last_modified(self, file_path: str) -> Optional[datetime]:
        """
        Returns the last modification time of the file from git history.
        """
        self._initialize_stats() # Use default since_days or make sure we have data
        return self._last_modified_cache.get(file_path)

    def get_hotspots(self, limit: int = 10, since_days: int = 90) -> List[Tuple[str, int]]:
        """
        Returns the top `limit` modified files.
        """
        self._initialize_stats(since_days)
        sorted_files = sorted(self._churn_cache.items(), key=lambda x: x[1], reverse=True)
        return sorted_files[:limit]
