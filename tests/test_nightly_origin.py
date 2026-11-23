import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pandas as pd

from basketball_common import forecast_meta, read_json, verified_pre_tip, write_json
from scripts import engine, master_fixtures, matchups, minutes, nightly, realmatch, views


class NightlyOriginTests(unittest.TestCase):
    def test_schedule_missing_tip_validity_does_not_invent_a_known_time(self):
        competition: dict[str, object] = {'competitors': [
            {'homeAway': 'home', 'team': {'id': '1', 'abbreviation': 'H'}},
            {'homeAway': 'away', 'team': {'id': '2', 'abbreviation': 'A'}},
        ]}
        event = {'id': 'g', 'date': '2026-11-23T00:00:00Z', 'competitions': [competition]}
        self.assertEqual(master_fixtures.row_from_event(event)['time_valid'], 0)
        competition['timeValid'] = True
        self.assertEqual(master_fixtures.row_from_event(event)['time_valid'], 1)
        competition['timeValid'] = False
        self.assertEqual(master_fixtures.row_from_event(event)['time_valid'], 0)

    def test_preview_uses_origin_for_inputs_and_target_for_game(self):
        origin, target = '2026-11-21', '2026-11-22'
        game = {'game_id': 'g', 'home_id': '1', 'away_id': '2', 'date_et': target,
                'tip_utc': '2099-01-01T00:00:00Z'}
        rows = [{'date_et': '2026-11-20'}, {'date_et': origin}]
        selected = lambda values, before: [r['date_et'] for r in values if r['date_et'] < before]
        with patch.object(nightly, 'team_table', side_effect=lambda values, before, teams:
                          ({'dates': selected(values, before)}, {'teams_gp': 20, 'games': 1})), \
                patch.object(nightly, 'player_table', side_effect=lambda values, before:
                             {'dates': selected(values, before)}), \
                patch.object(nightly, 'period_profiles', side_effect=lambda values, players, before, teams, blowout:
                             ({'dates': selected(values, before)}, {})) as periods, \
                patch.object(nightly.projection, 'simulate_game',
                             return_value={'home': {}, 'away': {}}) as simulate:
            part = nightly.project_slate(target, {}, [game], rows, rows, {}, True, 100,
                                         period_rows=rows, origin=origin)
        self.assertEqual(part['origin'], origin)
        self.assertEqual(part['T']['dates'], ['2026-11-20'])
        self.assertEqual(part['P']['dates'], ['2026-11-20'])
        self.assertEqual(periods.call_args.args[2], origin)
        self.assertEqual(simulate.call_args.args[5], target)
        self.assertEqual(simulate.call_args.args[8]['dates'], ['2026-11-20'])

    def test_preview_rejects_origin_after_target(self):
        with self.assertRaisesRegex(ValueError, 'origin'):
            nightly.project_slate('2026-11-21', {}, [], [], [], {}, True, 100,
                                  period_rows=[], origin='2026-11-22')

    def test_written_cutoff_and_season_share_origin(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            derived, snapshots, master = root / 'derived', root / 'snapshots', root / 'master.csv'
            derived.mkdir()
            master.write_text('fixture')
            for name in ('player_games.csv', 'team_games.csv', 'player_periods.csv'):
                (derived / name).write_text(name)
            write_json(derived / 'players.json', {'run': 'run'})
            game: dict[str, str | None] = {'game_id': 'g', 'home_id': '1', 'away_id': '2', 'date_et': '2026-11-22',
                                           'tip_utc': '2026-11-23T00:00:00Z', 'time_valid': '1'}
            with patch.object(nightly, 'team_table', return_value=({}, {'teams_gp': 20, 'games': 1})), \
                    patch.object(nightly, 'player_table', return_value={}), \
                    patch.object(nightly, 'period_profiles', return_value=({}, {})), \
                    patch.object(nightly.projection, 'simulate_game', return_value={'home': {}, 'away': {}}):
                part = nightly.project_slate('2026-11-22', {}, [game], [], [], {}, True, 100,
                                             period_rows=[], origin='2026-11-21')
            part['generated'] = '2026-11-22T23:59:59Z'
            season = {'model': 'pathway', 'as_of': '2026-11-21', 'pathway': {'label': 'test'}, 'games': []}
            with patch.object(nightly, 'DERIVED', derived), patch.object(nightly, 'SNAPSHOTS', snapshots), \
                    patch.object(nightly, 'MASTER_CSV', master), \
                    patch.object(nightly, 'utc_now', return_value='2026-11-23T00:00:01Z'):
                meta = nightly.write_snapshot(part, season)
                self.assertEqual((meta['origin'], meta['cutoff']), ('2026-11-21', '2026-11-20'))
                self.assertEqual((meta['started_at'], meta['completed_at']),
                                 ('2026-11-22T23:59:59Z', '2026-11-23T00:00:01Z'))
                self.assertFalse(meta['pre_tip']['g'])
                self.assertEqual(read_json(snapshots / '2026-11-22' / 'meta.json')['origin'], '2026-11-21')
                with self.assertRaisesRegex(ValueError, 'origin'):
                    nightly.write_snapshot(part, {**season, 'as_of': '2026-11-22'})
                for flag in ('0', None):
                    game['time_valid'] = flag
                    with self.subTest(time_valid=flag), \
                            patch.object(nightly, 'utc_now', return_value='2026-11-22T23:59:59Z'), \
                            patch.object(nightly, 'archive_paths', return_value='archive'):
                        unknown = nightly.write_snapshot(part, season)
                    self.assertIsNone(unknown['pre_tip']['g'])
                    self.assertIsNone(views.verified_pre_tip(unknown, 'g'))

    def test_legacy_or_incomplete_timing_is_not_treated_as_pre_tip(self):
        self.assertIsNone(views.verified_pre_tip({'pre_tip': {'g': True}}, 'g'))
        self.assertIsNone(views.verified_pre_tip({'completed_at': None, 'pre_tip': {'g': False}}, 'g'))
        self.assertTrue(views.verified_pre_tip({'completed_at': '2026-11-21T23:00:00Z',
                                                'pre_tip': {'g': True}}, 'g'))
        self.assertFalse(views.verified_pre_tip({'completed_at': '2026-11-21T23:00:00Z',
                                                 'pre_tip': {'g': False}}, 'g'))

    def test_per_game_provenance_preserves_original_timing_and_model(self):
        retained = {'kind': 'prospective', 'completed_at': '2026-11-22T17:00:00Z',
                    'pre_tip': {'g': True}, 'model': {'id': 'old'}}
        fresh = {'kind': 'prospective', 'completed_at': '2026-11-22T19:00:00Z',
                 'pre_tip': {'h': False}, 'model': {'id': 'new'}}
        meta = {**fresh, 'game_provenance_schema': 1, 'game_provenance': {'g': retained, 'h': fresh}}
        self.assertTrue(verified_pre_tip(meta, 'g'))
        self.assertFalse(verified_pre_tip(meta, 'h'))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            write_json(path / 'games.json', {'g': {}, 'h': {}})
            records = views.load_projections({'2026-11-22': {'path': path, 'meta': meta}}, '2026-11-22')
        self.assertEqual(records['g']['meta'], retained)
        self.assertEqual(records['h']['meta'], fresh)
        self.assertIs(forecast_meta(fresh, 'h'), fresh)

    def test_malformed_per_game_provenance_fails_closed(self):
        for meta in ({'game_provenance_schema': 2, 'game_provenance': {'g': {}}},
                     {'game_provenance_schema': True, 'game_provenance': {'g': {}}},
                     {'game_provenance': {'g': {}}},
                     {'game_provenance_schema': 1, 'game_provenance': {}},
                     {'game_provenance_schema': 1, 'game_provenance': {'g': {'game_provenance': {}}}}):
            with self.subTest(meta=meta), self.assertRaises(ValueError):
                verified_pre_tip(meta, 'g')

    def test_live_status_cannot_be_labelled_pre_tip_even_with_a_future_tip(self):
        game = {'game_id': 'g', 'tip_utc': '2026-11-23T00:00:00Z', 'time_valid': '1', 'status': 'live'}
        self.assertFalse(nightly.tip_is_future(game, '2026-11-22T23:00:00Z'))
        game['time_valid'] = '0'
        self.assertIsNone(nightly.tip_is_future(game, '2026-11-22T23:00:00Z'))

    def test_engine_rejects_profiles_from_origin_date(self):
        for player_day, team_day in (('2026-11-21', '2026-11-20'), ('2026-11-20', '2026-11-21')):
            profiles = pd.DataFrame({'date_et': [player_day], 'season': [2026]})
            team_latest = pd.DataFrame({'last_game': [team_day]})
            with self.subTest(player_day=player_day, team_day=team_day), \
                    patch.object(engine.projection, 'player_inputs', return_value=[]), \
                    patch.object(engine, 'features_dir', return_value=Path('/nonexistent-a1-features')), \
                    patch.object(engine.pd, 'read_parquet', side_effect=[profiles, team_latest]):
                with self.assertRaisesRegex(ValueError, '2026-11-21'):
                    engine.inputs_for({'home_id': '1', 'away_id': '2'}, '2026-11-22',
                                      {}, {}, {}, {}, origin='2026-11-21')

    def test_engine_uses_pre_origin_minutes_and_stints_with_target_game_date(self):
        origin, target = '2026-11-21', '2026-11-22'
        players = [{'id': str(i), 'pos': 'G', 'availability': 1.0} for i in range(5)]
        profiles = pd.DataFrame({'date_et': ['2026-11-20'], 'season': [2026]})
        team_latest = pd.DataFrame({'last_game': ['2026-11-20']})
        stints = pd.DataFrame({'date_et': ['2026-11-20', origin]})
        with patch.object(engine.projection, 'player_inputs', side_effect=[players.copy(), players.copy()]), \
                patch.object(engine, 'features_dir', return_value=Path('/nonexistent-a1-features')), \
                patch.object(engine.pd, 'read_parquet', side_effect=[profiles, team_latest, stints]), \
                patch.dict(engine._MINUTES, {}, clear=True), \
                patch.object(minutes, 'build', return_value={}) as build, \
                patch.object(minutes, 'player_state', return_value={}) as state, \
                patch.object(minutes, 'projected_starters', return_value=list(range(5))), \
                patch.object(engine, 'Game', return_value=SimpleNamespace()) as factory:
            result = engine.inputs_for({'home_id': '1', 'away_id': '2'}, target, {}, {}, {}, {},
                                       rotation='targets', origin=origin)
        build.assert_called_once_with(origin, include_current=True, upto=origin)
        self.assertTrue(all(call.args[3] == target for call in state.call_args_list))
        self.assertEqual(factory.call_args.args[4]['date_et'].tolist(), ['2026-11-20'])
        self.assertEqual(factory.call_args.args[5], target)
        self.assertEqual(result.input_before, origin)

    def test_real_matchup_pair_history_is_selected_before_origin(self):
        ids = [str(i) for i in range(10)]
        profile = {key: np.ones(10) for key in ('grp_code', 'min_avg', 'height_in', 'weight_lb', 'usage')}
        game = SimpleNamespace(P=profile, game={'game_id': 'g'}, day='2026-11-22',
                               input_before='2026-11-21', ids=ids, pair_hist=None, pair_met=None)
        simulation = object.__new__(engine.Engine)
        simulation.m = object.__new__(engine.Models)
        simulation.m.theta = {'kind': 'real'}
        matrix = np.zeros((10, 10), dtype=np.float32)
        with patch.object(realmatch, 'pair_matrix', return_value=(matrix, matrix)) as pairs, \
                patch.object(matchups, 'mu_columns', return_value={'value': np.zeros(1)}):
            simulation._mu(game, np.array([[5, 6, 7, 8, 9]]), np.array([0]), np.array([0]),
                           np.array([[0, 1, 2, 3, 4]]), np.array([0]))
        pairs.assert_called_once_with('g', '2026-11-21', ids)


if __name__ == '__main__':
    unittest.main()
