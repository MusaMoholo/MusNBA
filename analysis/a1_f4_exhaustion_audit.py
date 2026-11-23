#!/usr/bin/env python3
"""Reconcile saved single-world captures from the fixed F4 exhaustion screen."""
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
    details_path = Path(summary['details'])
    if sha256_file(details_path) != summary['details_sha256']:
        raise ValueError('detailed manifest differs from summary')
    details = read_json(details_path)
    for key in ('fingerprints', 'attempts', 'exhausted', 'invalid_initial_branches'):
        if details[key] != summary[key]:
            raise ValueError(f'{key} differs between summary and detail')
    if any(sha256_file(ROOT / name) != digest for name, digest in details['fingerprints'].items()):
        raise ValueError('source, panel or fold input differs')
    ids = read_json(ROOT / details['panel'])
    if [game['game'] for game in details['games']] != ids or len(ids) != 200:
        raise ValueError('game panel differs')
    start = time.monotonic()
    completed = exhausted = invalid = snapshots = attempts = 0
    paths = set()
    for game in details['games']:
        if not '2026-01-01' <= game['day'] < '2026-07-01':
            raise ValueError('game is outside the F4 development period')
        if read_json(details_path.parent / f"{game['game']}.json") != game:
            raise ValueError('saved game record differs')
        if [b['branch'] for b in game['branches']] != ['plays', 'sits']:
            raise ValueError('branch coverage differs')
        for branch in game['branches']:
            if branch['status'] == 'invalid initial roster or allocation':
                if branch['attempts'] or not branch['reason']:
                    raise ValueError('invalid initial branch contains attempts or no reason')
                invalid += 1
                continue
            if branch['status'] != 'simulated' or len(branch['attempts']) != 5:
                raise ValueError('branch did not record five attempts')
            for draw, attempt in enumerate(branch['attempts']):
                expected = seed_for('a1-f4-exhaustion-v1', game['game'], branch['branch'], draw)
                if attempt['draw'] != draw or int(attempt['seed']) != expected:
                    raise ValueError('draw order or seed differs')
                attempts += 1
                if attempt['status'] == 'exhausted':
                    if 'fewer than five eligible players' not in attempt['reason']:
                        raise ValueError('unclassified world rejection')
                    exhausted += 1
                    continue
                if attempt['status'] != 'complete':
                    raise ValueError('unknown attempt status')
                path = Path(attempt['capture'])
                if path in paths or path.parent != details_path.parent or sha256_file(path) != attempt['capture_sha256']:
                    raise ValueError('capture path or hash differs')
                paths.add(path)
                with np.load(path, allow_pickle=False) as data:
                    capture = {key: data[key] for key in data.files}
                    if str(capture['game_id']) != game['game'] or capture_digest(capture) != attempt['world_sha256']:
                        raise ValueError('captured world identity differs')
                    audit = audit_worlds(capture)
                if audit != attempt['audit'] or audit['worlds'] != 1:
                    raise ValueError('world accounting differs')
                completed += 1
                snapshots += audit['lineup_snapshots']
    if (attempts != summary['attempts'] or exhausted != summary['exhausted']
            or invalid != summary['invalid_initial_branches'] or completed + exhausted != attempts):
        raise ValueError('aggregate accounting differs')
    if any(sha256_file(ROOT / name) != digest for name, digest in details['fingerprints'].items()):
        raise ValueError('source or input changed during audit')
    write_json(args.output, {
        'kind': 'independent fixed-F4 saved-world and attempt accounting; not a forecast',
        'summary': str(args.summary), 'summary_sha256': sha256_file(args.summary),
        'details_sha256': sha256_file(details_path), 'audit_sha256': sha256_file(Path(__file__)),
        'games': len(ids), 'attempts': attempts, 'completed_worlds': completed,
        'exhausted': exhausted, 'invalid_initial_branches': invalid, 'lineup_snapshots': snapshots,
        'elapsed_seconds': round(time.monotonic() - start, 3),
        'limitations': ['Successful traces independently replayed; rejected trajectories were not retained.',
                        'Oracle F4 rosters and synthetic status are not pre-game availability forecasts.',
                        'This does not compare policies, estimate retry bias or score protected outcomes.'],
    }, pretty=True)
    print(f'Audited {completed} completed worlds, {exhausted} recorded exhaustions')


if __name__ == '__main__':
    main()
