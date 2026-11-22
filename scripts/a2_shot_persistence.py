#!/usr/bin/env python3
"""Earlier-fold, player/game-clustered cross-game shot-residual feasibility screen."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, sha256_file, write_json  # noqa: E402
from scripts import a1_compare, a1_substitution_engine, a2_shot_residuals  # noqa: E402
from scripts.evaluate import EXPERIMENTS  # noqa: E402

FOLDS = tuple(a2_shot_residuals.FOLD_SEASONS)
ROLES = a2_shot_residuals.ROLES
REPORT = EXPERIMENTS / '20261122_a2_shot_persistence_f1_f3.json'


def prepare(rows: pd.DataFrame) -> pd.DataFrame:
    keys = ['fold', 'game_id', 'player']
    if rows[keys].isna().any().any() or rows.duplicated(keys).any():
        raise ValueError('player-game keys are missing or duplicated')
    if (not rows['fold'].isin(FOLDS).all() or not rows['tier'].isin(ROLES).all()
            or not np.isfinite(rows[['shots', 'residual_sum']].to_numpy(dtype=float)).all()
            or (rows['shots'] < 2).any()):
        raise ValueError('player-games contain invalid folds, roles, shot counts or residuals')
    count = rows.groupby(['fold', 'player', 'tier'])['game_id'].transform('nunique')
    return rows[count >= 2].sort_values(['fold', 'player', 'tier', 'game_id'], kind='stable').reset_index(drop=True)


def populations(rows: pd.DataFrame) -> dict:
    result = {}
    for fold in (*FOLDS, 'pooled_F1_F3'):
        selected = rows if fold == 'pooled_F1_F3' else rows[rows['fold'].eq(fold)]
        result[fold] = {}
        for role in ('all', *ROLES):
            cohort = selected if role == 'all' else selected[selected['tier'].eq(role)]
            groups = cohort.groupby(['fold', 'player', 'tier'])['shots']
            cross_pairs = ((groups.sum() ** 2) - groups.apply(lambda values: int((values ** 2).sum()))).sum()
            counts: dict = {'games': int(cohort[['fold', 'game_id']].drop_duplicates().shape[0]),
                            'player_games': len(cohort), 'player_role_folds': int(groups.ngroups),
                            'shots': int(cohort['shots'].sum()), 'ordered_cross_game_shot_pairs': int(cross_pairs)}
            counts['status'] = ('supported' if counts['games'] >= 50 and counts['player_games'] >= 100
                                and counts['player_role_folds'] >= 30 else 'insufficient')
            result[fold][role] = counts
    return result


def cluster_weights(rng: np.random.Generator, replicates: int, count: int) -> np.ndarray:
    draws = rng.integers(0, count, (replicates, count))
    weights = np.zeros((replicates, count), dtype=np.int16)
    np.add.at(weights, (np.arange(replicates)[:, None], draws), 1)
    return weights


def evaluate(rows: pd.DataFrame, weights: dict[str, tuple[np.ndarray, np.ndarray]]) -> dict[str, np.ndarray]:
    replicates = next(iter(weights.values()))[0].shape[0]
    sums = np.zeros((replicates, len(FOLDS), len(ROLES)))
    totals = np.zeros_like(sums)
    for f_index, fold in enumerate(FOLDS):
        frame = rows[rows['fold'].eq(fold)]
        if frame.empty:
            continue
        players = sorted(frame['player'].unique())
        games = sorted(frame['game_id'].unique())
        player_index = {value: index for index, value in enumerate(players)}
        game_index = {value: index for index, value in enumerate(games)}
        player_weights, game_weights = weights[fold]
        if player_weights.shape != (replicates, len(players)) or game_weights.shape != (replicates, len(games)):
            raise ValueError('bootstrap cluster weights have incorrect dimensions')
        for role_index, role in enumerate(ROLES):
            role_frame = frame[frame['tier'].eq(role)]
            if role_frame.empty:
                continue
            ri = np.array([player_index[value] for value in role_frame['player']])
            gi = np.array([game_index[value] for value in role_frame['game_id']])
            weighted = player_weights[:, ri] * game_weights[:, gi]
            grouped = list(role_frame.groupby('player', sort=False).indices.items())
            for _, indices in grouped:
                supported = (game_weights[:, gi[indices]] > 0).sum(axis=1) >= 2
                weighted[:, indices] *= supported[:, None]
            residual = role_frame['residual_sum'].to_numpy(dtype=float)
            shots = role_frame['shots'].to_numpy(dtype=float)
            exposure = weighted @ shots
            mean = np.divide(weighted @ residual, exposure, out=np.zeros(replicates), where=exposure > 0)
            for player, indices in grouped:
                group = role_frame.iloc[indices]
                p_weight = player_weights[:, player_index[player]]
                g_indices = [game_index[value] for value in group['game_id']]
                g_weight = game_weights[:, g_indices]
                n = group['shots'].to_numpy(dtype=float)
                r = group['residual_sum'].to_numpy(dtype=float) - mean[:, None] * n
                weighted_r = g_weight * r
                weighted_n = g_weight * n
                denominator = weighted_n.sum(axis=1) ** 2 - (weighted_n ** 2).sum(axis=1)
                numerator = weighted_r.sum(axis=1) ** 2 - (weighted_r ** 2).sum(axis=1)
                valid = denominator > 0
                pair_mean = np.divide(numerator, denominator, out=np.zeros(replicates), where=valid)
                sums[:, f_index, role_index] += p_weight * pair_mean
                totals[:, f_index, role_index] += p_weight * valid
    return {'sums': sums, 'totals': totals}


def cohort_value(results: dict[str, np.ndarray], fold: str, role: str) -> np.ndarray:
    fold_indices = list(range(len(FOLDS))) if fold == 'pooled_F1_F3' else [FOLDS.index(fold)]
    role_indices = list(range(len(ROLES))) if role == 'all' else [ROLES.index(role)]
    sums = results['sums'][:, fold_indices][:, :, role_indices].sum(axis=(1, 2))
    totals = results['totals'][:, fold_indices][:, :, role_indices].sum(axis=(1, 2))
    if (totals <= 0).any():
        raise ValueError(f'{fold} {role}: a bootstrap replicate has no eligible cross-game pairs')
    return sums / totals


def main() -> None:
    if REPORT.exists():
        raise FileExistsError('refusing to overwrite an existing persistence report')
    sources, inputs, coverage = [], {}, {}
    for fold in FOLDS:
        shots, fingerprints = a2_shot_residuals.aligned_source(fold)
        roles = a1_substitution_engine.load_features(fold)
        usable, coverage[fold] = a2_shot_residuals.attach_roles(shots, roles)
        inputs.update(fingerprints)
        role_file = DERIVED / f'experiments/20261122_a1_s05_unconditional_{fold}_corrected.parquet'
        inputs[str(role_file.relative_to(ROOT))] = sha256_file(role_file)
        sources.append(usable)
    rows = prepare(a2_shot_residuals.player_games(pd.concat(sources, ignore_index=True)))
    counts = populations(rows)
    rng = np.random.default_rng(a1_compare.BOOTSTRAP_SEED)
    point_weights, bootstrap_weights = {}, {}
    for fold in FOLDS:
        frame = rows[rows['fold'].eq(fold)]
        players, games = frame['player'].nunique(), frame['game_id'].nunique()
        if not players or not games:
            raise ValueError(f'{fold}: no supported player or game clusters')
        point_weights[fold] = (np.ones((1, players), dtype=np.int16), np.ones((1, games), dtype=np.int16))
        bootstrap_weights[fold] = (cluster_weights(rng, a1_compare.BOOTSTRAP_REPLICATES, players),
                                   cluster_weights(rng, a1_compare.BOOTSTRAP_REPLICATES, games))
    point = evaluate(rows, point_weights)
    batches = []
    started = time.monotonic()
    for start in range(0, a1_compare.BOOTSTRAP_REPLICATES, 100):
        weights = {fold: (p[start:start + 100], g[start:start + 100])
                   for fold, (p, g) in bootstrap_weights.items()}
        batches.append(evaluate(rows, weights))
        done = min(start + 100, a1_compare.BOOTSTRAP_REPLICATES)
        if done % 1000 == 0:
            print(f'bootstrap {done}/{a1_compare.BOOTSTRAP_REPLICATES}: '
                  f'{time.monotonic() - started:.1f}s', flush=True)
    boot = {key: np.concatenate([batch[key] for batch in batches]) for key in ('sums', 'totals')}
    for fold in counts:
        for role, result in counts[fold].items():
            if result['status'] == 'supported':
                estimate = cohort_value(point, fold, role)[0]
                samples = cohort_value(boot, fold, role)
                result.update({'estimate': float(estimate),
                               'ci_95': [float(value) for value in np.quantile(samples, [.025, .975])]})
    write_json(REPORT, {
        'experiment': 'a2_earlier_fold_cross_game_shot_persistence',
        'protocol': 'TRAINING_PLAN.md: cross-game persistence feasibility',
        'population': 'teacher-forced F1-F3 fixed role panels, not all validation games',
        'bootstrap': {'unit': 'independently resampled complete player and game clusters within each fold',
                      'replicates': a1_compare.BOOTSTRAP_REPLICATES, 'seed': a1_compare.BOOTSTRAP_SEED,
                      'confidence': .95},
        'coverage': coverage, 'cohorts': counts, 'input_sha256': inputs,
        'limitations': ['actual shot selection and observed lineups',
                        'persistent talent, sustained form, opponents and misspecification are not separated',
                        'not a simulated-world comparison or a model promotion result'],
    }, pretty=True)
    print(f'saved {REPORT.relative_to(ROOT)}; eligible player-games: {len(rows)}')


if __name__ == '__main__':
    main()
