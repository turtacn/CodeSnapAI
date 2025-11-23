import unittest
import os
from codesage.risk.scorers.coverage_scorer import CoverageScorer

class TestCoverageScorer(unittest.TestCase):
    def setUp(self):
        self.sample_xml = "tests/fixtures/reports/coverage_sample.xml"

    def test_parse_coverage(self):
        scorer = CoverageScorer(self.sample_xml)

        # main.py has 1.0 coverage
        self.assertEqual(scorer.get_coverage("src/main.py"), 1.0)

        # utils.py has 0.0 coverage
        self.assertEqual(scorer.get_coverage("src/utils.py"), 0.0)

        # Unlisted file (but report exists) -> 0.0
        self.assertEqual(scorer.get_coverage("src/unknown.py"), 0.0)

    def test_no_coverage_file(self):
        scorer = CoverageScorer(None)
        # Should return 1.0 (no penalty)
        self.assertEqual(scorer.get_coverage("src/main.py"), 1.0)

    def test_invalid_file(self):
        scorer = CoverageScorer("non_existent.xml")
        # Should log warning but not crash, and return 1.0
        self.assertEqual(scorer.get_coverage("src/main.py"), 1.0)

if __name__ == '__main__':
    unittest.main()
