#!/usr/bin/env python3
"""Complete the S06 side of the prespecified selected-roster comparison."""
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
from analysis import a1_f4_six_roster_penalty_compare as prior, a1_f4_six_roster_stress as stress  # noqa: E402
from basketball_common import read_json, sha256_file, write_json  # noqa: E402
from scripts import a1_substitution_world_audit, a1_substitution_world_capture, projection  # noqa: E402

PENALTY = ROOT / 'analysis/experiments/20261122_a1_f4_six_roster_penalty_v1.json'
PENALTY_AUDIT = ROOT / 'analysis/experiments/20261122_a1_f4_six_roster_penalty_v1_audit.json'
STRESS_AUDIT = ROOT / 'analysis/experiments/20261122_a1_f4_six_roster_v1_audit.json'


def attempt(previous: dict, directory: str) -> dict:
    draw = previous['draw']
    if (previous['status'] != 'complete'
            or int(previous['seed']) != projection.seed_for('a1-f4-six-roster-v1', stress.GAME, draw)):
        raise ValueError('survivor draw or seed differs')
    eng, branch, policy = (prior._WORKER[key] for key in ('engine', 'branch', 'policy'))
    eng.rotation_policy = policy
    prior._WORKER['simulate'](branch, 1, int(previous['seed']))
    capture = a1_substitution_world_capture.capture(branch, eng.last, policy)
    audit = a1_substitution_world_audit.audit_worlds(capture, foul_penalty=True)
    path = Path(directory) / f'world-{draw:04d}.npz'
    if path.exists():
        raise FileExistsError(f'{path}: refusing to overwrite capture')
    np.savez_compressed(path, **capture)
    return {'draw': draw, 'seed': previous['seed'], 'capture': str(path),
            'capture_sha256': sha256_file(path), 'audit': audit}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worlds-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.worlds_dir.exists() or args.output.exists():
        raise FileExistsError('refusing to overwrite an experiment')
    if any(os.environ.get(name) != '1' for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS')):
        raise ValueError('set OMP_NUM_THREADS=1 and OPENBLAS_NUM_THREADS=1')
    original, old, source_audit, penalty_audit = (read_json(p) for p in
                                                   (prior.SUMMARY, PENALTY, STRESS_AUDIT, PENALTY_AUDIT))
    if (source_audit['summary_sha256'] != sha256_file(prior.SUMMARY)
            or penalty_audit['report_sha256'] != sha256_file(PENALTY)):
        raise ValueError('prior independent audit does not match the source')
    detail_path, old_path = ROOT / original['details'], ROOT / old['manifest']
    if sha256_file(detail_path) != original['details_sha256'] or sha256_file(old_path) != old['manifest_sha256']:
        raise ValueError('prior manifests differ')
    attempts, old_manifest = read_json(detail_path)['attempts'], read_json(old_path)
    survivors = [row for row in attempts if row['status'] == 'complete']
    if (len(attempts) != 1000 or len(survivors) != 798 or len(old_manifest['worlds']) != 202
            or {r['draw'] for r in old_manifest['worlds']} != {r['draw'] for r in attempts if r['status'] == 'exhausted'}):
        raise ValueError('prior selected seed populations differ')
    panel = read_json(ROOT / read_json(stress.SUMMARY)['details'])
    selected = [game for game in panel['games'] if game['game'] == stress.GAME]
    if len(selected) != 1:
        raise ValueError('selected game is missing from panel')
    fingerprints = dict(old_manifest['fingerprints'])
    for path in (PENALTY, PENALTY_AUDIT, STRESS_AUDIT, Path(__file__),
                 ROOT / 'analysis/a1_f4_six_roster_full_audit.py'):
        fingerprints[str(path.relative_to(ROOT))] = sha256_file(path)

    def verify_inputs() -> None:
        if any(sha256_file(ROOT / name) != digest for name, digest in fingerprints.items()):
            raise ValueError('source, model or input changed')

    verify_inputs()
    args.worlds_dir.mkdir(parents=True)
    started = time.monotonic()
    records = {}
    with ProcessPoolExecutor(max_workers=4, initializer=prior.init_worker,
                             initargs=(selected[0]['selected_player'],)) as pool:
        futures = {pool.submit(attempt, record, str(args.worlds_dir)): record['draw'] for record in survivors}
        try:
            for future in as_completed(futures):
                draw = futures[future]
                result = future.result()
                write_json(args.worlds_dir / f'world-{draw:04d}.json', result, pretty=True)
                records[draw] = result
                if len(records) % 80 == 0 or len(records) == len(survivors):
                    elapsed = time.monotonic() - started
                    print(f'{len(records)}/{len(survivors)} worlds in {elapsed:.1f}s '
                          f'({len(records) / elapsed:.2f} worlds/s)', flush=True)
        except BaseException:
            for future in futures:
                future.cancel()
            raise
    verify_inputs()
    manifest = args.worlds_dir / 'manifest.json'
    write_json(manifest, {'game': stress.GAME, 'fingerprints': fingerprints,
                          'worlds': [records[r['draw']] for r in survivors]}, pretty=True)
    write_json(args.output, {
        'kind': 'selected six-player F4 S06 survivor-seed captures; diagnostic only',
        'stress': str(prior.SUMMARY.relative_to(ROOT)), 'stress_sha256': sha256_file(prior.SUMMARY),
        'penalty': str(PENALTY.relative_to(ROOT)), 'penalty_sha256': sha256_file(PENALTY),
        'manifest': str(manifest), 'manifest_sha256': sha256_file(manifest),
        'worlds': len(records), 'workers': 4,
        'elapsed_seconds': round(time.monotonic() - started, 3),
        'limitations': ['Synthetic selected oracle-roster case, not an NBA rate or accuracy test.',
                        'Different policies and random paths prevent identifying retry bias.'],
    }, pretty=True)


if __name__ == '__main__':
    main()
