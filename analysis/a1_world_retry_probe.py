#!/usr/bin/env python3
"""Reproduce isolated engine worlds around one deliberately injected retry on a fixed development game."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, sha256_file, write_json  # noqa: E402
from scripts import (a1_branch_world_probe, a1_lineup_branches, a1_substitution_world_audit,
                     a1_world_retry, backtest, engine)  # noqa: E402


class CapturedGame(Exception):
    pass


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', required=True)
    parser.add_argument('--worlds', type=int, default=3)
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.worlds < 2:
        raise ValueError('at least two isolated worlds are required')
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an experiment')
    panel = ROOT / 'data/derived/experiments/20261122_a1_s03_f4_game_ids.json'
    if args.game not in json.loads(panel.read_text()):
        raise ValueError('game is outside the frozen F4 panel')
    spec = ROOT / 'models/v1.2d.json'
    spec_data = json.loads(spec.read_text())
    features = ROOT / Path(spec_data['default']['features']).parent
    model_dir = ROOT / 'data/models/folds/v1.2d_F4_all'
    inputs = [panel, spec, features / 'pregame.parquet', features / 'team_pregame.parquet',
              DERIVED / 'history/2026/segments.parquet', DERIVED / 'history/2026/stints.parquet',
              DERIVED / 'history/2026/player_periods.csv.gz', DERIVED / 'teams.json', model_dir / 'config.json']
    inputs.extend(sorted((DERIVED / 'history').glob('*/on_court.parquet')))
    inputs.extend(sorted((ROOT / 'data/raw/hoopr').glob('player_box_*.parquet')))
    inputs.extend(sorted(model_dir.glob('*.txt')))
    input_hashes = {str(p.relative_to(ROOT)): sha256_file(p) for p in inputs}
    paths = [Path(__file__), ROOT / 'scripts/a1_world_retry.py', ROOT / 'scripts/a1_branch_world_probe.py',
             ROOT / 'scripts/a1_branch_foul_out.py', ROOT / 'scripts/a1_lineup_branches.py',
             ROOT / 'scripts/engine.py', ROOT / 'scripts/backtest.py', ROOT / 'scripts/minutes.py',
             ROOT / 'scripts/projection.py', ROOT / 'scripts/a1_substitution_world_audit.py']
    source_hashes = {str(p.relative_to(ROOT)): sha256_file(p) for p in paths}
    backtest._init('folds/v1.2d_F4_all', str(spec), 'F4', 1, rotation='targets', pool=0)
    eng = backtest._W['engine']
    if eng.rotation_policy is not None:
        raise ValueError('expected unchanged engine policy')
    simulate = eng.simulate
    result = {}

    def run(g: engine.Game, _worlds: int, _seed: int) -> dict:
        home = np.flatnonzero(g.side == 0)
        if len(home) < 6:
            raise ValueError('fixed game has fewer than six home participants')
        index = min(home, key=lambda i: (-g.expected[i], str(g.ids[i])))
        g.avail[index] = 0.5
        g.players['home'][index]['availability'] = 0.5
        branch = a1_lineup_branches.one_player(g, str(g.game['home_id']), str(g.ids[index]), True)
        calls = 0

        def replay(world: int, attempt: int, seed: int, *, inject: bool) -> dict:
            nonlocal calls
            start = time.monotonic()
            policy = a1_branch_world_probe.RepairedTrace()
            eng.rotation_policy = policy
            simulate(branch, 1, seed)
            data = policy.capture(branch, eng.last)
            audit = a1_substitution_world_audit.audit_worlds(data)
            calls += 1
            print(f'engine attempt {calls}: world {world}, attempt {attempt}, '
                  f'{time.monotonic() - start:.2f}s', flush=True)
            if inject and world == 1 and attempt == 0:
                raise a1_world_retry.RecoverableWorldError('deliberately injected after successful world audit')
            return {'capture': data, 'audit': audit}

        control = a1_world_retry.simulate_isolated(
            lambda w, a, s: replay(w, a, s, inject=False), worlds=args.worlds, seed=args.seed,
            attempts_per_world=3, max_rejections=3)
        retried = a1_world_retry.simulate_isolated(
            lambda w, a, s: replay(w, a, s, inject=True), worlds=args.worlds, seed=args.seed,
            attempts_per_world=3, max_rejections=3)
        for world in range(args.worlds):
            if world == 1:
                if retried.accepted_seeds[world] == control.accepted_seeds[world]:
                    raise ValueError('replacement used the rejected seed')
                continue
            a, b = control.worlds[world]['capture'], retried.worlds[world]['capture']
            if (control.accepted_seeds[world] != retried.accepted_seeds[world]
                    or a.keys() != b.keys() or any(not np.array_equal(a[k], b[k]) for k in a)):
                raise ValueError(f'world {world}: survivor changed after another world was retried')
        if len(retried.rejections) != 1 or len(retried.worlds) != args.worlds:
            raise ValueError('injected retry did not yield the expected valid world count')
        result.update({'selected_player': str(g.ids[index]), 'worlds': args.worlds, 'engine_attempts': calls,
                       'control_seeds': [str(s) for s in control.accepted_seeds],
                       'retry_seeds': [str(s) for s in retried.accepted_seeds],
                       'rejections': [{'world': r.world, 'attempt': r.attempt, 'seed': str(r.seed),
                                       'reason': r.reason} for r in retried.rejections],
                       'control_audits': [w['audit'] for w in control.worlds],
                       'retry_audits': [w['audit'] for w in retried.worlds]})
        raise CapturedGame()

    started = time.monotonic()
    try:
        with patch.object(eng, 'simulate', side_effect=run):
            backtest.run_game(args.game)
    except CapturedGame:
        pass
    if not result:
        raise ValueError('fixed game was not reached')
    if any(sha256_file(ROOT / name) != digest for name, digest in {**input_hashes, **source_hashes}.items()):
        raise ValueError('a fold input, source or model changed during the probe')
    write_json(args.output, {'kind': 'research synthetic-rejection wiring; not a forecast or promotion',
                             'population': 'fixed F4 game with actual participants; selected availability synthetic',
                             'game': args.game, 'model': 'folds/v1.2d_F4_all', 'seed': str(args.seed),
                             'result': result, 'elapsed_seconds': round(time.monotonic() - started, 3),
                             'sha256': source_hashes,
                             'input_sha256': input_hashes,
                             'limitations': ['Injected failure is not an observed foul-out.',
                                             'No rejection rate, bias or 10,000-world runtime has been measured.',
                                             'Single-world seeds differ from production vectorized streams.']}, pretty=True)


if __name__ == '__main__':
    main()
