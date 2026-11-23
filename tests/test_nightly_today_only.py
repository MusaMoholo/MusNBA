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

    def test_season_replay_uses_only_its_declared_engine_worlds(self):
        with tempfile.TemporaryDirectory() as tmp:
            snaps = [Path(tmp) / day for day in ('today', 'discarded')]
            for path, games in ((snaps[0], {'a': np.array([1])}),
                                (snaps[1], {'b': np.array([2])})):
                write_json(path / 'season.json', {'as_of': '2026-11-22'})
                np.savez(path / 'engine_worlds.npz', **games)
            worlds = smoke.season_worlds(snaps, {'engine_games': ['a']}, '2026-11-22')
            self.assertEqual(list(worlds), ['a'])
            np.testing.assert_array_equal(worlds['a'], [1])
            with self.assertRaisesRegex(ValueError, 'missing'):
                smoke.season_worlds(snaps, {'engine_games': ['a', 'missing']}, '2026-11-22')
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                smoke.season_worlds(snaps, {'engine_games': ['a', 'a']}, '2026-11-22')
            np.savez(snaps[1] / 'engine_worlds.npz', a=np.array([1]))
            with self.assertRaisesRegex(ValueError, 'multiple snapshots'):
                smoke.season_worlds(snaps, {'engine_games': ['a']}, '2026-11-22')

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
            slate = [{'game_id': 'a', 'tip_utc': '2026-11-22T18:00:00Z', 'time_valid': '1', 'status': 'scheduled'},
                     {'game_id': 'b', 'tip_utc': '2026-11-22T20:00:00Z', 'time_valid': '1', 'status': 'scheduled'}]
            nightly.protect_pre_tip(snapshot, slate, True, '2026-11-22T17:59:59Z')
            for games, prospective, completed in (
                    (slate, True, '2026-11-22T18:00:00Z'),
                    ([{**slate[0], 'status': 'live'}, slate[1]], True, '2026-11-22T17:00:00Z'),
                    ([{**slate[0], 'status': 'suspended'}, slate[1]], True, '2026-11-22T17:00:00Z'),
                    ([{k: v for k, v in slate[0].items() if k != 'status'}, slate[1]],
                     True, '2026-11-22T17:00:00Z'),
                    ([{**slate[0], 'time_valid': '0'}, slate[1]], True, '2026-11-22T17:00:00Z'),
                    ([{k: v for k, v in slate[0].items() if k != 'time_valid'}, slate[1]],
                     True, '2026-11-22T17:00:00Z'),
                    ([{**slate[0], 'tip_utc': None}, slate[1]], True, '2026-11-22T17:00:00Z'),
                    ([{**slate[0], 'tip_utc': '2026-11-22T18:00:00'}, slate[1]],
                     True, '2026-11-22T17:00:00Z'),
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

    def test_retention_selects_only_old_pre_tip_games_that_can_no_longer_be_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = Path(tmp) / '2026-11-22'
            write_json(snapshot / 'meta.json', {'kind': 'prospective', 'slate_date': '2026-11-22',
                       'origin': '2026-11-22', 'completed_at': '2026-11-22T17:00:00Z',
                       'games': ['a', 'b'], 'pre_tip': {'a': True, 'b': True}})
            slate = [{'game_id': 'a', 'tip_utc': '2026-11-22T18:00:00Z', 'time_valid': '1', 'status': 'scheduled'},
                     {'game_id': 'b', 'tip_utc': '2026-11-22T20:00:00Z', 'time_valid': '1', 'status': 'scheduled'}]
            self.assertEqual(nightly.retained_game_ids(snapshot, slate, True, '2026-11-22T17:59:59Z'), set())
            self.assertEqual(nightly.retained_game_ids(snapshot, slate, True, '2026-11-22T18:00:00Z'), {'a'})
            self.assertEqual(nightly.retained_game_ids(snapshot, [{**slate[0], 'time_valid': '0'}, slate[1]],
                                                       True, '2026-11-22T17:59:59Z'), {'a'})
            with self.assertRaisesRegex(ValueError, 'missing'):
                nightly.retained_game_ids(snapshot, slate[1:], True, '2026-11-22T17:00:00Z')

    def test_retained_snapshot_preserves_game_worlds_and_per_game_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            derived, snapshots, master = root / 'derived', root / 'snapshots', root / 'master.csv'
            derived.mkdir()
            master.write_text('fixture')
            for name in ('player_games.csv', 'team_games.csv', 'player_periods.csv'):
                (derived / name).write_text(name)
            write_json(derived / 'players.json', {'run': 'run'})
            target = snapshots / '2026-11-22'
            model = {'id': 'engine-v1.3'}
            old_meta = {'kind': 'prospective', 'slate_date': '2026-11-22', 'origin': '2026-11-22',
                        'completed_at': '2026-11-22T17:00:00Z', 'model': model, 'sims': 2,
                        'games': ['a', 'b'], 'pre_tip': {'a': True, 'b': True}}
            fixtures = [{'game_id': gid, 'home_id': '1', 'away_id': '2', 'time_valid': '1', 'status': 'scheduled',
                         'tip_utc': tip} for gid, tip in (
                             ('a', '2026-11-22T18:00:00Z'), ('b', '2026-11-22T20:00:00Z'))]
            old_games = {gid: {'game_id': gid, 'model': model['id'], 'sims': 2,
                               'home': {'team_id': '1'}, 'away': {'team_id': '2'},
                               'periods': {'fg': {'home': {'pts': {'mean': .5}, 'win': .5},
                                                  'away': {'pts': {'mean': .5}}}},
                               'marker': f'old-{gid}'} for gid in ('a', 'b')}
            scores = np.array([[[1, 0, 0, 0, 0], [0, 0, 0, 0, 0]],
                               [[0, 0, 0, 0, 0], [1, 0, 0, 0, 0]]], dtype=np.int16)
            player_arrays = {f'{gid}__{key}': value for gid in ('a', 'b') for key, value in {
                'ids': np.array(['h', 'v']), 'side': np.array([0, 1], dtype=np.int8),
                'lines': np.zeros((2, 2, 15), dtype=np.uint8)}.items()}
            for gid in ('a', 'b'):
                player_arrays[f'{gid}__lines'][:, :, 1] = scores.sum(axis=2)
            write_json(target / 'meta.json', old_meta)
            write_json(target / 'games.json', old_games)
            write_json(target / 'games_placeholder.json', {'a': 'old-a', 'b': 'old-b'})
            write_json(target / 'stats.json', {'teams': {}, 'league': {'games': 1}, 'players': {}})
            np.savez_compressed(target / 'engine_worlds.npz', a=scores, b=scores)
            np.savez_compressed(target / 'engine_players.npz', **player_arrays)
            retained = nightly.load_retained(target, fixtures, '2026-11-22T18:30:00Z')
            self.assertEqual(set(retained), {'a'})
            part = {'day': '2026-11-22', 'origin': '2026-11-22', 'T': {}, 'lg': {'games': 1}, 'P': {},
                    'slate': fixtures, 'prospective': True, 'generated': '2026-11-22T18:30:00Z',
                    'model': model, 'sims': 2, 'season_sims': 2, 'engine_inputs': {}, 'started': 0,
                    'games': {'a': old_games['a'], 'b': {**old_games['b'], 'marker': 'new-b'}},
                    'placeholder': {'a': 'old-a', 'b': 'new-b'}, 'worlds': {'a': scores, 'b': scores},
                    'player_worlds': {gid: {key: player_arrays[f'{gid}__{key}']
                                           for key in ('ids', 'side', 'lines')} for gid in ('a', 'b')},
                    'retained': retained}
            season = {'model': 'pathway', 'as_of': '2026-11-22', 'pathway': {'label': 'test'}, 'sims': 2,
                      'games': [{'game_id': gid, 'source': 'engine', 'p_home': .5, 'mu_home': .5, 'mu_away': .5}
                                for gid in ('a', 'b')]}
            with patch.object(nightly, 'DERIVED', derived), patch.object(nightly, 'SNAPSHOTS', snapshots), \
                    patch.object(nightly, 'MASTER_CSV', master), \
                    patch.object(nightly, 'utc_now', return_value='2026-11-22T18:31:00Z'), \
                    patch.object(nightly, 'archive_paths', return_value='archive'):
                with self.assertRaisesRegex(ValueError, 'statistics'):
                    nightly.validate_retained({**part, 'P': {'different': {}}}, season, target,
                                              '2026-11-22T18:31:00Z')
                altered = {**part, 'worlds': {**part['worlds'], 'a': np.zeros_like(scores)}}
                with self.assertRaisesRegex(ValueError, 'worlds changed'):
                    nightly.validate_retained(altered, season, target, '2026-11-22T18:31:00Z')
                with self.assertRaisesRegex(ValueError, 'season does not use'):
                    nightly.validate_retained(part, {**season, 'games': []}, target, '2026-11-22T18:31:00Z')
                with patch.object(nightly, 'utc_now', side_effect=['2026-11-22T19:59:59Z',
                                                                  '2026-11-22T20:00:01Z']):
                    with self.assertRaisesRegex(ValueError, 'refusing to replace'):
                        nightly.write_snapshot(part, season)
                self.assertEqual(read_json(target / 'games.json'), old_games)
                meta = nightly.write_snapshot(part, season)
            projected = views.load_projections({'2026-11-22': {'path': target, 'meta': meta}}, '2026-11-22')
            self.assertEqual(projected['a']['meta'], old_meta)
            self.assertEqual(projected['a']['sim'], old_games['a'])
            self.assertEqual(projected['b']['meta']['completed_at'], '2026-11-22T18:31:00Z')
            self.assertEqual(projected['b']['sim']['marker'], 'new-b')
            with np.load(target / 'engine_worlds.npz') as saved:
                np.testing.assert_array_equal(saved['a'], scores)
            with np.load(target / 'engine_players.npz') as saved:
                for key in ('ids', 'side', 'lines'):
                    np.testing.assert_array_equal(saved[f'a__{key}'], player_arrays[f'a__{key}'])
            later = nightly.load_retained(target, fixtures, '2026-11-22T20:01:00Z')
            self.assertEqual(later['a']['meta'], old_meta)
            self.assertEqual(later['b']['meta']['completed_at'], '2026-11-22T18:31:00Z')

    def test_project_slate_does_not_resimulate_a_retained_game(self):
        game = {'game_id': 'a', 'date_et': '2026-11-22'}
        saved = {'game': {'marker': 'original'}, 'placeholder': {'marker': 'placeholder'},
                 'worlds': np.zeros((2, 2, 5), dtype=np.int16),
                 'players': {'ids': np.array(['h']), 'side': np.array([0]),
                             'lines': np.zeros((2, 1, 15), dtype=np.uint8)}}
        with patch.object(nightly, 'team_table', return_value=({}, {'teams_gp': 20, 'games': 1})), \
                patch.object(nightly, 'player_table', return_value={}), \
                patch.object(nightly, 'period_profiles', return_value=({}, {})), \
                patch('scripts.engine.Engine', side_effect=AssertionError('retained games must not be simulated')), \
                patch.object(nightly.projection, 'simulate_game',
                             side_effect=AssertionError('retained placeholder must not be simulated')):
            part = nightly.project_slate('2026-11-22', {}, [game], [], [], {}, True, 2, period_rows=[],
                                         engine_worlds=2, retained={'a': saved})
        self.assertEqual(part['games']['a'], saved['game'])
        np.testing.assert_array_equal(part['worlds']['a'], saved['worlds'])
        with self.assertRaisesRegex(ValueError, 'prospective engine'):
            nightly.project_slate('2026-11-22', {}, [game], [], [], {}, False, 2, period_rows=[],
                                  engine_worlds=2, retained={'a': saved})

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
                    'slate': [{'game_id': 'a', 'tip_utc': '2026-11-22T18:00:00Z', 'time_valid': '1', 'status': 'scheduled'}], 'prospective': True,
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

    def test_snapshot_publish_rolls_back_if_staged_rename_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            derived, snapshots, master = root / 'derived', root / 'snapshots', root / 'master.csv'
            derived.mkdir()
            master.write_text('fixture')
            for name in ('player_games.csv', 'team_games.csv', 'player_periods.csv'):
                (derived / name).write_text(name)
            write_json(derived / 'players.json', {'run': 'run'})
            target, staging = snapshots / '2026-11-22', snapshots / '.2026-11-22.partial'
            write_json(target / 'meta.json', {'kind': 'prospective', 'completed_at': '2026-11-22T17:00:00Z',
                                              'games': ['a'], 'pre_tip': {'a': True}})
            write_json(target / 'games.json', {'a': 'original'})
            part = {'day': '2026-11-22', 'origin': '2026-11-22', 'T': {}, 'lg': {'games': 1}, 'P': {},
                    'slate': [{'game_id': 'a', 'tip_utc': '2026-11-22T18:00:00Z', 'time_valid': '1', 'status': 'scheduled'}], 'prospective': True,
                    'generated': '2026-11-22T17:30:00Z', 'model': {'id': 'test'}, 'sims': 1,
                    'season_sims': 1, 'engine_inputs': {}, 'games': {'a': 'replacement'},
                    'placeholder': {}, 'worlds': {}, 'started': 0}
            season = {'model': 'pathway', 'as_of': '2026-11-22', 'pathway': {'label': 'test'}, 'games': []}
            original_rename = Path.rename

            def rename(path, destination):
                if path == staging:
                    raise OSError('injected publish failure')
                return original_rename(path, destination)

            with patch.object(nightly, 'DERIVED', derived), patch.object(nightly, 'SNAPSHOTS', snapshots), \
                    patch.object(nightly, 'MASTER_CSV', master), \
                    patch.object(nightly, 'utc_now', return_value='2026-11-22T17:45:00Z'), \
                    patch.object(nightly, 'archive_paths', return_value='archive'), patch.object(Path, 'rename', rename):
                with self.assertRaisesRegex(OSError, 'injected publish failure'):
                    nightly.write_snapshot(part, season)
            self.assertEqual(read_json(target / 'games.json'), {'a': 'original'})
            self.assertEqual(read_json(staging / 'games.json'), {'a': 'replacement'})
            self.assertFalse((snapshots / '.2026-11-22.previous').exists())

    def test_write_snapshot_keeps_original_when_tip_passes_during_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            derived, snapshots, master = root / 'derived', root / 'snapshots', root / 'master.csv'
            derived.mkdir()
            master.write_text('fixture')
            for name in ('player_games.csv', 'team_games.csv', 'player_periods.csv'):
                (derived / name).write_text(name)
            write_json(derived / 'players.json', {'run': 'run'})
            target = snapshots / '2026-11-22'
            original = {'kind': 'prospective', 'completed_at': '2026-11-22T17:00:00Z',
                        'games': ['a'], 'pre_tip': {'a': True}}
            write_json(target / 'meta.json', original)
            write_json(target / 'games.json', {'a': 'original'})
            part = {'day': '2026-11-22', 'origin': '2026-11-22', 'T': {}, 'lg': {'games': 1}, 'P': {},
                    'slate': [{'game_id': 'a', 'tip_utc': '2026-11-22T18:00:00Z', 'time_valid': '1', 'status': 'scheduled'}],
                    'prospective': True, 'generated': '2026-11-22T17:30:00Z', 'model': {'id': 'test'},
                    'sims': 1, 'season_sims': 1, 'engine_inputs': {}, 'games': {'a': 'replacement'},
                    'placeholder': {}, 'worlds': {}, 'started': 0}
            season = {'model': 'pathway', 'as_of': '2026-11-22', 'pathway': {'label': 'test'}, 'games': []}
            with patch.object(nightly, 'DERIVED', derived), patch.object(nightly, 'SNAPSHOTS', snapshots), \
                    patch.object(nightly, 'MASTER_CSV', master), \
                    patch.object(nightly, 'utc_now', side_effect=['2026-11-22T17:59:59Z', '2026-11-22T18:00:01Z']), \
                    patch.object(nightly, 'archive_paths', return_value='archive'):
                with self.assertRaisesRegex(ValueError, 'refusing to replace'):
                    nightly.write_snapshot(part, season)
            self.assertEqual(read_json(target / 'meta.json'), original)
            self.assertEqual(read_json(target / 'games.json'), {'a': 'original'})

    def test_interrupted_publish_recovers_previous_before_checking_protection(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = Path(tmp) / '2026-11-22'
            previous = Path(tmp) / '.2026-11-22.previous'
            write_json(previous / 'meta.json', {'kind': 'prospective', 'completed_at': '2026-11-22T17:00:00Z',
                                                'games': ['a'], 'pre_tip': {'a': True}})
            write_json(previous / 'games.json', {'a': 'original'})
            slate = [{'game_id': 'a', 'tip_utc': '2026-11-22T18:00:00Z', 'time_valid': '1', 'status': 'scheduled'}]
            with self.assertRaisesRegex(ValueError, 'refusing to replace'):
                nightly.protect_pre_tip(snapshot, slate, True, '2026-11-22T19:00:00Z')
            self.assertEqual(read_json(snapshot / 'games.json'), {'a': 'original'})
            self.assertFalse(previous.exists())

    def test_interrupted_publish_with_two_snapshots_requires_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = Path(tmp) / '2026-11-22'
            previous = Path(tmp) / '.2026-11-22.previous'
            write_json(snapshot / 'meta.json', {'marker': 'new'})
            write_json(previous / 'meta.json', {'marker': 'old'})
            with self.assertRaisesRegex(ValueError, 'previous'):
                nightly.protect_pre_tip(snapshot, [], True, '2026-11-22T19:00:00Z')
            self.assertEqual(read_json(snapshot / 'meta.json')['marker'], 'new')
            self.assertEqual(read_json(previous / 'meta.json')['marker'], 'old')

    def test_view_builder_rejects_an_interrupted_snapshot_publish(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_json(root / '2026-11-21' / 'meta.json', {'origin': '2026-11-21'})
            write_json(root / '.2026-11-22.previous' / 'meta.json', {'origin': '2026-11-22'})
            with patch.object(views, 'SNAPSHOTS', root), self.assertRaisesRegex(ValueError, 'previous'):
                views.load_snapshots()

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
