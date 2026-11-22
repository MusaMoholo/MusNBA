import unittest

import numpy as np

from scripts import a1_rim_calibration


class RimCalibrationTests(unittest.TestCase):
    def setUp(self):
        self.matchup = np.tile(np.array([0.3, 0.4, 0.5, 0.6, 0.7]), 4)
        self.probabilities = np.tile(np.array([0.5, 0.4, 0.1]), (20, 1))
        self.zones = np.full(20, 'rim')
        self.outcomes = np.array([0, 0, 1, 1, 1, 0, 1, 0, 1, 1,
                                  0, 0, 0, 1, 1, 0, 0, 1, 0, 1])
        self.dates = np.full(20, '2025-12-30')

    def test_training_preserves_make_level_and_learns_existing_matchup_signal(self):
        fitted = a1_rim_calibration.fit(self.probabilities, self.matchup, self.zones, self.outcomes,
                                        self.dates, '2025-12-31')
        adjusted = a1_rim_calibration.apply(self.probabilities, self.matchup, self.zones, fitted)
        self.assertGreater(fitted['slope'], 0)
        np.testing.assert_allclose(adjusted.sum(axis=1), 1.0, rtol=0, atol=1e-12)
        self.assertAlmostEqual(adjusted[:, 1:].sum(axis=1).mean(), 0.5, places=12)
        np.testing.assert_allclose(adjusted[:, 2] / adjusted[:, 1], 0.25, rtol=0, atol=1e-12)
        self.assertLess(fitted['objective'], np.log(2))

    def test_missing_and_non_rim_rows_keep_their_baseline_probabilities(self):
        fitted = a1_rim_calibration.fit(self.probabilities, self.matchup, self.zones, self.outcomes,
                                        self.dates, '2025-12-31')
        matchup = np.array([np.nan, 0.7, 0.7])
        zones = np.array(['rim', 'paint', 'rim'])
        baseline = self.probabilities[:3]
        adjusted = a1_rim_calibration.apply(baseline, matchup, zones, fitted)
        np.testing.assert_array_equal(adjusted[:2], baseline[:2])
        self.assertNotEqual(adjusted[2, 0], baseline[2, 0])

    def test_future_fit_dates_and_invalid_probabilities_are_rejected(self):
        later = self.dates.copy()
        later[0] = '2026-01-01'
        with self.assertRaisesRegex(ValueError, 'dates'):
            a1_rim_calibration.fit(self.probabilities, self.matchup, self.zones, self.outcomes,
                                    later, '2025-12-31')
        invalid = self.probabilities.copy()
        invalid[0, 0] = 0.6
        with self.assertRaisesRegex(ValueError, 'probabilities'):
            a1_rim_calibration.fit(invalid, self.matchup, self.zones, self.outcomes,
                                    self.dates, '2025-12-31')


if __name__ == '__main__':
    unittest.main()
