#!/usr/bin/env python3
"""Capture and independently audit isolated one-player branches on a fixed development-fold game."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import sha256_file, write_json  # noqa: E402
from scripts import a1_lineup_branches, a1_substitution_world_audit, backtest, engine, projection  # noqa: E402


class TracePolicy:
    """Observe scheduled lineups without changing them or consuming random draws."""

    def __init__(self) -> None:
        self.counts: dict[str, int] = {}
        self.trace: list[dict[str, np.ndarray]] = []
        self.available = np.empty((0, 0), dtype=bool)

    def begin(self, g: engine.Game, worlds: int, available: np.ndarray, seed: int) -> None:
        self.available = available.copy()
        if self.available.shape != (worlds, g.n):
            raise ValueError('availability dimensions differ from game')

    def before_segment(self, g: engine.Game, st: engine.Worlds, active: np.ndarray,
                       scheduled: np.ndarray) -> np.ndarray:
        self.trace.append({
            'world': active.copy(), 'period': st.period[active].copy(), 'clock': st.clock[active].copy(),
            'lineups': scheduled.copy(), 'fouls': st.ingame['pf_so_far'][active[:, None, None], scheduled].copy(),
            'phase': np.zeros(len(active), dtype=np.int8),
        })
        return scheduled

    def after_fouls(self, g: engine.Game, st: engine.Worlds, active: np.ndarray,
                    offense: np.ndarray, defense: np.ndarray) -> bool:
        return False

    def finish(self, g: engine.Game, st: engine.Worlds) -> None:
        if not st.done.all() or not self.trace:
            raise ValueError('engine did not complete the captured worlds')

    def capture(self, g: engine.Game, st: engine.Worlds) -> dict[str, np.ndarray]:
        return {
            'game_id': np.asarray(str(g.game['game_id'])),
            'player_ids': np.asarray(g.ids, dtype=str), 'side': g.side.copy(),
            'available': self.available.copy(), 'final_period': st.period.copy(), 'final_score': st.score.copy(),
            'minutes': st.minutes.copy(), 'player_points': st.box['pts'].copy(),
            'player_fouls': st.box['pf'].copy(), 'team_points': st.pts.copy(),
            **{f'trace_{key}': np.concatenate([entry[key] for entry in self.trace])
               for key in ('world', 'period', 'clock', 'lineups', 'fouls', 'phase')},
        }


class CapturedGame(Exception):
    pass


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', required=True)
    parser.add_argument('--worlds', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--worlds-dir', type=Path, required=True)
    args = parser.parse_args()
    if not args.game.isascii() or not args.game.isdigit() or args.worlds < 1:
        raise ValueError('game must be an ASCII-digit ID and worlds must be positive')
    if args.output.exists() or args.worlds_dir.exists():
        raise FileExistsError('refusing to overwrite an existing report or world capture directory')
    ids = json.loads((ROOT / 'data/derived/experiments/20261122_a1_s03_f4_game_ids.json').read_text())
    if args.game not in ids:
        raise ValueError('game is outside the frozen F4 panel')
    spec = ROOT / 'models/v1.2d.json'
    backtest._init('folds/v1.2d_F4_all', str(spec), 'F4', args.worlds, rotation='targets', pool=0)
    eng = backtest._W['engine']
    if eng.rotation_policy is not None:
        raise ValueError('probe requires the unchanged control policy')
    simulate = eng.simulate
    records: list[dict] = []
    args.worlds_dir.mkdir(parents=True)

    def run_branches(g: engine.Game, worlds: int, _seed: int) -> dict:
        home = np.flatnonzero(g.side == 0)
        if len(home) < 6:
            raise ValueError('fixed game has fewer than six home participants')
        index = min(home, key=lambda i: (-g.expected[i], str(g.ids[i])))
        player, team = str(g.ids[index]), str(g.game['home_id'])
        g.avail[index] = 0.5
        g.players['home'][int(index)]['availability'] = 0.5
        for plays in (True, False):
            label = 'plays' if plays else 'sits'
            branch_id = f'lineup-v1:{team}/{player}={label}'
            seed = projection.seed_for('lineup-v1', engine.ENGINE['id'], g.day, g.day, args.game, branch_id)
            branch = a1_lineup_branches.one_player(g, team, player, plays)
            eng.rotation_policy = None
            simulate(branch, worlds, seed)
            reference = eng.last
            expected = {key: value.copy() for key, value in {
                'score': reference.score, 'pts': reference.pts, 'minutes': reference.minutes,
                'period': reference.period, **{f'box_{key}': value for key, value in reference.box.items()},
            }.items()}
            policy = TracePolicy()
            eng.rotation_policy = policy
            simulate(branch, worlds, seed)
            state = eng.last
            actual = {'score': state.score, 'pts': state.pts, 'minutes': state.minutes,
                      'period': state.period, **{f'box_{key}': value for key, value in state.box.items()}}
            if any(not np.array_equal(expected[key], actual[key]) for key in expected):
                raise ValueError('tracing changed the simulated outputs')
            capture = policy.capture(branch, state)
            path = args.worlds_dir / f'{label}.npz'
            np.savez_compressed(path, **capture)
            record = {'branch_id': branch_id, 'seed': str(seed), 'worlds': worlds,
                      'trace_preserves_outputs': True, 'capture': str(path), 'capture_sha256': sha256_file(path)}
            try:
                record['audit'] = a1_substitution_world_audit.audit_worlds(capture)
            except ValueError as exc:
                record['audit_error'] = str(exc)
            records.append(record)
        raise CapturedGame()

    try:
        with patch.object(eng, 'simulate', side_effect=run_branches):
            backtest.run_game(args.game)
    except CapturedGame:
        pass
    if len(records) != 2:
        raise ValueError('probe did not complete both branches')
    paths = (Path(__file__), ROOT / 'scripts/a1_lineup_branches.py', ROOT / 'scripts/engine.py',
             ROOT / 'scripts/a1_substitution_world_audit.py', spec,
             ROOT / 'data/models/folds/v1.2d_F4_all/config.json')
    write_json(args.output, {
        'population': 'fixed F4 game with actual participants; selected availability is synthetic',
        'game': args.game, 'model': 'folds/v1.2d_F4_all', 'records': records,
        'sha256': {str(path.relative_to(ROOT)): sha256_file(path) for path in paths},
    }, pretty=True)
    for record in records:
        print(f"{record['branch_id']}: {record.get('audit_error', 'audit passed')}", flush=True)
    if any('audit_error' in record for record in records):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
