import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from scripts import a1_availability_cohort as cohort, a1_minutes_audit, a1_minutes_candidate, a1_minutes_diagnose, a1_minutes_fold_eval, a1_minutes_no_report, a1_minutes_unconditional, a1_rotation_diagnose, minutes


class AvailabilityCohortTests(unittest.TestCase):
    def test_membership_uses_only_prior_unique_latest_team(self):
        history = pd.DataFrame([
            ('2026-01-01', 'a', 'old'), ('2026-01-02', 'a', 'new'),
            ('2026-01-02', 'b', 'old'), ('2026-01-02', 'b', 'new'),
            ('2026-01-03', 'c', 'old'), ('2026-01-03', 'a', 'same-day'),
        ], columns=['day', 'player', 'team'])
        members, ambiguous = cohort.prior_membership(history, '2026-01-03')
        self.assertEqual(members.to_dict(orient='records'), [{'prior_day': '2026-01-02', 'player': 'a', 'team': 'new'}])
        self.assertEqual(ambiguous, ['b'])

    def test_participation_keeps_zero_or_missing_minutes_unknown(self):
        box = pd.DataFrame({'did_not_play': [True, False, False, False, None],
                            'minutes': [None, 12, 0, None, 4]})
        labels = cohort.participation(box)
        self.assertEqual(labels.iloc[:2].tolist(), [0.0, 1.0])
        self.assertTrue(labels.iloc[2:].isna().all())
        box.loc[0, 'minutes'] = 1
        with self.assertRaisesRegex(ValueError, 'DNP with positive minutes'):
            cohort.participation(box)
        box.loc[0, 'minutes'] = -1
        with self.assertRaisesRegex(ValueError, 'negative minutes'):
            cohort.participation(box)

    def test_non_nba_team_record_cannot_replace_player_team(self):
        boxes = pd.DataFrame([
            ('1', 'a', '1'), ('2', 'a', 'all-star'),
        ], columns=['game_id', 'player', 'team'])
        regular, exclusions = cohort.nba_team_records(boxes, {str(n) for n in range(1, 31)})
        self.assertEqual(regular['team'].tolist(), ['1'])
        self.assertEqual(exclusions['non_nba_team_box_rows'], 1)
        self.assertEqual(exclusions['non_nba_team_games'], 1)
        self.assertEqual(exclusions['non_nba_team_ids'], ['all-star'])

    def test_minutes_role_join_uses_strictly_prior_appearance(self):
        candidates = pd.DataFrame([
            (pd.Timestamp('2026-01-03'), 'a'),
            (pd.Timestamp('2026-01-01'), 'b'),
        ], columns=['date_et', 'player'])
        events = pd.DataFrame([
            (pd.Timestamp('2026-01-02'), 'a', 25.0),
            (pd.Timestamp('2026-01-03'), 'a', 5.0),
            (pd.Timestamp('2026-01-01'), 'b', 30.0),
        ], columns=['day', 'player', 'recent'])
        joined = a1_minutes_audit.prior_join(candidates, events, ['recent']).set_index('player')
        self.assertEqual(joined.loc['a', 'recent'], 25.0)
        self.assertTrue(pd.isna(joined.loc['b', 'recent']))

    def test_rotation_replay_matches_d29_and_excludes_same_day_dnp(self):
        games = []
        for date, game, players in [('2024-01-01', 'g1', range(6)),
                                    ('2024-01-02', 'g2', range(5))]:
            for player in players:
                games.append((date, game, '1', str(player), 2024, 40.0, player < 5))
        pg = pd.DataFrame(games, columns=['date_et', 'game_id', 'team', 'player', 'season', 'reg', 'starter'])
        cd = {('g2', '1'): ['5']}
        events = a1_minutes_diagnose.rotation_events(pg, cd)
        _, latest, _ = minutes.state_pass(pg, cd=cd)
        final = events.sort_values('day').drop_duplicates('player', keep='last').set_index('player')
        for player, state in latest.items():
            self.assertAlmostEqual(final.loc[player, 'rotation_share'], state['rotation'])
        candidates = pd.DataFrame({'date_et': [pd.Timestamp('2024-01-02')], 'player': ['5']})
        before = a1_minutes_audit.prior_join(candidates, events, ['rotation_share'])
        day_one = events[(events['player'] == '5') & (events['date_et'] == '2024-01-01')]
        self.assertEqual(before['rotation_share'].iloc[0], day_one['rotation_share'].iloc[0])
        conflict = a1_minutes_diagnose.rotation_events(pg, {('g2', '1'): ['4']})
        self.assertEqual(conflict.attrs['conflicting_play_and_coach_dnp'], 1)
        with self.assertRaisesRegex(ValueError, 'duplicate play or DNP'):
            a1_minutes_diagnose.rotation_events(pg, {('g2', '1'): ['4', '4']})

    def test_rotation_weight_counterfactual_preserves_team_minutes(self):
        players = pd.DataFrame({
            'game_id': ['g'] * 10, 'team': ['1'] * 10,
            'healthy': [36.0] * 5 + [12.0] * 5, 'cap': [40.0] * 10,
            'start_share': [1.0] * 5 + [0.0] * 5, 'ramp': [1.0] * 10,
            'rotation_share': [1.0] * 9 + [0.1],
        })
        out = a1_rotation_diagnose.weighted_targets(players)
        self.assertAlmostEqual(out['target_rotation_weighted'].sum(), 240)
        self.assertAlmostEqual(out['target_known_play'].sum(), 240)
        self.assertLess(out['target_rotation_weighted'].iloc[-1], out['target_known_play'].iloc[-1])

    def test_candidate_history_filters_all_star_and_rejects_same_day_leakage(self):
        games = pd.DataFrame([
            ('g1', '2024-01-01', '1', 'p'), ('g1', '2024-01-01', '2', 'q'),
            ('asg', '2024-01-02', 'all-star', 'p'),
            ('g2', '2024-01-03', '1', 'p'), ('g2', '2024-01-03', '2', 'q'),
        ], columns=['game_id', 'date_et', 'team', 'player'])
        teams = {str(n) for n in range(1, 31)}
        self.assertEqual(a1_minutes_candidate.nba_history(games, teams)['game_id'].tolist(), ['g1', 'g1', 'g2', 'g2'])
        bad = pd.concat([games, pd.DataFrame([('g3', '2024-01-03', '2', 'p')], columns=games.columns)])
        with self.assertRaisesRegex(ValueError, 'multiple player games'):
            a1_minutes_candidate.nba_history(bad, teams)
        bad = pd.concat([games, pd.DataFrame([('g3', '2024-01-03', '1', 'q')], columns=games.columns)])
        with self.assertRaisesRegex(ValueError, 'multiple player games'):
            a1_minutes_candidate.nba_history(bad, teams)
        bad = pd.concat([games, pd.DataFrame([('g3', '2024-01-03', '1', 'r')], columns=games.columns)])
        with self.assertRaisesRegex(ValueError, 'multiple team games'):
            a1_minutes_candidate.nba_history(bad, teams)
        bad = pd.concat([games, pd.DataFrame([('g3', '2024-01-04', '1', 'r')], columns=games.columns)])
        with self.assertRaisesRegex(ValueError, 'without exactly two NBA teams'):
            a1_minutes_candidate.nba_history(bad, teams)

    def test_candidate_matches_d29_when_history_has_only_nba_games(self):
        games = []
        for date, game in [('2024-01-01', 'g1'), ('2024-01-02', 'g2')]:
            for team in ('1', '2'):
                for player in range(6):
                    games.append((date, game, team, f'{team}-{player}', 2024, 40.0, player < 5))
        pg = pd.DataFrame(games, columns=['date_et', 'game_id', 'team', 'player', 'season', 'reg', 'starter'])
        with patch.object(minutes, 'player_games', return_value=pg), patch.object(minutes, 'coach_dnps', return_value={}):
            control = minutes.build('2024-01-03', include_current=False)
            candidate = a1_minutes_candidate.build('2024-01-03', include_current=False)
        pd.testing.assert_frame_equal(control['rows'], candidate['rows'])
        self.assertEqual(control['latest'], candidate['latest'])
        self.assertEqual(control['ramp'], candidate['ramp'])

    def test_candidate_conserves_minutes_for_short_rosters_and_absences(self):
        rng = np.random.default_rng(20261122)
        for n in (5, 6, 7, 10, 15):
            mu = np.full(n, 240 / n)
            cap = np.full(n, 48.0)
            sd = np.full(n, 7.0)
            drawn = a1_minutes_candidate.redraw(mu, cap, sd, 500, np.random.default_rng(11))
            repeated = a1_minutes_candidate.redraw(mu, cap, sd, 500, np.random.default_rng(11))
            np.testing.assert_array_equal(drawn, repeated)
            np.testing.assert_allclose(drawn.sum(axis=1), 240, rtol=0, atol=1e-10)
            self.assertTrue(((drawn >= 0) & (drawn <= 48)).all())
            for _ in range(20):
                healthy = rng.uniform(0, 40, n)
                target = a1_minutes_candidate.allocate(healthy, rng.uniform(6, 46, n), healthy, gamma=0, room=1)
                self.assertAlmostEqual(float(target.sum()), 240, places=10)
                self.assertTrue(((target >= 0) & (target <= 48)).all())
        states = [{'healthy': h, 'cap': 40.0, 'ramp': 1.0, 'rotation': 1.0, 'priority': h}
                  for h in [36.0] * 5 + [12.0] * 5]
        original = a1_minutes_candidate.game_targets(states)
        remaining = a1_minutes_candidate.game_targets(states[1:])
        self.assertAlmostEqual(float(remaining.sum()), 240, places=10)
        self.assertAlmostEqual(float((remaining - original[1:]).sum()), float(original[0]), places=10)
        with self.assertRaisesRegex(ValueError, 'fewer than five'):
            a1_minutes_candidate.redraw(np.ones(4), np.ones(4) * 48, np.ones(4), 1, rng)
        with self.assertRaisesRegex(ValueError, 'positive target'):
            a1_minutes_candidate.redraw(np.zeros(5), np.ones(5) * 48, np.zeros(5), 1, rng)

    @unittest.expectedFailure
    def test_strict_redistribution_preserves_zero_when_active_players_can_fill(self):
        targets = np.array([
            [48.0, 48.0, 48.0, 48.0, 47.9999, 0.0],
            [30.0, 30.0, 30.0, 30.0, 30.0, 0.0],
            [48.0, 48.0, 48.0, 48.0, 0.0, 0.0],
        ])
        result = a1_minutes_candidate.legal_minutes(targets)
        np.testing.assert_array_equal(result[:2, -1], [0.0, 0.0])
        self.assertTrue((result[2, -2:] > 0).all())
        np.testing.assert_allclose(result.sum(axis=1), 240.0, rtol=0, atol=1e-10)
        self.assertTrue(((result >= 0) & (result <= 48)).all())

    def test_fold_minute_distribution_reuses_deterministic_stream(self):
        states = [{'healthy': 24.0, 'cap': 40.0, 'ramp': 1.0, 'rotation': 1.0, 'priority': 24.0}
                  for _ in range(10)]
        sd = {'edges': [0, 10, 20, 30, 40, 50], 'sd': {3: 4.0}}
        actual = np.full(10, 24.0)
        first = a1_minutes_fold_eval.distribution(states, sd, actual, 123, True, 100)
        second = a1_minutes_fold_eval.distribution(states, sd, actual, 123, True, 100)
        for key in ('mean', 'crps', 'covered'):
            np.testing.assert_array_equal(first[key], second[key])
        self.assertTrue(((first['covered'] == 0) | (first['covered'] == 1)).all())

    def test_unconditional_actuals_keep_unknowns_and_conflicts_missing(self):
        roster = pd.DataFrame({
            'game_id': ['g'] * 5, 'team': ['t'] * 5, 'player': list('abcde'),
            'played': [0.0, 0.0, 1.0, 1.0, np.nan],
        })
        observed = pd.DataFrame({
            'game_id': ['g', 'g'], 'team': ['t', 't'], 'player': ['a', 'c'], 'reg': [5.0, 20.0],
        })
        rows = a1_minutes_unconditional.attach_actuals(roster, observed).set_index('player')
        self.assertTrue(rows.loc['a', 'source_conflict'])
        self.assertTrue(pd.isna(rows.loc['a', 'actual_reg']))
        self.assertEqual(rows.loc['b', 'actual_reg'], 0)
        self.assertEqual(rows.loc['c', 'actual_reg'], 20)
        self.assertTrue(pd.isna(rows.loc['d', 'actual_reg']))
        self.assertTrue(pd.isna(rows.loc['e', 'actual_reg']))

    def test_unconditional_distribution_scores_zero_but_not_unknown(self):
        states = [{'healthy': 24.0, 'cap': 40.0, 'ramp': 1.0, 'rotation': 1.0, 'priority': 24.0}
                  for _ in range(10)]
        sd = {'edges': [0, 10, 20, 30, 40, 50], 'sd': {3: 4.0}}
        actual = np.array([0.0, np.nan] + [24.0] * 8)
        played = np.array([0.0, np.nan] + [1.0] * 8)
        result = a1_minutes_unconditional.distribution(states, sd, actual, played, 123, True, 100)
        self.assertTrue(np.isfinite(result['crps'][0]))
        self.assertTrue(np.isnan(result['crps'][1]))
        self.assertTrue(np.isnan(result['play_brier'][1]))
        self.assertTrue((result['play_probability'] >= 0).all() and (result['play_probability'] <= 1).all())

    def test_no_report_patterns_are_deterministic_and_legal(self):
        probability = np.full(6, 0.7)
        patterns, rejected = a1_minutes_no_report.availability_patterns(probability, 200, 17)
        repeated, rejected_again = a1_minutes_no_report.availability_patterns(probability, 200, 17)
        np.testing.assert_array_equal(patterns, repeated)
        self.assertEqual(rejected, rejected_again)
        self.assertGreater(rejected, 0)
        self.assertTrue((patterns.sum(axis=1) >= 5).all())
        with self.assertRaisesRegex(ValueError, 'could not draw legal'):
            a1_minutes_no_report.availability_patterns(np.zeros(5), 1, 17)

    def test_no_report_targets_reallocate_only_available_players(self):
        states = [{'healthy': 35.0, 'cap': 46.0, 'ramp': 1.0, 'rotation': 1.0, 'priority': 35.0}
                  for _ in range(6)]
        sd = {'edges': [0, 10, 20, 30, 40, 50], 'sd': {5: 4.0}}
        available = np.array([[True] * 6, [True] * 5 + [False]])
        draws = a1_minutes_no_report.target_draws(states, sd, available, ('test',), True)
        repeated = a1_minutes_no_report.target_draws(states, sd, available, ('test',), True)
        np.testing.assert_array_equal(draws, repeated)
        np.testing.assert_allclose(draws.sum(axis=1), 240, rtol=0, atol=1e-10)
        self.assertEqual(draws[1, 5], 0)
        self.assertTrue((draws <= 48).all())

    def test_report_and_rows_cannot_overwrite_each_other(self):
        argv = ['a1_availability_cohort.py', 'run', '--output', '/tmp/a1-same-path',
                '--rows-output', '/tmp/a1-same-path']
        with patch('sys.argv', argv), patch.object(cohort, 'build') as build:
            with self.assertRaisesRegex(ValueError, 'different output paths'):
                cohort.main()
            build.assert_not_called()


if __name__ == '__main__':
    unittest.main()
