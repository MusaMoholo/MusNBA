import unittest

import numpy as np

from analysis.a1_branch_game_summary_audit import audit_distribution


class GameSummaryAuditTests(unittest.TestCase):
    def test_detects_incorrect_weighted_histogram_and_quantiles(self):
        arrays = [np.array([1.0, 2.0]), np.array([2.0, np.nan])]
        valid = {'min': 0, 'hist': [0, 1, 4], 'mean': 1.8, 'sd': 0.4,
                 'q': [1, 2, 2, 2, 2], 'defined_mass': 5, 'total_mass': 8}
        audit_distribution(valid, arrays, [1, 3], 'example')
        with self.assertRaisesRegex(ValueError, 'histogram'):
            audit_distribution({**valid, 'hist': [0, 2, 3]}, arrays, [1, 3], 'example')
        with self.assertRaisesRegex(ValueError, 'quantiles'):
            audit_distribution({**valid, 'q': [2, 2, 2, 2, 2]}, arrays, [1, 3], 'example')
        with self.assertRaisesRegex(ValueError, 'defined mass'):
            audit_distribution({**valid, 'defined_mass': 8}, arrays, [1, 3], 'example')


if __name__ == '__main__':
    unittest.main()
