"""Independent discrete-coverage examples, including atoms and unsupported outcomes."""
import unittest

import numpy as np
import pandas as pd

from analysis.rule3_confirmation import expected_coverage
from analysis.rule3_capture_audit import scores
from analysis.rule3_scores import distribution


class CoverageTests(unittest.TestCase):
    def test_analytic_atoms_and_gaps(self):
        for y, expected in ((0, .8), (1, .8), (.5, 1.), (-1, 0.), (2, 0.)):
            self.assertAlmostEqual(expected_coverage([0, 0, 1, 1], y), expected)
            self.assertAlmostEqual(scores([0, 0, 1, 1], y)[2], expected)
        self.assertAlmostEqual(expected_coverage([3] * 10, 3), .8)

    def test_crps_independent_pairwise_definition(self):
        x = np.array([-2., 0., 0., 5.])
        expected = np.abs(x - 1.).mean() - .5 * np.abs(x[:, None] - x[None, :]).mean()
        self.assertAlmostEqual(scores(x, 1.)[1], expected)

    def test_unknown_data_fails(self):
        for x, y in (([], 0), ([0, np.nan], 0), ([0], np.nan)):
            with self.assertRaises(ValueError):
                expected_coverage(x, y)
            with self.assertRaises(ValueError):
                scores(x, y)

    def test_integrated_coverage_preserves_scores_and_the_legacy_diagnostic(self):
        rows = pd.DataFrame({'game_id': [str(i // 4) for i in range(120)]})
        for side, coverage in (('control', .8), ('candidate', .7)):
            for key, value in (('actual', 2.), ('sim', 2.), ('crps', .5), ('pit', .5), ('coverage_expected', coverage)):
                rows['pts_' + key + '_' + side] = value
        result = distribution(rows, 'pts', [str(i) for i in range(30)], np.ones((20, 30)), True)
        self.assertAlmostEqual(result['crps']['change'], 0.)
        self.assertAlmostEqual(result['coverage']['change'], .1)
        self.assertAlmostEqual(result['coverage']['ci_95'][0], .1)
        self.assertAlmostEqual(result['coverage_legacy_randomised_pit']['change'], 0.)
