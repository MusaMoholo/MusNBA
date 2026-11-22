#!/usr/bin/env python3
"""Stress isolated retries with an intentionally five-player development-game roster."""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import read_json, sha256_file, write_json  # noqa: E402
from scripts import (a1_branch_world_probe, a1_lineup_branches, a1_substitution_world_audit,
                     a1_world_retry, backtest, engine)  # noqa: E402


class CapturedGame(Exception):
    pass


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--provenance', type=Path, required=True)
    parser.add_argument('--worlds', type=int, required=True)
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--attempts-per-world', type=int, required=True)
    parser.add_argument('--max-rejections', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an experiment')
    provenance = read_json(args.provenance)
    if provenance['game'] != '401810327' or provenance['model'] != 'folds/v1.2d_F4_all':
        raise ValueError('stress probe requires the fixed F4 provenance')
    fingerprints = {**provenance['input_sha256'], **provenance['sha256']}
    if any(sha256_file(ROOT / name) != digest for name, digest in fingerprints.items()):
        raise ValueError('fixed-game source, input or model differs from its manifest')
    backtest._init('folds/v1.2d_F4_all', str(ROOT / 'models/v1.2d.json'), 'F4', 1,
                   rotation='targets', pool=0)
    eng = backtest._W['engine']
    if eng.rotation_policy is not None:
        raise ValueError('expected unchanged engine policy')
    simulate = eng.simulate
    result = {}

    def run(g: engine.Game, _worlds: int, _seed: int) -> dict:
        if g.mstate is None:
            raise ValueError('stress game needs D29 minute states')
        side_index = 1
        indices = np.flatnonzero(g.side == side_index)
        if len(indices) < 6:
            raise ValueError('stress game needs at least six away participants')
        selected = sorted(indices, key=lambda i: (-g.expected[i], str(g.ids[i])))[:5]
        kept = set(selected)
        side_start = int(indices[0])
        for index in indices:
            available = 1.0 if index in kept else 0.0
            g.avail[index] = available
            g.players['away'][index - side_start]['availability'] = available
            if index in kept:
                g.mstate[index].update(healthy=48.0, cap=48.0, priority=48.0, ramp=1.0, rotation=1.0)
        focal = int(selected[0])
        g.avail[focal] = g.players['away'][focal - side_start]['availability'] = 0.5
        branch = a1_lineup_branches.one_player(g, str(g.game['away_id']), str(g.ids[focal]), True)
        attempts = 0

        def replay(world: int, attempt: int, seed: int) -> dict:
            nonlocal attempts
            attempts += 1
            policy = a1_branch_world_probe.RepairedTrace()
            eng.rotation_policy = policy
            try:
                simulate(branch, 1, seed)
            finally:
                print(f'attempt {attempts}: target world {world}, attempt {attempt}', flush=True)
            data = policy.capture(branch, eng.last)
            return a1_substitution_world_audit.audit_worlds(data)

        try:
            accepted = a1_world_retry.simulate_isolated(
                replay, worlds=args.worlds, seed=args.seed, attempts_per_world=args.attempts_per_world,
                max_rejections=args.max_rejections)
        except a1_world_retry.RetryLimitExceeded as exc:
            result.update({'status': 'retry limit exceeded',
                           'rejections': [{'world': r.world, 'attempt': r.attempt, 'seed': str(r.seed),
                                           'reason': r.reason} for r in exc.rejections],
                           'attempts': attempts, 'kept_away_player_ids': [str(g.ids[i]) for i in selected]})
        else:
            result.update({'status': 'complete', 'worlds': len(accepted.worlds),
                           'accepted_seeds': [str(s) for s in accepted.accepted_seeds],
                           'rejections': [{'world': r.world, 'attempt': r.attempt, 'seed': str(r.seed),
                                           'reason': r.reason} for r in accepted.rejections],
                           'audits': accepted.worlds, 'attempts': attempts,
                           'kept_away_player_ids': [str(g.ids[i]) for i in selected]})
        raise CapturedGame()

    started = time.monotonic()
    try:
        with patch.object(eng, 'simulate', side_effect=run):
            backtest.run_game(provenance['game'])
    except CapturedGame:
        pass
    if not result:
        raise ValueError('fixed game was not reached')
    if any(sha256_file(ROOT / name) != digest for name, digest in fingerprints.items()):
        raise ValueError('a source, input or model changed during the stress probe')
    write_json(args.output, {
        'kind': 'artificial five-player roster and 48-minute roles; not an NBA failure-rate estimate',
        'game': provenance['game'], 'model': provenance['model'], 'seed': str(args.seed),
        'attempts_per_world': args.attempts_per_world, 'max_rejections': args.max_rejections,
        'provenance': str(args.provenance), 'provenance_sha256': sha256_file(args.provenance),
        'analysis_sha256': sha256_file(Path(__file__)), 'elapsed_seconds': round(time.monotonic() - started, 3),
        'result': result, 'limitations': ['Roster deliberately restricted to five players with synthetic 48-minute roles.',
                                          'Not a realistic failure-rate, bias or predictive comparison.',
                                          'Short-roster foul-penalty exception remains unsupported.'],
    }, pretty=True)
    if result['status'] != 'complete':
        raise SystemExit('retry limit exceeded; failure evidence saved')
    print(f"{result['worlds']} valid worlds, {len(result['rejections'])} rejected attempts", flush=True)


if __name__ == '__main__':
    main()
