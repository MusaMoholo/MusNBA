#!/usr/bin/env python3
"""Research-only actual isolated retries versus matched first-seed continuation."""
from __future__ import annotations

import argparse
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from analysis import a1_f4_six_roster_stress as stress, a1_matched_penalty_repair as repair  # noqa: E402
from analysis import a1_matched_penalty_run as matched  # noqa: E402
from analysis.a1_parallel_world_retry import simulate_parallel  # noqa: E402
from basketball_common import read_json, sha256_file, write_json  # noqa: E402
from scripts import a1_branch_foul_out, a1_substitution_world_audit, a1_world_retry, projection  # noqa: E402

SOURCE = ROOT / 'analysis/experiments/20261122_a1_f4_six_roster_v1.json'
AUDIT = ROOT / 'analysis/experiments/20261122_a1_f4_six_roster_v1_audit.json'
BASE_SEED = 20261123


def save_capture(directory, name, capture, *, penalty):
    audit = a1_substitution_world_audit.audit_worlds(capture, foul_penalty=penalty)
    path = Path(directory) / f'{name}.npz'
    if path.exists():
        raise FileExistsError(f'{path}: refusing to overwrite capture')
    np.savez_compressed(path, **capture)
    return {'path': str(path), 'sha256': sha256_file(path), 'audit': audit}


def attempt(world, attempt_number, seed, *, batch, directory):
    slot = batch * 100 + world
    eng, branch = stress._WORKER['engine'], stress._WORKER['branch']
    policy = matched.FailureTrace()
    eng.rotation_policy = policy
    try:
        stress._WORKER['simulate'](branch, 1, seed)
    except a1_branch_foul_out.ExhaustedEligiblePlayers as exc:
        if attempt_number == 0:
            failure = policy.failure
            continuation = repair.MatchedPenaltyTrace()
            eng.rotation_policy = continuation
            try:
                stress._WORKER['simulate'](branch, 1, seed)
            except a1_world_retry.RecoverableWorldError as continuation_error:
                raise ValueError('continuation failed; do not retry it') from continuation_error
            if continuation.first_exhaustion.get(0) != failure:
                raise ValueError('continuation differs at original failure') from exc
            capture = continuation.capture(branch, eng.last)
            saved = save_capture(directory, f'first-{slot:04d}', capture, penalty=True)
            write_json(Path(directory) / f'first-{slot:04d}.json',
                       {'slot': slot, 'seed': str(seed), 'status': 'exhausted',
                        'failure': failure, 'capture': saved}, pretty=True)
        raise a1_world_retry.RecoverableWorldError(str(exc)) from exc
    except a1_world_retry.RecoverableWorldError as exc:
        raise ValueError('unclassified recoverable failure; do not retry it') from exc
    capture = policy.capture(branch, eng.last)
    saved = save_capture(directory, f'accepted-{slot:04d}', capture, penalty=False)
    result = {'slot': slot, 'attempt': attempt_number, 'seed': str(seed), 'capture': saved}
    if attempt_number == 0:
        write_json(Path(directory) / f'first-{slot:04d}.json',
                   {'slot': slot, 'seed': str(seed), 'status': 'complete',
                    'failure': None, 'capture': saved}, pretty=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worlds-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pilot', action='store_true', help='run 20 slots instead of 1,000')
    args = parser.parse_args()
    if args.worlds_dir.exists() or args.output.exists():
        raise FileExistsError('refusing to overwrite an experiment')
    if any(os.environ.get(name) != '1' for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS')):
        raise ValueError('set OMP_NUM_THREADS=1 and OPENBLAS_NUM_THREADS=1')
    source, audit = read_json(SOURCE), read_json(AUDIT)
    if audit['summary_sha256'] != sha256_file(SOURCE):
        raise ValueError('source audit differs')
    panel_summary = read_json(stress.SUMMARY)
    panel_path = ROOT / panel_summary['details']
    if sha256_file(panel_path) != panel_summary['details_sha256']:
        raise ValueError('original panel differs')
    panel = [g for g in read_json(panel_path)['games'] if g['game'] == stress.GAME]
    if len(panel) != 1 or panel[0]['actual_participant_counts'][0] != 7:
        raise ValueError('selected game or roster differs')
    fingerprints = dict(source['fingerprints'])
    for path in (SOURCE, AUDIT, stress.SUMMARY, panel_path, Path(__file__),
                 ROOT / 'analysis/a1_real_retry_paired_audit.py',
                 ROOT / 'analysis/a1_parallel_world_retry.py',
                 ROOT / 'scripts/a1_world_retry.py',
                 ROOT / 'analysis/a1_matched_penalty_run.py',
                 ROOT / 'analysis/a1_matched_penalty_repair.py'):
        fingerprints[str(path.relative_to(ROOT))] = sha256_file(path)

    def verify():
        if any(sha256_file(ROOT / name) != digest for name, digest in fingerprints.items()):
            raise ValueError('source, input or model changed')

    verify()
    args.worlds_dir.mkdir(parents=True)
    count = 20 if args.pilot else 1000
    batches = 1 if args.pilot else 10
    rejections, accepted = [], []
    start = time.monotonic()
    with ProcessPoolExecutor(max_workers=8, initializer=stress.init_worker,
                             initargs=(panel[0]['selected_player'],)) as pool:
        for batch in range(batches):
            batch_seed = projection.seed_for('a1-real-retry-paired-batch-v1', BASE_SEED, batch)
            result = simulate_parallel(partial(attempt, batch=batch, directory=str(args.worlds_dir)),
                                       pool, worlds=20 if args.pilot else 100, seed=batch_seed,
                                       attempts_per_world=10, max_rejections=500 - len(rejections), window=8)
            accepted.extend(result.worlds)
            rejections.extend({'slot': batch * 100 + r.world, 'attempt': r.attempt, 'seed': str(r.seed),
                               'reason': r.reason} for r in result.rejections)
            print(f'{len(accepted)}/{count} accepted, {len(rejections)} rejected in '
                  f'{time.monotonic() - start:.1f}s', flush=True)
    if len(accepted) != count:
        raise ValueError('accepted count differs')
    first = [read_json(args.worlds_dir / f'first-{slot:04d}.json') for slot in range(count)]
    verify()
    manifest_path = args.worlds_dir / 'manifest.json'
    write_json(manifest_path, {'game': stress.GAME, 'fingerprints': fingerprints, 'first': first,
                               'accepted': accepted, 'rejections': rejections}, pretty=True)
    write_json(args.output, {
        'kind': 'paired real D29 retries and matched continuation; research only',
        'game': stress.GAME, 'pilot': args.pilot, 'worlds': count, 'base_seed': BASE_SEED,
        'attempts_per_world': 10, 'max_rejections': 500, 'workers': 8,
        'manifest': str(manifest_path), 'manifest_sha256': sha256_file(manifest_path),
        'rejections': len(rejections), 'elapsed_seconds': round(time.monotonic() - start, 3),
        'limitations': ['Selected six-player synthetic oracle roster, not a population failure rate.',
                        'Continuation is an explicit assumption, not the no-exception counterfactual.',
                        'Neither a predictive comparison nor permission to promote or serve retries.'],
    }, pretty=True)


if __name__ == '__main__':
    main()
