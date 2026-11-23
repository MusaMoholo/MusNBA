#!/usr/bin/env python3
"""Compare independently audited fixed-panel runs across worker counts."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from analysis.a1_parallel_world_probe import capture_digest  # noqa: E402
from basketball_common import read_json, sha256_file, write_json  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('four', type=Path)
    parser.add_argument('four_audit', type=Path)
    parser.add_argument('eight', type=Path)
    parser.add_argument('eight_audit', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite comparison')
    paths = (args.four, args.eight)
    reports = [read_json(path) for path in paths]
    for path, audit_path in zip(paths, (args.four_audit, args.eight_audit), strict=True):
        if read_json(audit_path)['report_sha256'] != sha256_file(path):
            raise ValueError('independent audit does not match report')
    left, right = reports
    for key in ('game_ids', 'worlds', 'fold', 'control', 'fingerprints'):
        if left[key] != right[key]:
            raise ValueError(f'fixed-run {key} differs')
    if (left['workers'] != 4 or right['workers'] != 8 or not left['scaling'] or not right['scaling']
            or left['games'] != 10 or right['games'] != 10):
        raise ValueError('worker-count or timing population differs')
    for a, b in zip(left['captures'], right['captures'], strict=True):
        if a['game'] != b['game'] or a['technical_events'] != b['technical_events']:
            raise ValueError('game identity or technical count differs')
        captures = []
        for item in (a, b):
            path = ROOT / item['capture']
            if sha256_file(path) != item['sha256']:
                raise ValueError('capture hash differs')
            with np.load(path, allow_pickle=False) as data:
                captures.append(dict(data))
        if capture_digest(captures[0]) != capture_digest(captures[1]):
            raise ValueError('world contents differ across worker counts')
    folder = ROOT / 'data/derived/experiments'
    for suffix in ('', '_players'):
        frames = [pd.read_parquet(folder / f"{report['run']}{suffix}.parquet") for report in reports]
        if not frames[0].equals(frames[1]):
            raise ValueError('backtest output differs across worker counts')
    write_json(args.output, {
        'kind': 'independently audited worker scaling comparison; not a forecast',
        'reports': [{'path': str(path), 'sha256': sha256_file(path)} for path in paths],
        'audits': [{'path': str(path), 'sha256': sha256_file(path)}
                   for path in (args.four_audit, args.eight_audit)],
        'comparison_script_sha256': sha256_file(Path(__file__)),
        'games': 10, 'worlds_per_game': left['worlds'], 'contents_and_outputs_identical': True,
        'four_seconds': left['elapsed_seconds'], 'eight_seconds': right['elapsed_seconds'],
        'elapsed_reduction_fraction': 1 - right['elapsed_seconds'] / left['elapsed_seconds'],
        'four_worker_peak_rss_sum_bytes': left['sum_worker_peak_rss_upper_bound_bytes'],
        'eight_worker_peak_rss_sum_bytes': right['sum_worker_peak_rss_upper_bound_bytes'],
        'limitations': ['Ten fixed oracle-roster games, not a full-slate benchmark.',
                        'Summed worker high-water RSS excludes parent, OS and other processes.'],
    }, pretty=True)


if __name__ == '__main__':
    main()
