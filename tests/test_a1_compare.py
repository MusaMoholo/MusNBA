import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from scripts import a1_compare, a1_manifest, a1_output_audit, backtest, projection


class A1ComparisonTests(unittest.TestCase):
    def test_pre_game_tiers_keep_missing_inputs_unknown(self):
        keys = pd.DataFrame({'game_id': ['1'] * 6, 'player': list('abcdef')})
        pre = keys.assign(date_et='2026-01-01', usage=[0.25, 0.2, 0.2, np.nan, 0.3, 0.2],
                          start_share=[0.0, 0.5, 0.49, 0.8, np.nan, np.nan],
                          starter=[False, False, True, True, True, True])
        pre[['usage', 'start_share']] = pre[['usage', 'start_share']].astype('Float64')
        games = pd.DataFrame({'game_id': ['1'], 'date_et': ['2026-01-01']})
        self.assertEqual(a1_compare.roles(keys, pre, games)['tier'].tolist(),
                         ['star', 'starter', 'bench', 'unknown', 'unknown', 'unknown'])
        pre.loc[0, 'date_et'] = '2026-01-02'
        with self.assertRaisesRegex(ValueError, 'profile date'):
            a1_compare.roles(keys, pre, games)
        pre.loc[0, 'date_et'] = '2026-01-01'
        pre.loc[0, 'start_share'] = 1.1
        with self.assertRaisesRegex(ValueError, 'between 0 and 1'):
            a1_compare.roles(keys, pre, games)

    def test_comparison_rejects_lost_and_duplicate_player_games(self):
        control = pd.DataFrame({'game_id': ['1', '1'], 'player': ['a', 'b']})
        with self.assertRaisesRegex(ValueError, 'keys differ'):
            a1_compare._same_keys(control, control.iloc[:1], ['game_id', 'player'], 'players')
        with self.assertRaisesRegex(ValueError, 'duplicate keys'):
            a1_compare._same_keys(control, pd.concat([control, control.iloc[:1]]), ['game_id', 'player'], 'players')

    def test_one_sided_metric_is_attributed_to_the_correct_run(self):
        control = pd.DataFrame({'game_id': ['1'], 'player': ['a']})
        candidate = control.assign(fg3m_actual=1.0, fg3m_sim=1.0, fg3m_crps=0.1, fg3m_pit=0.5)
        paired = a1_compare._pair(control, candidate, ['game_id', 'player'])
        result = a1_compare.distribution(paired, 'fg3m', ['1'], np.array([[1]]), True)
        self.assertEqual(result['status'], 'unavailable')
        self.assertEqual(set(result['missing_columns']),
                         {f'fg3m_{part}_control' for part in ('actual', 'sim', 'crps', 'pit')})

    def test_paired_statistics_weight_player_games_and_resample_whole_games(self):
        ids = [f'{i:02}' for i in range(40)]
        keys = [gid for i, gid in enumerate(ids) for _ in range(4 if i < 10 else 3)]
        rows = pd.DataFrame({'game_id': keys})
        rows['pts_actual_control'] = rows['pts_actual_candidate'] = 1.0
        rows['pts_sim_control'], rows['pts_sim_candidate'] = 1.25, 1.5
        rows['pts_crps_control'] = 1.0
        rows['pts_crps_candidate'] = np.where(rows['game_id'].isin(ids[:10]), 1.4, 1.0)
        rows['pts_pit_control'], rows['pts_pit_candidate'] = 0.5, 0.05
        weights = np.array([[1] * 40, [2] * 20 + [0] * 20])
        result = a1_compare.distribution(rows, 'pts', ids, weights, True)
        self.assertEqual((result['status'], result['observations'], result['games']), ('ok', 130, 40))
        self.assertAlmostEqual(result['crps']['change'], 0.4 * 40 / 130)
        self.assertTrue(np.allclose(result['crps']['ci_95'], np.quantile([0.4 * 40 / 130, 0.4 * 40 / 70], [.025, .975])))
        self.assertAlmostEqual(result['bias']['change'], 0.25)
        self.assertAlmostEqual(result['coverage']['change'], 0.6)
        rows.loc[0, 'pts_actual_candidate'] = 2.0
        with self.assertRaisesRegex(ValueError, 'actuals differs'):
            a1_compare.distribution(rows, 'pts', ids, weights, True)

    def test_missing_metric_and_sparse_tier_cannot_pass_as_success(self):
        rows = pd.DataFrame({'game_id': ['1'], 'pts_actual_control': [1.0]})
        result = a1_compare.distribution(rows, 'pts', ['1'], np.array([[1]]), True)
        self.assertEqual(result['status'], 'unavailable')
        for side in ('control', 'candidate'):
            rows[f'pts_actual_{side}'] = 1.0
            rows[f'pts_sim_{side}'] = 1.0
            rows[f'pts_crps_{side}'] = 0.5
            rows[f'pts_pit_{side}'] = 0.5
        result = a1_compare.distribution(rows, 'pts', ['1'], np.array([[1]]), True)
        self.assertEqual(result['status'], 'insufficient_sample')
        self.assertIsNone(result['crps']['ci_95'])
        rows['pts_actual_control'] = rows['pts_actual_candidate'] = np.inf
        with self.assertRaisesRegex(ValueError, 'infinite actual'):
            a1_compare.distribution(rows, 'pts', ['1'], np.array([[1]]), True)

    def test_game_selection_and_simulation_streams_are_independent(self):
        eligible = np.array(['1', '2', '3'])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'games.json'
            path.write_text(json.dumps(['3', '1']))
            self.assertEqual(backtest.select_games(eligible, 0, 7, path).tolist(), ['1', '3'])
            path.write_text(json.dumps(['1', '1']))
            with self.assertRaisesRegex(ValueError, 'unique'):
                backtest.select_games(eligible, 0, 7, path)
            path.write_text(json.dumps(['4']))
            with self.assertRaisesRegex(ValueError, 'outside'):
                backtest.select_games(eligible, 0, 7, path)
        legacy = projection.seed_for('backtest', 'v1', '2026-01-01', '1')
        self.assertEqual(backtest.simulation_seed('v1', '2026-01-01', '1'), legacy)
        self.assertNotEqual(backtest.simulation_seed('v1', '2026-01-01', '1', 1), legacy)
        self.assertEqual(backtest.simulation_seed('v1', '2026-01-01', '1', 1, 'shared'),
                         backtest.simulation_seed('v2', '2026-01-01', '1', 1, 'shared'))

    def test_manifest_rejects_changed_missing_or_duplicate_inputs(self):
        baseline = [{'path': 'one', 'bytes': 5, 'sha256': 'abc'}]
        a1_manifest.require_fingerprints(baseline, baseline, 'control')
        for changed in ([], [{'path': 'one', 'bytes': 5, 'sha256': 'def'}], baseline + baseline):
            with self.assertRaisesRegex(ValueError, 'control:'):
                a1_manifest.require_fingerprints(changed, baseline, 'control')

    def test_manifest_rejects_missing_configured_node_files(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            nodes = {name: {'file': f'{name}.txt'} for name in a1_manifest.train.NODES}
            (path / 'config.json').write_text(json.dumps({'nodes': nodes}))
            for entry in list(nodes.values())[:-1]:
                (path / entry['file']).touch()
            with self.assertRaisesRegex(FileNotFoundError, 'configured node model is missing'):
                a1_manifest.model_paths(path)

    def test_seed_noise_floor_uses_the_larger_absolute_interval_endpoint(self):
        metric = {'ci_95': [-0.3, 0.1]}
        unavailable = {'ci_95': None}
        report = {'players': {'all': {'pts': {'status': 'ok', 'crps': metric},
                                      'reb': {'status': 'insufficient_sample', 'crps': unavailable}}},
                  'games': {'total': {'status': 'ok', 'bias': metric}}, 'win': {'status': 'ok', 'brier': metric}}
        floors = a1_manifest.noise_floors(report)
        self.assertEqual(floors['players']['all']['pts']['crps'], 0.3)
        self.assertIsNone(floors['players']['all']['reb']['crps'])
        self.assertEqual(floors['games']['total']['bias'], 0.3)
        self.assertEqual(floors['win']['brier'], 0.3)

    def test_win_brier_uses_unmodified_boundary_probabilities(self):
        games = pd.DataFrame({'game_id': ['a', 'b'], 'real_home_control': [100, 90],
                              'real_away_control': [90, 100], 'p_home_control': [1.0, 0.0],
                              'p_home_candidate': [0.0, 1.0]})
        result = a1_compare._win_metrics(games, ['a', 'b'], np.zeros((1, 2), dtype=np.int16))
        self.assertEqual(result['brier']['control'], 0.0)
        self.assertEqual(result['brier']['candidate'], 1.0)
        self.assertEqual(result['status'], 'infinite_log_loss')
        self.assertEqual(result['log_loss']['control'], 0.0)
        self.assertIsNone(result['log_loss']['candidate'])
        self.assertEqual(result['log_loss']['infinite_candidate_games'], 2)

    def test_legacy_output_audit_rejects_changed_or_missing_fields(self):
        baseline = pd.DataFrame({'game_id': ['1', '2'], 'margin_crps': [2.0, 3.0]})
        replay = baseline.iloc[::-1].copy()
        self.assertEqual(a1_output_audit.legacy_check(replay, baseline, ['game_id'], 'game')['rows'], 2)
        replay.loc[0, 'margin_crps'] = 2.1
        with self.assertRaisesRegex(ValueError, 'margin_crps differs'):
            a1_output_audit.legacy_check(replay, baseline, ['game_id'], 'game')
        with self.assertRaisesRegex(ValueError, 'missing legacy columns'):
            a1_output_audit.legacy_check(replay.drop(columns='margin_crps'), baseline, ['game_id'], 'game')

    def test_accounting_identifies_simulated_players_missing_from_box_outputs(self):
        roster = pd.DataFrame({'game_id': ['1', '1'], 'player': ['a', 'b'], 'team': ['x', 'x']})
        observed = roster.iloc[:1].copy()
        gaps = a1_compare.roster_gaps(roster, observed)
        self.assertEqual(gaps.to_dict(orient='records'), [{'game_id': '1', 'player': 'b', 'team': 'x'}])
        observed.loc[0, 'team'] = 'y'
        with self.assertRaisesRegex(ValueError, 'roster teams differs'):
            a1_compare.roster_gaps(roster, observed)
        observed.loc[0, 'team'] = 'x'
        observed.loc[0, 'player'] = 'c'
        with self.assertRaisesRegex(ValueError, 'absent from the simulated roster'):
            a1_compare.roster_gaps(roster, observed)


if __name__ == '__main__':
    unittest.main()
