#!/usr/bin/env python3
"""Screen isolated branch exhaustion on the fixed actual-participant F4 panel."""
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
from analysis.a1_parallel_world_probe import capture_digest  # noqa: E402
from basketball_common import read_json, sha256_file, write_json  # noqa: E402
from scripts import a1_branch_foul_out, a1_branch_world_probe, a1_lineup_branches  # noqa: E402
from scripts import a1_substitution_world_audit, backtest, projection  # noqa: E402

PANEL = ROOT / 'data/derived/experiments/20261122_a1_s03_f4_game_ids.json'
PROVENANCE = ROOT / 'analysis/experiments/20261122_a1_restart_provenance_v1.json'
_WORKER = {}


class CapturedGame(Exception):
    pass


def init_worker() -> None:
    backtest._init('folds/v1.2d_F4_all', str(ROOT / 'models/v1.2d.json'), 'F4', 1,
                   rotation='targets', pool=0)
    _WORKER['engine'] = backtest._W['engine']


def screen_game(gid: str, directory: str) -> dict:
    eng = _WORKER['engine']
    if eng.rotation_policy is not None:
        raise ValueError('worker must start each game with the default policy')
    simulate = eng.simulate
    result = {}

    def run(g, _worlds, _seed):
        if not '2026-01-01' <= g.day < '2026-07-01':
            raise ValueError(f'{gid}: game is outside the protected F4 development period')
        home = np.flatnonzero(g.side == 0)
        if len(home) < 5:
            raise ValueError(f'{gid}: observed home roster has fewer than five players')
        index = min(home, key=lambda i: (-g.expected[i], str(g.ids[i])))
        player, team = str(g.ids[index]), str(g.game['home_id'])
        g.avail[index] = g.players['home'][int(index)]['availability'] = 0.5
        branches = []
        for plays in (True, False):
            label = 'plays' if plays else 'sits'
            try:
                branch = a1_lineup_branches.one_player(g, team, player, plays)
            except ValueError as exc:
                if not any(str(exc) == f'{side} {problem}' for side in ('home', 'away') for problem in (
                        'has fewer than five possible available players',
                        'D29 targets do not form a legal 240-minute allocation')):
                    raise
                branches.append({'branch': label, 'status': 'invalid initial roster or allocation',
                                 'reason': str(exc), 'attempts': []})
                continue
            attempts = []
            for draw in range(5):
                seed = projection.seed_for('a1-f4-exhaustion-v1', gid, label, draw)
                policy = a1_branch_world_probe.RepairedTrace()
                eng.rotation_policy = policy
                try:
                    simulate(branch, 1, seed)
                except a1_branch_foul_out.ExhaustedEligiblePlayers as exc:
                    attempts.append({'draw': draw, 'seed': str(seed), 'status': 'exhausted',
                                     'reason': str(exc)})
                    continue
                capture = policy.capture(branch, eng.last)
                accounting = a1_substitution_world_audit.audit_worlds(capture)
                path = Path(directory) / f'{gid}-{label}-{draw}.npz'
                if path.exists():
                    raise FileExistsError(f'{path}: refusing to overwrite capture')
                np.savez_compressed(path, **capture)
                attempts.append({'draw': draw, 'seed': str(seed), 'status': 'complete',
                                 'capture': str(path), 'capture_sha256': sha256_file(path),
                                 'world_sha256': capture_digest(capture), 'audit': accounting})
            branches.append({'branch': label, 'status': 'simulated', 'attempts': attempts})
        result.update({'game': gid, 'day': g.day, 'selected_player': player,
                       'actual_participant_counts': [int((g.side == side).sum()) for side in (0, 1)],
                       'branches': branches})
        raise CapturedGame()

    try:
        with patch.object(eng, 'simulate', side_effect=run):
            backtest.run_game(gid)
    except CapturedGame:
        pass
    finally:
        eng.rotation_policy = None
    if not result:
        raise ValueError(f'{gid}: game was not reached')
    write_json(Path(directory) / f'{gid}.json', result, pretty=True)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worlds-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.worlds_dir.exists() or args.output.exists():
        raise FileExistsError('refusing to overwrite an experiment')
    if any(os.environ.get(name) != '1' for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS')):
        raise ValueError('set OMP_NUM_THREADS=1 and OPENBLAS_NUM_THREADS=1')
    ids = read_json(PANEL)
    if len(ids) != 200 or len(set(ids)) != 200:
        raise ValueError('expected the fixed 200 unique F4 games')
    provenance = read_json(PROVENANCE)
    fingerprints = {**provenance['input_sha256'], **provenance['sha256']}
    for path in (PANEL, PROVENANCE, Path(__file__), ROOT / 'analysis/a1_parallel_world_probe.py',
                 ROOT / 'analysis/a1_f4_exhaustion_audit.py'):
        fingerprints[str(path.relative_to(ROOT))] = sha256_file(path)

    def verify_inputs() -> None:
        if any(sha256_file(ROOT / name) != digest for name, digest in fingerprints.items()):
            raise ValueError('fixed-panel sources, inputs or models changed')

    verify_inputs()
    args.worlds_dir.mkdir(parents=True)
    start = time.monotonic()
    results = {}
    with ProcessPoolExecutor(max_workers=10, initializer=init_worker) as pool:
        jobs = {pool.submit(screen_game, gid, str(args.worlds_dir)): gid for gid in ids}
        for future in as_completed(jobs):
            gid = jobs[future]
            results[gid] = future.result()
            if len(results) % 20 == 0:
                elapsed = time.monotonic() - start
                print(f'{len(results)}/200 games in {elapsed:.1f}s '
                      f'({len(results) / elapsed:.3f} games/s)', flush=True)
    verify_inputs()
    ordered = [results[gid] for gid in ids]
    branches = [branch for game in ordered for branch in game['branches']]
    attempts = [attempt for branch in branches for attempt in branch['attempts']]
    detail_path = args.worlds_dir / 'panel_manifest.json'
    details = {
        'kind': 'fixed F4 actual-participant synthetic branch stress; not a forecast or promotion',
        'panel': str(PANEL.relative_to(ROOT)), 'fingerprints': fingerprints,
        'workers': 10, 'threads': 'OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1',
        'draws_per_feasible_branch': 5, 'games': ordered,
        'invalid_initial_branches': sum(branch['status'] != 'simulated' for branch in branches),
        'attempts': len(attempts), 'exhausted': sum(attempt['status'] == 'exhausted' for attempt in attempts),
        'elapsed_seconds': round(time.monotonic() - start, 3),
        'limitations': ['Actual-participant sets are oracle rosters, not known pre-game availability.',
                        'Focal home-player plays/sits status is synthetic and not a calibrated injury model.',
                        'Five first attempts per feasible branch do not establish retry bias or 10k runtimes.',
                        'F4 only; no protected 2026–27 actual outcomes are scored.'],
    }
    write_json(detail_path, details, pretty=True)
    write_json(args.output, {key: value for key, value in details.items() if key != 'games'} | {
        'game_count': len(ordered), 'details': str(detail_path), 'details_sha256': sha256_file(detail_path),
    }, pretty=True)


if __name__ == '__main__':
    main()
