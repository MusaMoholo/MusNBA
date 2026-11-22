#!/usr/bin/env python3
"""Independently reproduce the frozen substitution-screen predictions and game bootstrap."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, sha256_file, write_json  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS, TEST_FROM  # noqa: E402

REPORT = EXPERIMENTS / '20261122_a1_s06_out_screen.json'
SCORES = DERIVED / 'experiments/20261122_a1_s06_out_screen.parquet'
TIERS = ('star', 'starter', 'bench', 'unknown')
NUMERIC = ('period', 'clock', 'margin', 'fouls_before', 'seconds_before', 'stint_before',
           'target_mean_proxy', 'target_deficit')
FEATURES = (*NUMERIC, *(f'tier_{tier}' for tier in TIERS))
PARAMS = {'objective': 'binary', 'num_leaves': 15, 'learning_rate': 0.05, 'min_data_in_leaf': 80,
          'lambda_l2': 1.0, 'seed': 20261122, 'num_threads': 1, 'deterministic': True,
          'force_col_wise': True, 'verbosity': -1}
SEED = 20261122
REPLICATES = 10_000


def matrix(rows: pd.DataFrame) -> pd.DataFrame:
    columns = {name: pd.to_numeric(rows[name], errors='raise').astype(float) for name in NUMERIC}
    columns.update({f'tier_{tier}': (rows['prior_tier'] == tier).astype(float) for tier in TIERS})
    return pd.DataFrame(columns, index=rows.index)


def baseline(train: pd.DataFrame, valid: pd.DataFrame) -> tuple[np.ndarray, int]:
    overall = float(train['label'].astype(int).mean())
    counts = train.assign(period_group=train['period'].clip(upper=5)).groupby(
        ['period_group', 'prior_tier'])['label'].agg(['sum', 'count'])
    lookup = valid[['period', 'prior_tier']].copy()
    lookup['period'] = lookup['period'].clip(upper=5)
    merged = lookup.merge(counts, left_on=['period', 'prior_tier'], right_index=True, how='left', sort=False)
    missing = int(merged['count'].isna().sum())
    expected = ((merged['sum'] + 20 * overall) / (merged['count'] + 20)).fillna(overall)
    return expected.to_numpy(dtype=float), missing


def audit_metrics(rows: pd.DataFrame, recorded: dict) -> float:
    games, inverse = np.unique(rows['game_id'].to_numpy(), return_inverse=True)
    counts = np.bincount(inverse)
    player_games = len(rows[['game_id', 'player']].drop_duplicates())
    supported = len(games) >= 30 and player_games >= 100
    expected_counts = {'observations': len(rows), 'games': len(games), 'player_games': player_games,
                       'outgoing_count': int(rows['label'].astype(int).sum()),
                       'status': 'ok' if supported else 'insufficient_sample'}
    if any(recorded[key] != value for key, value in expected_counts.items()):
        raise ValueError('screen population counts or support status differ')
    y = rows['label'].astype(int).to_numpy(dtype=float)
    draws = np.random.default_rng(SEED).integers(0, len(games), (REPLICATES, len(games))) if supported else None
    maximum_error = 0.0
    for metric in ('brier', 'log_loss'):
        losses = {}
        for name in ('baseline', 'candidate'):
            probability = rows[f'{name}_probability'].to_numpy(dtype=float)
            if not np.isfinite(probability).all() or ((probability <= 0) | (probability >= 1)).any():
                raise ValueError(f'{name} contains a non-finite or boundary probability')
            losses[name] = ((probability - y) ** 2 if metric == 'brier'
                            else -np.log(np.where(y == 1, probability, 1 - probability)))
        by_game = {name: np.bincount(inverse, weights=loss) for name, loss in losses.items()}
        actual = recorded[metric]
        for key, value in (('baseline', losses['baseline'].mean()), ('candidate', losses['candidate'].mean()),
                           ('change', (losses['candidate'] - losses['baseline']).mean())):
            maximum_error = max(maximum_error, abs(float(value) - float(actual[key])))
        if draws is None:
            if actual['ci_95'] is not None:
                raise ValueError('an unsupported cell has a bootstrap interval')
        else:
            sampled_difference = ((by_game['candidate'][draws] - by_game['baseline'][draws]).sum(axis=1)
                                  / counts[draws].sum(axis=1))
            interval = np.quantile(sampled_difference, [0.025, 0.975])
            maximum_error = max(maximum_error, float(np.max(np.abs(interval - np.asarray(actual['ci_95'])))))
    if maximum_error > 1e-12:
        raise ValueError(f'point estimate or direct-resampling bootstrap differs by {maximum_error}')
    return maximum_error


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=EXPERIMENTS / '20261122_a1_s06_out_screen_audit.json')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite the screen audit')
    report = json.loads(REPORT.read_text())
    if report['model_params'] != PARAMS or report['num_boost_round'] != 120 or report['features'] != list(FEATURES):
        raise ValueError('screen model differs from its frozen protocol')
    for path, digest in report['input_sha256'].items():
        if sha256_file(ROOT / path) != digest:
            raise ValueError(f'screen input differs from its fingerprint: {path}')
    if sha256_file(SCORES) != report['output_sha256'][str(SCORES.relative_to(ROOT))]:
        raise ValueError('saved screen scores differ from their fingerprint')
    populations = {}
    paths = [Path(__file__), REPORT, SCORES]
    for name in ('seed', *FOLDS):
        path = DERIVED / 'experiments' / f'20261122_a1_s06_fold_{name}_v3.parquet'
        all_rows = pd.read_parquet(path)
        populations[name] = all_rows.loc[all_rows['decision'].eq('out')].reset_index(drop=True)
        paths.append(path)
    saved = pd.read_parquet(SCORES)
    if len(saved) != sum(len(populations[fold]) for fold in FOLDS):
        raise ValueError('saved scores do not contain the fixed outgoing populations')
    maximum_probability_error = maximum_metric_error = 0.0
    checked_cells = 0
    for index, fold in enumerate(FOLDS):
        valid = populations[fold]
        train = pd.concat([populations[name] for name in ['seed', *list(FOLDS)[:index]]], ignore_index=True)
        recorded = report['folds'][fold]
        if (train['date_et'].max() >= FOLDS[fold][1] or valid['date_et'].ge(TEST_FROM).any()
                or set(train['game_id']) & set(valid['game_id'])
                or not valid['date_et'].between(FOLDS[fold][1], FOLDS[fold][2]).all()):
            raise ValueError(f'{fold}: training/validation cutoff differs')
        if (recorded['training_rows'] != len(train) or recorded['training_games'] != train['game_id'].nunique()
                or recorded['training_through'] != train['date_et'].max()
                or recorded['target_missing'] != valid['target_mean_proxy'].isna().sum()
                or recorded['deficit_missing'] != valid['target_deficit'].isna().sum()):
            raise ValueError(f'{fold}: recorded training or missingness counts differ')
        scored = saved.loc[saved['fold'].eq(fold)].reset_index(drop=True)
        fields = ['window_id', 'game_id', 'date_et', 'team', 'player', 'prior_tier', 'period', 'label']
        pd.testing.assert_frame_equal(scored[fields], valid[fields], check_dtype=False)
        expected_baseline, missing = baseline(train, valid)
        if missing != recorded['baseline_overall_fallback_rows']:
            raise ValueError(f'{fold}: baseline fallback count differs')
        model = lgb.train(PARAMS, lgb.Dataset(matrix(train), label=train['label'].astype(int)),
                          num_boost_round=120)
        expected_candidate = model.predict(matrix(valid), num_threads=1)
        if not isinstance(expected_candidate, np.ndarray):
            raise ValueError(f'{fold}: model returned non-array predictions')
        for name, expected in (('baseline', expected_baseline), ('candidate', expected_candidate)):
            error = float(np.max(np.abs(scored[f'{name}_probability'].to_numpy(dtype=float) - expected)))
            maximum_probability_error = max(maximum_probability_error, error)
            if error > 1e-12:
                raise ValueError(f'{fold}: {name} probability differs by {error}')
        splits = dict(zip(FEATURES, (int(value) for value in model.feature_importance())))
        if splits != recorded['feature_split_counts']:
            raise ValueError(f'{fold}: independently fitted feature splits differ')
        maximum_metric_error = max(maximum_metric_error, audit_metrics(scored, recorded['all']))
        checked_cells += 1
        for tier, tier_report in recorded['tiers'].items():
            maximum_metric_error = max(maximum_metric_error,
                                       audit_metrics(scored.loc[scored['prior_tier'].eq(tier)], tier_report))
            checked_cells += 1
        print(f'{fold}: {len(scored)} predictions independently reproduced', flush=True)
    maximum_metric_error = max(maximum_metric_error, audit_metrics(saved, report['pooled']))
    upper = report['pooled']['brier']['ci_95'][1]
    favourable = sum(report['folds'][fold]['all']['brier']['change'] < 0 for fold in FOLDS)
    if (favourable != report['favourable_fold_points']
            or report['diagnostic_screen_pass'] != (upper < 0 and favourable >= 3)):
        raise ValueError('reported frozen screening decision differs')
    result = {'experiment': 'a1_s06_outgoing_screen_independent_audit',
              'scored_rows': len(saved), 'games': int(saved['game_id'].nunique()),
              'fold_and_tier_cells': checked_cells, 'bootstrap_replicates_per_supported_cell': REPLICATES,
              'maximum_probability_error': maximum_probability_error, 'maximum_metric_error': maximum_metric_error,
              'diagnostic_screen_pass': report['diagnostic_screen_pass'],
              'input_sha256': {str(path.relative_to(ROOT)): sha256_file(path) for path in paths}}
    write_json(args.output, result, pretty=True)
    print(f'audited {len(saved)} rows, {checked_cells} fold/tier cells and pooled game bootstrap', flush=True)


if __name__ == '__main__':
    main()
