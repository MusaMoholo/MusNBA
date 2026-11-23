#!/usr/bin/env python3
"""Replay selected F4 attempts with matched D29 foul-penalty continuation."""
from __future__ import annotations

import argparse
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from analysis import a1_f4_six_roster_stress as stress, a1_matched_penalty_repair as repair  # noqa: E402
from analysis.a1_parallel_world_probe import capture_digest  # noqa: E402
from basketball_common import read_json, sha256_file, write_json  # noqa: E402
from scripts import a1_branch_foul_out, a1_branch_world_probe, a1_substitution_world_audit, projection  # noqa: E402

SUMMARY = ROOT / 'analysis/experiments/20261122_a1_f4_six_roster_v1.json'
AUDIT = ROOT / 'analysis/experiments/20261122_a1_f4_six_roster_v1_audit.json'


class FailureTrace(a1_branch_world_probe.RepairedTrace):
    def after_fouls(self, g, st, active, offense, defense):
        try:
            return super().after_fouls(g, st, active, offense, defense)
        except a1_branch_foul_out.ExhaustedEligiblePlayers as exc:
            self.failure = {'reason': str(exc), 'state_sha256': repair.state_digest(st, offense, defense, self.trace)}
            raise


def original_failure(previous):
    policy = FailureTrace()
    eng, branch = stress._WORKER['engine'], stress._WORKER['branch']
    eng.rotation_policy = policy
    try:
        stress._WORKER['simulate'](branch, 1, int(previous['seed']))
    except a1_branch_foul_out.ExhaustedEligiblePlayers as exc:
        if str(exc) != previous['reason'] or policy.failure['reason'] != previous['reason']:
            raise ValueError('original failure differs from saved record') from exc
        return policy.failure
    raise ValueError('expected an original exhaustion')


def attempt(previous, directory):
    draw = previous['draw']
    if int(previous['seed']) != projection.seed_for('a1-f4-six-roster-v1', stress.GAME, draw):
        raise ValueError('original seed differs')
    expected_failure = original_failure(previous) if previous['status'] == 'exhausted' else None
    if previous['status'] not in ('complete', 'exhausted'):
        raise ValueError('unclassified original attempt')
    eng, branch = stress._WORKER['engine'], stress._WORKER['branch']
    policy = repair.MatchedPenaltyTrace()
    eng.rotation_policy = policy
    stress._WORKER['simulate'](branch, 1, int(previous['seed']))
    captured = policy.capture(branch, eng.last)
    if expected_failure is not None:
        if policy.first_exhaustion.get(0) != expected_failure:
            raise ValueError('continuation differs at the first original exhaustion')
    else:
        if policy.first_exhaustion:
            raise ValueError('original survivor unexpectedly exhausted')
        with np.load(ROOT / previous['capture'], allow_pickle=False) as original:
            original_keys = original.files
            if sha256_file(ROOT / previous['capture']) != previous['capture_sha256']:
                raise ValueError('original survivor capture hash differs')
            if capture_digest({key: captured[key] for key in original_keys}) != previous['world_sha256']:
                raise ValueError('original survivor trajectory differs')
    audit = a1_substitution_world_audit.audit_worlds(captured, foul_penalty=True)
    path = Path(directory) / f'world-{draw:04d}.npz'
    if path.exists():
        raise FileExistsError(f'{path}: refusing to overwrite capture')
    np.savez_compressed(path, **captured)
    return {'draw': draw, 'seed': previous['seed'], 'original_status': previous['status'],
            'first_exhaustion': expected_failure, 'capture': str(path),
            'capture_sha256': sha256_file(path), 'audit': audit}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worlds-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pilot', action='store_true', help='first five survivors and first five failures')
    args = parser.parse_args()
    if args.worlds_dir.exists() or args.output.exists():
        raise FileExistsError('refusing to overwrite an experiment')
    if any(os.environ.get(name) != '1' for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS')):
        raise ValueError('set OMP_NUM_THREADS=1 and OPENBLAS_NUM_THREADS=1')
    source, audit = read_json(SUMMARY), read_json(AUDIT)
    if audit['summary_sha256'] != sha256_file(SUMMARY):
        raise ValueError('source audit differs')
    details_path = ROOT / source['details']
    if sha256_file(details_path) != source['details_sha256']:
        raise ValueError('source manifest differs')
    details = read_json(details_path)
    records = details['attempts']
    if len(records) != 1000 or sum(row['status'] == 'exhausted' for row in records) != 202:
        raise ValueError('original population differs')
    if args.pilot:
        records = sorted([row for row in records if row['status'] == 'complete'][:5]
                         + [row for row in records if row['status'] == 'exhausted'][:5], key=lambda row: row['draw'])
    panel = read_json(ROOT / read_json(stress.SUMMARY)['details'])
    selected = [game for game in panel['games'] if game['game'] == stress.GAME]
    if len(selected) != 1:
        raise ValueError('selected game is missing from panel')
    fingerprints = dict(source['fingerprints'])
    for path in (SUMMARY, AUDIT, Path(__file__), ROOT / 'analysis/a1_matched_penalty_repair.py'):
        fingerprints[str(path.relative_to(ROOT))] = sha256_file(path)

    def verify():
        if any(sha256_file(ROOT / name) != digest for name, digest in fingerprints.items()):
            raise ValueError('source or input changed')

    verify()
    args.worlds_dir.mkdir(parents=True)
    started = time.monotonic()
    results = {}
    with ProcessPoolExecutor(max_workers=4, initializer=stress.init_worker,
                             initargs=(selected[0]['selected_player'],)) as pool:
        futures = {pool.submit(attempt, record, str(args.worlds_dir)): record['draw'] for record in records}
        try:
            for future in as_completed(futures):
                result = future.result()
                write_json(args.worlds_dir / f"world-{result['draw']:04d}.json", result, pretty=True)
                results[result['draw']] = result
                if len(results) % (1 if args.pilot else 100) == 0:
                    elapsed = time.monotonic() - started
                    print(f'{len(results)}/{len(records)} worlds in {elapsed:.1f}s', flush=True)
        except BaseException:
            for future in futures:
                future.cancel()
            raise
    verify()
    ordered = [results[row['draw']] for row in records]
    manifest = args.worlds_dir / 'manifest.json'
    write_json(manifest, {'game': stress.GAME, 'fingerprints': fingerprints, 'worlds': ordered}, pretty=True)
    write_json(args.output, {
        'kind': 'isolated matched D29 foul-penalty continuation; diagnostic only',
        'stress': str(SUMMARY.relative_to(ROOT)), 'stress_sha256': sha256_file(SUMMARY),
        'manifest': str(manifest), 'manifest_sha256': sha256_file(manifest), 'pilot': args.pilot,
        'worlds': len(ordered), 'workers': 4, 'elapsed_seconds': round(time.monotonic() - started, 3),
        'limitations': ['One selected synthetic oracle-roster case, not an NBA rate or accuracy test.',
                        'Continuation is an explicit alternative rule, not the unknowable no-exception outcome.',
                        'Does not establish a production retry, availability or promotion gate.'],
    }, pretty=True)


if __name__ == '__main__':
    main()
