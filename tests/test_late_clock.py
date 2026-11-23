import unittest

import numpy as np

from scripts.late_clock import ContextClock


class EnumerateDraws:
    def integers(self, high, size):
        return np.arange(size) % high


class ContextClockTests(unittest.TestCase):
    def policy(self):
        return ContextClock({'bridge': {'20': {'x': [2., 24.], 'quiet': .5}},
                             'contextual': {'22': {'x': [.25] * 75 + [1.] * 25, 'quiet': .25}}},
                            {'22': {'opportunities': 100, 'games': 30, 'supported': True}})

    def test_joint_mass_and_clock_scaling(self):
        policy = self.policy()
        policy.rng = EnumerateDraws()
        # clock bin (16,24], margin -5 -> cell 22; enumerate the whole empirical pool.
        time, quiet = policy.sample(np.full(100, 4), np.full(100, 20.), np.full(100, -5), np.zeros(100), np.zeros(100, bool))
        np.testing.assert_array_equal(time[:75], 5.)
        np.testing.assert_array_equal(time[75:], 20.)
        self.assertEqual(int(quiet.sum()), 25)
        self.assertTrue((time[quiet] == 20).all())

    def test_fallbacks_unaffected_periods_and_repeatability(self):
        policy = self.policy()
        period, clock, margin = np.array([1, 4, 4, 5]), np.array([20., 20., 20., 20.]), np.array([-5., 0., np.nan, -5.])
        original, quiet = np.full(4, 7.), np.zeros(4, bool)
        policy.begin(123)
        first = policy.sample(period, clock, margin, original, quiet)
        policy.begin(123)
        second = policy.sample(period, clock, margin, original, quiet)
        for a, b in zip(first, second):
            np.testing.assert_array_equal(a, b)
        self.assertEqual(first[0][0], 7.)
        self.assertEqual(first[0][2], 7.)
        self.assertIn(first[0][1], [2., 20.])
        self.assertIn(first[0][3], [5., 20.])
        np.testing.assert_array_equal(original, 7.)
        np.testing.assert_array_equal(quiet, False)

    def test_invalid_quiet_mass_and_sparse_support_fail(self):
        with self.assertRaises(ValueError):
            ContextClock({'bridge': {'1': {'x': [.5], 'quiet': 1.}}, 'contextual': {}}, {})
        with self.assertRaises(ValueError):
            ContextClock({'bridge': {}, 'contextual': {'0': {'x': [.5] * 100, 'quiet': 0.}}},
                         {'0': {'opportunities': 100, 'games': 29, 'supported': False}})


if __name__ == '__main__':
    unittest.main()
