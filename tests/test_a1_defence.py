import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from scripts import a1_rim_calibration, a1_rim_screen, a1_tracking_audit, a1_tracking_features, a1_tracking_screen


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

    def test_training_tail_reports_actual_dates_not_datetime_integer_units(self):
        days = np.array([f'2024-01-{day:02d}' for day in range(1, 12)] + ['2024-02-01'])
        all_train, tail, earlier, start = a1_rim_screen.training_tail_masks(days, '2024-01-11')
        self.assertEqual(start, '2024-01-10')
        np.testing.assert_array_equal(days[tail], ['2024-01-10', '2024-01-11'])
        self.assertEqual(int(all_train.sum()), 11)
        self.assertEqual(int(earlier.sum()), 9)


class TrackingFeatureTests(unittest.TestCase):
    def test_missing_and_nonfinite_nba_player_ids_are_rejected(self):
        for person in (None, float('inf')):
            logs = pd.DataFrame([('2024-01-01', person, 'BOS')],
                                columns=['date', 'PLAYER_ID', 'TEAM_ABBREVIATION'])
            with self.subTest(person=person), \
                    patch.object(a1_tracking_features.nbastats, 'nba_tables', return_value=(pd.DataFrame(), logs)):
                with self.assertRaisesRegex(ValueError, 'missing or non-finite'):
                    a1_tracking_features.load_tracking()
                with self.assertRaisesRegex(ValueError, 'missing or non-finite'):
                    a1_tracking_audit.sources()

    def test_prior_rates_exclude_same_day_and_leave_unseen_players_missing(self):
        source = pd.DataFrame([
            ('2025-01-01', 'a', 'rim', 2, 4), ('2025-01-02', 'a', 'rim', 0, 6),
            ('2025-01-01', 'b', 'rim', 0, 0), ('2025-01-01', 'a', 'three', 1, 2),
        ], columns=['day', 'player', 'bucket', 'made', 'attempted'])
        history = a1_tracking_features.cumulative_history(source)
        targets = pd.DataFrame([('2025-01-02', 'a'), ('2025-01-03', 'a'),
                                ('2025-01-02', 'b'), ('2025-01-01', 'a'), ('2025-01-03', 'c')],
                               columns=['day', 'player'])
        prior = a1_tracking_features.previous_rates(targets, history, 'rim')
        np.testing.assert_allclose(prior['rate'].to_numpy()[:2], [0.5, 0.2], rtol=0, atol=1e-12)
        self.assertTrue(prior['rate'].iloc[2:].isna().all())
        self.assertEqual(str(prior['source_day'].iloc[0].date()), '2025-01-01')
        duplicate = pd.concat([source, source.iloc[[0]]], ignore_index=True)
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            a1_tracking_features.cumulative_history(duplicate)

    def test_defender_five_requires_distinct_players_and_matching_team(self):
        shots = pd.DataFrame([
            ('g1', '2025-01-02', '10', 'a', 'b', 'c', 'd', 'e'),
            ('g1', '2025-01-02', '10', 'a', 'b', 'c', 'd', 'd'),
        ], columns=['game_id', 'date_et', 'defense', 'def_1', 'def_2', 'def_3', 'def_4', 'def_5'])
        pregame = pd.DataFrame([('g1', p, '10' if p != 'e' else '11') for p in 'abcde'],
                               columns=['game_id', 'player', 'team'])
        targets, valid_five = a1_tracking_features.player_game_targets(shots, pregame)
        np.testing.assert_array_equal(valid_five, [True, False])
        self.assertFalse(targets.set_index('player').loc['e', 'team_valid'])
        self.assertTrue(targets.set_index('player').loc['a', 'team_valid'])

    def test_tracking_buckets_change_only_their_actual_zone_and_known_fives(self):
        zones = np.array(['rim', 'paint', 'corner3', 'above3', 'rim'])
        rates = np.array([0.6, 0.6, 0.6, 0.6, np.nan])
        control = np.tile([0.5, 0.4, 0.1], (5, 1))
        calibration = {'center': 0.5, 'slope': 1.0, 'intercept': 0.0}
        rim = a1_rim_calibration.apply(control, rates, a1_tracking_screen.source_zone(zones, 'rim'), calibration)
        candidate = a1_rim_calibration.apply(rim, rates, a1_tracking_screen.source_zone(zones, 'three'), calibration)
        np.testing.assert_array_equal(candidate[[1, 4]], control[[1, 4]])
        self.assertTrue((candidate[[0, 2, 3], 0] < control[[0, 2, 3], 0]).all())
        with self.assertRaisesRegex(ValueError, 'unknown tracking bucket'):
            a1_tracking_screen.source_zone(zones, 'unregistered')


if __name__ == '__main__':
    unittest.main()
