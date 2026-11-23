import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from basketball_common import read_json, write_json
from scripts import nightly, pathway, projection, smoke, views


class TodayOnlyTests(unittest.TestCase):
    def test_only_origin_is_selected_even_on_a_game_free_day(self):
        self.assertEqual(nightly.engine_days('2026-11-22', ['2026-11-23'], 0), ['2026-11-22'])
        self.assertEqual(nightly.engine_days('2026-11-22', ['2026-11-22', '2026-11-23'], 0), ['2026-11-22'])
        with self.assertRaises(ValueError):
            nightly.engine_days('2026-11-22', ['2026-11-23'], 1)

    def test_old_future_preview_is_not_a_current_snapshot(self):
        snapshots = {
            '2026-11-22': {'meta': {'origin': '2026-11-22'}},
            '2026-11-23': {'meta': {'origin': '2026-11-22'}},
        }
        with patch.object(views, 'today_et', return_value='2026-11-23'):
            self.assertEqual(views.current_snapshot(snapshots), '2026-11-22')

    def test_future_preview_is_hidden_but_historical_forecast_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            snaps = {}
            for day, gid in (('2026-11-21', 'past'), ('2026-11-22', 'today'), ('2026-11-23', 'tomorrow')):
                path = Path(tmp) / day
                write_json(path / 'games.json', {gid: {'marker': gid}})
                snaps[day] = {'path': path, 'meta': {'origin': day}}
            result = views.load_projections(snaps, '2026-11-22')
            self.assertEqual(set(result), {'past', 'today'})
            self.assertTrue((snaps['2026-11-23']['path'] / 'games.json').exists())

    def test_discarded_preview_does_not_reappear_on_a_later_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            snaps = {}
            for day, origin, gid in (('2026-11-21', '2026-11-20', 'old-review'),
                                     ('2026-11-22', '2026-11-22', 'origin'),
                                     ('2026-11-23', '2026-11-22', 'discarded'),
                                     ('2026-11-24', '2026-11-24', 'new')):
                path = Path(tmp) / day
                write_json(path / 'games.json', {gid: {'marker': gid}})
                snaps[day] = {'path': path, 'meta': {'origin': origin}}
            result = views.load_projections(snaps, '2026-11-24')
            self.assertEqual(set(result), {'old-review', 'origin', 'new'})
            self.assertTrue((snaps['2026-11-23']['path'] / 'games.json').exists())

    def test_empty_today_builds_a_team_season_without_loading_engine_models(self):
        with patch.object(nightly, 'team_table', return_value=({}, {'teams_gp': 20, 'games': 1})), \
                patch.object(nightly, 'player_table', return_value={}), \
                patch.object(nightly, 'period_profiles', return_value=({}, {})), \
                patch('scripts.engine.Engine', side_effect=AssertionError('no games should load models')):
            part = nightly.project_slate('2026-11-22', {}, [], [], [], {}, True, 100,
                                         period_rows=[], engine_worlds=10000)
        self.assertEqual(part['games'], {})
        self.assertEqual(part['worlds'], {})
        self.assertEqual(part['model']['id'], 'engine-v1.3')
        self.assertEqual(part['sims'], 10000)

    def test_pre_tip_snapshot_cannot_be_replaced_after_tip_or_by_missing_game(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = Path(tmp) / 'snapshot'
            meta = {'kind': 'prospective', 'completed_at': '2026-11-22T17:00:00Z',
                    'games': ['a', 'b'], 'pre_tip': {'a': True, 'b': True}}
            write_json(snapshot / 'meta.json', meta)
            slate = [{'game_id': 'a', 'tip_utc': '2026-11-22T18:00:00Z'},
                     {'game_id': 'b', 'tip_utc': '2026-11-22T20:00:00Z'}]
            nightly.protect_pre_tip(snapshot, slate, True, '2026-11-22T17:59:59Z')
            for games, prospective, completed in (
                    (slate, True, '2026-11-22T18:00:00Z'),
                    ([{**slate[0], 'status': 'live'}, slate[1]], True, '2026-11-22T17:00:00Z'),
                    (slate[1:], True, '2026-11-22T17:00:00Z'),
                    (slate, False, '2026-11-22T17:00:00Z')):
                with self.subTest(games=games, prospective=prospective), \
                        self.assertRaisesRegex(ValueError, 'refusing to replace'):
                    nightly.protect_pre_tip(snapshot, games, prospective, completed)
            self.assertEqual(read_json(snapshot / 'meta.json'), meta)

    def test_discarded_future_preview_does_not_block_its_slate(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = Path(tmp) / '2026-11-23'
            write_json(snapshot / 'meta.json', {'kind': 'prospective', 'slate_date': '2026-11-23',
                                                 'origin': '2026-11-22', 'completed_at': '2026-11-22T17:00:00Z',
                                                 'games': ['a'], 'pre_tip': {'a': True}})
            nightly.protect_pre_tip(snapshot, [{'game_id': 'a', 'tip_utc': '2026-11-23T18:00:00Z'}],
                                    True, '2026-11-23T19:00:00Z')

    def test_write_snapshot_keeps_original_when_simulation_crosses_tip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            derived, snapshots, master = root / 'derived', root / 'snapshots', root / 'master.csv'
            derived.mkdir()
            master.write_text('fixture')
            for name in ('player_games.csv', 'team_games.csv', 'player_periods.csv'):
                (derived / name).write_text(name)
            write_json(derived / 'players.json', {'run': 'run'})
            original = {'kind': 'prospective', 'completed_at': '2026-11-22T17:00:00Z',
                        'games': ['a'], 'pre_tip': {'a': True}}
            target = snapshots / '2026-11-22'
            write_json(target / 'meta.json', original)
            write_json(target / 'games.json', {'a': {'marker': 'original'}})
            part = {'day': '2026-11-22', 'origin': '2026-11-22', 'T': {}, 'lg': {'games': 1}, 'P': {},
                    'slate': [{'game_id': 'a', 'tip_utc': '2026-11-22T18:00:00Z'}], 'prospective': True,
                    'generated': '2026-11-22T17:59:59Z', 'model': {'id': 'test'}, 'sims': 1,
                    'season_sims': 1, 'engine_inputs': {}, 'games': {'a': {'marker': 'new'}},
                    'placeholder': {}, 'worlds': {}, 'started': 0}
            season = {'model': 'pathway', 'as_of': '2026-11-22', 'pathway': {'label': 'test'}, 'games': []}
            with patch.object(nightly, 'DERIVED', derived), patch.object(nightly, 'SNAPSHOTS', snapshots), \
                    patch.object(nightly, 'MASTER_CSV', master), \
                    patch.object(nightly, 'utc_now', return_value='2026-11-22T18:00:01Z'):
                with self.assertRaisesRegex(ValueError, 'refusing to replace'):
                    nightly.write_snapshot(part, season)
            self.assertEqual(read_json(target / 'meta.json'), original)
            self.assertEqual(read_json(target / 'games.json'), {'a': {'marker': 'original'}})

    def test_future_regulation_distributions_use_season_worlds(self):
        teams = {'1': {'conf': 'East'}, '2': {'conf': 'West'}}
        ratings = {tid: {'w': 0, 'l': 0} for tid in teams}
        game = {'game_id': 'g', 'date_et': '2026-11-23', 'tip_utc': '2026-11-23T00:00Z',
                'home_id': '1', 'away_id': '2', 'status': 'scheduled'}
        points = np.array([[[100, 100]], [[101, 100]], [[98, 102]]])
        wins = np.array([[True], [True], [False]])
        with patch.object(pathway, 'play', return_value={'points': points, 'home_win': wins}):
            season = projection.simulate_season(ratings, {}, [game], '2026-11-22', teams, sims=3)
        row = season['games'][0]
        self.assertEqual(row['source'], 'pathway')
        self.assertEqual(row['p_home'], round(2 / 3, 4))
        for key in ('home', 'away', 'total', 'margin'):
            self.assertEqual(sum(row['regulation'][key]['hist']), 3)
        self.assertEqual(row['regulation']['home']['mean'], round(299 / 3, 3))
        self.assertEqual(row['regulation']['total']['mean'], round(601 / 3, 3))
        self.assertEqual(season['regulation_distribution_schema'], 1)

    def test_season_replay_accepts_legacy_but_checks_new_distributions(self):
        stored = {'games': [{'game_id': 'g', 'source': 'pathway'}]}
        replay = {'games': [{'game_id': 'g', 'source': 'pathway', 'regulation': {'home': 1}}],
                  'regulation_distribution_schema': 1}
        smoke.align_legacy_season_schema(stored, replay)
        self.assertEqual(stored, replay)
        stored['regulation_distribution_schema'] = 1
        replay['regulation_distribution_schema'] = 1
        replay['games'][0]['regulation'] = {'home': 1}
        smoke.align_legacy_season_schema(stored, replay)
        self.assertNotEqual(stored, replay)


if __name__ == '__main__':
    unittest.main()
