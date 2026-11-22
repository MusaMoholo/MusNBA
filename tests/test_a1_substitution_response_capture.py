import unittest

import numpy as np
import pandas as pd

from scripts import a1_substitution_response_audit as audit
from scripts import a1_substitution_response_capture as capture


class TimeoutStateCaptureTests(unittest.TestCase):
    def test_recorded_margin_foul_and_stint_boundaries(self):
        codes = capture.state_codes(
            np.array([1, 2, 3, 4, 5]), np.array([-15, 15, -5, 6, 0]),
            np.array([2, 2, 4, 4, 5]), np.array([0., 239., 240., 479., 480.]))
        self.assertEqual(codes['margin'].tolist(), [0, 1, 2, 3, 2])
        self.assertEqual(codes['period'].tolist(), [0, 1, 2, 3, 4])
        self.assertEqual(codes['foul_trouble'].tolist(), [1, 0, 1, 0, 1])
        self.assertEqual(codes['duration'].tolist(), [0, 0, 1, 1, 2])

    def test_invalid_state_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'invalid'):
            capture.state_codes(np.array([1]), np.array([0]), np.array([0]), np.array([-1.]))

    def test_paired_game_rates_and_unsupported_cells(self):
        ids = [str(i) for i in range(30)]
        real = pd.DataFrame([{'game_id': game, 'player': str(player), 'changed': player < 2}
                             for game in ids for player in range(4)])
        simulated = pd.DataFrame([{'game_id': game, 'player': str(player), 'decisions': 10, 'exits': 2}
                                  for game in ids for player in range(4)])
        weights = np.ones((3, len(ids)), dtype=int)
        result = audit.rate_comparison(real, simulated, ids, weights)
        self.assertEqual(result['status'], 'ok')
        self.assertAlmostEqual(result['recorded_exit_rate'], 0.5)
        self.assertAlmostEqual(result['simulated_exit_rate'], 0.2)
        np.testing.assert_allclose(result['simulated_minus_recorded_ci_95'], [-0.3, -0.3])
        sparse = audit.rate_comparison(real.iloc[:1], simulated.iloc[:1], ids, weights)
        self.assertEqual(sparse['status'], 'insufficient_sample')
        self.assertIsNone(sparse['simulated_minus_recorded_ci_95'])


if __name__ == '__main__':
    unittest.main()
