#!/usr/bin/env python3
"""Replay the isolated S06 policy and capture selected-timeout state responses."""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, atomic_bytes, sha256_file, write_json  # noqa: E402
from scripts import (a1_compare, a1_flow_compare, a1_foul_penalty_engine, a1_substitution_engine,
                     backtest)  # noqa: E402
from scripts.evaluate import EXPERIMENTS  # noqa: E402

REPORT = EXPERIMENTS / '20261122_a1_s06_engine_models_F4.json'
CONFIG = ROOT / 'models/v1.2d.json'
MODEL = 'folds/v1.2d_F4_all'
DIMENSIONS = {
    'margin': ('behind_15_plus', 'ahead_15_plus', 'close_5_or_less', 'intermediate'),
    'period': ('1', '2', '3', '4', 'OT'),
    'foul_trouble': ('no', 'yes'),
    'duration': ('under_4', '4_to_under_8', '8_plus'),
}


def state_codes(period: np.ndarray, margin: np.ndarray, fouls: np.ndarray,
                duration: np.ndarray) -> dict[str, np.ndarray]:
    if (period.shape != margin.shape or period.shape != fouls.shape or period.shape != duration.shape
            or not np.isfinite(period).all() or not np.equal(period, np.floor(period)).all()
            or not np.isfinite(margin).all() or not np.isfinite(fouls).all()
            or not np.isfinite(duration).all() or (period < 1).any() or (fouls < 0).any()
            or (duration < 0).any()):
        raise ValueError('invalid simulated timeout-state values')
    return {
        'margin': np.select([margin <= -15, margin >= 15, np.abs(margin) <= 5], [0, 1, 2], default=3),
        'period': np.minimum(period - 1, 4).astype(int),
        'foul_trouble': (fouls >= np.minimum(5, period + 1)).astype(int),
        'duration': np.select([duration < 240, duration < 480], [0, 1], default=2),
    }


class CapturedPolicy(a1_foul_penalty_engine.PlayerFoulPenaltyPolicy):
    def __init__(self, outgoing, incoming, timing, features, roles):
        super().__init__(outgoing, incoming, timing, features)
        self.roles = roles

    def begin(self, g, worlds, available, seed) -> None:
        super().begin(g, worlds, available, seed)
        self.state_counts = np.zeros((g.n, sum(map(len, DIMENSIONS.values())), 2), dtype=np.int64)
        gid = str(g.game.get('game_id', g.game.get('id', '')))
        self.capture_ids = list(map(str, g.ids))
        self.capture_tiers = [self.roles.get((gid, str(player)), 'unknown') for player in g.ids]
        if not set(self.capture_tiers).issubset(a1_compare.ROLE_TIERS):
            raise ValueError('unrecognised captured pregame tier')

    def _apply_timeouts(self, g, st, due: np.ndarray) -> None:
        worlds, sides = np.repeat(due, 2), np.tile(np.arange(2), len(due))
        before = self.current[worlds, sides].copy()
        flat_worlds, flat_sides, flat_players = np.repeat(worlds, 5), np.repeat(sides, 5), before.reshape(-1)
        now = a1_substitution_engine.elapsed(st.period[flat_worlds], st.clock[flat_worlds])
        values = self._numeric(st, flat_worlds, flat_sides, flat_players, now, rest=False)
        codes = state_codes(values[0], values[2], values[3], values[5])
        super()._apply_timeouts(g, st, due)
        after = self.current[worlds, sides]
        exited = ~(before[:, :, None] == after[:, None, :]).any(axis=2).reshape(-1)
        offset = 0
        for dimension, labels in DIMENSIONS.items():
            index = offset + codes[dimension]
            np.add.at(self.state_counts[:, :, 0], (flat_players, index), 1)
            np.add.at(self.state_counts[:, :, 1], (flat_players, index), exited.astype(int))
            offset += len(labels)


def init_worker() -> None:
    backtest._init(MODEL, str(CONFIG), 'F4', 1000, 'targets', False, 0,
                   None, None, False, 'control', False, None, False, False)
    outgoing, incoming, timing = a1_substitution_engine.load_candidate(REPORT, 'F4')
    features = a1_substitution_engine.load_features('F4')
    profiles = backtest._W['inputs'][0]
    if profiles.duplicated(['game_id', 'player']).any():
        raise ValueError('captured pregame profiles have duplicate keys')
    usage = pd.to_numeric(profiles['usage'], errors='raise').to_numpy(dtype=float)
    starts = pd.to_numeric(profiles['start_share'], errors='raise').to_numpy(dtype=float)
    if (np.isinf(usage) | (usage < 0) | (usage > 1)
            | np.isinf(starts) | (starts < 0) | (starts > 1)).any():
        raise ValueError('captured pregame usage or start share is invalid')
    known = np.isfinite(usage) & np.isfinite(starts)
    tiers = np.select([~known, usage >= 0.25, starts >= 0.5], ['unknown', 'star', 'starter'], default='bench')
    roles = {(str(game), str(player)): tier
             for game, player, tier in zip(profiles['game_id'], profiles['player'], tiers)}
    backtest._W['engine'].rotation_policy = CapturedPolicy(outgoing, incoming, timing, features, roles)


def capture_game(game_id: str) -> tuple[dict, list[dict], list[dict]]:
    result = backtest.run_game(game_id)
    players = result.pop('players')
    policy = backtest._W['engine'].rotation_policy
    counts = policy.state_counts
    if counts.shape[0] != len(policy.capture_tiers):
        raise ValueError('captured role and state arrays differ')
    rows = []
    offset = 0
    for dimension, labels in DIMENSIONS.items():
        for index, value in enumerate(labels):
            for player in np.flatnonzero(counts[:, offset + index, 0]):
                decisions, exits = counts[player, offset + index]
                rows.append({'game_id': game_id, 'player': policy.capture_ids[player],
                             'tier': policy.capture_tiers[player], 'dimension': dimension, 'value': value,
                             'decisions': int(decisions), 'exits': int(exits)})
        offset += len(labels)
    if any(int(counts[:, start:start + len(labels), 0].sum()) != 5 * policy.counts['timeout_team_windows']
           or int(counts[:, start:start + len(labels), 1].sum()) != policy.counts['timeout_outgoing']
           for start, labels in offsets()):
        raise ValueError('captured state decisions do not reconcile with policy counters')
    return result, players, rows


def offsets():
    offset = 0
    for labels in DIMENSIONS.values():
        yield offset, labels
        offset += len(labels)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', help='same-policy fixed backtest to reproduce')
    parser.add_argument('--jobs', type=int, default=4)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--rows-output', type=Path, required=True)
    args = parser.parse_args()
    if (args.output.exists() or args.rows_output.exists()
            or args.output.resolve() == args.rows_output.resolve() or args.jobs < 1):
        raise ValueError('capture outputs must be distinct/new and jobs must be positive')
    ref_log = EXPERIMENTS / f'{args.reference}.json'
    log = json.loads(ref_log.read_text())
    candidate = log.get('substitution_candidate', {})
    if (log['fold'] != 'F4' or log['worlds'] != 1000 or log['models'] != MODEL
            or log['rotation'] != 'targets' or log['known_starters'] or log['pool'] != 0
            or not candidate.get('foul_penalty_exception')
            or candidate.get('report') != str(REPORT.relative_to(ROOT))):
        raise ValueError('reference is not the fixed S06 foul-penalty candidate')
    for path, digest in candidate.get('sha256', {}).items():
        if sha256_file(ROOT / path) != digest:
            raise ValueError(f'candidate source differs from the reference run: {path}')
    ids = log['game_ids']
    if not ids or len(ids) != len(set(ids)) or len(ids) != log['games']:
        raise ValueError('reference game IDs are invalid')
    started = time.monotonic()
    print(f'capturing {len(ids)} matched games × 1000 worlds with {args.jobs} workers', flush=True)
    results = []
    with mp.get_context('spawn').Pool(args.jobs, initializer=init_worker) as pool:
        for index, result in enumerate(pool.imap(capture_game, ids, chunksize=1), 1):
            results.append(result)
            if index % min(10, max(1, len(ids) // 10)) == 0 or index == len(ids):
                print(f'game {index}/{len(ids)} {time.monotonic() - started:.0f}s', flush=True)
    games = pd.DataFrame([result[0] for result in results])
    players = pd.DataFrame([row for result in results for row in result[1]])
    cells = pd.DataFrame([row for result in results for row in result[2]])
    old_games = pd.read_parquet(DERIVED / 'experiments' / f'{args.reference}.parquet')
    old_players = pd.read_parquet(DERIVED / 'experiments' / f'{args.reference}_players.parquet')
    if set(games.columns) - set(old_games.columns) or set(players.columns) - set(old_players.columns):
        raise ValueError('capture has a saved column absent from its same-policy reference')
    game_checks = a1_flow_compare.exact_reproduction(old_games[games.columns], games, ['game_id'])
    player_checks = a1_flow_compare.exact_reproduction(old_players[players.columns], players, ['game_id', 'player'])
    if cells.empty or cells.duplicated(['game_id', 'player', 'dimension', 'value']).any():
        raise ValueError('captured timeout cells are empty or duplicated')
    atomic_bytes(args.rows_output, cells.to_parquet(index=False))
    inputs = [Path(__file__), ROOT / 'scripts/a1_substitution_engine.py',
              ROOT / 'scripts/a1_foul_penalty_engine.py', ROOT / 'scripts/backtest.py',
              ROOT / 'scripts/engine.py', CONFIG, REPORT, ref_log,
              DERIVED / 'experiments' / f'{args.reference}.parquet',
              DERIVED / 'experiments' / f'{args.reference}_players.parquet']
    report = {
        'experiment': 'a1_s06_state_conditioned_capture', 'reference': args.reference,
        'games': len(ids), 'worlds_per_game': 1000, 'game_values_reproduced': game_checks,
        'player_values_reproduced': player_checks, 'captured_cells': len(cells),
        'seconds': round(time.monotonic() - started, 1),
        'limitations': 'Selected simulated timeout opportunities and actual-participant rosters are not an '
                       'exhaustive stoppage process or a pre-game availability forecast.',
        'input_sha256': {str(path.relative_to(ROOT)): sha256_file(path) for path in inputs},
        'output_sha256': {str(args.rows_output.resolve().relative_to(ROOT)): sha256_file(args.rows_output)},
    }
    write_json(args.output, report, pretty=True)
    print(f'captured {len(cells)} player-state cells; reproduced {game_checks} game and {player_checks} player values')


if __name__ == '__main__':
    main()
