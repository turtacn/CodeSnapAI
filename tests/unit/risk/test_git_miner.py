import unittest
from unittest.mock import patch, MagicMock
from codesage.history.git_miner import GitMiner
from datetime import datetime

class TestGitMiner(unittest.TestCase):

    @patch('subprocess.run')
    def test_get_file_churn(self, mock_run):
        # Mock git log output
        # Timestamp followed by files
        # Commit 1: 1700000000, file1.py
        # Commit 2: 1699900000, file1.py, file2.py
        # Commit 3: 1699800000, file2.py

        mock_output = """1700000000
file1.py

1699900000
file1.py
file2.py

1699800000
file2.py"""

        mock_process = MagicMock()
        mock_process.stdout = mock_output
        mock_process.return_code = 0
        mock_run.return_value = mock_process

        miner = GitMiner()

        # Check churn
        churn1 = miner.get_file_churn("file1.py")
        churn2 = miner.get_file_churn("file2.py")
        churn3 = miner.get_file_churn("file3.py")

        self.assertEqual(churn1, 2)
        self.assertEqual(churn2, 2)
        self.assertEqual(churn3, 0)

        # Check hotspots
        hotspots = miner.get_hotspots(limit=2)
        # file1: 2, file2: 2. Order might vary but counts should be correct.
        self.assertEqual(len(hotspots), 2)
        self.assertEqual(hotspots[0][1], 2)

        # Check last modified
        # file1 last modified at 1700000000
        last_mod1 = miner.get_last_modified("file1.py")
        self.assertEqual(last_mod1, datetime.fromtimestamp(1700000000))

if __name__ == '__main__':
    unittest.main()
