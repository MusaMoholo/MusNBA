#!/usr/bin/env python3
"""Audit every near-term world atom and measure finite coupling dependence, without real outcomes."""
import argparse
import os
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from basketball_common import SNAPSHOTS, read_json, sha256_file, write_json


def correlations(matrix, weights=None):
    centered = matrix - np.average(matrix, axis=0, weights=weights)
    covariance = (centered.T @ centered if weights is None else (centered * weights[:, None]).T @ centered)
    scale = np.sqrt(np.diag(covariance))
    correlation = covariance / scale[:, None] / scale[None, :]
    pairs = [abs(correlation[i,j]) for i in range(matrix.shape[1]) for j in range(i) if i//2 != j//2]
    return max(pairs, default=0.)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', default='2026-11-23')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('preserve existing independent audit evidence')
    folder = SNAPSHOTS / args.snapshot
    season = read_json(folder / 'season.json')
    ids = sorted(season['engine_games'])
    tables, chosen, statuses, expected_probabilities = [], [], [], []
    with np.load(folder / 'engine_worlds.npz') as original, np.load(folder / 'engine_players.npz') as players, np.load(folder / 'season_engine_worlds.npz') as coupled, np.load(folder / 'season_player_indices.npz') as indices:
        weights = coupled['weights']
        assert np.array_equal(weights, indices['weights']) and len(weights) == season['sims']
        denominator = int(weights.sum())
        for gid in ids:
            points, index = original[gid], indices[gid]
            mass = players[f'{gid}__weights'] if f'{gid}__weights' in players else np.ones(len(points), np.int64)
            count = np.zeros(len(points), np.int64)
            np.add.at(count, index, weights)
            assert np.array_equal(count * int(mass.sum()), mass * denominator), 'near-term world atom mass changed'
            assert np.array_equal(points[index], coupled[gid]), 'near-term joint period scores changed'
            totals = points.sum(2).astype(float)
            values = np.column_stack([totals.sum(1), totals[:,0]-totals[:,1]])
            tables.append((values, mass/mass.sum()))
            chosen.append(values[index])
            branch = folder / 'lineups' / gid / 'worlds.json'
            if branch.exists():
                payload = read_json(branch)
                for player in payload['selected_players']:
                    availability = np.concatenate([np.full(b['worlds']['worlds'], dict((pid, val) for _,pid,val in b['assignments'])[player['player_id']]) for b in payload['branches']])
                    statuses.append(availability[index])
                    expected_probabilities.append(player['probability'])
    ess = denominator**2 / float(np.dot(weights, weights))
    selected = np.column_stack(chosen)
    measured = correlations(selected, weights)
    rng = np.random.default_rng(20261123)
    reference = []
    for _ in range(32):
        independent = np.column_stack([values[rng.choice(len(values), int(ess), p=p)] for values,p in tables])
        reference.append(correlations(independent))
    joint_errors = []
    for i, values in enumerate(statuses):
        assert abs(np.average(values, weights=weights)-expected_probabilities[i]) < 1e-12
        for j in range(i):
            joint_errors.append(float(np.average(values & statuses[j], weights=weights)-expected_probabilities[i]*expected_probabilities[j]))
    write_json(args.output, {
        'kind':'exact near-term atom accounting and numerical-dependence diagnostic; no real outcome scoring',
        'origin':args.snapshot,'games':len(ids),'game_ids':ids,'paths':len(weights),'probability_mass':denominator,'effective_paths':ess,
        'every_joint_world_atom_exact':True,'status_joint_errors':joint_errors,
        'max_abs_cross_game_total_margin_correlation':measured,
        'independent_references':32,'independent_effective_size':int(ess),
        'reference_max_abs_correlation_range':[min(reference),max(reference)],
        'reference_max_abs_correlation_quantiles':np.quantile(reference,[.025,.5,.975]).tolist(),
        'sources':{str(p.relative_to(ROOT)):sha256_file(p) for p in (Path(__file__),folder/'season.json',folder/'season_engine_worlds.npz',folder/'season_player_indices.npz')},
        'limitation':'Independent offsets imply product marginals in expectation; a finite coupling has numerical cross-game dependence. Availability dependence is an assumption, not calibrated injury skill.'},pretty=True)
    print(f'{len(ids)} games: every original world atom exact; {len(weights)} weighted paths; max cross-game correlation {measured:.6f}; independent range {min(reference):.6f}–{max(reference):.6f}',flush=True)


if __name__ == '__main__':
    main()
