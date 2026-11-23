#!/usr/bin/env python3
"""Compare independently audited uninterrupted and resumed isolated captures."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import read_json, sha256_file, write_json  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('control', type=Path)
    parser.add_argument('resumed', type=Path)
    parser.add_argument('control_audit', type=Path)
    parser.add_argument('resumed_audit', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an experiment')
    control, resumed = read_json(args.control), read_json(args.resumed)
    audits = [read_json(args.control_audit), read_json(args.resumed_audit)]
    for path, audit in zip((args.control, args.resumed), audits):
        if audit['report_sha256'] != sha256_file(path):
            raise ValueError(f'{path}: independent audit is for a different report')
    for key in ('pilot', 'fingerprints', 'worlds', 'base_seed', 'rejection_count'):
        if control[key] != resumed[key]:
            raise ValueError(f'run {key} differs')
    if control['resumed_batches'] != 0 or not 0 < resumed['resumed_batches'] < len(resumed['batches']):
        raise ValueError('expected an uninterrupted run and a partially resumed run')
    for key in ('worlds', 'batches', 'lineup_snapshots', 'rejections', 'serial_pilot_worlds_checked'):
        if audits[0][key] != audits[1][key]:
            raise ValueError(f'audit {key} differs')
    if len(control['batches']) != len(resumed['batches']):
        raise ValueError('batch counts differ')
    for index, (left, right) in enumerate(zip(control['batches'], resumed['batches'])):
        for key in ('batch', 'batch_seed', 'capture_sha256', 'dtype_overrides', 'accepted_seeds', 'rejections'):
            if left[key] != right[key]:
                raise ValueError(f'batch {index}: {key} differs')
    write_json(args.output, {
        'kind': 'independently audited clean-stop/resume comparison; not a forecast or promotion',
        'control': str(args.control), 'control_sha256': sha256_file(args.control),
        'resumed': str(args.resumed), 'resumed_sha256': sha256_file(args.resumed),
        'control_audit': str(args.control_audit), 'control_audit_sha256': sha256_file(args.control_audit),
        'resumed_audit': str(args.resumed_audit), 'resumed_audit_sha256': sha256_file(args.resumed_audit),
        'worlds': control['worlds'], 'batches': len(control['batches']),
        'resumed_batches': resumed['resumed_batches'], 'rejections': control['rejection_count'],
        'lineup_snapshots_per_run': audits[0]['lineup_snapshots'],
        'limitations': ['Clean stop at a completed batch, not a hard interruption during a write.',
                        'One fixed F4 game with synthetic availability and one injected rejection.',
                        'This does not validate production, predictive accuracy or bias.'],
    }, pretty=True)
    print(f"Matched {control['worlds']} audited world hashes, seeds and rejection records")


if __name__ == '__main__':
    main()
