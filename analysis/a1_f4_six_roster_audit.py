#!/usr/bin/env python3
"""Replay completed captures and check every seed of the targeted F4 stress."""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from analysis.a1_parallel_world_probe import capture_digest  # noqa: E402
from basketball_common import read_json, sha256_file, write_json  # noqa: E402
from scripts.a1_substitution_world_audit import audit_worlds  # noqa: E402
from scripts.projection import seed_for  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('summary', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an audit')
    summary = read_json(args.summary)
    detail_path = Path(summary['details'])
    if sha256_file(detail_path) != summary['details_sha256']:
        raise ValueError('detailed manifest differs')
    detail = read_json(detail_path)
    if (detail['game'] != summary['game'] or detail['fingerprints'] != summary['fingerprints']
            or summary['attempts'] != 1000 or len(detail['attempts']) != 1000):
        raise ValueError('manifest and summary differ')
    if any(sha256_file(ROOT / name) != digest for name, digest in detail['fingerprints'].items()):
        raise ValueError('source, panel or fold input differs')
    completed = exhausted = snapshots = 0
    started = time.monotonic()
    for draw, record in enumerate(detail['attempts']):
        seed = seed_for('a1-f4-six-roster-v1', detail['game'], draw)
        if (record['draw'] != draw or int(record['seed']) != seed
                or read_json(detail_path.parent / f'world-{draw:04d}.json') != record):
            raise ValueError('draw, seed or per-world record differs')
        if record['status'] == 'exhausted':
            if 'fewer than five eligible players' not in record['reason']:
                raise ValueError('unclassified world rejection')
            exhausted += 1
            continue
        if record['status'] != 'complete':
            raise ValueError('unknown attempt status')
        path = Path(record['capture'])
        if path != detail_path.parent / f'world-{draw:04d}.npz' or sha256_file(path) != record['capture_sha256']:
            raise ValueError('capture path or hash differs')
        with np.load(path, allow_pickle=False) as data:
            capture = {key: data[key] for key in data.files}
            if (str(capture['game_id']) != detail['game'] or capture_digest(capture) != record['world_sha256']
                    or (capture['available'][:, capture['side'] == 0].sum(axis=1) != 6).any()):
                raise ValueError('game, capture or six-player branch identity differs')
            audit = audit_worlds(capture)
        if audit != record['audit'] or audit['worlds'] != 1:
            raise ValueError('world accounting differs')
        completed += 1
        snapshots += audit['lineup_snapshots']
    if exhausted != summary['exhausted'] or completed + exhausted != 1000:
        raise ValueError('attempt counts differ')
    if any(sha256_file(ROOT / name) != digest for name, digest in detail['fingerprints'].items()):
        raise ValueError('source or input changed during audit')
    write_json(args.output, {
        'kind': 'independent targeted F4 saved-world and seed accounting',
        'summary': str(args.summary), 'summary_sha256': sha256_file(args.summary),
        'details_sha256': sha256_file(detail_path), 'audit_sha256': sha256_file(Path(__file__)),
        'attempts': 1000, 'completed_worlds': completed, 'exhausted': exhausted,
        'lineup_snapshots': snapshots, 'elapsed_seconds': round(time.monotonic() - started, 3),
        'limitations': ['Successful traces independently replayed; rejected trajectories not retained.',
                        'One selected oracle-roster game; not an NBA rate or retry-bias comparison.'],
    }, pretty=True)
    print(f'Audited {completed} completed worlds, {exhausted} recorded exhaustions')


if __name__ == '__main__':
    main()
