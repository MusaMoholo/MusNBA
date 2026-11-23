import unittest

import numpy as np
import pandas as pd

from analysis.a2_world_diagnostics import cells, late_terms, joint


class WorldDiagnosticTests(unittest.TestCase):
    def test_disjoint_clock_and_score_edges(self):
        self.assertEqual(cells(np.array([24, 24.1, 60, 60.1]), np.array([-9, -8, 0, 9])).tolist(), [0, 8, 10, 20])
        counts = late_terms(np.array([24., 120.]), np.array([0, 1]), np.array([3., 2.]),
                            np.array([True, False]), np.array([0, 1]), np.array([0, 1]))
        self.assertEqual(counts[:, 0].sum(), 2)
        self.assertEqual(counts[:, 2].sum(), 1)
        with self.assertRaises(ValueError):
            late_terms(np.array([0.]), np.array([0]), np.array([1.]), np.array([False]), np.array([1]), np.array([0]))

    def test_observed_and_simulated_dependence_use_distinct_pairs(self):
        rows = pd.DataFrame({'game_id': ['1'] * 4, 'player': list('abcd'), 'team': ['0', '0', '1', '1'],
                             'tier': ['starter'] * 4, 'minutes': [0., 1., 2., 3.], 'points': [0., 2., 4., 6.]})
        m = np.array([[9., 11., 9., 11.], [11., 9., 11., 9.]])
        worlds = {'1': {'ids': list('abcd'), 'minutes': m, 'points': m * 2}}
        result = joint(rows, worlds, ['1'], np.ones((2, 1)), False)['metrics']
        self.assertAlmostEqual(result['teammate_MIN']['observed_role_centred_error_product'], .75)
        self.assertAlmostEqual(result['opponent_MIN']['observed_role_centred_error_product'], -1.)
        self.assertAlmostEqual(result['teammate_MIN']['within_world_covariance'], -1.)
        self.assertAlmostEqual(result['opponent_MIN']['within_world_covariance'], 0.)
