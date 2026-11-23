#!/usr/bin/env python3
"""Backtest the isolated vectorized matched-penalty candidate against fixed F4 games."""
from __future__ import annotations

import argparse
import os
import resource
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from analysis import a1_vector_matched_penalty as candidate  # noqa: E402
from basketball_common import read_json, sha256_file, write_json  # noqa: E402
from scripts import backtest  # noqa: E402

CONTROL = '20261122T022323Z_a1_s01_control'
PROBE = ROOT / 'analysis/experiments/20261123_a1_vector_matched_penalty_probe_v1.json'
PANEL = ROOT / 'data/derived/experiments/20261122_a1_s03_f4_game_ids.json'
PILOT = ROOT / 'analysis/experiments/20261122_a1_reproduction_games.json'


def init_worker():
    backtest._init('folds/v1.2d_F4_all', str(ROOT / 'models/v1.2d.json'), 'F4', 1000,
                   rotation='targets', pool=0)


def game(gid, directory):
    eng = backtest._W['engine']
    original = eng.simulate
    policy = candidate.VectorMatchedPenaltyTrace()
    eng.rotation_policy = policy

    def simulate(g, worlds, seed):
        result = original(g, worlds, seed)
        capture = policy.capture(g, eng.last)
        for key in ('oreb', 'dreb', 'ast', 'fg3m'):
            capture[f'player_{key}'] = eng.last.box[key].copy()
        path = Path(directory) / f'{gid}.npz'
        if path.exists():
            raise FileExistsError('refusing to overwrite a world capture')
        np.savez_compressed(path, **capture)
        return result

    try:
        with patch.object(eng, 'simulate', side_effect=simulate):
            result = backtest.run_game(gid)
    finally:
        eng.rotation_policy = None
    path = Path(directory) / f'{gid}.npz'
    if not path.is_file():
        raise ValueError(f'{gid}: missing candidate capture')
    peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform != 'darwin':
        peak_rss *= 1024
    return result, {'game': gid, 'capture': str(path), 'sha256': sha256_file(path),
                    'technical_events': len(policy.technical_events), 'worker_pid': os.getpid(),
                    'worker_peak_rss_bytes': int(peak_rss)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True, help='fresh experiment slug')
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument('--pilot', action='store_true', help='use the fixed three-game wiring panel')
    selection.add_argument('--scaling', action='store_true', help='use ten fixed games for runtime measurement')
    parser.add_argument('--jobs', type=int, default=4, help='single-thread workers, at most ten')
    args = parser.parse_args()
    if not args.name or not all(c.isascii() and (c.isalnum() or c in '-_') for c in args.name):
        raise ValueError('name must contain only ASCII letters, digits, hyphens or underscores')
    if not 1 <= args.jobs <= 10:
        raise ValueError('jobs must be between 1 and 10')
    if any(os.environ.get(name) != '1' for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS')):
        raise ValueError('set OMP_NUM_THREADS=1 and OPENBLAS_NUM_THREADS=1')
    derived, experiments = ROOT / 'data/derived/experiments', ROOT / 'analysis/experiments'
    world_dir = derived / f'{args.name}_worlds'
    paths = [world_dir, derived / f'{args.name}.parquet', derived / f'{args.name}_players.parquet',
             experiments / f'{args.name}.json']
    if any(path.exists() for path in paths):
        raise FileExistsError('refusing to overwrite experiment files')
    probe = read_json(PROBE)
    if probe['worlds'] != 1000 or probe['failed_first_seeds'] != 190:
        raise ValueError('single-world wiring population differs')
    fingerprints = dict(probe['fingerprints'])
    sources = (PROBE, PANEL, PILOT, ROOT / f'analysis/experiments/{CONTROL}.json',
               derived / f'{CONTROL}.parquet', derived / f'{CONTROL}_players.parquet',
               Path(__file__), ROOT / 'analysis/a1_vector_penalty_backtest_audit.py')
    for path in sources:
        fingerprints[str(path.relative_to(ROOT))] = sha256_file(path)

    def verify():
        if any(sha256_file(ROOT / name) != digest for name, digest in fingerprints.items()):
            raise ValueError('source, control, model or input changed')

    verify()
    ids = read_json(PILOT if args.pilot else PANEL)
    if args.scaling:
        ids = sorted(ids)[:10]
    if len(ids) != (3 if args.pilot else 10 if args.scaling else 200) or len(set(ids)) != len(ids):
        raise ValueError('fixed panel differs')
    control = read_json(experiments / f'{CONTROL}.json')
    if (control['fold'] != 'F4' or control['worlds'] != 1000 or control['rotation'] != 'targets'
            or control['pool'] != 0 or control['simulation_stream'] is not None
            or control['seed_key'] is not None or not set(ids) <= set(control['game_ids'])):
        raise ValueError('control is not the fixed comparable backtest')
    world_dir.mkdir(parents=True)
    start = time.monotonic()
    results, captures, peaks = {}, {}, {}
    with ProcessPoolExecutor(max_workers=args.jobs, initializer=init_worker) as pool:
        futures = {pool.submit(game, gid, str(world_dir)): gid for gid in ids}
        for future in as_completed(futures):
            result, capture = future.result()
            gid = futures[future]
            if result['game_id'] != gid or capture['game'] != gid:
                raise ValueError('worker returned the wrong game')
            pid = capture.pop('worker_pid')
            peaks[pid] = max(peaks.get(pid, 0), capture['worker_peak_rss_bytes'])
            results[gid], captures[gid] = result, capture
            if len(results) % (1 if args.pilot or args.scaling else 20) == 0:
                print(f'{len(results)}/{len(ids)} games in {time.monotonic() - start:.1f}s', flush=True)
    verify()
    ordered = [results[gid] for gid in sorted(ids)]
    players = pd.DataFrame([row for result in ordered for row in result.pop('players')])
    games = pd.DataFrame(ordered)
    games.to_parquet(paths[1], index=False)
    players.to_parquet(paths[2], index=False)
    write_json(paths[3], {
        'experiment': 'isolated F4 matched-penalty backtest; not a forecast or promotion',
        'run': args.name, 'config': 'models/v1.2d.json', 'fold': 'F4',
        'models': 'folds/v1.2d_F4_all', 'games': len(ids), 'worlds': 1000,
        'rotation': 'targets', 'known_starters': False, 'pool': 0, 'simulation_stream': None,
        'seed_key': None, 'game_ids': sorted(ids), 'control': CONTROL, 'pilot': args.pilot,
        'scaling': args.scaling, 'workers': args.jobs, 'workers_observed': len(peaks),
        'sum_worker_peak_rss_upper_bound_bytes': sum(peaks.values()),
        'memory_limitation': 'Sum of per-worker high-water RSS; excludes parent, OS and other processes.',
        'game_rows_sha256': sha256_file(paths[1]),
        'player_rows_sha256': sha256_file(paths[2]), 'captures': [captures[gid] for gid in sorted(ids)],
        'fingerprints': fingerprints, 'elapsed_seconds': round(time.monotonic() - start, 3),
        'limitations': ['Actual-participant oracle rosters are not pre-game availability forecasts.',
                        'Vectorized world draws share engine RNG; equal starting seeds are not paired paths.',
                        'F4 diagnostic only; not a promotion or protected-season evaluation.'],
    }, pretty=True)


if __name__ == '__main__':
    main()
