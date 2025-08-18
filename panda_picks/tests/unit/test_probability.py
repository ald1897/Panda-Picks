import math
import unittest

from panda_picks.analysis.utils.probability import calculate_win_probability
from panda_picks.config.settings import Settings


class TestProbability(unittest.TestCase):
    def test_zero_advantage(self):
        self.assertAlmostEqual(calculate_win_probability(0), 0.5, places=6)

    def test_positive_advantage(self):
        self.assertGreater(calculate_win_probability(3), 0.5)

    def test_negative_advantage(self):
        self.assertLess(calculate_win_probability(-3), 0.5)

    def test_formula_equivalence(self):
        adv = 2.5
        expected = 1.0 / (1 + math.exp(-Settings.K_PROB_SCALE * adv))
        self.assertAlmostEqual(calculate_win_probability(adv), expected, places=12)


if __name__ == '__main__':
    unittest.main()

