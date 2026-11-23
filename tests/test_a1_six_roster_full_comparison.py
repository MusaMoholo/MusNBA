import unittest

import numpy as np

from analysis.a1_f4_six_roster_full_audit import estimates, metrics


class FullComparisonTest(unittest.TestCase):
    def test_seed_bootstrap_uses_all_s06_and_only_d29_survivors(self):
        d29 = np.array([[10.0], [np.nan], [20.0]])
        s06 = np.array([[4.0], [5.0], [9.0]])
        draws = np.array([[0, 1, 2], [0, 0, 1], [1, 2, 2]])
        point, bounds = estimates(d29, s06, draws)
        bootstrap = [15 - 6, 10 - 13 / 3, 20 - 23 / 3]
        self.assertAlmostEqual(point[0], 9)
        np.testing.assert_allclose(bounds[0], np.quantile(bootstrap, [0.025, 0.975]))

    def test_missing_or_unmatched_values_fail(self):
        with self.assertRaises(ValueError):
            estimates(np.array([[np.nan]]), np.array([[1.0]]), np.array([[0]]))
        data = {'player_ids': np.array([str(i) for i in range(7)]),
                'side': np.array([0] * 6 + [1]), 'available': np.ones((1, 7), dtype=bool),
                'final_score': np.array([[100, 90]]), 'player_points': np.ones((1, 7, 5)),
                'minutes': np.ones((1, 7, 5))}
        value, ids, available = metrics(data)
        self.assertEqual(value.shape, (16,))
        with self.assertRaises(ValueError):
            metrics(data, ids, available, np.array([1] * 6 + [0]))


if __name__ == '__main__':
    unittest.main()
