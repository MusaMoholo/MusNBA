#!/usr/bin/env python3
"""Probe isolated-world exhaustion in one deliberately selected six-player branch."""
from __future__ import annotations

import argparse
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from analysis import a1_f4_exhaustion_screen as panel  # noqa: E402
from analysis.a1_parallel_world_probe import capture_digest  # noqa: E402
from basketball_common import read_json, sha256_file, write_json  # noqa: E402
from scripts import a1_branch_foul_out, a1_branch_world_probe, a1_lineup_branches  # noqa: E402
from scripts import a1_substitution_world_audit, backtest, projection  # noqa: E402

GAME = '401811022'
SUMMARY = ROOT / 'analysis/experiments/20261122_a1_f4_exhaustion_v1.json'
_WORKER = {}


def init_worker(expected_player: str) -> None:
    panel.init_worker()
    eng = panel._WORKER['engine']
    simulate = eng.simulate

    def prepare(g, _worlds, _seed):
        home = np.flatnonzero(g.side == 0)
        if len(home) != 7 or not '2026-01-01' <= g.day < '2026-07-01':
            raise ValueError('target is not the fixed seven-home-player F4 game')
        index = min(home, key=lambda i: (-g.expected[i], str(g.ids[i])))
        if str(g.ids[index]) != expected_player:
            raise ValueError('selected player differs from the frozen panel')
        g.avail[index] = g.players['home'][int(index)]['availability'] = 0.5
        branch = a1_lineup_branches.one_player(g, str(g.game['home_id']), expected_player, False)
        if int((branch.avail[home] > 0).sum()) != 6:
            raise ValueError('target branch does not have six available home players')
        _WORKER.update(engine=eng, simulate=simulate, branch=branch)
        raise panel.CapturedGame()

    try:
        with patch.object(eng, 'simulate', side_effect=prepare):
            backtest.run_game(GAME)
    except panel.CapturedGame:
        pass
    if not _WORKER:
        raise ValueError('target game was not reached')


def attempt(draw: int, directory: str) -> dict:
    seed = projection.seed_for('a1-f4-six-roster-v1', GAME, draw)
    eng, branch = _WORKER['engine'], _WORKER['branch']
    policy = a1_branch_world_probe.RepairedTrace()
    eng.rotation_policy = policy
    try:
        _WORKER['simulate'](branch, 1, seed)
    except a1_branch_foul_out.ExhaustedEligiblePlayers as exc:
        return {'draw': draw, 'seed': str(seed), 'status': 'exhausted', 'reason': str(exc)}
    capture = policy.capture(branch, eng.last)
    accounting = a1_substitution_world_audit.audit_worlds(capture)
    path = Path(directory) / f'world-{draw:04d}.npz'
    if path.exists():
        raise FileExistsError(f'{path}: refusing to overwrite capture')
    np.savez_compressed(path, **capture)
    return {'draw': draw, 'seed': str(seed), 'status': 'complete', 'capture': str(path),
            'capture_sha256': sha256_file(path), 'world_sha256': capture_digest(capture), 'audit': accounting}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worlds-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.worlds_dir.exists() or args.output.exists():
        raise FileExistsError('refusing to overwrite an experiment')
    if any(os.environ.get(name) != '1' for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS')):
        raise ValueError('set OMP_NUM_THREADS=1 and OPENBLAS_NUM_THREADS=1')
    summary = read_json(SUMMARY)
    detail_path = ROOT / summary['details']
    if sha256_file(detail_path) != summary['details_sha256']:
        raise ValueError('F4 panel details differ from their summary')
    detail = read_json(detail_path)
    selected = [g for g in detail['games'] if g['actual_participant_counts'][0] == 7]
    if len(selected) != 1 or selected[0]['game'] != GAME:
        raise ValueError('expected one fixed seven-home-player game')
    fingerprints = {**summary['fingerprints'],
                    str(SUMMARY.relative_to(ROOT)): sha256_file(SUMMARY),
                    str(detail_path.relative_to(ROOT)): sha256_file(detail_path),
                    str(Path(__file__).relative_to(ROOT)): sha256_file(Path(__file__)),
                    'analysis/a1_f4_six_roster_audit.py': sha256_file(ROOT / 'analysis/a1_f4_six_roster_audit.py')}

    def verify_inputs() -> None:
        if any(sha256_file(ROOT / name) != digest for name, digest in fingerprints.items()):
            raise ValueError('panel, source, model or input changed')

    verify_inputs()
    args.worlds_dir.mkdir(parents=True)
    start = time.monotonic()
    records = {}
    with ProcessPoolExecutor(max_workers=10, initializer=init_worker,
                             initargs=(selected[0]['selected_player'],)) as pool:
        futures = {pool.submit(attempt, draw, str(args.worlds_dir)): draw for draw in range(1000)}
        for future in as_completed(futures):
            draw = futures[future]
            record = future.result()
            write_json(args.worlds_dir / f'world-{draw:04d}.json', record, pretty=True)
            records[draw] = record
            if len(records) % 100 == 0:
                elapsed = time.monotonic() - start
                print(f'{len(records)}/1000 attempts in {elapsed:.1f}s '
                      f'({len(records) / elapsed:.2f} attempts/s)', flush=True)
    verify_inputs()
    ordered = [records[draw] for draw in range(1000)]
    details_path = args.worlds_dir / 'manifest.json'
    details = {'game': GAME, 'attempts': ordered, 'fingerprints': fingerprints}
    write_json(details_path, details, pretty=True)
    write_json(args.output, {
        'kind': 'selected six-player F4 branch stress; not an NBA failure-rate estimate',
        'fingerprints': fingerprints, 'game': GAME, 'attempts': len(ordered),
        'exhausted': sum(r['status'] == 'exhausted' for r in ordered),
        'workers': 10, 'threads': 'OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1',
        'elapsed_seconds': round(time.monotonic() - start, 3),
        'details': str(details_path), 'details_sha256': sha256_file(details_path),
        'limitations': ['One deliberately selected oracle-roster game with synthetic status.',
                        'First attempts only; no retry bias, penalty comparison or production rate.',
                        'No protected-season actual outcomes are scored.'],
    }, pretty=True)


if __name__ == '__main__':
    main()
