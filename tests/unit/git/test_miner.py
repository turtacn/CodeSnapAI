
import pytest
import os
from unittest.mock import MagicMock, patch
from codesage.git.miner import GitMiner
from datetime import datetime

class TestGitMiner:

    @patch("codesage.git.miner.Repo")
    def test_get_file_churn_score(self, mock_repo_class):
        # Setup mock repo
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo

        # Mock commits
        mock_commit1 = MagicMock()
        mock_commit1.stats.files = {"test.py": 1}
        mock_commit2 = MagicMock()
        mock_commit2.stats.files = {"test.py": 1}

        mock_repo.iter_commits.return_value = [mock_commit1, mock_commit2]

        miner = GitMiner(".")

        # Test churn calculation
        # 2 commits in 90 days. 90/30 = 3 months.
        # Score = min(10, 2 / 3) = 0.67
        score = miner.get_file_churn_score("test.py", days=90)
        assert score == 0.67

        # Test max score
        # Reset cache
        miner._churn_cache = {}
        miner._cache_initialized = False

        mock_repo.iter_commits.return_value = [MagicMock(stats=MagicMock(files={"test.py": 1}))] * 50
        score_high = miner.get_file_churn_score("test.py", days=90)
        assert score_high == 10.0

    @patch("codesage.git.miner.Repo")
    def test_get_file_author_count(self, mock_repo_class):
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo

        c1 = MagicMock()
        c1.author.email = "a@example.com"
        c1.stats.files = {"test.py": 1}
        c2 = MagicMock()
        c2.author.email = "b@example.com"
        c2.stats.files = {"test.py": 1}
        c3 = MagicMock()
        c3.author.email = "a@example.com" # Duplicate
        c3.stats.files = {"test.py": 1}

        mock_repo.iter_commits.return_value = [c1, c2, c3]

        miner = GitMiner(".")
        count = miner.get_file_author_count("test.py")
        assert count == 2

    @patch("codesage.git.miner.Repo")
    def test_get_hotspot_files(self, mock_repo_class):
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo

        c1 = MagicMock()
        c1.stats.files = {"file1.py": 1, "file2.py": 1}
        c2 = MagicMock()
        c2.stats.files = {"file1.py": 1}

        mock_repo.iter_commits.return_value = [c1, c2]

        miner = GitMiner(".")
        hotspots = miner.get_hotspot_files(top_n=2)

        assert len(hotspots) == 2
        assert hotspots[0]["path"] == "file1.py"
        assert hotspots[0]["commits"] == 2
        assert hotspots[1]["path"] == "file2.py"
        assert hotspots[1]["commits"] == 1
