import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pandas as pd

from scripts import a1_flow_audit, a1_flow_capture, a1_flow_compare, a1_profile_spread, a1_shot_trace, a1_signal, a1_variant_components, aggregate, smoke


class SignalDiagnosisTests(unittest.TestCase):
    def sides(self):
        rows = []
        for game in range(6):
            for side, shift in (('away', -0.5), ('home', 0.5)):
                off = game + shift
                defence = (game % 3) - shift
                row = {'game_id': str(game), 'side': side, 'offence': off, 'opp_defence': defence}
                for j, outcome in enumerate(a1_signal.OUTCOMES):
                    actual = j + 2 * off + 3 * defence
                    row[f'real_{outcome}'] = actual
                    row[f'sim_{outcome}'] = actual + 1 + 0.4 * off - 0.2 * defence
                rows.append(row)
        return pd.DataFrame(rows)

    def test_paired_game_bootstrap_recovers_known_difference(self):
        report = a1_signal.loading_report(self.sides(), replicates=100, seed=3)
        for outcome in a1_signal.OUTCOMES:
            diff = report[outcome]['sim_minus_real']
            for key, expected in (('intercept', 1), ('offence', 0.4), ('opp_defence', -0.2)):
                self.assertAlmostEqual(diff[key]['estimate'], expected)
                np.testing.assert_allclose(diff[key]['ci_95'], [expected, expected], atol=1e-10)

    def test_bootstrap_rejects_missing_or_duplicate_team_sides(self):
        rows = self.sides()
        with self.assertRaisesRegex(ValueError, 'exactly two'):
            a1_signal.loading_report(rows.iloc[:-1], replicates=10)
        duplicate = pd.concat([rows.iloc[:-1], rows.iloc[[-2]]], ignore_index=True)
        with self.assertRaisesRegex(ValueError, 'distinct team sides'):
            a1_signal.loading_report(duplicate, replicates=10)

    def test_manifest_rejects_missing_or_duplicate_games(self):
        ids = [str(n) for n in range(200)]
        manifest = {'control': {'games': [{'game_id': x} for x in ids]}}
        games = pd.DataFrame({'game_id': ids, 'home': '1', 'away': '2'})
        self.assertEqual(len(a1_signal.fixed_games(games, manifest)), 200)
        with self.assertRaisesRegex(ValueError, 'exactly match'):
            a1_signal.fixed_games(games.iloc[:-1], manifest)
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            a1_signal.fixed_games(pd.concat([games, games.iloc[[0]]]), manifest)

    def test_components_use_the_same_side_and_matching_denominators(self):
        game = {'game_id': '1', 'date_et': '2026-01-01', 'home': 'H', 'away': 'A',
                'home_sim': 100, 'away_sim': 110, 'real_home': 101, 'real_away': 111}
        for side in ('home', 'away'):
            for prefix in ('sim', 'real'):
                for name, count in (('poss', 100), ('fga', 80), ('fgm', 40), ('fg3a', 30), ('fg3m', 12),
                                    ('fta', 20), ('tov', 10), ('oreb', 8)):
                    game[f'{prefix}_{name}_{side}'] = count
        games = pd.DataFrame([game])
        ratings = pd.DataFrame([{'game_id': '1', 'off_h': 2, 'off_a': 3, 'def_h': -4, 'def_a': -5}])
        sides = a1_signal.component_sides(games, ratings).set_index('side')
        self.assertEqual(sides.loc['home', 'offence'], 2)
        self.assertEqual(sides.loc['home', 'opp_defence'], -5)
        self.assertEqual(sides.loc['away', 'opp_defence'], -4)
        self.assertEqual(sides.loc['home', 'real_points_100'], 101)
        self.assertEqual(sides.loc['home', 'sim_fg_pct'], 0.5)
        self.assertEqual(sides.loc['away', 'real_fg3a_share'], 0.375)
        game['real_fg3a_home'] = 0
        with self.assertRaisesRegex(ValueError, 'fg3a must be positive'):
            a1_signal.component_sides(pd.DataFrame([game]), ratings)
        game['real_fg3a_home'] = 30
        game['sim_tov_away'] = -1
        with self.assertRaisesRegex(ValueError, 'counts cannot be negative'):
            a1_signal.component_sides(pd.DataFrame([game]), ratings)

    def test_hypothetical_actor_uses_its_own_matchup_and_zone(self):
        base = SimpleNamespace(
            seg=pd.DataFrame({'seg_id': [0], 'actor': ['a'], 'zone': ['rim'],
                              'mu_fg_rim': [0.4], 'mu_fg_three': [0.3], 'mu_fg_shot': [0.4]}),
            off=pd.DataFrame({'seg_id': [0, 0], 'player': ['a', 'b']}),
            dfn=pd.DataFrame({'seg_id': [0], 'player': ['d']}),
            _pos_off=(np.array([0]), np.array([2])), _pos_def=(np.array([0]), np.array([1])),
            profile=['usage'], lineup=['off_usage'], mu_cols=['mu_fg_rim', 'mu_fg_three'],
            mu_shot=['mu_fg_shot'], stype=False, _relative_missing_policy='legacy', _preserve_groups=False)
        scorer = aggregate.Scorer(base, {})
        index = pd.MultiIndex.from_tuples([(0, 'a'), (0, 'b')], names=['source', 'actor'])
        scorer.actor_mu = pd.DataFrame({'mu_fg_rim': [0.4, 0.6], 'mu_fg_three': [0.3, 0.5]}, index=index)
        branch = scorer._branches('shot_result', np.array([0, 0]),
                                  {'actor': np.array(['a', 'b']), 'zone': np.array(['rim', 'above3'])})
        self.assertEqual(branch.profile, base.profile)
        self.assertEqual(branch._relative_missing_policy, 'legacy')
        np.testing.assert_allclose(branch.seg['mu_fg_rim'], [0.4, 0.6])
        np.testing.assert_allclose(branch.seg['mu_fg_shot'], [0.4, 0.5])
        with self.assertRaisesRegex(ValueError, 'absent from the offensive lineup'):
            scorer._branches('what', np.array([0]), {'actor': np.array(['missing'])})

    def test_saved_models_require_the_matching_fold_and_feature_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = {'version': 'candidate', 'default': {'features': 'input.parquet', 'segments': None}}
            metadata = {'columns': ['x'], 'categorical': [], 'temperature': 1.0, 'intercepts': None}
            config = {'version': 'candidate_F4', 'fold': True, 'train_through': '2025-12-31',
                      'features': 'input.parquet', 'segments': None,
                      'nodes': {name: {**metadata, 'file': f'{name}.txt'} for name in aggregate.SIM_NODES}}
            meta = {'fitted': {name: metadata for name in aggregate.SIM_NODES}, 'metrics': {}}
            (root / 'spec.json').write_text(json.dumps(spec))
            (root / 'config.json').write_text(json.dumps(config))
            (root / 'meta.json').write_text(json.dumps(meta))
            with patch('lightgbm.Booster', return_value=object()) as booster:
                fitted, _, loaded = aggregate.load_saved_models('F4', root / 'spec.json', root)
                self.assertEqual(len(fitted), len(aggregate.SIM_NODES))
                self.assertEqual(booster.call_count, len(aggregate.SIM_NODES))
                self.assertEqual(loaded, spec)
            config['train_through'] = '2026-01-01'
            (root / 'config.json').write_text(json.dumps(config))
            with self.assertRaisesRegex(ValueError, 'training cutoff'):
                aggregate.load_saved_models('F4', root / 'spec.json', root)
            config['train_through'] = '2025-12-31'
            config['features'] = 'other.parquet'
            (root / 'config.json').write_text(json.dumps(config))
            with self.assertRaisesRegex(ValueError, 'features differs'):
                aggregate.load_saved_models('F4', root / 'spec.json', root)

    def test_variant_score_and_pace_decompositions_reconcile(self):
        control = {'game_id': '1', 'date_et': '2026-01-01', 'home': 'H', 'away': 'A',
                   'real_home': 101, 'real_away': 99, 'total_sim': 200}
        for side in ('home', 'away'):
            for name, value in (('poss', 100), ('fga', 85), ('fgm', 40), ('fg3a', 30), ('fg3m', 10),
                                ('fta', 20), ('tov', 12), ('oreb', 8)):
                control[f'sim_{name}_{side}'] = value
        candidate = {**control, 'total_sim': 204, 'sim_fgm_home': 41, 'sim_fg3m_home': 11,
                     'sim_poss_home': 101}
        changes = a1_variant_components.paired_components(pd.DataFrame([control]), pd.DataFrame([candidate])).iloc[0]
        self.assertEqual(changes['points'], 4)
        self.assertEqual(changes['two_point_points'], 0)
        self.assertEqual(changes['three_point_points'], 3)
        self.assertEqual(changes['free_throw_residual'], 1)
        self.assertAlmostEqual(changes['pace_term'] + changes['efficiency_term'], 4)
        candidate['real_home'] = 102
        with self.assertRaisesRegex(ValueError, 'real_home differ'):
            a1_variant_components.paired_components(pd.DataFrame([control]), pd.DataFrame([candidate]))

    def test_profile_spread_preserves_negative_cross_half_covariance(self):
        rows = []
        for player, profile in (('a', 0.4), ('b', 0.6)):
            for half, date in (('early', '2026-01-15'), ('late', '2026-03-15')):
                for i in range(15):
                    rows.append({'game_id': f'{half}-{i % 3}', 'date_et': date, 'zone': 'rim', 'player': player,
                                 'team_valid': True, 'profile': profile,
                                 'made': int((player == 'a') == (half == 'early'))})
        spread = a1_profile_spread.cross_half_spread(pd.DataFrame(rows), ('rim',))['rim']
        self.assertEqual(spread['players'], 2)
        self.assertAlmostEqual(spread['profile_variance'], 0.01)
        self.assertAlmostEqual(spread['observed_cross_half_covariance'], -0.25)

    def test_invalid_defensive_five_is_counted_and_excluded(self):
        shot = {'game_id': '1', 'date_et': '2026-01-01', 'zone': 'rim', 'made': 1,
                'actor': 'a', 'offense': 'H', 'defense': 'A'}
        for i in range(1, 6):
            shot[f'off_{i}'] = 'a' if i == 1 else f'o{i}'
            shot[f'def_{i}'] = f'd{i}'
        invalid = {**shot, 'def_5': 'd4'}
        profiles = []
        for player in ('a', 'd1', 'd2', 'd3', 'd4', 'd5'):
            row = {'game_id': '1', 'player': player, 'team': 'H' if player == 'a' else 'A',
                   'usage': 0.2, 'shots_eff': 100, 'd_segs_eff': 300}
            row.update({f'fg_{z}': 0.5 for z in a1_profile_spread.SHOOTER_ZONES})
            row.update({f'd_fg_{z}': 0.4 for z in a1_profile_spread.DEFENDER_ZONES})
            profiles.append(row)
        shooter, defender, coverage = a1_profile_spread.profile_exposures(pd.DataFrame([shot, invalid]), pd.DataFrame(profiles))
        self.assertEqual(len(shooter), 2)
        self.assertEqual(len(defender), 5)
        self.assertEqual(coverage['invalid_defensive_lineups'], 1)

    def test_shot_trace_quartiles_keep_missing_and_score_observed_makes(self):
        rows = pd.DataFrame({'game_id': ['1', '1', '2', '2', '3'],
                             'player': ['a', 'b', 'c', 'd', 'e'], 'actor_on_five': [True] * 5,
                             'made': [1, 0, 1, 0, 1], 'predicted': [0.8, 0.2, 0.7, 0.3, 0.9],
                             'input': [1, 2, 3, 4, np.nan]})
        report = a1_shot_trace.quartiles(rows, 'input')
        self.assertEqual([report['bins'][q]['shots'] for q in ('Q1', 'Q2', 'Q3', 'Q4', 'unknown')], [1] * 5)
        self.assertAlmostEqual(report['bins']['unknown']['brier'], 0.01)
        self.assertAlmostEqual(report['bins']['Q1']['actual_make'], 1)

    def test_scheduled_lineups_exclude_unknown_real_players(self):
        ids = ['a', 'b', 'c', 'd', 'e', 'f']
        tables = np.broadcast_to(np.array([0, 1, 2, 3, 4]), (1, 2880, 5)).copy()
        combo = np.array([[0, 0]])
        profiles = {name: np.arange(6, dtype=float) for name in ('usage', 'fg_rim', 'd_fg_rim')}
        stints = pd.DataFrame([{'team': 'H', 'player': player, 'period': 1, 'start_t': 0, 'end_t': 2880}
                               for player in ids[:5]])
        report = a1_flow_capture.scheduled_overlap(tables, combo, ids, profiles, stints, 'H', 0)
        self.assertEqual(report['valid_ticks'], 288)
        self.assertEqual(report['scheduled_exact_five'], 1)
        self.assertEqual(a1_flow_audit.real_tick_counts(stints, set(ids)), (288, 0, 0))
        tables[0, 5, 0] = 5
        report = a1_flow_capture.scheduled_overlap(tables, combo, ids, profiles, stints, 'H', 0)
        self.assertAlmostEqual(report['scheduled_exact_five'], 287 / 288)
        stints.loc[0, 'player'] = 'unknown'
        report = a1_flow_capture.scheduled_overlap(tables, combo, ids, profiles, stints, 'H', 0)
        self.assertEqual(report['invalid_ticks'], 288)
        self.assertIsNone(report['scheduled_exact_five'])
        self.assertEqual(a1_flow_audit.real_tick_counts(stints, set(ids)), (0, 288, 1))
        with self.assertRaisesRegex(ValueError, 'accounting mismatch'):
            a1_flow_audit.assert_equal(np.array([1.0, 2.0]), np.array([1.0, 3.0]), 'corrupt')

    def test_smoke_discovers_only_reported_m6a_player_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('2026_m6a.parquet', '2026_m6a_events.parquet', '2026_m6a_components.parquet'):
                (root / name).touch()
            (root / '2026_m6a.json').write_text(json.dumps({'experiment': 'm6a_aggregation'}))
            (root / '2026_m6a_events.json').write_text(json.dumps({'experiment': 'other'}))
            self.assertEqual([p.name for p in smoke.m6a_player_outputs(root, root)], ['2026_m6a.parquet'])

    def test_expanded_control_requires_every_original_value(self):
        baseline = pd.DataFrame({'game_id': ['1', '2'], 'player': ['a', 'b'], 'pts_sim': [4.5, 6.0]})
        expanded = baseline.assign(fga_sim=[3.0, 5.0]).iloc[::-1]
        self.assertEqual(a1_flow_compare.exact_reproduction(baseline, expanded, ['game_id', 'player']), 6)
        expanded.loc[expanded['game_id'] == '1', 'pts_sim'] += 0.1
        with self.assertRaisesRegex(ValueError, 'differs in pts_sim'):
            a1_flow_compare.exact_reproduction(baseline, expanded, ['game_id', 'player'])

    def test_teacher_components_use_teacher_possessions_and_team_identity(self):
        free = pd.DataFrame([{'game_id': '1', 'side': 'home', 'team': 'H', 'offence': 1.0, 'opp_defence': -1.0}])
        values = {'game_id': '1', 'side': 'home', 'team': 'H', 'eligible_possessions': 100}
        for kind in ('actual', 'sim'):
            for stat, count in (('pts', 110), ('fga', 80), ('fgm', 40), ('fg3a', 30), ('fg3m', 12),
                                ('fta', 20), ('tov', 10), ('oreb', 8)):
                values[f'{stat}_{kind}'] = count
        teacher = a1_flow_compare.teacher_sides(free, pd.DataFrame([values]))
        self.assertEqual(teacher.loc[0, 'real_points_100'], 110)
        self.assertEqual(teacher.loc[0, 'sim_fg_pct'], 0.5)
        values['team'] = 'A'
        with self.assertRaisesRegex(ValueError, 'team identities differ'):
            a1_flow_compare.teacher_sides(free, pd.DataFrame([values]))


if __name__ == '__main__':
    unittest.main()
