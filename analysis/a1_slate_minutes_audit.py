#!/usr/bin/env python3
"""Independently reconcile a completed slate's precise-minute views with its saved worlds."""
import argparse
import base64
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.projection import SLICES  # noqa: E402


def require(condition, message):
    if not condition:
        raise ValueError(message)


def audit(snapshot: Path, api: Path, expected_worlds: int) -> dict:
    start = time.monotonic()
    meta = json.loads((snapshot / 'meta.json').read_text())
    require(meta['origin'] == meta['slate_date'] and meta['cutoff'] < meta['origin'], 'invalid slate origin/cutoff')
    require(meta['sims'] == expected_worlds and meta['season_sims'] == expected_worlds, 'unexpected world count')
    require(meta['games'] and len(meta['games']) == len(set(meta['games'])), 'empty or duplicate slate')
    values_checked = marginal_values_checked = scores_checked = overtime_worlds = 0
    max_team_minute_error = max_overtime_error = max_marginal_error = 0.0
    with np.load(snapshot / 'engine_players.npz', allow_pickle=False) as players, \
            np.load(snapshot / 'engine_worlds.npz', allow_pickle=False) as teams:
        for gid in meta['games']:
            prefix = f'{gid}__'
            ids, side, lines, minutes = (players[prefix + key] for key in ('ids', 'side', 'lines', 'minutes'))
            require(int(players[prefix + 'minutes_schema']) == 1, f'{gid}: unsupported minute schema')
            W, n = expected_worlds, len(ids)
            require(minutes.shape == (W, n, 5) and lines.shape[:2] == (W, n), f'{gid}: invalid player dimensions')
            require(minutes.dtype.kind == 'f' and minutes.dtype.itemsize == 8
                    and np.isfinite(minutes).all() and (minutes >= 0).all(), f'{gid}: invalid minutes')
            require(side.shape == (n,) and np.isin(side, [0, 1]).all(), f'{gid}: invalid sides')
            require(np.array_equal(np.clip(np.rint(minutes.sum(axis=2)), 0, 255), lines[:, :, 0]),
                    f'{gid}: rounded lines disagree with minutes')
            points = teams[gid]
            require(points.shape == (W, 2, 5), f'{gid}: invalid team dimensions')
            world = json.loads((api / 'game' / gid / 'worlds.json').read_text())
            marginal = json.loads((api / 'game' / gid / 'minute-marginals.json').read_text())
            require(world['worlds'] == W and marginal['worlds'] == W and world['minutes_schema'] == 1
                    and marginal['schema'] == 1, f'{gid}: invalid view schema')
            names = list(map(str, ids))
            require(world['players'] == names and marginal['players'] == names
                    and world['side'] == side.tolist() and marginal['periods'] == list(SLICES),
                    f'{gid}: mismatched player or period ordering')
            decoded = np.frombuffer(base64.b64decode(world['period_minutes_f64_le'], validate=True), dtype='<f8')
            require(np.array_equal(decoded.reshape(minutes.shape), minutes), f'{gid}: world minute values differ')
            decoded_lines = np.frombuffer(base64.b64decode(world['lines'], validate=True), dtype=np.uint8)
            require(np.array_equal(decoded_lines.reshape(lines.shape), lines), f'{gid}: world player lines differ')
            decoded_teams = np.frombuffer(base64.b64decode(world['team_periods'], validate=True), dtype=np.uint8)
            require(np.array_equal(decoded_teams.reshape(points.shape), points), f'{gid}: world team periods differ')
            phone = np.frombuffer(base64.b64decode(marginal['minutes_f64_le'], validate=True), dtype='<f8')
            phone = phone.reshape(W, n, len(SLICES))
            for i in range(n):
                for period, cols in enumerate(SLICES.values()):
                    source = np.sort(minutes[:, i, cols].sum(axis=1))
                    error = float(np.max(np.abs(phone[:, i, period] - source)))
                    max_marginal_error = max(max_marginal_error, error)
                    require(error <= 1e-12, f'{gid}: phone minute distribution differs')
            overtime = []
            for s in (0, 1):
                side_minutes = minutes[:, side == s, :].sum(axis=1)
                error = float(np.max(np.abs(side_minutes[:, :4] - 60)))
                max_team_minute_error = max(max_team_minute_error, error)
                require(error <= 1e-8, f'{gid}: regulation team minutes do not sum to 60 per quarter')
                overtime.append(side_minutes[:, 4])
                require(np.array_equal(lines[:, side == s, 1].astype(np.int64).sum(axis=1),
                                       points[:, s, :].astype(np.int64).sum(axis=1)),
                        f'{gid}: player and team points differ')
            ot_error = max(float(np.max(np.abs(overtime[0] - overtime[1]))),
                           float(np.max(np.abs(overtime[0] - 25 * np.rint(overtime[0] / 25)))))
            max_overtime_error = max(max_overtime_error, ot_error)
            require(ot_error <= 1e-8, f'{gid}: overtime team minutes do not reconcile')
            regulation = points[:, :, :4].astype(np.int64).sum(axis=2)
            require(np.array_equal(overtime[0] > 1e-8, regulation[:, 0] == regulation[:, 1]),
                    f'{gid}: overtime does not match tied regulation')
            overtime_worlds += int(np.count_nonzero(overtime[0] > 1e-8))
            values_checked += minutes.size
            marginal_values_checked += phone.size
            scores_checked += 2 * W
    return {'kind': 'independent live slate minute and score accounting; not a predictive test',
            'origin': meta['origin'], 'model': meta['model']['id'], 'games': len(meta['games']),
            'worlds_per_game': expected_worlds, 'season_worlds': meta['season_sims'],
            'simulated_overtime_worlds': overtime_worlds,
            'world_minute_values_checked': values_checked, 'phone_marginal_values_checked': marginal_values_checked,
            'team_scores_checked': scores_checked, 'max_team_quarter_minute_error': max_team_minute_error,
            'max_overtime_team_minute_error': max_overtime_error,
            'max_phone_marginal_error': max_marginal_error, 'elapsed_seconds': round(time.monotonic() - start, 3)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', type=Path)
    parser.add_argument('--api', type=Path, default=ROOT / 'data/views/api')
    parser.add_argument('--worlds', type=int, default=10000)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.worlds <= 0:
        parser.error('--worlds must be positive')
    result = audit(args.snapshot, args.api, args.worlds)
    with args.output.open('x') as out:
        json.dump(result, out, indent=2, allow_nan=False)
        out.write('\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
