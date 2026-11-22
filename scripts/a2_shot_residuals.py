#!/usr/bin/env python3
"""Earlier-fold, teacher-forced within-player shooting residual feasibility screen."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, sha256_file, write_json  # noqa: E402
from scripts import a1_compare, a1_substitution_engine, nodes  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS, TEST_FROM  # noqa: E402

FOLD_SEASONS = {'F1': '2024', 'F2': '2025', 'F3': '2026'}
ROLES = ('star', 'starter', 'bench')
REPORT = EXPERIMENTS / '20261122_a2_shot_residuals_f1_f3.json'


def aligned_source(fold: str) -> tuple[pd.DataFrame, dict[str, str]]:
    cutoff, start, end = FOLDS[fold]
    if end >= TEST_FROM:
        raise ValueError('final-test dates are not eligible')
    report_path = EXPERIMENTS / f'20261122_a1_s04_rim_{fold}_v2.json'
    predictions_path = DERIVED / f'experiments/20261122_a1_s04_rim_{fold}_v2.parquet'
    segment_path = DERIVED / f'history/{FOLD_SEASONS[fold]}/segments.parquet'
    report = json.loads(report_path.read_text())
    if report['training_cutoff'] != cutoff or report['rows_sha256'] != sha256_file(predictions_path):
        raise ValueError(f'{fold}: source prediction provenance differs')
    caches = [ROOT / path for path in report['input_sha256'] if path.endswith('/shot_result.npz')]
    if len(caches) != 1 or report['input_sha256'][str(caches[0].relative_to(ROOT))] != sha256_file(caches[0]):
        raise ValueError(f'{fold}: saved shot cache fingerprint differs')
    columns = ['game_id', 'date_et', 'game_ok', 'offense', 'defense', 'end_type', 'heave', 'zone',
               'made', 'and_one', 'actor', 'period', 'score_off', 'score_def', 'start_clock', 'shot_time',
               'x', 'y', *[f'off_{i}' for i in range(1, 6)]]
    source = pd.read_parquet(segment_path, columns=columns)
    eligible = (source['game_ok'] & source['offense'].astype(str).isin(nodes.NBA_TEAM_IDS)
                & source['defense'].astype(str).isin(nodes.NBA_TEAM_IDS) & source['end_type'].eq('shot')
                & ~source['heave'].fillna(False) & source['zone'].isin(nodes.ZONES)
                & source['date_et'].between(start, end))
    source = source.loc[eligible].reset_index(drop=True)
    predictions = pd.read_parquet(predictions_path)
    if len(source) != len(predictions):
        raise ValueError(f'{fold}: source and prediction row counts differ')
    actual_y = np.where(source['made'].eq(1), np.where(source['and_one'], 2, 1), 0)
    for column in ('game_id', 'date_et', 'zone', 'made'):
        if not np.array_equal(source[column].to_numpy(), predictions[column].to_numpy()):
            raise ValueError(f'{fold}: {column} differs between shot and prediction rows')
    if not np.array_equal(actual_y, predictions['outcome'].to_numpy()):
        raise ValueError(f'{fold}: predicted shot outcome labels differ')
    with np.load(caches[0], allow_pickle=False) as cache:
        selection = (cache['date'] >= start) & (cache['date'] <= end)
        metadata = {'game': source['game_id'], 'date': source['date_et'], 'zone': source['zone'],
                    'period': source['period'], 'margin': source['score_off'] - source['score_def'],
                    'y': actual_y}
        for name, actual in metadata.items():
            if not np.array_equal(cache[name][selection], np.asarray(actual)):
                raise ValueError(f'{fold}: cached {name} differs from actual shot rows')
        cache_columns = list(cache['columns'])
        matrix = cache['X'][selection]
        extra = {'start_clock': source['start_clock'], 'shot_time': source['shot_time'].clip(lower=0),
                 'distance': np.sqrt((source['x'] - 25) ** 2 + source['y'] ** 2),
                 'lateral': (source['x'] - 25).abs()}
        for name, actual in extra.items():
            cached = matrix[:, cache_columns.index(name)]
            if not np.isclose(cached, np.asarray(actual, dtype=float), rtol=1e-5, atol=1e-4, equal_nan=True).all():
                raise ValueError(f'{fold}: cached {name} differs from actual shot rows')
    source['probability'] = predictions['control_make']
    if (not source['made'].isin([0, 1]).all() or not np.isfinite(source['probability']).all()
            or not source['probability'].between(0, 1).all()):
        raise ValueError(f'{fold}: invalid observed or predicted make probability')
    source['fold'] = fold
    inputs = {str(path.relative_to(ROOT)): sha256_file(path)
              for path in (report_path, predictions_path, segment_path, caches[0])}
    return source, inputs


def attach_roles(shots: pd.DataFrame, roles: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    if roles.duplicated(['game_id', 'player']).any():
        raise ValueError('prior roles have duplicate player-game keys')
    on_five = shots[[f'off_{i}' for i in range(1, 6)]].eq(shots['actor'], axis=0).any(axis=1)
    source = shots[on_five].rename(columns={'actor': 'player'}).copy()
    source = source.merge(roles[['game_id', 'player', 'team', 'tier']], on=['game_id', 'player'],
                          how='left', validate='many_to_one')
    valid = source['team'].notna() & source['team'].eq(source['offense']) & source['tier'].isin(ROLES)
    counts = {'shots': len(shots), 'actor_outside_recorded_five': int((~on_five).sum()),
              'missing_wrong_team_or_unknown_role': int((~valid).sum()), 'eligible_shots': int(valid.sum())}
    rows = source.loc[valid, ['fold', 'game_id', 'player', 'tier', 'made', 'probability']].copy()
    rows['residual'] = rows['made'] - rows['probability']
    return rows, counts


def player_games(shots: pd.DataFrame) -> pd.DataFrame:
    rows = shots.assign(residual_squared=shots['residual'] ** 2).groupby(
        ['fold', 'game_id', 'player', 'tier'], as_index=False).agg(
            shots=('residual', 'size'), residual_sum=('residual', 'sum'),
            residual_squared=('residual_squared', 'sum'))
    rows = rows[rows['shots'] >= 2].copy()
    rows['ordered_pairs'] = rows['shots'] * (rows['shots'] - 1)
    rows['pair_mean'] = (rows['residual_sum'] ** 2 - rows['residual_squared']) / rows['ordered_pairs']
    return rows


def summarize(rows: pd.DataFrame) -> dict:
    games = rows.groupby(['fold', 'game_id'])['pair_mean'].mean().to_numpy(dtype=float)
    result: dict = {'games': len(games), 'player_games': len(rows), 'shots': int(rows['shots'].sum()),
                    'ordered_pairs': int(rows['ordered_pairs'].sum())}
    if len(games) < 50 or len(rows) < 100:
        result['status'] = 'insufficient'
        return result
    rng = np.random.default_rng(a1_compare.BOOTSTRAP_SEED)
    draws = rng.integers(0, len(games), (a1_compare.BOOTSTRAP_REPLICATES, len(games)))
    bootstrap = games[draws].mean(axis=1)
    result.update({'status': 'supported', 'estimate': float(games.mean()),
                   'ci_95': [float(x) for x in np.quantile(bootstrap, [.025, .975])]})
    return result


def main() -> None:
    if REPORT.exists():
        raise FileExistsError('refusing to overwrite an existing feasibility report')
    all_shots = []
    inputs, counts = {}, {}
    for fold in FOLD_SEASONS:
        shots, fingerprints = aligned_source(fold)
        roles = a1_substitution_engine.load_features(fold)
        usable, counts[fold] = attach_roles(shots, roles)
        counts[fold]['usable_player_games_with_fewer_than_two_shots'] = int(
            usable.groupby(['game_id', 'player']).size().lt(2).sum())
        inputs.update(fingerprints)
        role_file = DERIVED / f'experiments/20261122_a1_s05_unconditional_{fold}_corrected.parquet'
        inputs[str(role_file.relative_to(ROOT))] = sha256_file(role_file)
        all_shots.append(usable)
    rows = player_games(pd.concat(all_shots, ignore_index=True))
    cohorts = {}
    for fold in (*FOLD_SEASONS, 'pooled_F1_F3'):
        subset = rows if fold == 'pooled_F1_F3' else rows[rows['fold'].eq(fold)]
        cohorts[fold] = {'all': summarize(subset), **{
            role: summarize(subset[subset['tier'].eq(role)]) for role in ROLES}}
    write_json(REPORT, {
        'experiment': 'a2_earlier_fold_shot_residual_feasibility',
        'protocol': 'TRAINING_PLAN.md: earlier-fold event feasibility screen',
        'population': 'teacher-forced observed shots, F1-F3 validation dates only',
        'bootstrap': {'unit': 'complete game', 'replicates': a1_compare.BOOTSTRAP_REPLICATES,
                      'seed': a1_compare.BOOTSTRAP_SEED, 'confidence': .95},
        'counts': counts, 'cohorts': cohorts, 'input_sha256': inputs,
        'limitations': ['actual shot selection and observed lineups',
                        'within-game covariance combines talent, form, shared factors and model misspecification',
                        'no simulated-world comparison; not an identified latent component or promotion result'],
    }, pretty=True)
    print(f'saved {REPORT.relative_to(ROOT)}; pooled eligible player-games: {len(rows)}')


if __name__ == '__main__':
    main()
