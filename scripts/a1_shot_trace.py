#!/usr/bin/env python3
"""Trace the frozen F4 shot-result node on the fixed, actual-shot panel."""
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
from basketball_common import sha256_file, write_json  # noqa: E402
from scripts import a1_compare, a1_profile_spread as profiles, a1_signal, nodes, train  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS  # noqa: E402

CACHE = ROOT / 'data/derived/nodes/variant_8424e4ae796e'
MODEL = ROOT / 'data/models/folds/v1.2d_F4_all'
SHOT_FILE = CACHE / 'shot_result.npz'


def aligned(shots: pd.DataFrame, shooter: pd.DataFrame, X: pd.DataFrame, meta: dict) -> int:
    checks = {
        'game': (meta['game'], shots['game_id']), 'date': (meta['date'], shots['date_et']),
        'period': (meta['period'], shots['period']), 'zone': (meta['zone'], shots['zone']),
        'result': (meta['y'], np.where(shots['made'] == 1, np.where(shots['and_one'], 2, 1), 0)),
        'margin': (meta['margin'], shots['score_off'] - shots['score_def']),
        'start_clock': (X['start_clock'], shots['start_clock']),
        'shot_time': (X['shot_time'], shots['shot_time'].clip(lower=0)),
        'distance': (X['distance'], np.sqrt((shots['x'] - 25) ** 2 + shots['y'] ** 2)),
        'lateral': (X['lateral'], (shots['x'] - 25).abs()),
    }
    for name, (cached, actual) in checks.items():
        if len(cached) != len(actual):
            raise ValueError(f'{name} row count differs')
        left, right = np.asarray(cached), np.asarray(actual)
        same = (np.isclose(left, right, rtol=1e-5, atol=1e-4, equal_nan=True)
                if np.issubdtype(left.dtype, np.number) else left == right)
        if not same.all():
            raise ValueError(f'{name} has {int((~same).sum())} mismatched rows')
    on_five = shots[[f'off_{i}' for i in range(1, 6)]].eq(shots['actor'], axis=0).any(axis=1)
    if not shooter['team_valid'].all():
        raise ValueError('shooter profile is missing or attached to the wrong team')
    for name in ('usage', 'shots_eff', *[f'fg_{z}' for z in nodes.ZONES]):
        actual = shooter[name].to_numpy(dtype=float)
        cached = X[f'actor_{name}'].to_numpy(dtype=float)
        if not np.isclose(cached[on_five], actual[on_five], rtol=1e-5, atol=1e-4, equal_nan=True).all():
            raise ValueError(f'shooter profile {name} differs on a recorded offensive five')
        if not np.isnan(cached[~on_five]).all():
            raise ValueError(f'shooter profile {name} exists for an actor outside the offensive five')
    return int((~on_five).sum())


def summary(rows: pd.DataFrame) -> dict:
    if rows.empty:
        return {'shots': 0, 'games': 0, 'players': 0}
    p, y = rows['predicted'].to_numpy(dtype=float), rows['made'].to_numpy(dtype=float)
    if not (np.isfinite(p).all() and ((0 < p) & (p < 1)).all() and np.isin(y, [0, 1]).all()):
        raise ValueError('invalid shot outcome or predicted probability')
    return {'shots': len(rows), 'games': rows['game_id'].nunique(), 'players': rows['player'].nunique(),
            'actor_outside_five': int((~rows['actor_on_five']).sum()),
            'predicted_make': float(p.mean()), 'actual_make': float(y.mean()),
            'binary_log_loss': float(np.mean(-y * np.log(p) - (1 - y) * np.log1p(-p))),
            'brier': float(np.mean((p - y) ** 2))}


def extreme_difference(rows: pd.DataFrame, labels: np.ndarray) -> dict | None:
    data = rows[['game_id', 'made', 'predicted']].copy()
    data['bin'] = labels
    data = data[data['bin'].isin(['Q1', 'Q4'])]
    if set(data['bin']) != {'Q1', 'Q4'}:
        return None
    games = np.sort(rows['game_id'].unique())
    grouped = data.groupby(['game_id', 'bin']).agg(n=('made', 'size'), actual=('made', 'sum'),
                                                 predicted=('predicted', 'sum'))
    matrices = []
    for label in ('Q1', 'Q4'):
        values = grouped.xs(label, level='bin').reindex(games, fill_value=0)
        matrices.append(values[['n', 'actual', 'predicted']].to_numpy(dtype=float))
    replicates, seed = a1_compare.BOOTSTRAP_REPLICATES, a1_compare.BOOTSTRAP_SEED
    draws = np.random.default_rng(seed).integers(0, len(games), (replicates, len(games)))
    weights = np.zeros(draws.shape, dtype=np.int16)
    np.add.at(weights, (np.arange(replicates)[:, None], draws), 1)
    first, fourth = (weights @ matrix for matrix in matrices)
    valid = (first[:, 0] > 0) & (fourth[:, 0] > 0)
    first, fourth = first[valid], fourth[valid]
    observed = fourth[:, 1] / fourth[:, 0] - first[:, 1] / first[:, 0]
    predicted = fourth[:, 2] / fourth[:, 0] - first[:, 2] / first[:, 0]
    totals1, totals4 = (matrix.sum(axis=0) for matrix in matrices)
    point_actual = totals4[1] / totals4[0] - totals1[1] / totals1[0]
    point_predicted = totals4[2] / totals4[0] - totals1[2] / totals1[0]
    def interval(point, samples):
        return {'estimate': float(point), 'ci_95': [float(v) for v in np.quantile(samples, [0.025, 0.975])]}
    return {'observed': interval(point_actual, observed), 'predicted': interval(point_predicted, predicted),
            'observed_minus_predicted': interval(point_actual - point_predicted, observed - predicted),
            'game_cluster_bootstrap_valid': int(valid.sum()), 'requested': replicates, 'seed': seed}


def quartiles(rows: pd.DataFrame, column: str) -> dict:
    values = rows[column].to_numpy(dtype=float)
    known = np.isfinite(values)
    if not known.any():
        return {'cutpoints': None, 'bins': {'unknown': summary(rows)}}
    cuts = np.quantile(values[known], [0.25, 0.5, 0.75])
    labels = np.select([~known, values <= cuts[0], values <= cuts[1], values <= cuts[2]],
                       ['unknown', 'Q1', 'Q2', 'Q3'], default='Q4')
    return {'cutpoints': [float(v) for v in cuts],
            'bins': {label: summary(rows[labels == label]) for label in ('Q1', 'Q2', 'Q3', 'Q4', 'unknown')},
            'q4_minus_q1': extreme_difference(rows, labels)}


def trace(rows: pd.DataFrame) -> dict:
    result = {}
    for zone in nodes.ZONES:
        subset = rows[rows['zone'] == zone]
        result[zone] = {'all': summary(subset)}
        for col in ('shooter_profile', 'matchup_profile', 'usage'):
            result[zone][col] = quartiles(subset, col)
        for col in ('shooter_effective', 'defender_five_mean_effective'):
            labels = profiles.reliability(subset[col])
            result[zone][col] = {label: summary(subset[labels == label])
                                 for label in ('<250', '250–750', '>750', 'unknown')}
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=EXPERIMENTS / '20261122_a1_s03_shot_trace.json')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f'refusing to overwrite {args.output}')
    manifest = json.loads(a1_signal.MANIFEST.read_text())
    ids = [g['game_id'] for g in manifest['control']['games']]
    inputs = {v['path']: v['sha256'] for v in manifest['input_fingerprints']}
    verified = [profiles.PREGAME, profiles.SEGMENTS, MODEL / 'config.json', MODEL / 'shot_result.txt']
    for path in verified:
        label = str(path.relative_to(ROOT))
        if inputs.get(label) != sha256_file(path):
            raise ValueError(f'{label} differs from the fixed control manifest')
    config = json.loads((MODEL / 'config.json').read_text())
    saved = json.loads((MODEL / 'meta.json').read_text())
    fitted_key = json.loads(saved['key'])
    signature = json.loads((CACHE / 'signature.json').read_text())
    if fitted_key['signature'] != signature:
        raise ValueError('shot cache does not match the saved model training signature')
    if config.get('train_through') != FOLDS['F4'][0] or config.get('version') != 'v1.2d_F4':
        raise ValueError('saved shot model has the wrong fold or training cutoff')
    node = config['nodes']['shot_result']
    if any(node.get(k) != saved['fitted']['shot_result'].get(k)
           for k in ('columns', 'categorical', 'temperature', 'intercepts')):
        raise ValueError('shot model configuration differs from saved fit metadata')
    spec = fitted_key['spec']
    settings = {**spec['default'], **spec.get('nodes', {}).get('shot_result', {})}
    if settings.get('banded') is not True:
        raise ValueError('expected training-window distance bands')

    shots = profiles.panel_shots(ids, ('and_one', 'period', 'start_clock', 'score_off', 'score_def',
                                      'shot_time', 'x', 'y'))
    pre = pd.read_parquet(profiles.PREGAME)
    shooter, defender, coverage = profiles.profile_exposures(shots, pre)
    with np.load(SHOT_FILE, allow_pickle=False) as archive:
        games, dates, cols = archive['game'], archive['date'], archive['columns'].tolist()
        selected = np.isin(games, ids)
        raw = archive['X']
        X = pd.DataFrame(raw[selected], columns=cols)
        meta = {k: archive[k][selected] for k in ('game', 'date', 'period', 'zone', 'y', 'margin')}
        n_outside = aligned(shots, shooter, X, meta)
        band_cols = ['zone', 'distance', 'lateral']
        all_bands = pd.DataFrame(raw[:, [cols.index(c) for c in band_cols]], columns=band_cols)
        training = (dates >= train.BURN_IN) & (dates <= FOLDS['F4'][0])
        banded = train.band_distances(all_bands, training)
        X[['distance', 'lateral']] = banded.loc[selected, ['distance', 'lateral']].reset_index(drop=True)
    booster = lgb.Booster(model_file=str(MODEL / node['file']))
    if booster.feature_name() != node['columns']:
        raise ValueError('saved shot model feature order differs from metadata')
    if node['intercepts'] is None:
        predicted = booster.predict(X[node['columns']], num_threads=1)
    else:
        raw_scores = booster.predict(X[node['columns']], raw_score=True, num_threads=1)
        predicted = train.apply_intercepts(raw_scores, np.asarray(node['intercepts']), 'multiclass')
    if not isinstance(predicted, np.ndarray):
        raise TypeError('shot-result model did not return a dense probability array')
    if predicted.shape != (len(shots), 3) or not np.allclose(predicted.sum(axis=1), 1):
        raise ValueError('shot-result model produced invalid class probabilities')

    effective = defender.groupby('shot_id').agg(
        count=('player', 'size'), valid=('team_valid', 'sum'), known=('effective', 'count'),
        mean=('effective', 'mean')).reindex(np.arange(len(shots)))
    effective['mean'] = effective['mean'].where(
        effective['count'].eq(5) & effective['valid'].eq(5) & effective['known'].eq(5))
    on_five = shots[[f'off_{i}' for i in range(1, 6)]].eq(shots['actor'], axis=0).any(axis=1)
    rows = pd.DataFrame({
        'game_id': shots['game_id'], 'zone': shots['zone'], 'player': shots['actor'],
        'made': shots['made'].astype(float), 'predicted': predicted[:, 1] + predicted[:, 2],
        'actor_on_five': on_five, 'matchup_profile': X['mu_fg_shot'], 'usage': X['actor_usage'],
        'shooter_effective': X['actor_shots_eff'], 'defender_five_mean_effective': effective['mean'],
        'shooter_profile': np.select([shots['zone'] == z for z in nodes.ZONES],
                                     [X[f'actor_fg_{z}'] for z in nodes.ZONES], default=np.nan),
    })
    by_shooter = {f'{player}:{zone}': summary(g) for (player, zone), g in rows.groupby(['player', 'zone'])}
    paths = [a1_signal.MANIFEST, profiles.PREGAME, profiles.SEGMENTS, SHOT_FILE, CACHE / 'signature.json',
             MODEL / 'config.json', MODEL / 'meta.json', MODEL / node['file'], Path(__file__), Path(profiles.__file__)]
    write_json(args.output, {
        'experiment': 'a1_s03_fixed_shot_node_trace',
        'method': {'games': len(ids), 'node': 'v1.2d F4 shot_result', 'train_through': FOLDS['F4'][0],
                   'prediction': 'saved three-class node, made probability is class 1 plus class 2',
                   'distance_bands': 'training-window means, computed from the exact fitted-model cache',
                   'quartiles': 'zone-specific quantiles of input values, never observed outcomes',
                   'quartile_uncertainty': 'paired game-cluster bootstrap, added after initial bin means as a '
                                           'descriptive uncertainty check, not a feature-selection gate',
                   'limitations': 'conditional on actual shot and zone; defender five exposures overlap and are '
                                  'not on-ball attribution; actor profiles unavailable when outside recorded five'},
        'coverage': {**coverage, 'actor_missing_from_node_five': n_outside,
                     'missing_defender_five_effective_mean': int(effective['mean'].isna().sum())},
        'all': summary(rows), 'zones': trace(rows), 'shooters_by_zone': by_shooter,
        'sha256': {str(p.resolve().relative_to(ROOT)): sha256_file(p) for p in paths},
    }, pretty=True)
    print(f'{len(shots)} aligned shots, {n_outside} actors outside the offensive five; saved {args.output}')


if __name__ == '__main__':
    main()
