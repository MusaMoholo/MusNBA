#!/usr/bin/env python3
"""Audit both selected-roster policies and compare prespecified full-game means."""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import read_json, sha256_file, write_json  # noqa: E402
from scripts import a1_substitution_world_audit, projection  # noqa: E402


def metrics(data: dict, expected_ids: np.ndarray | None = None,
            expected_available: np.ndarray | None = None,
            expected_side: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    ids, side, available = data['player_ids'], data['side'], data['available'][0]
    if (len(set(ids.tolist())) != len(ids) or (side[available] == 0).sum() != 6
            or (expected_ids is not None and not np.array_equal(ids, expected_ids))
            or (expected_available is not None and not np.array_equal(available, expected_available))
            or (expected_side is not None and not np.array_equal(side, expected_side))):
        raise ValueError('player identity or six-player availability differs')
    score = data['final_score'][0]
    home = np.flatnonzero((side == 0) & available)
    points = data['player_points'][0, home].sum(axis=1)
    minutes = data['minutes'][0, home].sum(axis=1)
    return np.concatenate((score, [score.sum(), score[0] - score[1]], points, minutes)), ids, available


def estimates(d29: np.ndarray, penalty: np.ndarray, draws: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if (d29.shape != penalty.shape or d29.ndim != 2 or draws.ndim != 2
            or draws.shape[1] != len(d29) or not np.isfinite(penalty).all()):
        raise ValueError('invalid comparison dimensions or penalty values')
    accepted = np.isfinite(d29).all(axis=1)
    if not accepted.any() or not np.isfinite(d29[accepted]).all() or np.isfinite(d29[~accepted]).any():
        raise ValueError('D29 rows must be wholly accepted or wholly missing')
    sampled = accepted[draws]
    counts = sampled.sum(axis=1)
    if (counts == 0).any():
        raise ValueError('bootstrap sample has no survivors')
    boot = np.empty((len(draws), d29.shape[1]))
    for column in range(d29.shape[1]):
        values = np.nan_to_num(d29[:, column], nan=0.0)
        boot[:, column] = values[draws].sum(axis=1) / counts - penalty[draws, column].mean(axis=1)
    return d29[accepted].mean(axis=0) - penalty.mean(axis=0), np.quantile(boot, [0.025, 0.975], axis=0).T


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an audit')
    report = read_json(args.report)
    stress_path, old_path, manifest_path = (ROOT / report[k] for k in ('stress', 'penalty', 'manifest'))
    for path, key in ((stress_path, 'stress_sha256'), (old_path, 'penalty_sha256'),
                      (manifest_path, 'manifest_sha256')):
        if sha256_file(path) != report[key]:
            raise ValueError(f'{path}: source hash differs')
    stress, old, manifest = (read_json(p) for p in (stress_path, old_path, manifest_path))
    detail_path, old_manifest_path = ROOT / stress['details'], ROOT / old['manifest']
    if sha256_file(detail_path) != stress['details_sha256'] or sha256_file(old_manifest_path) != old['manifest_sha256']:
        raise ValueError('original manifest hash differs')
    detail, old_manifest = read_json(detail_path), read_json(old_manifest_path)
    fingerprints = manifest['fingerprints']
    if any(sha256_file(ROOT / name) != digest for name, digest in fingerprints.items()):
        raise ValueError('source, model or input changed')
    attempts = detail['attempts']
    combined = old_manifest['worlds'] + manifest['worlds']
    by_draw = {row['draw']: row for row in combined}
    if (stress['game'] != manifest['game'] or len(attempts) != 1000 or len(combined) != 1000
            or len(by_draw) != 1000 or report['worlds'] != 798):
        raise ValueError('population, game or S06 count differs')
    started = time.monotonic()
    d29, penalty = [], []
    identities = availability = sides = None
    legal_fives = technicals = 0
    for draw, previous in enumerate(attempts):
        current = by_draw[draw]
        seed = projection.seed_for('a1-f4-six-roster-v1', stress['game'], draw)
        if (previous['draw'] != draw or int(previous['seed']) != seed or current['seed'] != previous['seed']):
            raise ValueError('draw or seed differs')
        directory = old_manifest_path.parent if previous['status'] == 'exhausted' else manifest_path.parent
        if read_json(directory / f'world-{draw:04d}.json') != current:
            raise ValueError('per-world manifest differs')
        path = ROOT / current['capture']
        if path != directory / f'world-{draw:04d}.npz' or sha256_file(path) != current['capture_sha256']:
            raise ValueError('S06 capture path or hash differs')
        with np.load(path, allow_pickle=False) as data:
            saved = dict(data)
        if str(saved['game_id']) != stress['game']:
            raise ValueError('S06 game differs')
        audit = a1_substitution_world_audit.audit_worlds(saved, foul_penalty=True)
        if audit != current['audit'] or audit['worlds'] != 1:
            raise ValueError('S06 accounting differs')
        value, ids, available = metrics(saved, identities, availability, sides)
        identities, availability = ids, available
        sides = saved['side']
        penalty.append(value)
        legal_fives += audit['lineup_fives_checked']
        technicals += audit['foul_penalty_events']
        if previous['status'] == 'exhausted':
            if current.get('original_rejection') != previous['reason']:
                raise ValueError('original rejection differs')
            d29.append(np.full(len(value), np.nan))
        elif previous['status'] == 'complete':
            path = ROOT / previous['capture']
            if (path != detail_path.parent / f'world-{draw:04d}.npz'
                    or sha256_file(path) != previous['capture_sha256']
                    or read_json(detail_path.parent / f'world-{draw:04d}.json') != previous):
                raise ValueError('D29 capture or per-world record differs')
            with np.load(path, allow_pickle=False) as data:
                survivor = dict(data)
            if str(survivor['game_id']) != stress['game']:
                raise ValueError('D29 game differs')
            audit = a1_substitution_world_audit.audit_worlds(survivor)
            if audit != previous['audit'] or audit['worlds'] != 1:
                raise ValueError('D29 accounting differs')
            d29.append(metrics(survivor, identities, availability, sides)[0])
        else:
            raise ValueError('unknown original attempt status')
    d29, penalty = np.asarray(d29), np.asarray(penalty)
    draws = np.random.default_rng(20261122).integers(0, 1000, (5000, 1000))
    difference, intervals = estimates(d29, penalty, draws)
    home_ids = identities[(sides == 0) & availability]
    labels = ['home_points', 'away_points', 'total_points', 'home_margin']
    labels += [f'home_player_{pid}_points' for pid in home_ids]
    labels += [f'home_player_{pid}_minutes' for pid in home_ids]
    results = {label: {'d29_survivor_mean': float(np.nanmean(d29[:, i])),
                       's06_all_mean': float(penalty[:, i].mean()),
                       'difference': float(difference[i]), 'ci_95': intervals[i].tolist()}
               for i, label in enumerate(labels)}
    if any(sha256_file(ROOT / name) != digest for name, digest in fingerprints.items()):
        raise ValueError('source or input changed during audit')
    write_json(args.output, {
        'kind': 'independent selected six-player full-game accounting and descriptive comparison',
        'report': str(args.report), 'report_sha256': sha256_file(args.report),
        'attempts': len(attempts), 'd29_survivors': int(np.isfinite(d29[:, 0]).sum()),
        's06_worlds': len(penalty), 's06_lineup_fives_checked': legal_fives,
        's06_technical_events': technicals, 'metrics': results,
        'bootstrap': {'replicates': 5000, 'seed': 20261122, 'unit': 'original seed',
                      'interval': '95% percentile, unadjusted across metrics'},
        'elapsed_seconds': round(time.monotonic() - started, 3),
        'limitations': ['Selected synthetic oracle-roster case; not an NBA rate or accuracy test.',
                        'Different substitutions and random paths confound policy differences with survivor selection.',
                        'Does not identify retry bias, counterfactual failed outcomes or promotion.'],
    }, pretty=True)
    print(f'{len(penalty)} S06 worlds and {int(np.isfinite(d29[:, 0]).sum())} D29 survivors audited', flush=True)


if __name__ == '__main__':
    main()
