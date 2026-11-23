#!/usr/bin/env python3
"""Replay selected six-player exhaustion seeds under the isolated S06 penalty policy."""
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
from analysis import a1_f4_six_roster_stress as stress  # noqa: E402
from basketball_common import read_json, sha256_file, write_json  # noqa: E402
from scripts import a1_foul_penalty_engine, a1_substitution_engine  # noqa: E402
from scripts import a1_substitution_world_audit, a1_substitution_world_capture, projection  # noqa: E402

SUMMARY = ROOT / 'analysis/experiments/20261122_a1_f4_six_roster_v1.json'
AUDIT = ROOT / 'analysis/experiments/20261122_a1_f4_six_roster_v1_audit.json'
CANDIDATE = ROOT / 'analysis/experiments/20261122_a1_s06_engine_models_F4.json'
_WORKER = {}


def init_worker(player: str) -> None:
    stress.init_worker(player)
    outgoing, incoming, timing = a1_substitution_engine.load_candidate(CANDIDATE, 'F4')
    features = a1_substitution_engine.load_features('F4')
    policy = a1_foul_penalty_engine.PlayerFoulPenaltyPolicy(
        outgoing, incoming, timing, features, capture_trace=True)
    _WORKER.update(engine=stress._WORKER['engine'], branch=stress._WORKER['branch'],
                   simulate=stress._WORKER['simulate'], policy=policy)


def attempt(previous: dict, directory: str) -> dict:
    draw = previous['draw']
    if (previous['status'] != 'exhausted'
            or int(previous['seed']) != projection.seed_for('a1-f4-six-roster-v1', stress.GAME, draw)):
        raise ValueError('rejected draw or seed differs')
    eng, branch, policy = _WORKER['engine'], _WORKER['branch'], _WORKER['policy']
    eng.rotation_policy = policy
    _WORKER['simulate'](branch, 1, int(previous['seed']))
    capture = a1_substitution_world_capture.capture(branch, eng.last, policy)
    audit = a1_substitution_world_audit.audit_worlds(capture, foul_penalty=True)
    path = Path(directory) / f'world-{draw:04d}.npz'
    if path.exists():
        raise FileExistsError(f'{path}: refusing to overwrite capture')
    np.savez_compressed(path, **capture)
    return {'draw': draw, 'seed': previous['seed'], 'original_rejection': previous['reason'],
            'capture': str(path), 'capture_sha256': sha256_file(path),
            'audit': audit, 'technical_events': policy.technical_events.copy()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worlds-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.worlds_dir.exists() or args.output.exists():
        raise FileExistsError('refusing to overwrite an experiment')
    if any(os.environ.get(name) != '1' for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS')):
        raise ValueError('set OMP_NUM_THREADS=1 and OPENBLAS_NUM_THREADS=1')
    summary, audit = read_json(SUMMARY), read_json(AUDIT)
    if audit['summary_sha256'] != sha256_file(SUMMARY) or audit['exhausted'] != summary['exhausted']:
        raise ValueError('independent source audit differs')
    details_path = ROOT / summary['details']
    if sha256_file(details_path) != summary['details_sha256']:
        raise ValueError('stress manifest differs')
    details = read_json(details_path)
    rejected = [record for record in details['attempts'] if record['status'] == 'exhausted']
    if len(rejected) != 202 or len({record['draw'] for record in rejected}) != 202:
        raise ValueError('expected 202 distinct rejected draws')
    panel = read_json(ROOT / read_json(stress.SUMMARY)['details'])
    selected = [game for game in panel['games'] if game['game'] == stress.GAME]
    if len(selected) != 1:
        raise ValueError('selected game is missing from panel')
    candidate = read_json(CANDIDATE)
    fingerprints = {**summary['fingerprints'], **candidate['input_sha256'], **candidate['output_sha256']}
    extra = (SUMMARY, AUDIT, CANDIDATE, Path(__file__),
             ROOT / 'analysis/a1_f4_six_roster_penalty_audit.py',
             ROOT / 'scripts/a1_foul_penalty_engine.py', ROOT / 'scripts/a1_substitution_engine.py',
             ROOT / 'scripts/a1_substitution_world_capture.py',
             ROOT / 'scripts/a1_substitution_in_coverage.py',
             ROOT / 'analysis/experiments/20261122_a1_s05_minutes_screen_accounting_corrected.json',
             ROOT / 'data/derived/experiments/20261122_a1_s05_unconditional_F4_corrected.parquet')
    fingerprints.update({str(path.relative_to(ROOT)): sha256_file(path) for path in extra})

    def verify_inputs() -> None:
        if any(sha256_file(ROOT / name) != digest for name, digest in fingerprints.items()):
            raise ValueError('stress, source, model or input changed')

    verify_inputs()
    args.worlds_dir.mkdir(parents=True)
    started = time.monotonic()
    records = {}
    with ProcessPoolExecutor(max_workers=4, initializer=init_worker,
                             initargs=(selected[0]['selected_player'],)) as pool:
        futures = {pool.submit(attempt, record, str(args.worlds_dir)): record['draw'] for record in rejected}
        for future in as_completed(futures):
            draw = futures[future]
            result = future.result()
            write_json(args.worlds_dir / f'world-{draw:04d}.json', result, pretty=True)
            records[draw] = result
            if len(records) % 20 == 0 or len(records) == len(rejected):
                elapsed = time.monotonic() - started
                print(f'{len(records)}/{len(rejected)} worlds in {elapsed:.1f}s '
                      f'({len(records) / elapsed:.2f} worlds/s)', flush=True)
    verify_inputs()
    ordered = [records[record['draw']] for record in rejected]
    manifest = args.worlds_dir / 'manifest.json'
    write_json(manifest, {'game': stress.GAME, 'fingerprints': fingerprints, 'worlds': ordered}, pretty=True)
    write_json(args.output, {
        'kind': 'selected six-player F4 rejected-seed S06 comparison; not an NBA rate or accuracy test',
        'stress': str(SUMMARY.relative_to(ROOT)), 'stress_sha256': sha256_file(SUMMARY),
        'manifest': str(manifest), 'manifest_sha256': sha256_file(manifest),
        'worlds': len(ordered), 'workers': 4, 'threads': 'OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1',
        'elapsed_seconds': round(time.monotonic() - started, 3),
        'technical_events': sum(len(record['technical_events']) for record in ordered),
        'worlds_with_technical': sum(bool(record['technical_events']) for record in ordered),
        'limitations': ['One selected oracle-roster game with synthetic absence and D29-rejected seeds.',
                        'S06 changes substitutions and random paths; matching seeds are not matched states.',
                        'Not an NBA rate, retry-bias measurement, predictive test, or production policy.'],
    }, pretty=True)


if __name__ == '__main__':
    main()
