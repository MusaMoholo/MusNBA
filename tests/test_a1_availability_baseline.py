import unittest

import numpy as np

from scripts import a1_availability_baseline as baseline


class AvailabilityBaselineTests(unittest.TestCase):
    def test_starters_use_only_sure_players_and_keep_unknown_positions_unsupported(self):
        states = [{'start_share': 1 - i / 10, 'priority': 20 - i} for i in range(7)]
        probability = np.array([1., 1., 1., 1., 1., .8, .5])
        selected, problem = baseline.choose_starters(states, ['G', 'G', 'F', 'F', 'C', None, None], probability)
        self.assertIsNone(problem)
        self.assertEqual(selected, [0, 1, 2, 3, 4])
        _, problem = baseline.choose_starters(states, ['G', 'G', 'F', 'F', None, 'F', 'C'], probability)
        self.assertEqual(problem, 'unknown_prior_position')
        probability[4] = .8
        _, problem = baseline.choose_starters(states, ['G', 'G', 'F', 'F', 'C', 'F', 'C'], probability)
        self.assertEqual(problem, 'fewer_than_five_sure_candidates')

    def test_starter_fallback_uses_all_only_when_no_sure_player(self):
        states = [{'start_share': 1 - i / 10, 'priority': 20 - i} for i in range(5)]
        selected, problem = baseline.choose_starters(states, ['G', 'G', 'F', 'F', 'C'], np.full(5, .5))
        self.assertIsNone(problem)
        self.assertEqual(selected, list(range(5)))

    def test_log_loss_preserves_infinite_impossible_outcomes(self):
        result = baseline.log_loss(np.array([1., .5]), np.array([0., 1.]))
        self.assertEqual(result['status'], 'infinite')
        self.assertEqual(result['impossible_outcomes'], 1)
        result = baseline.log_loss(np.array([1., .5]), np.array([1., 1.]))
        self.assertAlmostEqual(result['value'], np.log(2) / 2)


if __name__ == '__main__':
    unittest.main()
