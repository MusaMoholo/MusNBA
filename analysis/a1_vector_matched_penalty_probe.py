#!/usr/bin/env python3
"""Verify the vector candidate against saved single-world and fresh vector traces."""
from __future__ import annotations

import argparse
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from analysis import a1_f4_six_roster_stress as stress, a1_real_retry_scale as scale  # noqa: E402
from analysis import a1_real_retry_paired_audit as audit, a1_vector_matched_penalty as candidate  # noqa: E402
from analysis.a1_parallel_world_probe import capture_digest  # noqa: E402
from basketball_common import read_json, sha256_file, write_json  # noqa: E402
from scripts import a1_branch_world_probe, a1_substitution_world_audit  # noqa: E402


def compare_single(first):
    eng, branch = stress._WORKER['engine'], stress._WORKER['branch']
    policy = candidate.VectorMatchedPenaltyTrace()
    eng.rotation_policy = policy
    stress._WORKER['simulate'](branch, 1, int(first['seed']))
    actual = policy.capture(branch, eng.last)
    expected = audit.load(first['capture'], stress.GAME, first['status'] == 'exhausted')
    if capture_digest({key: actual[key] for key in expected}) != capture_digest(expected):
        raise ValueError(f"slot {first['slot']}: single-world continuation differs")
    if policy.first_exhaustion.get(0) != first['failure']:
        raise ValueError(f"slot {first['slot']}: failure state differs")
    accounting = a1_substitution_world_audit.audit_worlds(actual, foul_penalty=True)
    return {'slot': first['slot'], 'exhausted': first['status'] == 'exhausted',
            'fives': accounting['lineup_fives_checked'],
            'technicals': accounting['foul_penalty_events']}


def vector_wiring():
    eng, branch = stress._WORKER['engine'], stress._WORKER['branch']
    captures = []
    for _ in range(2):
        policy = candidate.VectorMatchedPenaltyTrace()
        eng.rotation_policy = policy
        stress._WORKER['simulate'](branch, 100, 20261123)
        capture = policy.capture(branch, eng.last)
        accounting = a1_substitution_world_audit.audit_worlds(capture, foul_penalty=True)
        captures.append(capture)
    if capture_digest(captures[0]) != capture_digest(captures[1]):
        raise ValueError('vector rerun differs')
    if accounting['worlds'] != 100 or not accounting['foul_penalty_events']:
        raise ValueError('vector sample did not exercise the foul penalty')
    base = a1_branch_world_probe.RepairedTrace()
    eng.rotation_policy = base
    stress._WORKER['simulate'](branch, 2, 20261123)
    original = base.capture(branch, eng.last)
    policy = candidate.VectorMatchedPenaltyTrace()
    eng.rotation_policy = policy
    stress._WORKER['simulate'](branch, 2, 20261123)
    current = policy.capture(branch, eng.last)
    if policy.first_exhaustion or policy.technical_events:
        raise ValueError('no-exception wiring sample unexpectedly exhausted')
    if capture_digest(original) != capture_digest({key: current[key] for key in original}):
        raise ValueError('no-exception vector trajectory differs')
    return {'worlds': accounting['worlds'], 'lineup_fives_checked': accounting['lineup_fives_checked'],
            'foul_penalty_events': accounting['foul_penalty_events'], 'deterministic_replay': True,
            'no_exception_worlds_identical': 2}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an experiment')
    if any(os.environ.get(name) != '1' for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS')):
        raise ValueError('set OMP_NUM_THREADS=1 and OPENBLAS_NUM_THREADS=1')
    prior, original = scale.prefix()
    fingerprints = dict(original['fingerprints'])
    for path in (scale.PREFIX, scale.PREFIX_AUDIT, Path(__file__), ROOT / 'analysis/a1_vector_matched_penalty.py'):
        fingerprints[str(path.relative_to(ROOT))] = sha256_file(path)

    def verify():
        if any(sha256_file(ROOT / name) != digest for name, digest in fingerprints.items()):
            raise ValueError('source, input or model changed')

    verify()
    panel = read_json(ROOT / read_json(stress.SUMMARY)['details'])
    selected = [game for game in panel['games'] if game['game'] == stress.GAME]
    if len(selected) != 1:
        raise ValueError('selected game differs')
    start = time.monotonic()
    results = {}
    with ProcessPoolExecutor(max_workers=10, initializer=stress.init_worker,
                             initargs=(selected[0]['selected_player'],)) as pool:
        futures = [pool.submit(compare_single, first) for first in original['first']]
        for future in as_completed(futures):
            row = future.result()
            results[row['slot']] = row
            if len(results) % 100 == 0:
                print(f"{len(results)}/1000 single worlds matched in {time.monotonic() - start:.1f}s", flush=True)
        vector = pool.submit(vector_wiring).result()
    if set(results) != set(range(1000)):
        raise ValueError('single-world population differs')
    verify()
    write_json(args.output, {
        'kind': 'isolated vectorized matched-penalty wiring; not a forecast',
        'reference': str(scale.PREFIX.relative_to(ROOT)), 'reference_sha256': sha256_file(scale.PREFIX),
        'worlds': len(results), 'failed_first_seeds': sum(r['exhausted'] for r in results.values()),
        'lineup_fives_checked': sum(r['fives'] for r in results.values()),
        'technical_events': sum(r['technicals'] for r in results.values()),
        'vector': vector, 'fingerprints': fingerprints,
        'elapsed_seconds': round(time.monotonic() - start, 3),
        'limitations': prior['limitations'] + [
            'Vectorized engine RNG streams are shared; a changed event can alter other whole-game trajectories.',
            'Wiring and accounting are not a real-outcome or production gate.'],
    }, pretty=True)


if __name__ == '__main__':
    main()
