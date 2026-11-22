import gzip
import hashlib
import json
import tempfile
import unittest
import warnings
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd
import numpy as np

from scripts import a1_data_inventory as inventory
from scripts import a1_lineup_audit
from scripts import a1_reconcile
from scripts import a1_rotation_audit
from scripts import a1_tracking_coverage
from scripts import aggregate
from scripts import fetch_nbastats
from scripts import features
from scripts import engine
from scripts import matchups
from scripts import nbastats
from scripts import nodes
from scripts import possessions
from scripts import train


class RawInventoryTests(unittest.TestCase):
    def test_nba_inventory_reports_unknown_metadata_missing_files_and_corruption(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            body = b'{"value": 1}'
            (folder / 'valid.json.gz').write_bytes(gzip.compress(body))
            (folder / 'unindexed.json.gz').write_bytes(gzip.compress(body))
            (folder / 'corrupt.json.gz').write_bytes(b'not gzip')
            (folder / 'changed.json.gz').write_bytes(gzip.compress(b'other'))
            entry = {'url': None, 'fetched_utc': None, 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}
            (folder / 'manifest.json').write_text(json.dumps({'valid': entry, 'missing': entry, 'corrupt': entry,
                                                              'changed': entry}))

            report = inventory.nba_folder(folder)

            self.assertEqual(report['unindexed'], ['unindexed'])
            self.assertEqual(report['missing_files'], ['missing'])
            self.assertEqual(report['missing_url_or_fetch_time'], ['changed', 'corrupt', 'missing', 'valid'])
            self.assertEqual([row['key'] for row in report['corrupt_gzip']], ['corrupt'])
            self.assertEqual(report['hash_or_size_mismatch'], ['changed'])


class DownloaderIntegrityTests(unittest.TestCase):
    def test_one_store_per_season_for_each_resumable_endpoint(self):
        games = [('2023-24', 'Regular Season', '1', '2024-01-01'),
                 ('2023-24', 'Regular Season', '2', '2024-01-02'),
                 ('2024-25', 'Regular Season', '3', '2025-01-01')]
        cases = (
            lambda client: fetch_nbastats.fetch_games(client, 'playbyplayv3', ['2023-24', '2024-25']),
            lambda client: fetch_nbastats.fetch_ptdefend(client, ['2023-24', '2024-25'], ['Overall', '3 Pointers']),
            lambda client: fetch_nbastats.fetch_hustle(client, ['2023-24', '2024-25']),
        )
        for case in cases:
            with self.subTest(endpoint=case):
                stores = []

                def create_store(endpoint, season):
                    store = Mock()
                    store.has.return_value = True
                    stores.append(store)
                    return store

                client = Mock()
                with patch.object(fetch_nbastats, 'logged_games', return_value=games), \
                     patch.object(fetch_nbastats, 'Store', side_effect=create_store) as factory:
                    case(client)
                self.assertEqual(factory.call_count, 2)
                client.get.assert_not_called()
                for store in stores:
                    store.flush.assert_called_once()

    def test_interrupted_season_logs_flush_successful_response_metadata(self):
        body = json.dumps({'resultSets': [{'rowSet': [[1]]}]}).encode()
        client = Mock()
        client.get.side_effect = [body, RuntimeError('interrupted')]
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(fetch_nbastats, 'NBA_RAW', Path(directory)):
            with self.assertRaisesRegex(RuntimeError, 'interrupted'):
                fetch_nbastats.fetch_logs(client, ['2025-26'])
            manifest = json.loads((Path(directory) / 'gamelogs' / '2025-26' / 'manifest.json').read_text())
            entry = manifest['regular_players_base']
            self.assertIsNotNone(entry['url'])
            self.assertIsNotNone(entry['fetched_utc'])
            self.assertEqual(entry['sha256'], hashlib.sha256(body).hexdigest())

    def test_game_fetch_resume_keeps_existing_metadata(self):
        games = [('2025-26', 'Regular Season', str(i), '2026-01-01') for i in range(3)]
        client = Mock()
        client.get.return_value = b'{"ok": true}'
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(fetch_nbastats, 'NBA_RAW', Path(directory)), \
             patch.object(fetch_nbastats, 'logged_games', return_value=games):
            first = fetch_nbastats.fetch_games(client, 'playbyplayv3', ['2025-26'], max_requests=1)
            path = Path(directory) / 'playbyplayv3' / '2025-26' / 'manifest.json'
            original = json.loads(path.read_text())['0']
            second = fetch_nbastats.fetch_games(client, 'playbyplayv3', ['2025-26'])
            manifest = json.loads(path.read_text())
            self.assertEqual((first['requests'], second['requests'], second['skipped']), (1, 2, 1))
            self.assertEqual(manifest['0'], original)
            self.assertTrue(all(entry['url'] and entry['fetched_utc'] for entry in manifest.values()))
            self.assertEqual(client.get.call_count, 3)


class CrosswalkIntegrityTests(unittest.TestCase):
    def test_missing_espn_id_cannot_be_a_matched_player(self):
        teams = pd.DataFrame([
            {'GAME_ID': 'nba', 'date': '2025-01-01', 'TEAM_ABBREVIATION': team,
             'season': '2024-25', 'season_type_nba': 'Regular Season'}
            for team in ('AAA', 'BBB')
        ])
        players = pd.DataFrame([
            {'GAME_ID': 'nba', 'PLAYER_ID': person, 'PLAYER_NAME': name, 'TEAM_ABBREVIATION': team,
             'PTS': points, 'FGA': 1, 'FGM': 0, 'REB': 0, 'AST': 0, 'MIN_SEC': '1:00'}
            for person, name, team, points in ((1, 'Real One', 'AAA', 1), (2, 'Missing Player', 'AAA', 0),
                                                (3, 'Real Two', 'BBB', 2))
        ])
        box = pd.DataFrame([
            {'game_id': 'espn', 'date': '2025-01-01', 'season': 2025, 'season_type': 2,
             'home': home, 'abbr': team, 'team_id': str(int(home) + 1), 'player': player, 'name': name,
             'min': 1, 'pts': points, 'fga': 1, 'fgm': 0, 'reb': 0, 'ast': 0}
            for home, team, player, name, points in ((True, 'AAA', '11', 'Real One', 1),
                                                     (True, 'AAA', None, None, 0),
                                                     (False, 'BBB', '22', 'Real Two', 2))
        ])
        with tempfile.TemporaryDirectory() as directory, patch.object(nbastats, 'OUT', Path(directory)):
            report = nbastats.crosswalk(teams, players, box)
            matches = pd.read_parquet(Path(directory) / 'player_games_map.parquet')
            unmatched = json.loads((Path(directory) / 'unmatched.json').read_text())
        self.assertEqual(report['players']['matched_player_games'], 2)
        self.assertEqual(report['players']['stages']['unmatched'], 1)
        self.assertFalse(matches['player'].isna().any())
        self.assertEqual([row['person'] for row in unmatched['players']], [2])


class ReconciliationIntegrityTests(unittest.TestCase):
    def test_invalid_ids_are_reported_and_duplicate_mappings_fail(self):
        games = pd.DataFrame([{'nba_game': 'nba', 'espn_game': 'espn'}])
        mapping = pd.DataFrame([
            {'nba_game': 'nba', 'espn_game': 'espn', 'person': 1, 'player': '11', 'stage': 'name'},
            {'nba_game': 'nba', 'espn_game': 'espn', 'person': 2, 'player': None, 'stage': 'stat_line'},
        ])
        clean, invalid = a1_reconcile.quarantine_mapping(games, mapping)
        self.assertEqual(clean['person'].tolist(), [1])
        self.assertEqual(invalid[0]['person'], 2)
        self.assertIsNone(invalid[0]['player'])
        with self.assertRaisesRegex(ValueError, 'more than once'):
            a1_reconcile.quarantine_mapping(games, pd.concat([mapping, mapping.iloc[[0]]], ignore_index=True))

    def test_missing_seconds_are_not_counted_as_agreement(self):
        result = a1_reconcile.seconds_difference(pd.Series([60, 120, 90]), pd.Series([60, None, 45]))
        self.assertEqual(result['known'], 2)
        self.assertEqual(result['missing_either'], 1)
        self.assertEqual(result['over_30_seconds'], 1)


class RotationIntegrityTests(unittest.TestCase):
    def test_windows_include_no_substitutions_and_report_count_mismatches(self):
        windows = pd.DataFrame([
            {'game_id': 'g', 'period': 1, 'clock': 700, 'subs_home': 0, 'subs_away': 0, 'kind': 'foul'},
            {'game_id': 'g', 'period': 1, 'clock': 600, 'subs_home': 2, 'subs_away': 0, 'kind': 'timeout'},
        ])
        subs = pd.DataFrame([
            {'game_id': 'g', 'period': 1, 'clock': 600, 'team': 'a', 'player_in': '1'},
        ])
        result = a1_rotation_audit.window_summary(windows, subs)
        self.assertEqual(result['no_substitution_windows'], 1)
        self.assertEqual(result['multiple_substitution_windows'], 1)
        self.assertEqual(result['window_count_mismatches'], 1)
        with self.assertRaisesRegex(ValueError, 'not unique'):
            a1_rotation_audit.window_summary(pd.concat([windows, windows.iloc[[0]]]), subs)


class SegmentLineupIntegrityTests(unittest.TestCase):
    @staticmethod
    def game():
        players = []
        for team, prefix in (('1', 100), ('2', 200)):
            for i in range(1, 7):
                players.append({'id': str(prefix + i), 'team': team, 'starter': i <= 5, 'dnp': False,
                                'pos': 'G', 'box': {'min': 10, 'pts': 2 if (team, i) in (('1', 6), ('2', 1)) else 0}})

        def event(seq, kind, clock, team, participants, shooting=False):
            return {'seq': seq, 'period': 1, 'type_id': '584' if kind == 'Substitution' else '1',
                    'type_text': kind, 'text': kind, 'clock': clock, 'team': team,
                    'participants': participants, 'shooting': shooting, 'scoring': shooting,
                    'points_attempted': 2 if shooting else 0, 'score_value': 2 if shooting else 0,
                    'x': 25, 'y': 3}

        return {'id': 'g', 'date_et': '2025-01-01', 'season': 2025, 'season_type': 2,
                'home': '1', 'away': '2', 'players': players,
                'plays': [event(1, 'Shot', '11:50', '2', ['201'], True),
                          event(2, 'Substitution', '11:49', '1', ['106', '105']),
                          event(3, 'Substitution', '11:49', '2', ['206', '205']),
                          event(4, 'Shot', '11:35', '1', ['106'], True),
                          event(5, 'End Period', '0:00', None, [])]}

    def test_candidate_splits_pre_action_subs_without_changing_possessions_or_points(self):
        game = self.game()
        original, _, _ = possessions.parse_game(game)
        old_shot = next(row for row in original if row['actor'] == '106')
        self.assertNotIn('106', old_shot['lineup_off'])

        fixed, _, _ = possessions.parse_game(game, split_substitutions=True)
        shot = next(row for row in fixed if row['actor'] == '106')
        prefix = next(row for row in fixed if row.get('sub_prefix'))
        self.assertIn('106', shot['lineup_off'])
        self.assertIn('206', shot['lineup_def'])
        self.assertNotIn('105', shot['lineup_off'])
        self.assertEqual(prefix['poss'], shot['poss'])
        self.assertEqual((prefix['start_clock'], prefix['end_clock'], shot['start_clock']), (710, 709, 709))
        self.assertEqual(sum(row['start_clock'] - row['end_clock'] for row in fixed), 720)
        self.assertEqual(sum(row['points'] for row in fixed), sum(row['points'] for row in original))
        self.assertEqual({row['poss'] for row in fixed}, {row['poss'] for row in original})

        frame = possessions.to_frame([{**row, 'game_ok': True} for row in fixed])
        on = pd.DataFrame([{**{f'm{i:02d}': 0.0 for i in range(1, 49)},
                           'game_id': 'g', 'player': player['id'], 'team': player['team'], 'date_et': '2025-01-01',
                           'season': 2025, 'season_type': 2, 'pos': 'G', 'starter': player['starter'], 'sec': 60}
                          for player in game['players']])
        counts = features.counts_for(frame, on, defence=True).set_index('player')
        self.assertEqual(counts.loc['106', 'off_segs'], 1)
        self.assertEqual(counts.loc['105', 'off_segs'], 0)
        self.assertEqual(counts.loc['206', 'd_shots'], 1)
        self.assertEqual(counts.loc['205', 'd_shots'], 0)

    def test_audit_identifies_actor_and_lineup_inconsistencies(self):
        game = self.game()
        rows, _, _ = possessions.parse_game(game)
        frame = possessions.to_frame(rows)
        actor = a1_lineup_audit.participant_summary(frame, 'actor', a1_lineup_audit.OFF)
        self.assertEqual(actor['known'], 2)
        self.assertEqual(actor['not_on_recorded_lineup'], 1)
        self.assertEqual(actor['by_end_type'], {'shot': 1})

    def test_candidate_quarantines_an_actor_still_missing_after_substitution(self):
        game = self.game()
        game['plays'][3]['participants'] = ['999']
        rows, _, _ = possessions.parse_game(game, split_substitutions=True)
        shot = next(row for row in rows if row['actor'] == '999')
        self.assertFalse(shot['lineup_valid'])
        self.assertIn('actor_not_offense', shot['lineup_issues'])
        frame = possessions.to_frame([{**row, 'game_ok': True} for row in rows])
        on = pd.DataFrame([{**{f'm{i:02d}': 0.0 for i in range(1, 49)},
                           'game_id': 'g', 'player': player['id'], 'team': player['team'], 'date_et': '2025-01-01',
                           'season': 2025, 'season_type': 2, 'pos': 'G', 'starter': player['starter'], 'sec': 60}
                          for player in game['players']])
        counts = features.counts_for(frame, on, defence=True).set_index('player')
        self.assertEqual(counts.loc['106', 'off_segs'], 0)
        self.assertEqual(counts.loc['206', 'd_shots'], 0)

    def test_candidate_node_dataset_rejects_quarantined_or_missing_validity(self):
        chain = object.__new__(nodes.Chain)
        chain.seg = pd.DataFrame({'lineup_valid': [True, False], 'end_type': ['shot', 'shot'],
                                  'actor': ['101', '999'], 'shot_time': [5.0, 5.0]})
        chain._frame = Mock(return_value=pd.DataFrame({'x': [1]}))
        chain._pack = Mock(return_value={})
        chain.dataset('event')
        self.assertEqual(chain._pack.call_args.args[4]['actor'].tolist(), ['101'])
        chain.seg['lineup_valid'] = [True, None]
        with self.assertRaisesRegex(ValueError, 'validity'):
            chain.dataset('event')

    def test_candidate_does_not_split_a_pending_free_throw_trip(self):
        game = self.game()
        shot = game['plays'][0]
        foul = {**shot, 'seq': 2, 'type_text': 'Shooting Foul', 'text': 'Shooting Foul', 'clock': '11:40',
                'team': '2', 'participants': ['201'], 'shooting': False, 'scoring': False,
                'points_attempted': 0, 'score_value': 0}
        sub = {**game['plays'][2], 'seq': 3, 'clock': '11:40'}
        free_throw = {**shot, 'seq': 4, 'type_text': 'Free Throw 1 of 2', 'clock': '11:40', 'team': '1',
                      'participants': ['101'], 'points_attempted': 1, 'score_value': 1}
        final_throw = {**free_throw, 'seq': 5, 'type_text': 'Free Throw 2 of 2'}
        game['plays'] = [shot, foul, sub, free_throw, final_throw, game['plays'][-1]]
        old, _, _ = possessions.parse_game(game)
        new, _, _ = possessions.parse_game(game, split_substitutions=True)
        trip = next(row for row in new if row['end_type'] == 'fouled')
        self.assertEqual((trip['actor'], trip['fta'], trip['ftm'], trip['points']), ('101', 2, 2, 2))
        self.assertEqual(sum(row['points'] for row in old), sum(row['points'] for row in new))
        self.assertFalse(any(row['sub_prefix'] for row in new))

    def test_candidate_cannot_overwrite_production_segments(self):
        with self.assertRaisesRegex(ValueError, 'isolated'):
            possessions.build_current(split_substitutions=True)


class CausalFeatureTests(unittest.TestCase):
    def test_same_day_player_results_do_not_enter_pregame_state(self):
        games = pd.DataFrame([
            {'player': 'p', 'season': 2023, 'date_et': '2022-10-20', 'value': 10},
            {'player': 'p', 'season': 2023, 'date_et': '2022-10-20', 'value': 500},
            {'player': 'p', 'season': 2023, 'date_et': '2022-10-21', 'value': 20},
        ])
        pre, _ = features.decayed_pregame(games, ['value'], 10, .5, strict_dates=True)
        self.assertEqual(pre[:2, 0].tolist(), [0, 0])
        self.assertGreater(pre[2, 0], 500)

    def test_positions_use_only_strictly_earlier_observations(self):
        source = pd.DataFrame([
            {'player': 'p', 'date_et': '2024-01-01', 'pos': 'G'},
            {'player': 'p', 'date_et': '2024-01-02', 'pos': 'F'},
            {'player': 'p', 'date_et': '2024-01-02', 'pos': 'F'},
            {'player': 'p', 'date_et': '2024-01-03', 'pos': 'C'},
            {'player': 'q', 'date_et': '2024-01-02', 'pos': None},
        ])
        before, latest = features.prior_positions(source)
        changed = source.copy()
        changed.loc[changed['date_et'].ge('2024-01-02'), 'pos'] = 'C'
        after, _ = features.prior_positions(changed)
        self.assertTrue(pd.isna(before.loc[0, 'pos']))
        self.assertEqual(before.loc[1:2, 'pos'].tolist(), ['G', 'G'])
        self.assertEqual(after.loc[1:2, 'pos'].tolist(), ['G', 'G'])
        self.assertEqual(before.loc[3, 'pos'], 'F')
        self.assertTrue(pd.isna(before.loc[4, 'pos']))
        self.assertEqual(latest['p'], 'C')
        conflict = source.copy()
        conflict.loc[2, 'pos'] = 'G'
        with self.assertRaisesRegex(ValueError, 'conflicting position'):
            features.prior_positions(conflict)

    def test_lineup_relative_inputs_ignore_other_games_and_match_engine(self):
        values = np.array([[1., 1., 2., np.nan, 3.], [np.nan] * 5])
        shares, ranks = nodes.relative_lineup(values)
        np.testing.assert_allclose(ranks[0], [4.5, 4.5, 2., 3., 1.])
        self.assertTrue(np.isnan(shares[1]).all())
        self.assertTrue(np.isnan(ranks[1]).all())

        chain = object.__new__(nodes.Chain)
        chain._relative_missing_policy = 'lineup_median'
        rows = [{'seg_id': i, 'player': str(j), **{c: v for c in (
            'usage', 'ast_rate', 'oreb_pct', 'shot_share', 'blk_rate', 'stl_rate', 'dreb_pct', 'pf_rate')}}
                for i, lineup in enumerate(values) for j, v in enumerate(lineup)]
        chain.off, chain.dfn = pd.DataFrame(rows), pd.DataFrame(rows)
        chain._relative()
        np.testing.assert_allclose(chain.off.loc[:4, 'usage_share'], shares[0])
        np.testing.assert_allclose(chain.off.loc[:4, 'usage_rank'], ranks[0])
        chain.off.loc[5:, 'usage'] = 9999.
        chain._relative()
        np.testing.assert_allclose(chain.off.loc[:4, 'usage_share'], shares[0])

        eng = object.__new__(engine.Engine)
        eng.m = SimpleNamespace(style=[], relative_missing_policy='lineup_median')
        P = {c: np.ones(5, dtype=np.float32) for c in nodes.PROFILE}
        P['usage'] = values[0].astype(np.float32)
        P['grp_code'] = np.zeros(5, dtype=np.float32)
        state = SimpleNamespace(period=np.array([1]),
                                ingame={c: np.zeros((1, 5), dtype=np.float32) for c in nodes.IN_GAME})
        actual = eng._five(SimpleNamespace(P=P), state, np.array([0]), np.array([[0, 1, 2, 3, 4]]), ['usage'])
        np.testing.assert_allclose(actual['usage_share'][0], shares[0])
        np.testing.assert_allclose(actual['usage_rank'][0], ranks[0])

    def test_candidate_baseline_uses_only_its_own_lineup(self):
        chain = object.__new__(nodes.Chain)
        chain._relative_missing_policy = 'lineup_median'
        values = [[np.nan, 1., 2., 3., 4.], [np.nan] * 5]
        cand = pd.DataFrame([{'seg_id': i, 'game_id': f'g{i}', 'date_et': '2024-01-01',
                              'season_type': 2, 'period': 1, 'margin': 0, 'usage': v}
                             for i, lineup in enumerate(values) for v in lineup])
        labels = np.tile([1, 0, 0, 0, 0], 2)
        scores = chain._candidates('who', cand, ['usage'], labels, 'usage')['profile_score']
        np.testing.assert_allclose(scores[:5], [2.5, 1., 2., 3., 4.])
        np.testing.assert_allclose(scores[5:], np.ones(5))
        changed = cand.copy()
        changed.loc[changed['seg_id'].eq(1), 'usage'] = 9999.
        injected = chain._candidates('who', changed, ['usage'], labels, 'usage')['profile_score']
        np.testing.assert_array_equal(scores[:5], injected[:5])

    def test_what_baseline_uses_training_not_other_validation_games(self):
        row = {'actor_shot_share': .7, 'actor_tov_share': .2, 'actor_foul_drawn_share': .1,
               **{f'actor_mix_{zone}': .2 for zone in nodes.ZONES}}
        frame = pd.DataFrame([row, row, {**row, 'actor_shot_share': np.nan}, row])
        tr, va = np.array([True, True, False, False]), np.array([False, False, True, True])
        d = {'X': frame, 'y': np.array([0, 1, 0, 1]), 'name': 'what', 'kind': 'multiclass',
             'profile': ('what', None), 'classes': 8}
        baseline = train.profile_baseline(d, tr, va)
        changed = frame.copy()
        changed.loc[3, ['actor_shot_share', 'actor_tov_share', 'actor_foul_drawn_share']] = [8., 7., 6.]
        injected = train.profile_baseline({**d, 'X': changed}, tr, va)
        np.testing.assert_allclose(baseline[0], injected[0])
        np.testing.assert_allclose(baseline.sum(axis=1), 1.)
        missing_training = frame.copy()
        missing_training.loc[tr, 'actor_shot_share'] = np.nan
        with self.assertRaisesRegex(ValueError, 'entirely missing training'):
            train.profile_baseline({**d, 'X': missing_training}, tr, va)

    def test_fold_model_cache_invalidates_when_training_code_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = root / 'spec.json'
            spec.write_text(json.dumps({'version': 'candidate', 'default': {}, 'nodes': {}}))
            metrics = {k: .5 for k in ('model', 'league', 'profile', 'gain_vs_best_baseline', 'ece_model')}
            metrics['iterations'] = 1
            fitted = {'model': Mock(), 'columns': [], 'categorical': [], 'temperature': 1.}
            with patch.object(train, 'MODELS', root / 'models'), \
                 patch.object(nodes, 'signature', return_value={}), \
                 patch.object(nodes, 'datasets', return_value=[{'name': 'who'}]), \
                 patch.object(train, 'run_node', return_value=(metrics, None, fitted)) as run, \
                 patch.object(aggregate, 'sha256_file', side_effect=['old', 'old', 'new']), \
                 patch('lightgbm.Booster'):
                aggregate.fit_models('F4', spec, 1, node_list=['who'])
                aggregate.fit_models('F4', spec, 1, node_list=['who'])
                self.assertEqual(run.call_count, 1)
                aggregate.fit_models('F4', spec, 1, node_list=['who'])
                self.assertEqual(run.call_count, 2)

    def test_engine_loads_only_fold_safe_scheduled_assignment(self):
        def model(through, valid_from):
            fitted = through is not None
            return {'through': through, 'valid_from': valid_from, 'match': {k: 0. for k in matchups.MATCH},
                    'prop': {k: 0. for k in matchups.PROP} if fitted else {},
                    'fill': {k: 0. for k in ('height_in', 'weight_lb', 'grp_code', 'min_avg',
                                             'pf_rate', 'blk_rate', 'stl_rate')} if fitted else {},
                    'body_policy': 'omit', 'missing_policy': 'retain_missing'}

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            models, feature_dir, season = root / 'models' / 'fold', root / 'features', root / 'history' / '2023'
            for path in (models, feature_dir, season):
                path.mkdir(parents=True)
            history = pd.DataFrame([
                {'date_et': '2023-12-20', 'game_ok': True, 'end_type': kind, 'heave': False,
                 'zone': 'rim', 'x': 25., 'y': 2., 'fta': 0, 'period': 1, 'start_clock': 50.,
                 'fouls_def': 1, 'made': 0., 'duration': 10., 'shot_time': 8.}
                for kind in ('shot', 'foul')
            ])
            history.to_parquet(season / 'segments.parquet', index=False)
            pre = pd.DataFrame([{'date_et': '2023-12-20', **{c: .1 for c in engine.OFF_REL + engine.DEF_REL}}])
            pre.to_parquet(feature_dir / 'pregame.parquet', index=False)
            schedule_path = root / 'schedule.json'
            schedule = {'kind': 'dated_implicit_schedule', 'training_through': '2023-12-31',
                        'models': [model(None, '1900-01-01'), model('2023-12-31', '2024-01-01')]}
            schedule_path.write_text(json.dumps(schedule))
            digest = hashlib.sha256(schedule_path.read_bytes()).hexdigest()
            (feature_dir / 'features_report.json').write_text(json.dumps({
                'causal_positions': True, 'relative_missing_policy': 'lineup_median',
                'input_sha256': {str(schedule_path): digest},
            }))
            config = {'version': 'candidate', 'fold': True, 'train_through': '2023-12-31',
                      'segments': str(root), 'features': str(feature_dir / 'pregame.parquet'),
                      'matchup': str(schedule_path),
                      'nodes': {'who': {'file': 'who.txt', 'columns': ['mu_fg_rim']}}}
            (models / 'config.json').write_text(json.dumps(config))
            with patch.object(engine, 'MODELS', root / 'models'), patch.object(engine.lgb, 'Booster'):
                loaded = engine.Models('fold')
                self.assertEqual(loaded.theta['through'], '2023-12-31')
                self.assertEqual(loaded.position_policy, 'prior_observed')
                self.assertEqual(loaded.relative_missing_policy, 'lineup_median')
                simulator = object.__new__(engine.Engine)
                simulator.m = loaded
                with self.assertRaisesRegex(ValueError, 'at or before'):
                    simulator.simulate(SimpleNamespace(day='2023-12-31'), 1, 1)
                schedule_path.write_text(json.dumps({**schedule, 'extra': 'tampered'}))
                with self.assertRaisesRegex(ValueError, 'provenance'):
                    engine.Models('fold')

    def test_first_season_player_prior_is_unchanged_by_same_day_and_future_results(self):
        columns = set().union(*(features.FAMILY_COLUMNS[f] for f in ('role', 'usage', 'accuracy', 'ft')))
        rows = []
        for player, date, uses in [('p', '2022-10-20', 10), ('q', '2022-10-21', 20), ('p', '2022-10-22', 30)]:
            row = {key: 0.0 for key in columns}
            row.update({'player': player, 'date_et': date, 'season': 2023, 'pos': 'G',
                        'games': 1.0, 'uses': float(uses), 'off_segs': 50.0})
            rows.append(row)
        df = pd.DataFrame(rows).sort_values(['player', 'date_et']).reset_index(drop=True)

        def pregame(frame):
            priors = features.priors_by_season(frame, causal_first=True)
            sums = {}
            for family in ('role', 'usage', 'accuracy', 'ft'):
                columns = features.FAMILY_COLUMNS[family]
                values, _ = features.decayed_pregame(frame, columns, 10, .5, strict_dates=True)
                sums[family] = pd.DataFrame(values, columns=columns)
            return features.profiles(frame, sums, priors, causal_first=True)

        baseline = pregame(df)
        changed = df.copy()
        changed.loc[changed['date_et'].ge('2022-10-21'), 'uses'] = 9999
        injected = pregame(changed)
        q = df['player'].eq('q')
        self.assertAlmostEqual(baseline.loc[q, 'usage'].iloc[0], .2)
        self.assertAlmostEqual(injected.loc[q, 'usage'].iloc[0], .2)
        self.assertTrue(pd.isna(baseline.loc[df['date_et'].eq('2022-10-20'), 'usage'].iloc[0]))

    def test_first_season_team_prior_ignores_same_day_and_future_games(self):
        rows = []
        for team, date, three in [('a', '2022-10-20', 30), ('a', '2022-10-21', 40),
                                  ('b', '2022-10-21', 90), ('b', '2022-10-22', 80)]:
            row = {f'{side}_{c}': 0.0 for side in ('off', 'def') for c in features.TEAM_COUNT_COLUMNS}
            row.update({'team': team, 'game_id': team + date, 'date_et': date, 'season': 2023,
                        'off_shots': 100.0, 'off_three': float(three)})
            rows.append(row)
        df = pd.DataFrame(rows)
        baseline = features.team_profiles(df, 15, .5, causal_first=True)
        changed = df.copy()
        changed.loc[changed['date_et'].ge('2022-10-21'), 'off_three'] = 9999
        injected = features.team_profiles(changed, 15, .5, causal_first=True)
        day = baseline['team'].eq('a') & baseline['date_et'].eq('2022-10-21')
        self.assertAlmostEqual(baseline.loc[day, 'off_three'].iloc[0], .3)
        self.assertAlmostEqual(injected.loc[day, 'off_three'].iloc[0], .3)

    def test_overlapping_seasons_and_production_candidate_output_fail(self):
        counts = pd.DataFrame([{'season': 2023, 'date_et': '2023-10-25', 'pos': 'G'},
                               {'season': 2024, 'date_et': '2023-10-24', 'pos': 'G'}])
        with self.assertRaisesRegex(ValueError, 'overlap'):
            features.priors_by_season(counts, causal_first=True)
        with self.assertRaisesRegex(ValueError, 'isolated'):
            features.build(causal_first=True)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'base profiles'):
                features.build(out=Path(directory), matchup=Path('unused.json'), causal_first=True)
            root = Path(directory)
            (root / 'features_report.json').write_text(json.dumps({'causal_first_priors': True}))
            (root / 'single.json').write_text(json.dumps({'through': '2025-12-31'}))
            with self.assertRaisesRegex(ValueError, 'dated assignment schedule'):
                features.build(out=root / 'output', matchup=root / 'single.json', causal_first=True,
                               base_pregame=root / 'pregame.parquet', history_only=True)

    def test_candidate_missing_defender_value_does_not_depend_on_another_game(self):
        actor = {'height_in': np.array([75., 75.]), 'weight_lb': np.array([200., 200.]),
                 'grp_code': np.array([0., 0.]), 'min_avg': np.array([20., 20.])}
        defense = {name: np.tile(value[:, None], (1, 5)) for name, value in actor.items()}
        defense['m_fg_rim'] = np.array([[np.nan] * 5, [.4] * 5])
        theta = {'match': {name: 0. for name in matchups.MATCH}, 'fill': {'height_in': 75.},
                 'missing_policy': 'retain_missing', 'top2': True}
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', RuntimeWarning)
            before = matchups.mu_columns(theta, actor, defense)
            defense['m_fg_rim'][1] = .6
            after = matchups.mu_columns(theta, actor, defense)
        self.assertTrue(np.isnan(before['mu_fg_rim'][0]))
        self.assertTrue(np.isnan(after['mu_fg_rim'][0]))
        self.assertTrue(np.isnan(after['mu1_fg_rim'][0]))
        self.assertAlmostEqual(before['mu_fg_rim'][1], .4)
        self.assertAlmostEqual(after['mu_fg_rim'][1], .6)

    def test_body_free_assignment_ignores_later_measurements(self):
        actor = {'height_in': np.array([75.]), 'weight_lb': np.array([200.]),
                 'grp_code': np.array([0.]), 'min_avg': np.array([20.])}
        defense = {name: np.tile(value[:, None], (1, 5)) for name, value in actor.items()}
        defense['height_in'][0] = [70., 72., 74., 76., 78.]
        defense['weight_lb'][0] = [180., 190., 200., 210., 220.]
        defense['m_fg_rim'] = np.array([[.4, .45, .5, .55, .6]])
        theta = {'match': {name: 1. for name in matchups.MATCH}, 'fill': {},
                 'body_policy': 'omit', 'missing_policy': 'retain_missing'}
        before = matchups.mu_columns(theta, actor, defense)
        defense['height_in'] *= 10
        defense['weight_lb'] *= 10
        actor['height_in'][:] = np.nan
        actor['weight_lb'][:] = np.nan
        after = matchups.mu_columns(theta, actor, defense)
        np.testing.assert_array_equal(before['mu_fg_rim'], after['mu_fg_rim'])
        self.assertTrue(np.isnan(before['mu_height_gap']).all())
        self.assertTrue(np.isnan(after['mu_height_gap']).all())

    def test_dated_assignments_freeze_and_match_single_fit_serving(self):
        def model(through, valid_from, role_weight):
            weights = {name: 0. for name in matchups.MATCH}
            weights['abs_role'] = role_weight
            fitted = through is not None
            return {'through': through, 'valid_from': valid_from, 'match': weights,
                    'prop': {k: 0. for k in matchups.PROP} if fitted else {},
                    'fill': {k: 0. for k in ('height_in', 'weight_lb', 'grp_code', 'min_avg',
                                             'pf_rate', 'blk_rate', 'stl_rate')} if fitted else {},
                    'body_policy': 'omit', 'missing_policy': 'retain_missing'}

        cold = model(None, '1900-01-01', 0.)
        fitted = model('2024-01-31', '2024-02-01', -1.)
        schedule = {'kind': 'dated_implicit_schedule', 'training_through': '2024-01-31', 'models': [cold, fitted]}
        actor = {'height_in': np.array([75., 75.]), 'weight_lb': np.array([200., 200.]),
                 'grp_code': np.array([0., 0.]), 'min_avg': np.array([20., 20.])}
        defense = {name: np.tile(value[:, None], (1, 5)) for name, value in actor.items()}
        defense['min_avg'][:] = [5., 10., 15., 20., 25.]
        defense['m_fg_rim'] = np.tile([.4, .45, .5, .55, .6], (2, 1))
        dates = np.array(['2024-01-31', '2024-02-01'])
        weighted = matchups.dated_assignment(schedule, actor, defense, dates)
        np.testing.assert_allclose(weighted[0], np.full(5, .2))
        self.assertFalse(np.allclose(weighted[1], weighted[0]))
        dated = matchups.dated_mu_columns(schedule, actor, defense, dates)
        for index, theta in enumerate((cold, fitted)):
            single = matchups.mu_columns(theta, {k: v[index:index + 1] for k, v in actor.items()},
                                         {k: v[index:index + 1] for k, v in defense.items()})
            for name in single:
                np.testing.assert_allclose(dated[name][index:index + 1], single[name], equal_nan=True)
        later = model('2024-02-29', '2024-03-01', 99.)
        extended = {**schedule, 'training_through': '2024-02-29', 'models': [cold, fitted, later]}
        np.testing.assert_array_equal(weighted, matchups.dated_assignment(extended, actor, defense, dates))
        unsafe = {**schedule, 'training_through': '2024-01-30'}
        with self.assertRaisesRegex(ValueError, 'within its fold'):
            matchups.dated_assignment(unsafe, actor, defense, dates)
        future = model('2024-02-01', '2024-02-01', 1.)
        with self.assertRaisesRegex(ValueError, 'within its fold'):
            matchups.dated_assignment({**schedule, 'models': [cold, future]}, actor, defense, dates)

    def test_dated_assignments_reject_corrupt_cutoffs_and_parameters(self):
        cold = {'through': None, 'valid_from': '1900-01-01', 'match': {k: 0. for k in matchups.MATCH},
                'fill': {}, 'body_policy': 'omit', 'missing_policy': 'retain_missing'}
        fitted = {'through': '2024-01-31', 'valid_from': '2024-02-01',
                  'match': {k: 0. for k in matchups.MATCH}, 'prop': {k: 0. for k in matchups.PROP},
                  'fill': {k: 0. for k in ('height_in', 'weight_lb', 'grp_code', 'min_avg',
                                           'pf_rate', 'blk_rate', 'stl_rate')},
                  'body_policy': 'omit', 'missing_policy': 'retain_missing'}
        broken = [
            {**fitted, 'through': 'NaT'},
            {**fitted, 'match': {**fitted['match'], 'abs_role': np.nan}},
            {**fitted, 'prop': {**fitted['prop'], 'foul_pf': np.inf}},
            {**fitted, 'fill': {**fitted['fill'], 'min_avg': np.inf}},
            {**fitted, 'fill': {k: v for k, v in fitted['fill'].items() if k != 'min_avg'}},
        ]
        schedule = {'kind': 'dated_implicit_schedule', 'training_through': '2024-01-31'}
        for model in broken:
            with self.subTest(model=model), self.assertRaises(ValueError):
                matchups.dated_masks({**schedule, 'models': [cold, model]}, ['2024-02-01'])

    def test_assignment_holdout_uses_training_fills_and_scales(self):
        segments, profiles, events = [], [], []
        for i in range(4):
            gid = f'g{i}'
            segment = {'seg_id': i, 'game_id': gid}
            for j in range(1, 6):
                segment[f'def_{j}'] = f'd{j}'
            segments.append(segment)
            for j, player in enumerate(['s', 'd1', 'd2', 'd3', 'd4', 'd5']):
                profiles.append({'game_id': gid, 'player': player, 'height_in': 70 + j, 'weight_lb': 190 + j,
                                 'grp_code': j % 3, 'min_avg': 10 + j, 'pf_rate': i + j + 1,
                                 'blk_rate': i + 2 * j + 1, 'stl_rate': i + 3 * j + 1})
            events.append({'seg_id': i, 'shooter': 's', 'credit': 'd1', 'kind': 'steal', 'event': 'steal', 'w': 1.})
        seg, pre, ev = pd.DataFrame(segments), pd.DataFrame(profiles), pd.DataFrame(events)
        _, _, _, _, train_preprocessing = matchups.design(seg, ev.iloc[:2], pre, return_preprocessing=True)
        before, _, _, _, _ = matchups.design(seg, ev.iloc[2:], pre, preprocessing=train_preprocessing)
        injected = pre.copy()
        injected.loc[injected['game_id'].eq('g3'), ['pf_rate', 'blk_rate', 'stl_rate']] = 9999.
        after, _, _, _, _ = matchups.design(seg, ev.iloc[2:], injected, preprocessing=train_preprocessing)
        np.testing.assert_array_equal(before[0], after[0])


class TrackingIntegrityTests(unittest.TestCase):
    def test_tracking_response_checks_provenance_and_date_parameters(self):
        headers = list(a1_tracking_coverage.REQUIRED + a1_tracking_coverage.ATTEMPT_FIELDS['Overall'])
        document = {'parameters': {'Season': '2024-25', 'DateFrom': '01/02/2025', 'DateTo': '01/02/2025',
                                   'DefenseCategory': 'Overall'},
                    'resultSets': [{'headers': headers, 'rowSet': [[1, 'AAA', 1, 2, 4]]}]}
        body = json.dumps(document).encode()
        entry = {'sha256': hashlib.sha256(body).hexdigest(), 'bytes': len(body)}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'response.json.gz'
            path.write_bytes(gzip.compress(body))
            _, rows = a1_tracking_coverage.decode(path, entry, '2024-25', '2025-01-02', 'Overall')
            self.assertEqual(rows[0]['D_FGA'], 4)
            with self.assertRaisesRegex(ValueError, 'parameters'):
                a1_tracking_coverage.decode(path, entry, '2024-25', '2025-01-03', 'Overall')
            with self.assertRaisesRegex(ValueError, 'hash or length'):
                a1_tracking_coverage.decode(path, {**entry, 'bytes': 1}, '2024-25', '2025-01-02', 'Overall')

    def test_special_categories_use_their_own_attempt_columns(self):
        for category, attempts in (('Less Than 6Ft', 'FGA_LT_06'), ('3 Pointers', 'FG3A')):
            with self.subTest(category=category), tempfile.TemporaryDirectory() as directory:
                headers = list(a1_tracking_coverage.REQUIRED + a1_tracking_coverage.ATTEMPT_FIELDS[category])
                document = {'parameters': {'Season': '2024-25', 'DateFrom': '01/02/2025', 'DateTo': '01/02/2025',
                                           'DefenseCategory': category},
                            'resultSets': [{'headers': headers, 'rowSet': [[1, 'AAA', 1, 2, 4]]}]}
                body = json.dumps(document).encode()
                entry = {'sha256': hashlib.sha256(body).hexdigest(), 'bytes': len(body)}
                path = Path(directory) / 'response.json.gz'
                path.write_bytes(gzip.compress(body))
                _, rows = a1_tracking_coverage.decode(path, entry, '2024-25', '2025-01-02', category)
                self.assertEqual(rows[0][attempts], 4)


if __name__ == '__main__':
    unittest.main()
