#!/usr/bin/env python3
"""Whole-slate exact-mixture size/runtime probe using repeated accepted scores, never new branch forecasts."""
import argparse
from fractions import Fraction
from pathlib import Path
import resource
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from basketball_common import SNAPSHOTS, read_json, sha256_file, write_json
from scripts import a1_season_mixture, master_fixtures, pathway, projection


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    plan = read_json(args.plan)
    day = plan['origin']
    stats = read_json(SNAPSHOTS / day / 'stats.json')
    from basketball_common import DERIVED
    teams = read_json(DERIVED / 'teams.json')
    source = SNAPSHOTS / day / 'engine_worlds.npz'
    with np.load(source, allow_pickle=False) as z:
        raw = {row['game']: z[row['game']] for row in plan['games']}
    pieces = {row['game']: [(raw[row['game']], Fraction(int(b['weight']['numerator']), int(b['weight']['denominator'])))
                             for b in row['branches']] if row['branches'] else [(raw[row['game']], Fraction(1))]
              for row in plan['games']}
    seed = projection.seed_for(pathway.PATHWAY['id'], day, 'season')
    started = time.monotonic()
    coupled = a1_season_mixture.couple(pieces, seed, max_paths=200000)
    layout_seconds = time.monotonic() - started
    units, denominator = coupled['numerators'], coupled['denominator']
    metrics = []
    for gid, values in raw.items():
        expected, counts = np.unique(values.reshape(len(values), -1), axis=0, return_counts=True)
        observed, inverse = np.unique(coupled['games'][gid].reshape(len(units), -1), axis=0, return_inverse=True)
        masses = np.zeros(len(observed), np.int64)
        np.add.at(masses, inverse, units)
        if denominator % len(values) or not np.array_equal(observed, expected) or not np.array_equal(masses, counts * (denominator // len(values))):
            raise ValueError('full joint score marginal is not exact')
        metrics.append((coupled['games'][gid][:, 0].sum(1) > coupled['games'][gid][:, 1].sum(1)).astype(float))
    matrix = np.stack(metrics, 1)
    weights = units / denominator
    means = weights @ matrix
    covariance = matrix.T @ (matrix * weights[:, None]) - means[:, None] * means
    pairs = covariance[np.triu_indices(len(raw), 1)]
    remaining = sorted((g for g in master_fixtures.load() if g['date_et'] >= day), key=lambda g: (g['date_et'], g['tip_utc'], g['game_id']))
    timings = {}
    for name, worlds in (('unweighted_10000', raw), ('exact_weighted_layout', coupled['games'])):
        W = len(next(iter(worlds.values())))
        started = time.monotonic()
        result = pathway.play(stats['teams'], stats['league'], remaining, W, np.random.default_rng(seed), worlds)
        timings[name] = {'paths': W, 'pathway_seconds': time.monotonic() - started}
        for gid, scores in worlds.items():
            index = next(i for i, game in enumerate(remaining) if game['game_id'] == gid)
            if not np.array_equal(result['points'][:, index], scores.sum(2)):
                raise ValueError('pathway did not use each supplied near-term score')
        del result
        print(name, timings[name], flush=True)
    write_json(args.output, {'kind': 'runtime/accounting probe only; both synthetic branches repeat the same accepted unconditional scores',
                            'origin': day, 'plan_sha256': sha256_file(args.plan), 'scores_sha256': sha256_file(source),
                            'source_sha256': sha256_file(Path(__file__)), 'coupling_sha256': sha256_file(Path(a1_season_mixture.__file__)),
                            'seed': str(seed), 'games': len(raw), 'batches': plan['game_branch_batches'],
                            'layout_seconds': layout_seconds, 'weighted_paths': len(units), 'mass_denominator': str(denominator),
                            'effective_paths': float(1 / np.dot(weights, weights)), 'all_full_joint_score_marginals_exact': True,
                            'cross_game_win_covariance': {'mean_absolute': float(np.abs(pairs).mean()), 'max_absolute': float(np.abs(pairs).max())},
                            'timings': timings, 'process_peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                            'concurrency': 'eight single-thread rule-final simulators plus one independent auditor; this probe is the tenth compute slot',
                            'limitations': 'Not branch accuracy, real availability dependence, isolated timing or a release. No live views/bundles changed.'}, pretty=True)


if __name__ == '__main__':
    main()
