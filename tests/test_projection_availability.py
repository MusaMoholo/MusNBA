import hashlib
import json
import unittest
import warnings
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pandas as pd

from scripts import engine, minutes, projection


class ProjectionAvailabilityTests(unittest.TestCase):
    def test_shooting_distributions_exclude_no_attempts_and_preserve_counts(self):
        counts = {
            'fgm': np.array([0, 1, 1, 2]), 'fga': np.array([0, 2, 1, 3]),
            'fg3m': np.array([0, 0, 1, 0]), 'fg3a': np.array([0, 1, 1, 0]),
            'ftm': np.zeros(4, dtype=int), 'fta': np.zeros(4, dtype=int),
        }
        got = projection.shooting_summaries(counts)
        self.assertEqual((got['fgpct']['defined'], got['fgpct']['total']), (3, 4))
        self.assertEqual([got['fgpct']['hist'][n] for n in (50, 67, 100)], [1, 1, 1])
        self.assertEqual((got['fg3pct']['defined'], got['fg3pct']['hist'][0]), (2, 1))
        self.assertNotIn('ftpct', got)
        with self.assertRaisesRegex(ValueError, 'Invalid shooting counts'):
            projection.shooting_summaries({'fgm': np.array([2]), 'fga': np.array([1])})

    def test_package_saves_period_attempts_and_conditional_percentage_distributions(self):
        box = {k: np.zeros((2, 1, 5), dtype=np.int64) for k in projection.BOX}
        box['fgm'][1, 0, 0], box['fga'][1, 0, 0] = 1, 2
        mins = np.zeros((2, 1, 5))
        mins[1, 0, 0] = 5
        player = {'id': 'p', 'name': 'Player', 'pos': 'G', 'jersey': '', 'starter': True,
                  'status': 'Active', 'injury': None, 'availability': 1, 'base_min': 5}
        team = {'tid': '1', 'players': [player], 'box': box, 'minutes': mins}
        scores = {'home': np.zeros((2, 5), dtype=int), 'away': np.zeros((2, 5), dtype=int)}
        packaged = projection.package({'game_id': 'g'}, {'home': team, 'away': team},
                                      scores, np.zeros(2, dtype=int), 2, {'mu_home': 0, 'mu_away': 0}, 'test')
        periods = packaged['home']['players'][0]['periods']
        for period in ('q1', 'h1', 'fg'):
            stats = periods[period]['stats']
            self.assertEqual(stats['fga']['hist'], [1, 0, 1])
            self.assertEqual((stats['fgpct']['defined'], stats['fgpct']['total']), (1, 2))
            self.assertEqual(stats['fgpct']['q'][2], 50)
        self.assertNotIn('fgpct', periods['q2']['stats'])

    def setUp(self):
        self.league = {
            'per_game': {k: v for k, v in (
                ('pts', 110), ('ast', 25), ('fgm', 40), ('fg3m', 12), ('ftm', 18),
                ('oreb', 10), ('dreb', 30), ('stl', 8), ('blk', 5), ('tov', 13),
            )},
            'fg3_pct': 0.36, 'fg2_pct': 0.54, 'ft_pct': 0.78,
        }
        self.teams = {'1': {'gp': 10}, '2': {'gp': 10}}
        self.history = {
            '10': {'team': '1', 'name': 'Traded Player', 'pos': 'G', 'totals': {'min': 100},
                   'gp': 10, 'recent_window': 3, 'recent_played': 3, 'recent_started': 1,
                   'min_ewma': 10},
        }

    def test_missing_status_is_unknown_and_uses_the_unvalidated_fallback(self):
        for status in (None, '', '  '):
            with self.subTest(status=status):
                self.assertEqual(projection.availability(status), 0.5)
                registry = {'10': {'team': '1', 'on_roster': True, 'status': status}}
                players = projection.player_inputs('1', self.history, registry, self.league, self.teams, True)
                self.assertEqual(players[0]['status'], 'Unknown')
                self.assertEqual(players[0]['availability'], 0.5)
                self.assertEqual(players[0]['availability_basis'], 'ambiguous_report')

    def test_known_status_probabilities_remain_unchanged(self):
        for status, expected in (('Active', 1.0), ('Probable', 0.75), ('Questionable', 0.5), ('Out', 0.0)):
            with self.subTest(status=status):
                self.assertEqual(projection.availability(status), expected)

    def test_unlisted_injury_is_an_assumption_not_a_reported_active_status(self):
        registry = {'10': {'team': '1', 'on_roster': True, 'status': 'Active',
                           'reported_status': None, 'status_source': 'not_listed_assumption'}}
        player = projection.player_inputs('1', self.history, registry, self.league, self.teams, True)[0]
        self.assertEqual((player['availability'], player['availability_basis']), (1.0, 'not_listed_assumption'))

    def test_traded_player_follows_roster_team_not_historical_team(self):
        registry = {'10': {'team': '2', 'on_roster': True, 'status': 'Active'}}
        self.assertEqual(projection.player_inputs('1', self.history, registry, self.league, self.teams, True), [])
        players = projection.player_inputs('2', self.history, registry, self.league, self.teams, True)
        self.assertEqual([p['id'] for p in players], ['10'])
        self.assertEqual(players[0]['availability'], 1.0)
        self.assertEqual(players[0]['availability_basis'], 'status')

    def test_unmapped_status_and_recent_inactivity_are_distinct_fallbacks(self):
        unknown = {'10': {'team': '1', 'on_roster': True, 'status': 'Not specified'}}
        player = projection.player_inputs('1', self.history, unknown, self.league, self.teams, True)[0]
        self.assertEqual((player['status'], player['availability'], player['availability_basis']),
                         ('Not specified', 0.5, 'ambiguous_report'))
        inactive = {'10': {**self.history['10'], 'recent_played': 0}}
        active = {'10': {'team': '1', 'on_roster': True, 'status': 'Active', 'status_source': 'not_listed_assumption'}}
        player = projection.player_inputs('1', inactive, active, self.league, self.teams, True)[0]
        self.assertEqual((player['status'], player['availability'], player['availability_basis']),
                         ('Active', 0.5, 'recent_inactivity'))

    def test_missing_roster_does_not_infer_actual_participants(self):
        self.assertEqual(projection.player_inputs('1', self.history, {}, self.league, self.teams, True), [])

    def placeholder_fixture(self, last_availability):
        base = {'base_min': 20, 'value': 1, 'usual_min': 20, 'starter': True,
                'qshare': [0.25] * 4, 'u_pts': [1] * 4, 'u_ast': [1] * 4,
                'r3': 0.05, 'r2': 0.1, 'rft': 0.05, 'miss3': 0.05, 'miss2': 0.05, 'missft': 0.02,
                'oreb': 0.02, 'dreb': 0.1, 'ast': 0.1, 'stl': 0.02, 'blk': 0.02, 'tov': 0.05,
                'name': 'Player', 'pos': 'G', 'jersey': '', 'status': 'Active', 'injury': None}
        roster = [{**base, 'id': str(i), 'availability': 1.0 if i < 4 else last_availability} for i in range(5)]
        rates = {'quarter_share': [0.25] * 4, 'share3': 0.3, 'shareft': 0.15, 'tov_pct': 0.13,
                 'opp_tov_pct': 0.13, 'oreb_pct': 0.25, 'dreb_pct': 0.75, 'ast_rate': 0.6,
                 'stl_share': 0.5, 'blk_per_miss': 0.1}
        game = {'game_id': 'synthetic', 'home_id': '1', 'away_id': '2', 'date_et': '2026-11-22'}
        return roster, rates, game

    def test_prospective_placeholder_rejects_short_availability_worlds(self):
        roster, rates, game = self.placeholder_fixture(0.5)
        with patch.object(projection, 'team_expectation', return_value={'mu_home': 110, 'mu_away': 110, 'pace': 100}), \
                patch.object(projection, 'team_rates', return_value=rates), \
                patch.object(projection, 'player_inputs', return_value=roster):
            with self.assertRaisesRegex(ValueError, 'fewer than five available players'):
                projection.simulate_game(game, {}, {}, {}, {}, '2026-11-22', True, sims=100)
            retrospective = projection.simulate_game(game, {}, {}, {}, {}, '2026-11-22', False, sims=100)
            self.assertEqual(retrospective['sims'], 100)

    def test_prospective_placeholder_labels_and_conserves_cold_rosters(self):
        roster, rates, game = self.placeholder_fixture(1.0)
        roster.append({**roster[0], 'id': '5'})
        roster.append({**roster[0], 'id': '6', 'availability': 0.0})
        for known in (0, 1, 4):
            with self.subTest(known=known):
                players = [{**player, 'starter': False, 'base_min': 20 if i < known else 0}
                           for i, player in enumerate(roster)]
                original_package = projection.package

                def verify_worlds(game, teams, scores, overtime, worlds, expected, model):
                    for side in ('home', 'away'):
                        team = teams[side]
                        np.testing.assert_allclose(team['minutes'][:, :, :4].sum(axis=1), 60, atol=1e-10)
                        np.testing.assert_array_equal(team['minutes'][:, -1, :], 0)
                        np.testing.assert_array_equal(team['box']['pts'][:, -1, :], 0)
                        np.testing.assert_array_equal(team['box']['pts'].sum(axis=1), scores[side])
                        np.testing.assert_allclose(team['minutes'][:, :, 4].sum(axis=1), 25 * overtime, atol=1e-10)
                    return original_package(game, teams, scores, overtime, worlds, expected, model)

                with patch.object(projection, 'team_expectation', return_value={'mu_home': 110, 'mu_away': 110, 'pace': 100}), \
                        patch.object(projection, 'team_rates', return_value=rates), \
                        patch.object(projection, 'player_inputs', return_value=players), \
                        patch.object(projection, 'package', side_effect=verify_worlds), \
                        warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter('always')
                    result = projection.simulate_game(game, {}, {}, {}, {}, '2026-11-22', True, sims=100)
                self.assertEqual(len(caught), 2)
                self.assertEqual({row['method'] for row in result['fallbacks']}, {'equal_share_available'})
                self.assertEqual({row['worlds'] for row in result['fallbacks']}, {100})
                for side in ('home', 'away'):
                    lines = result[side]['players']
                    self.assertEqual(sum(p['starter'] for p in lines), 5)
                    self.assertNotIn('periods', lines[-1])
                    self.assertEqual(lines[-1]['played'], 0)
                    for period in ('q1', 'q2', 'q3', 'q4'):
                        self.assertAlmostEqual(sum(p['periods'][period]['sec'] for p in lines[:-1]), 3600, places=1)
                        self.assertAlmostEqual(sum(p['periods'][period]['mean']['pts'] for p in lines[:-1]),
                                               result[side]['box'][period]['pts'], places=2)

    def test_valid_placeholder_forecast_matches_pre_guard(self):
        roster, rates, game = self.placeholder_fixture(1.0)
        with patch.object(projection, 'team_expectation', return_value={'mu_home': 110, 'mu_away': 110, 'pace': 100}), \
                patch.object(projection, 'team_rates', return_value=rates), \
                patch.object(projection, 'player_inputs', return_value=roster):
            result = projection.simulate_game(game, {}, {}, {}, {}, '2026-11-22', True, sims=100)
        result.pop('shooting_distribution_schema')
        for side in ('home', 'away'):
            for player in result[side]['players']:
                for period, line in player.get('periods', {}).items():
                    for key in ('fgpct', 'fg3pct', 'ftpct'):
                        line['stats'].pop(key, None)
                    if period != 'fg':
                        for key in ('fga', 'fg3a', 'fta'):
                            line['stats'].pop(key, None)
        payload = json.dumps(result, sort_keys=True, separators=(',', ':')).encode()
        self.assertEqual(hashlib.sha256(payload).hexdigest(),
                         '87a6bb19a59d81bba09899653a5c3e37b9224235123acc9bc2a69acebb211ffe')

    def test_availability_basis_is_saved_in_packaged_forecast(self):
        roster, rates, game = self.placeholder_fixture(1.0)
        roster[0]['availability_basis'] = 'status'
        with patch.object(projection, 'team_expectation', return_value={'mu_home': 110, 'mu_away': 110, 'pace': 100}), \
                patch.object(projection, 'team_rates', return_value=rates), \
                patch.object(projection, 'player_inputs', return_value=roster):
            result = projection.simulate_game(game, {}, {}, {}, {}, '2026-11-22', True, sims=100)
        self.assertEqual(result['home']['players'][0]['availability_basis'], 'status')

    def test_cold_start_uses_existing_minutes_prior_without_a_lineup(self):
        state = minutes.player_state(
            {'params': minutes.MINUTES, 'latest': {}, 'team_dates': {}, 'sd': {}},
            '2', 'new-player', '2026-11-22',
        )
        self.assertEqual(state['healthy'], minutes.MINUTES['prior_min'])
        self.assertEqual(state['rotation'], 0.5)
        self.assertEqual(state['start_share'], 0.0)

    def test_projected_starters_fill_from_uncertain_eligible_roster(self):
        day = '2026-11-22'
        game = {'home_id': '1', 'away_id': '2', 'date_et': '2026-11-22'}
        home = [{'id': f'h{i}', 'pos': 'G', 'availability': 1.0 if i < 4 else 0.6} for i in range(7)]
        away = [{'id': f'a{i}', 'pos': 'G', 'availability': 1.0 if i < 5 else 0.6} for i in range(7)]
        state = {'healthy': 20, 'cap': 40, 'ramp': 1, 'rotation': 1, 'priority': 20,
                 'start_share': 0, 'sd_table': {}}
        profiles = pd.DataFrame({'date_et': ['2026-11-21'], 'season': [2026]})
        team_latest = pd.DataFrame({'last_game': ['2026-11-21']})
        with patch.object(engine.projection, 'player_inputs', side_effect=[home, away]), \
                patch.object(engine, 'features_dir', return_value=Path('/nonexistent-a1-features')), \
                patch.object(engine.pd, 'read_parquet', side_effect=[profiles, team_latest, pd.DataFrame({'date_et': pd.Series(dtype=str)})]), \
                patch.dict(engine._MINUTES, {day: {}}, clear=True), \
                patch.object(minutes, 'player_state', return_value=state), \
                patch.object(engine, 'Game', return_value=SimpleNamespace()) as game_factory:
            engine.inputs_for(game, day, {}, {}, {}, {}, rotation='targets')
        selected = game_factory.call_args.args[1]
        self.assertEqual(sum(p['projected_starter'] for p in selected['home']), 5)
        self.assertEqual(sum(p['projected_starter'] for p in selected['away']), 5)
        self.assertTrue(all(p['availability'] > 0 for p in selected['home'] if p['projected_starter']))
        self.assertTrue(all(p['availability'] == 1 for p in selected['away'] if p['projected_starter']))


if __name__ == '__main__':
    unittest.main()
