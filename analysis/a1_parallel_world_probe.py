#!/usr/bin/env python3
"""Compare serial and process-parallel isolated engine worlds on the frozen F4 game."""
from __future__ import annotations

import argparse
import hashlib
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from analysis.a1_parallel_world_retry import simulate_parallel  # noqa: E402
from basketball_common import read_json, sha256_file, write_json  # noqa: E402
from scripts import (a1_branch_world_probe, a1_lineup_branches, a1_substitution_world_audit,  # noqa: E402
                     a1_world_retry, backtest)

_WORKER = {}


class CapturedGame(Exception):
    pass


def init_worker(game: str) -> None:
    backtest._init('folds/v1.2d_F4_all', str(ROOT / 'models/v1.2d.json'), 'F4', 1,
                   rotation='targets', pool=0)
    eng = backtest._W['engine']
    if eng.rotation_policy is not None:
        raise ValueError('expected unchanged engine policy')
    simulate = eng.simulate

    def prepare(g, _worlds, _seed):
        home = np.flatnonzero(g.side == 0)
        if len(home) < 6:
            raise ValueError('fixed game has fewer than six home participants')
        index = min(home, key=lambda i: (-g.expected[i], str(g.ids[i])))
        g.avail[index] = g.players['home'][index]['availability'] = 0.5
        branch = a1_lineup_branches.one_player(g, str(g.game['home_id']), str(g.ids[index]), True)
        _WORKER.update(engine=eng, simulate=simulate, branch=branch, player=str(g.ids[index]))
        raise CapturedGame()

    try:
        with patch.object(eng, 'simulate', side_effect=prepare):
            backtest.run_game(game)
    except CapturedGame:
        pass
    if not _WORKER:
        raise ValueError('fixed game was not reached')


def capture_digest(capture: dict[str, np.ndarray]) -> str:
    h = hashlib.sha256()
    for key, value in sorted(capture.items()):
        array = np.ascontiguousarray(value)
        h.update(f'{key}|{array.dtype.str}|{array.shape}\n'.encode())
        h.update(array.tobytes())
    return h.hexdigest()


def run_world(world: int, attempt: int, seed: int, *, inject: bool) -> dict:
    policy = a1_branch_world_probe.RepairedTrace()
    eng, branch = _WORKER['engine'], _WORKER['branch']
    eng.rotation_policy = policy
    _WORKER['simulate'](branch, 1, seed)
    capture = policy.capture(branch, eng.last)
    audit = a1_substitution_world_audit.audit_worlds(capture)
    if inject and world == 1 and attempt == 0:
        raise a1_world_retry.RecoverableWorldError('deliberately injected after successful world audit')
    return {'world': world, 'capture_sha256': capture_digest(capture), 'audit': audit}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--provenance', type=Path, required=True)
    parser.add_argument('--worlds', type=int, default=20)
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an experiment')
    if args.worlds < 2 or not 1 <= args.workers <= 4:
        raise ValueError('at least two worlds and one to four workers are required')
    provenance = read_json(args.provenance)
    if provenance['game'] != '401810327' or provenance['model'] != 'folds/v1.2d_F4_all':
        raise ValueError('expected fixed F4 game provenance')
    fingerprints = {**provenance['input_sha256'], **provenance['sha256']}
    if any(sha256_file(ROOT / name) != digest for name, digest in fingerprints.items()):
        raise ValueError('fixed-game source, input or model differs from its manifest')
    from functools import partial

    results = {}
    for workers in (1, args.workers):
        if workers in results:
            continue
        started = time.monotonic()
        with ProcessPoolExecutor(max_workers=workers, initializer=init_worker,
                                 initargs=(provenance['game'],)) as pool:
            control = simulate_parallel(partial(run_world, inject=False), pool, worlds=args.worlds,
                                        seed=args.seed, attempts_per_world=3, max_rejections=3, window=workers)
            retry = simulate_parallel(partial(run_world, inject=True), pool, worlds=args.worlds,
                                      seed=args.seed, attempts_per_world=3, max_rejections=3, window=workers)
        if len(retry.rejections) != 1 or retry.rejections[0].world != 1:
            raise ValueError('injected retry did not yield exactly one rejection')
        for index in range(args.worlds):
            if index == 1:
                if retry.accepted_seeds[index] == control.accepted_seeds[index]:
                    raise ValueError('replacement used the rejected seed')
            elif (retry.worlds[index] != control.worlds[index]
                  or retry.accepted_seeds[index] != control.accepted_seeds[index]):
                raise ValueError(f'world {index}: unrelated world changed after retry')
        results[workers] = {'seconds': round(time.monotonic() - started, 3), 'control': control, 'retry': retry}
        print(f'{workers} workers: {args.worlds} control and {args.worlds} retry worlds audited', flush=True)
    baseline = results[1]
    for workers, result in results.items():
        if result['control'] != baseline['control'] or result['retry'] != baseline['retry']:
            raise ValueError(f'{workers} workers: outputs differ from single worker')
    if any(sha256_file(ROOT / name) != digest for name, digest in fingerprints.items()):
        raise ValueError('fixed-game inputs or sources changed during the probe')
    write_json(args.output, {
        'kind': 'parallel isolated-world synthetic-rejection wiring; not a forecast or promotion',
        'game': provenance['game'], 'model': provenance['model'], 'worlds': args.worlds,
        'seed': str(args.seed), 'provenance': str(args.provenance), 'provenance_sha256': sha256_file(args.provenance),
        'source_sha256': {str(p.relative_to(ROOT)): sha256_file(p) for p in (
            Path(__file__), ROOT / 'analysis/a1_parallel_world_retry.py')},
        'worker_seconds': {str(k): v['seconds'] for k, v in results.items()},
        'control_seeds': [str(s) for s in baseline['control'].accepted_seeds],
        'retry_seeds': [str(s) for s in baseline['retry'].accepted_seeds],
        'control': baseline['control'].worlds, 'retry': baseline['retry'].worlds,
        'rejections': [{'world': r.world, 'attempt': r.attempt, 'seed': str(r.seed), 'reason': r.reason}
                       for r in baseline['retry'].rejections],
        'limitations': ['The rejection is deliberately injected, not an observed foul-out.',
                        'Captures are hashed but not persisted for independent replay.',
                        'No real failure rate, bias or 10,000-world runtime is measured.',
                        'Single-world seeds differ from production vectorized streams.'],
    }, pretty=True)


if __name__ == '__main__':
    main()
