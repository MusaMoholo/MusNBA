#!/usr/bin/env python3
"""Prespecified F4 retrospective player residual-dependence screen."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, sha256_file, write_json  # noqa: E402
from scripts import a1_compare, a1_substitution_engine  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS, TEST_FROM  # noqa: E402

CONTROL = DERIVED / 'experiments/20261122T022323Z_a1_s01_control_players.parquet'
ROLES_FILE = DERIVED / 'experiments/20261122_a1_s05_unconditional_F4_corrected.parquet'
ROLE_AUDIT = EXPERIMENTS / '20261122_a1_s05_minutes_screen_accounting_corrected.json'
MANIFEST = EXPERIMENTS / '20261122_a1_manifest.json'
REPORT = EXPERIMENTS / '20261122_a2_residual_dependence_f4.json'
ROLES = ('star', 'starter', 'bench')
METRICS = ('minutes', 'points_per_36')


def prepare(control: pd.DataFrame, roles: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    keys = ['game_id', 'player']
    if control[keys].isna().any().any() or control.duplicated(keys).any():
        raise ValueError('control has missing or duplicate player-game keys')
    if roles[keys].isna().any().any() or roles.duplicated(keys).any():
        raise ValueError('roles have missing or duplicate player-game keys')
    rows = control.merge(roles[keys + ['team', 'tier']], on=keys, how='left',
                         validate='one_to_one', indicator=True)
    if rows.loc[rows['_merge'].eq('both'), 'team'].isna().any():
        raise ValueError('matched player has no team')
    known_roles = rows['tier'].isin(ROLES)
    matched = rows['_merge'].eq('both')
    numeric = ['min_actual', 'min_sim', 'pts_actual', 'pts_sim']
    values = rows[numeric].apply(pd.to_numeric, errors='raise').to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError('control contains missing, non-finite or negative observations')
    supported = matched & known_roles & rows['min_actual'].ge(8) & rows['min_sim'].ge(8)
    counts = {
        'control_player_games': len(rows),
        'matched': int(matched.sum()),
        'unmatched': int((~matched).sum()),
        'matched_unknown_role': int((matched & ~known_roles).sum()),
        'matched_known_role_below_minutes_threshold': int((matched & known_roles & ~supported).sum()),
        'supported': int(supported.sum()),
    }
    rows = rows.loc[supported, keys + ['team', 'tier'] + numeric].copy()
    rows['minutes'] = rows['min_actual'] - rows['min_sim']
    rows['points_per_36'] = 36 * (rows['pts_actual'] / rows['min_actual'] - rows['pts_sim'] / rows['min_sim'])
    if (rows.groupby('game_id')['team'].nunique() > 2).any():
        raise ValueError('a game has more than two mapped teams')
    return rows, counts


def pair_terms(left: pd.DataFrame, right: pd.DataFrame, same_team: bool) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    a = left[list(METRICS)].to_numpy(dtype=float)
    b = right[list(METRICS)].to_numpy(dtype=float)
    ar = pd.Categorical(left['tier'], categories=ROLES).codes
    br = pd.Categorical(right['tier'], categories=ROLES).codes
    if (ar < 0).any() or (br < 0).any():
        raise ValueError('pair contains unknown role')
    i, j = np.indices((len(a), len(b)))
    mask = i != j if same_team else np.ones(i.shape, dtype=bool)
    i, j = i[mask], j[mask]
    count = len(i)
    if count == 0:
        raise ValueError('pair set is empty')
    base = (a[i] * b[j]).mean(axis=0)
    linear = np.zeros((len(METRICS), len(ROLES)))
    quadratic = np.zeros((len(ROLES), len(ROLES)))
    for role in range(len(ROLES)):
        linear[:, role] = (a[i][br[j] == role].sum(axis=0) + b[j][ar[i] == role].sum(axis=0)) / count
        for other in range(len(ROLES)):
            quadratic[role, other] = np.mean((ar[i] == role) & (br[j] == other))
    return base, linear, quadratic, count


def build_terms(rows: pd.DataFrame, game_ids: list[str]) -> tuple[dict, dict]:
    n = len(game_ids)
    game_index = {game: index for index, game in enumerate(game_ids)}
    if len(game_index) != n or not set(rows['game_id']).issubset(game_index):
        raise ValueError('invalid fixed game population')
    terms = {
        'role_sum': np.zeros((n, len(METRICS), len(ROLES))),
        'role_count': np.zeros((n, len(ROLES))),
    }
    for relation in ('teammate', 'opponent'):
        terms[f'{relation}_base'] = np.zeros((n, len(METRICS)))
        terms[f'{relation}_linear'] = np.zeros((n, len(METRICS), len(ROLES)))
        terms[f'{relation}_quadratic'] = np.zeros((n, len(ROLES), len(ROLES)))
        terms[f'{relation}_units'] = np.zeros(n)
    counts = {'player_games': len(rows), 'games': int(rows['game_id'].nunique()),
              'team_games': 0, 'teammate_team_games': 0, 'teammate_ordered_pairs': 0,
              'opponent_games': 0, 'opponent_pairs': 0}
    for gid, game in rows.groupby('game_id', sort=False):
        index = game_index[str(gid)]
        teams = [side for _, side in game.groupby('team', sort=True)]
        counts['team_games'] += len(teams)
        for role_index, role in enumerate(ROLES):
            role_rows = game.loc[game['tier'].eq(role), list(METRICS)]
            terms['role_sum'][index, :, role_index] = role_rows.sum().to_numpy(dtype=float)
            terms['role_count'][index, role_index] = len(role_rows)
        for side in teams:
            if len(side) < 2:
                continue
            base, linear, quadratic, pairs = pair_terms(side, side, True)
            terms['teammate_base'][index] += base
            terms['teammate_linear'][index] += linear
            terms['teammate_quadratic'][index] += quadratic
            terms['teammate_units'][index] += 1
            counts['teammate_team_games'] += 1
            counts['teammate_ordered_pairs'] += pairs
        if len(teams) == 2:
            base, linear, quadratic, pairs = pair_terms(teams[0], teams[1], False)
            terms['opponent_base'][index] = base
            terms['opponent_linear'][index] = linear
            terms['opponent_quadratic'][index] = quadratic
            terms['opponent_units'][index] = 1
            counts['opponent_games'] += 1
            counts['opponent_pairs'] += pairs
    return terms, counts


def evaluate(terms: dict, weights: np.ndarray) -> dict[str, np.ndarray]:
    weights = np.atleast_2d(weights)
    role_count = weights @ terms['role_count']
    role_sum = np.einsum('bg,gmr->bmr', weights, terms['role_sum'])
    means = np.divide(role_sum, role_count[:, None, :], out=np.zeros_like(role_sum),
                      where=role_count[:, None, :] > 0)
    output = {}
    for relation in ('teammate', 'opponent'):
        units = weights @ terms[f'{relation}_units']
        if (units <= 0).any():
            raise ValueError(f'bootstrap replicate lacks {relation} pairs')
        base = weights @ terms[f'{relation}_base']
        linear = np.einsum('bg,gmr->bmr', weights, terms[f'{relation}_linear'])
        quadratic = np.einsum('bg,grs->brs', weights, terms[f'{relation}_quadratic'])
        adjusted = base - np.sum(means * linear, axis=2) + np.einsum('bmr,brs,bms->bm', means, quadratic, means)
        output[relation] = adjusted / units[:, None]
    output['difference'] = output['teammate'] - output['opponent']
    return output


def main() -> None:
    manifest = json.loads(MANIFEST.read_text())
    game_rows = manifest['control']['games']
    game_ids = [str(game['game_id']) for game in game_rows]
    if (manifest['control']['regenerated_run'] != '20261122T022323Z_a1_s01_control'
            or manifest['control']['worlds'] != 1000
            or len(game_ids) != 200 or len(set(game_ids)) != 200
            or any(not FOLDS['F4'][1] <= game['date_et'] <= FOLDS['F4'][2] for game in game_rows)
            or any(game['date_et'] >= TEST_FROM for game in game_rows)):
        raise ValueError('manifest is not the fixed pre-final-test F4 population')
    control = pd.read_parquet(CONTROL)
    if set(control['game_id']) != set(game_ids):
        raise ValueError('control player games differ from manifest')
    roles = a1_substitution_engine.load_features('F4')
    rows, counts = prepare(control, roles)
    report = {
        'protocol': 'TRAINING_PLAN.md: Chunk A A2 residual-dependence screen',
        'population': 'F4 actual participants, 200 fixed games, 1000 simulated worlds',
        'input_sha256': {str(path.relative_to(ROOT)): sha256_file(path)
                         for path in (CONTROL, ROLES_FILE, ROLE_AUDIT, MANIFEST)},
        'join_and_selection': counts,
        'bootstrap': {'replicates': a1_compare.BOOTSTRAP_REPLICATES, 'seed': a1_compare.BOOTSTRAP_SEED,
                      'unit': 'complete game', 'confidence': 0.95},
        'cohorts': {},
        'limitations': ['actual-participant and actual-minute selection', 'ratio of simulated means',
                        'retrospective observed residual association, not simulated-world covariance or causality'],
    }
    draws = np.random.default_rng(a1_compare.BOOTSTRAP_SEED).integers(
        0, len(game_ids), (a1_compare.BOOTSTRAP_REPLICATES, len(game_ids)))
    weights = np.zeros((len(draws), len(game_ids)), dtype=np.int16)
    np.add.at(weights, (np.arange(len(draws))[:, None], draws), 1)
    for name, cohort in (('all_supported', rows), ('stars_and_starters', rows[rows['tier'].isin(ROLES[:2])])):
        terms, cohort_counts = build_terms(cohort, game_ids)
        result: dict = {'counts': cohort_counts}
        if (cohort_counts['games'] < 50 or cohort_counts['teammate_team_games'] < 100
                or cohort_counts['opponent_games'] < 50):
            result['status'] = 'insufficient supported games or team-games'
        else:
            point = evaluate(terms, np.ones((1, len(game_ids))))
            boot = evaluate(terms, weights)
            result['status'] = 'supported'
            result['metrics'] = {
                metric: {
                    relation: {'estimate': float(point[relation][0, index]),
                               'ci_95': [float(x) for x in np.quantile(boot[relation][:, index], [.025, .975])]}
                    for relation in ('teammate', 'opponent', 'difference')
                }
                for index, metric in enumerate(METRICS)
            }
        report['cohorts'][name] = result
    write_json(REPORT, report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
