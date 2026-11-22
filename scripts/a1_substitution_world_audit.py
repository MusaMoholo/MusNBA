#!/usr/bin/env python3
"""Independently replay saved S06 lineups and reconcile every world's minutes and points."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Mapping

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, sha256_file, write_json  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS  # noqa: E402


def audit_worlds(data: Mapping[str, np.ndarray]) -> dict:
    ids, side = data['player_ids'], data['side']
    available, final_period = data['available'], data['final_period']
    minutes, player_points = data['minutes'], data['player_points']
    player_fouls, team_points, final_score = data['player_fouls'], data['team_points'], data['final_score']
    world, period, clock = data['trace_world'], data['trace_period'], data['trace_clock']
    fives, fouls, phase = data['trace_lineups'], data['trace_fouls'], data['trace_phase']
    if available.ndim != 2 or available.dtype != bool:
        raise ValueError('world availability must be a boolean world-by-player array')
    n_worlds, n_players = available.shape
    if not n_worlds or not n_players or side.shape != (n_players,) or ids.shape != (n_players,):
        raise ValueError('empty or inconsistent world roster')
    if len(set(ids.tolist())) != n_players or not np.isin(side, (0, 1)).all():
        raise ValueError('player IDs must be unique and each player must have a valid side')
    if (available[:, side == 0].sum(axis=1) < 5).any() or (available[:, side == 1].sum(axis=1) < 5).any():
        raise ValueError('a world starts with fewer than five available players')
    expected_player_shape = (n_worlds, n_players, 5)
    if (minutes.shape != expected_player_shape or player_points.shape != expected_player_shape
            or player_fouls.shape != expected_player_shape or team_points.shape != (n_worlds, 2, 5)
            or final_score.shape != (n_worlds, 2) or final_period.shape != (n_worlds,)):
        raise ValueError('saved world accounting arrays have inconsistent shapes')
    if (not np.issubdtype(final_period.dtype, np.integer) or (final_period < 4).any()
            or not np.isfinite(minutes).all() or (minutes < 0).any()
            or not np.isfinite(player_points).all() or (player_points < 0).any()
            or not np.isfinite(player_fouls).all() or (player_fouls < 0).any()
            or not np.isfinite(team_points).all() or (team_points < 0).any()
            or not np.isfinite(final_score).all()):
        raise ValueError('saved world accounting contains invalid values')
    if (minutes[~available] != 0).any() or (player_points[~available] != 0).any() or (player_fouls[~available] != 0).any():
        raise ValueError('an unavailable player accumulated minutes, points or fouls')
    if (player_fouls.sum(axis=2) > 6).any():
        raise ValueError('a player accumulated more than six personal fouls')

    n_trace = len(world)
    if (not n_trace or not np.issubdtype(world.dtype, np.integer) or not np.issubdtype(period.dtype, np.integer)
            or period.shape != (n_trace,) or clock.shape != (n_trace,) or phase.shape != (n_trace,)
            or fives.shape != (n_trace, 2, 5) or fouls.shape != fives.shape
            or not np.issubdtype(fives.dtype, np.integer)):
        raise ValueError('lineup trace arrays have inconsistent shapes or types')
    if ((world < 0) | (world >= n_worlds)).any() or ((fives < 0) | (fives >= n_players)).any():
        raise ValueError('lineup trace contains an invalid world or player index')
    if ((period < 1) | (period > final_period[world])).any() or not np.isin(phase, (0, 1)).all():
        raise ValueError('lineup trace has an invalid period or phase')
    length = np.where(period <= 4, 720.0, 300.0)
    if not np.isfinite(clock).all() or ((clock < 0) | (clock > length)).any():
        raise ValueError('lineup trace has an invalid game clock')
    if not np.isfinite(fouls).all() or ((fouls < 0) | (fouls >= 6)).any():
        raise ValueError('lineup trace contains a disqualified player')
    if (np.diff(np.sort(fives, axis=2), axis=2) == 0).any():
        raise ValueError('lineup trace contains fewer than five distinct players')
    expected_side = np.broadcast_to(np.array([0, 1])[None, :, None], fives.shape)
    if not np.array_equal(side[fives], expected_side) or not available[world[:, None, None], fives].all():
        raise ValueError('lineup trace uses a wrong-side or unavailable player')
    final_fouls = player_fouls.sum(axis=2)
    if (fouls > final_fouls[world[:, None, None], fives]).any():
        raise ValueError('trace foul count exceeds the recorded final foul count')

    start = np.where(period <= 4, (period - 1) * 720.0, 2880.0 + (period - 5) * 300.0)
    elapsed = start + length - clock
    order = np.argsort(world, kind='stable')
    world, period, phase = world[order], period[order], phase[order]
    elapsed, start, length, fives = elapsed[order], start[order], length[order], fives[order]
    first = np.r_[True, world[1:] != world[:-1]]
    last = np.r_[world[1:] != world[:-1], True]
    if (np.bincount(world, minlength=n_worlds) == 0).any():
        raise ValueError('a simulated world has no lineup trace')
    if (phase[first] != 0).any() or not np.allclose(elapsed[first], 0, atol=1e-8, rtol=0):
        raise ValueError('each world must begin with a traced opening lineup')
    previous_phase = np.r_[-1, phase[:-1]]
    if ((phase == 1) & (first | (previous_phase != 0))).any():
        raise ValueError('a post-foul lineup lacks its preceding segment lineup')
    if (period[last] != final_period[world[last]]).any():
        raise ValueError('a world trace does not reach its final period')
    period_start = (phase == 0) & np.isclose(elapsed, start, atol=1e-8, rtol=0)
    for number in range(1, int(final_period.max()) + 1):
        present = np.bincount(world[period_start & (period == number)], minlength=n_worlds) > 0
        if not present[final_period >= number].all():
            raise ValueError(f'a world has no traced start for period {number}')
    ends = np.where(last, 2880.0 + 300.0 * (final_period[world] - 4),
                    np.r_[elapsed[1:], 0.0])
    duration = ends - elapsed
    if (duration < -1e-8).any() or (ends > start + length + 1e-8).any():
        raise ValueError('lineup trace is out of order or skips a period boundary')
    duration = np.maximum(duration, 0)
    replayed = np.zeros_like(minutes)
    bucket = np.minimum(period - 1, 4)
    np.add.at(replayed, (world[:, None, None], fives, bucket[:, None, None]), duration[:, None, None] / 60)
    max_error = float(np.max(np.abs(replayed - minutes)))
    if max_error > 1e-5:
        raise ValueError(f'lineup-replayed player minutes differ from saved minutes by {max_error:.9g}')

    expected_minutes = np.column_stack([np.full(n_worlds, 60.0)] * 4 + [25.0 * (final_period - 4)])
    for team in (0, 1):
        actual_minutes = minutes[:, side == team].sum(axis=1)
        if not np.allclose(actual_minutes, expected_minutes, atol=1e-5, rtol=0):
            raise ValueError(f'side {team}: player minutes do not equal five-player period time')
        if not np.array_equal(player_points[:, side == team].sum(axis=1), team_points[:, team]):
            raise ValueError(f'side {team}: player points do not equal team period points')
    if not np.array_equal(team_points.sum(axis=2), final_score) or (final_score[:, 0] == final_score[:, 1]).any():
        raise ValueError('team period points do not reconcile to a non-tied final score')
    return {
        'game_id': str(data['game_id'].item()),
        'worlds': n_worlds,
        'players': n_players,
        'lineup_snapshots': n_trace,
        'post_foul_snapshots': int((phase == 1).sum()),
        'lineup_fives_checked': 2 * n_trace,
        'overtime_worlds': int((final_period > 4).sum()),
        'max_replayed_player_minute_error': max_error,
    }


def audit_run(run: str) -> dict:
    log_path = EXPERIMENTS / f'{run}.json'
    log = json.loads(log_path.read_text())
    if log['fold'] not in FOLDS or 'substitution_world_audit' not in log:
        raise ValueError('run is not a captured development-fold substitution candidate')
    files = log['substitution_world_audit']['world_sha256']
    frame_path = DERIVED / 'experiments' / f'{run}.parquet'
    player_path = DERIVED / 'experiments' / f'{run}_players.parquet'
    games, players = pd.read_parquet(frame_path), pd.read_parquet(player_path)
    if games['game_id'].duplicated().any() or players.duplicated(['game_id', 'player']).any():
        raise ValueError('saved backtest game or player keys are duplicated')
    records = []
    checked_players = 0
    for relative, digest in sorted(files.items()):
        path = ROOT / relative
        if sha256_file(path) != digest:
            raise ValueError(f'world capture fingerprint differs: {relative}')
        with np.load(path, allow_pickle=False) as data:
            record = audit_worlds(data)
            gid = record['game_id']
            match = games[games['game_id'] == gid]
            if len(match) != 1 or record['worlds'] != log['worlds']:
                raise ValueError(f'{gid}: world capture does not match the saved game')
            game = match.iloc[0]
            for side, index in (('home', 0), ('away', 1)):
                mean = float(data['final_score'][:, index].mean())
                if not np.isclose(mean, float(game[f'{side}_sim']), atol=1e-10, rtol=0):
                    raise ValueError(f'{gid}: captured {side} scores differ from backtest means')
            for q in range(4):
                points = data['team_points'][:, :, q].mean(axis=0)
                for label, value in (('total', points.sum()), ('margin', points[0] - points[1])):
                    if not np.isclose(value, float(game[f'q{q + 1}_{label}_sim']), atol=1e-10, rtol=0):
                        raise ValueError(f'{gid}: captured quarter {q + 1} {label} differs from backtest')
            ids = data['player_ids'].tolist()
            indices = {player: index for index, player in enumerate(ids)}
            for row in players[players['game_id'] == gid].itertuples(index=False):
                if row.player not in indices:
                    raise ValueError(f'{gid}: saved player {row.player} missing from captured roster')
                index = indices[row.player]
                for label, values in (('pts', data['player_points']), ('min', data['minutes'])):
                    actual = float(values[:, index].sum(axis=1).mean())
                    if not np.isclose(actual, getattr(row, f'{label}_sim'), atol=1e-10, rtol=0):
                        raise ValueError(f'{gid}: {row.player} captured {label} differs from backtest')
                checked_players += 1
            records.append(record)
    if len(records) != len(games) or {r['game_id'] for r in records} != set(games['game_id']):
        raise ValueError('world captures do not cover the saved game population exactly')
    return {
        'experiment': 'a1_s06_independent_world_accounting',
        'run': run,
        'games': len(records),
        'worlds': sum(r['worlds'] for r in records),
        'lineup_fives_checked': sum(r['lineup_fives_checked'] for r in records),
        'post_foul_snapshots': sum(r['post_foul_snapshots'] for r in records),
        'overtime_worlds': sum(r['overtime_worlds'] for r in records),
        'saved_player_means_checked': checked_players,
        'max_replayed_player_minute_error': max(r['max_replayed_player_minute_error'] for r in records),
        'games_detail': records,
        'input_sha256': {str(p.relative_to(ROOT)): sha256_file(p)
                         for p in (Path(__file__), log_path, frame_path, player_path)},
        'world_sha256': files,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f'refusing to overwrite {args.output}')
    report = audit_run(args.run)
    write_json(args.output, report, pretty=True)
    print(f"{report['games']} games, {report['worlds']} worlds and "
          f"{report['lineup_fives_checked']} traced fives independently reconciled")


if __name__ == '__main__':
    main()
