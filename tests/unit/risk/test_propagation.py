import unittest
from codesage.risk.propagation import RiskPropagator

class TestRiskPropagator(unittest.TestCase):
    def test_propagate_chain(self):
        # A -> B -> C
        # A depends on B, B depends on C
        # C is risky (100), B is 0, A is 0.
        # Expect C risk to propagate to B, then to A.

        graph = {
            "A": ["B"],
            "B": ["C"],
            "C": []
        }

        base_scores = {
            "A": 0.0,
            "B": 0.0,
            "C": 100.0
        }

        propagator = RiskPropagator(attenuation_factor=0.5, max_iterations=5)
        final_scores = propagator.propagate(graph, base_scores)

        # Iteration 1:
        # B gets 0.5 * 100 = 50.
        # A gets 0.5 * 0 = 0 (using old scores usually, but let's see implementation order).
        # If implementation updates in place or uses previous round?
        # My implementation uses `current_scores = final_scores.copy()` at start of loop, so it uses previous round values.
        # So Iteration 1: B=50, A=0.
        # Iteration 2: B=50 (C didn't change), A gets 0.5 * 50 = 25.

        self.assertEqual(final_scores["C"], 100.0)
        self.assertEqual(final_scores["B"], 50.0)
        self.assertEqual(final_scores["A"], 25.0)

    def test_propagate_cycle(self):
        # A <-> B
        graph = {
            "A": ["B"],
            "B": ["A"]
        }
        base_scores = {
            "A": 10.0,
            "B": 10.0
        }

        propagator = RiskPropagator(attenuation_factor=0.1, max_iterations=10)
        final_scores = propagator.propagate(graph, base_scores)

        # It should converge to something slightly higher than 10.
        # A = 10 + 0.1 * B
        # B = 10 + 0.1 * A
        # A = 10 + 0.1(10 + 0.1A) = 10 + 1 + 0.01A => 0.99A = 11 => A = 11.11

        self.assertAlmostEqual(final_scores["A"], 11.11, delta=0.1)
        self.assertAlmostEqual(final_scores["B"], 11.11, delta=0.1)

if __name__ == '__main__':
    unittest.main()
