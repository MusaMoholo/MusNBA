#!/usr/bin/env python3
"""Frozen teacher-forced, different-player shooting residual diagnostic; no fitted factor."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from basketball_common import sha256_file, write_json
from scripts import a2_shot_residuals as source, a1_substitution_engine


def terms(shots):
    ids = sorted(shots['game_id'].unique())
    result = np.zeros((len(ids), 9))
    # Columns: residual sum, shot count; teammate base/linear/units; opponent base/linear/units; fold.
    pairs = {'teammate': 0, 'opponent': 0}
    team_games = 0
    for index, (_, game) in enumerate(shots.groupby('game_id', sort=True)):
        result[index, :2] = game['residual'].sum(), len(game)
        result[index, 8] = int(game['fold'].iloc[0][1:])
        teams = []
        for _, team in game.groupby('team'):
            pg = team.groupby('player')['residual'].agg(['sum', 'size'])
            n, s = len(team), team['residual'].sum()
            denominator = n * n - np.square(pg['size']).sum()
            team_games += 1
            if denominator:
                result[index, 2] += (s * s - np.square(pg['sum']).sum()) / denominator
                result[index, 3] += 2 * (n * s - (pg['size'] * pg['sum']).sum()) / denominator
                result[index, 4] += 1
                pairs['teammate'] += int(denominator)
            teams.append((n, s))
        if len(teams) == 2:
            (n, s), (m, t) = teams
            result[index, 5:8] = s * t / (n * m), s / n + t / m, 1
            pairs['opponent'] += n * m
        elif len(teams) > 2:
            raise ValueError('more than two teams in a game')
    return result, {'games': len(ids), 'team_games': team_games, 'shots': len(shots),
                    'teammate_contributing_team_games': int(result[:, 4].sum()),
                    'opponent_contributing_games': int(result[:, 7].sum()), 'shot_pairs': pairs}


def evaluate(values, weights):
    output = {}
    for relation, base, linear, units in (('teammate', 2, 3, 4), ('opponent', 5, 6, 7)):
        total = np.zeros(len(weights))
        count = weights @ values[:, units]
        for fold in np.unique(values[:, 8]):
            selected = values[:, 8] == fold
            w, v = weights[:, selected], values[selected]
            n = w @ v[:, 1]
            mean = np.divide(w @ v[:, 0], n, out=np.zeros_like(n), where=n > 0)
            total += w @ v[:, base] - mean * (w @ v[:, linear]) + mean**2 * (w @ v[:, units])
        if (count <= 0).any():
            raise ValueError('bootstrap lacks contributing pairs')
        output[relation] = total / count
    output['difference'] = output['teammate'] - output['opponent']
    return output


def summarize(shots):
    v, counts = terms(shots)
    counts['status'] = 'supported' if counts['games'] >= 50 and counts['teammate_contributing_team_games'] >= 100 else 'insufficient'
    if counts['status'] != 'supported':
        return counts
    point = evaluate(v, np.ones((1, len(v))))
    rng = np.random.default_rng(20261122)
    weights = rng.multinomial(len(v), np.full(len(v), 1 / len(v)), size=10_000).astype(float)
    draws = evaluate(v, weights)
    counts['moments'] = {key: {'estimate': float(point[key][0]),
                               'ci_95': np.quantile(draws[key], [.025, .975]).tolist()} for key in point}
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    source.FOLD_SEASONS['F4'] = '2026'  # Same exact alignment checks; F4 also precedes the protected test.
    inputs, exclusions, all_shots = {}, {}, []
    for fold in ('F1', 'F2', 'F3', 'F4'):
        shots, fingerprints = source.aligned_source(fold)
        roles = a1_substitution_engine.load_features(fold)
        usable, exclusions[fold] = source.attach_roles(shots, roles)
        usable = usable.merge(roles[['game_id', 'player', 'team']], on=['game_id', 'player'], validate='many_to_one')
        inputs.update(fingerprints)
        role_path = ROOT / f'data/derived/experiments/20261122_a1_s05_unconditional_{fold}_corrected.parquet'
        inputs[str(role_path.relative_to(ROOT))] = sha256_file(role_path)
        all_shots.append(usable)
        print(f'{fold}: {len(usable)} eligible shots', flush=True)
    rows = pd.concat(all_shots, ignore_index=True)
    cohorts = {}
    for fold in ('F1', 'F2', 'F3', 'F4', 'pooled_F1_F3'):
        subset = rows[rows['fold'].isin(('F1', 'F2', 'F3'))] if fold == 'pooled_F1_F3' else rows[rows['fold'].eq(fold)]
        cohorts[fold] = {'all': summarize(subset), 'stars_starters': summarize(subset[subset['tier'].isin(('star', 'starter'))])}
    if any(sha256_file(ROOT / path) != digest for path, digest in inputs.items()):
        raise ValueError('diagnostic inputs changed during execution')
    write_json(args.output, {'kind': 'A2 distinct-player shared-shooting feasibility; not a fitted factor',
               'protocol': 'docs/protocols/a2_joint_late_20261123.md', 'exclusions': exclusions, 'cohorts': cohorts,
               'source_sha256': {str(p.relative_to(ROOT)): sha256_file(p) for p in (Path(__file__),
                    ROOT / 'scripts/a2_shot_residuals.py', ROOT / 'docs/protocols/a2_joint_late_20261123.md')},
               'input_sha256': inputs, 'bootstrap': {'replicates': 10000, 'seed': 20261122, 'unit': 'game', 'refit': 'fold/cohort residual centre'},
               'limitations': ['fixed prior-role panels, observed shots and recorded lineups',
                              'talent, form, shared conditions and misspecification remain confounded',
                              'no factor selected, calibrated or promoted']}, pretty=True)


if __name__ == '__main__':
    main()
