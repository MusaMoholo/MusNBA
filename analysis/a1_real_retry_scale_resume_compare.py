#!/usr/bin/env python3
"""Compare uninterrupted and clean-resume paired retry captures."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from analysis import a1_f4_six_roster_stress as stress, a1_real_retry_paired_audit as audit  # noqa: E402
from analysis.a1_parallel_world_probe import capture_digest  # noqa: E402
from basketball_common import read_json, sha256_file, write_json  # noqa: E402


def load_report(path):
    report = read_json(path)
    manifest_path = ROOT / report['manifest']
    if sha256_file(manifest_path) != report['manifest_sha256']:
        raise ValueError('manifest changed')
    return report, read_json(manifest_path)


def equivalent(first, second, *, penalty):
    left = {key: value for key, value in first.items() if key != 'capture'}
    right = {key: value for key, value in second.items() if key != 'capture'}
    if left != right or first['capture']['audit'] != second['capture']['audit']:
        raise ValueError('metadata or world accounting differs')
    a = audit.load(first['capture'], stress.GAME, penalty)
    b = audit.load(second['capture'], stress.GAME, penalty)
    if capture_digest(a) != capture_digest(b):
        raise ValueError('world contents differ')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('uninterrupted', type=Path)
    parser.add_argument('resumed', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite comparison')
    control, left = load_report(args.uninterrupted)
    restarted, right = load_report(args.resumed)
    if (control['worlds'] != 1200 or restarted['worlds'] != 1200
            or control['resumed_new_batches'] != 0 or restarted['resumed_new_batches'] != 1
            or left['prefix'] != right['prefix'] or left['fingerprints'] != right['fingerprints']):
        raise ValueError('pilot populations or source versions differ')
    for batch_a, batch_b in zip(left['batches'], right['batches'], strict=True):
        if (batch_a['batch'] != batch_b['batch'] or batch_a['rejections'] != batch_b['rejections']):
            raise ValueError('batch or rejection sequence differs')
        for first_a, first_b in zip(batch_a['first'], batch_b['first'], strict=True):
            equivalent(first_a, first_b, penalty=first_a['status'] == 'exhausted')
        for accepted_a, accepted_b in zip(batch_a['accepted'], batch_b['accepted'], strict=True):
            equivalent(accepted_a, accepted_b, penalty=False)
    if control['rejections'] != restarted['rejections']:
        raise ValueError('rejection total differs')
    write_json(args.output, {
        'kind': 'clean-stop/resume versus uninterrupted paired retry pilot',
        'uninterrupted': str(args.uninterrupted), 'uninterrupted_sha256': sha256_file(args.uninterrupted),
        'resumed': str(args.resumed), 'resumed_sha256': sha256_file(args.resumed),
        'comparison_script_sha256': sha256_file(Path(__file__)),
        'shared_audited_prefix': 1000, 'new_slots_compared': 200, 'rejections': control['rejections'],
        'result': 'first and accepted world contents, failure states, seeds and rejection order match',
        'limitations': ['Synthetic selected-roster diagnostic; not a predictive or full-slate benchmark.'],
    }, pretty=True)


if __name__ == '__main__':
    main()
