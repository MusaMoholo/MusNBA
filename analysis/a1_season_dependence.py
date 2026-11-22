#!/usr/bin/env python3
"""Compare research season-coupling dependence with independent empirical draws."""
from __future__ import annotations

import argparse
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import SNAPSHOTS, read_json, sha256_file, write_json  # noqa: E402
from scripts import a1_season_mixture, master_fixtures, projection  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--coupling-report', type=Path, required=True)
    parser.add_argument('--runs', type=int, default=32)
    parser.add_argument('--draws', type=int, default=10000)
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.runs < 1 or args.draws < 2:
        raise ValueError('runs must be positive and independent draws must exceed one')
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an experiment')
    report = read_json(args.coupling_report)
    for source in report['sources']:
        if sha256_file(source['report']) != source['sha256']:
            raise ValueError('branch report hash changed')
    games, _, origin = a1_season_mixture.from_reports(
        [Path(source['report']) for source in report['sources']])
    for source in report['snapshot_sources']:
        snapshot = SNAPSHOTS / source['day']
        path = snapshot / 'engine_worlds.npz'
        if (sha256_file(path) != source['worlds_sha256']
                or sha256_file(snapshot / 'meta.json') != source['meta_sha256']):
            raise ValueError('retained snapshot hash changed')
        with np.load(path, allow_pickle=False) as data:
            for game in data.files:
                if game in report['unbranched_games']:
                    if game in games:
                        raise ValueError('duplicate unbranched game')
                    games[game] = [(data[game], Fraction(1))]
    if sorted(games) != sorted(report['unbranched_games'] + [s['game'] for s in report['sources']]):
        raise ValueError('game inventory differs from coupling report')
    ids = sorted(games)
    fixture = {row['game_id']: row for row in master_fixtures.load() if row['game_id'] in games}
    if set(fixture) != set(ids):
        raise ValueError('missing fixture metadata')
    pairs = [(i, j) for i in range(len(ids)) for j in range(i + 1, len(ids))]
    if not pairs:
        raise ValueError('at least two games are required')
    exact = []
    for game in ids:
        p = sum((weight * Fraction(int((worlds[:, 0].sum(axis=1) > worlds[:, 1].sum(axis=1)).sum()),
                                   len(worlds)) for worlds, weight in games[game]), Fraction())
        exact.append(float(p))
    runs = []
    pair_values = [[] for _ in pairs]
    for run in range(args.runs):
        seed = args.seed + run
        coupled = a1_season_mixture.couple(games, seed)
        weights = coupled['numerators'].astype(np.float64) / coupled['denominator']
        outcomes = np.column_stack([
            (coupled['games'][game][:, 0].sum(axis=1) > coupled['games'][game][:, 1].sum(axis=1))
            for game in ids
        ]).astype(np.float64)
        marginals = weights @ outcomes
        if not np.allclose(marginals, exact, rtol=0, atol=1e-12):
            raise ValueError('weighted win marginals do not match exact source fractions')
        joint = outcomes.T @ (weights[:, None] * outcomes)
        deviations = [float(joint[i, j] - marginals[i] * marginals[j]) for i, j in pairs]
        for values, value in zip(pair_values, deviations, strict=True):
            values.append(value)
        independent = np.empty((args.draws, len(ids)), dtype=np.float64)
        for column, game in enumerate(ids):
            rng = np.random.default_rng(projection.seed_for('a1-season-independent-reference', seed, game))
            pieces = games[game]
            which = rng.choice(len(pieces), size=args.draws, p=[float(w) for _, w in pieces])
            for branch, (worlds, _) in enumerate(pieces):
                selected = np.flatnonzero(which == branch)
                draws = worlds[rng.integers(len(worlds), size=len(selected))]
                independent[selected, column] = draws[:, 0].sum(axis=1) > draws[:, 1].sum(axis=1)
        independent_marginals = independent.mean(axis=0)
        independent_joint = independent.T @ independent / args.draws
        reference = [float(independent_joint[i, j] - independent_marginals[i] * independent_marginals[j])
                     for i, j in pairs]
        runs.append({'seed': seed, 'paths': len(weights),
                     'effective_weighted_paths': float(1 / np.square(weights).sum()),
                     'coupled_mean_abs_covariance': float(np.mean(np.abs(deviations))),
                     'coupled_max_abs_covariance': float(np.max(np.abs(deviations))),
                     'independent_mean_abs_covariance': float(np.mean(np.abs(reference))),
                     'independent_max_abs_covariance': float(np.max(np.abs(reference)))})
        print(f'{run + 1}/{args.runs} seeds; {len(weights)} weighted paths', flush=True)
    details = []
    for (i, j), values in zip(pairs, pair_values, strict=True):
        left, right = fixture[ids[i]], fixture[ids[j]]
        shared = sorted({left['home_id'], left['away_id']} & {right['home_id'], right['away_id']})
        details.append({'games': [ids[i], ids[j]], 'shared_teams': shared,
                        'minimum': min(values), 'maximum': max(values),
                        'mean': float(np.mean(values)), 'mean_absolute': float(np.mean(np.abs(values)))})
    write_json(args.output, {
        'kind': 'research covariance diagnostic; not a forecast or predictive acceptance',
        'origin': origin, 'runs': args.runs, 'independent_draws_per_run': args.draws,
        'coupling_report': str(args.coupling_report), 'coupling_report_sha256': sha256_file(args.coupling_report),
        'algorithm_sha256': sha256_file(ROOT / 'scripts/a1_season_mixture.py'),
        'analysis_sha256': sha256_file(Path(__file__)), 'fixtures_sha256': sha256_file(master_fixtures.MASTER_CSV),
        'limitations': ('Only two games use branch mixtures; other games are unconditional. Comparison to independent '
                        'draws does not establish realistic across-game dependence, predictive skill, or acceptance.'),
        'games': ids, 'exact_home_win_probabilities': exact, 'runs_detail': runs, 'pairs': details,
    }, pretty=True)


if __name__ == '__main__':
    main()
