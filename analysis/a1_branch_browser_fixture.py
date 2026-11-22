#!/usr/bin/env python3
"""Build an isolated browser-format fixture from audited research branch worlds."""
from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from analysis import a1_branch_persist_audit  # noqa: E402
from basketball_common import sha256_file, write_json  # noqa: E402
from scripts import a1_expected, views  # noqa: E402


def packed_bytes(values: np.ndarray) -> str:
    values = np.asarray(values)
    if (not np.isfinite(values).all() or (values < 0).any() or (values > 255).any()
            or not np.equal(values, np.floor(values)).all()):
        raise ValueError('browser fixture values must be whole bytes without clipping')
    return base64.b64encode(np.ascontiguousarray(values, dtype=np.uint8).tobytes()).decode('ascii')


def pack_capture(data: dict[str, np.ndarray]) -> dict:
    ids, side = np.asarray(data['player_ids']), np.asarray(data['side'])
    available, minutes = np.asarray(data['available']), np.asarray(data['minutes'])
    periods = np.asarray(data['team_points'])
    final_period = np.asarray(data['final_period'])
    if available.ndim != 2 or available.dtype != bool:
        raise ValueError('availability must be a world-by-player boolean array')
    worlds, players = available.shape
    if (not worlds or not players or ids.shape != (players,) or side.shape != (players,)
            or len(set(map(str, ids))) != players or not np.isin(side, (0, 1)).all()
            or minutes.shape != (worlds, players, 5) or periods.shape != (worlds, 2, 5)
            or final_period.shape != (worlds,) or (final_period < 4).any()):
        raise ValueError('capture roster or world dimensions are invalid')
    box = {}
    period_box = {}
    for stat in ('pts', 'oreb', 'dreb', 'ast', 'fg3m', 'stl', 'blk', 'tov', 'fgm', 'fga', 'fg3a', 'fta', 'ftm'):
        values = np.asarray(data[f'box_{stat}'])
        if values.shape != minutes.shape or not np.isfinite(values).all() or (values < 0).any():
            raise ValueError(f'capture {stat} has invalid dimensions or values')
        period_box[stat] = values
        box[stat] = values.sum(axis=2)
    exact_minutes = minutes.sum(axis=2)
    lines = {'min': np.rint(exact_minutes), **box}
    lines['reb'] = lines['oreb'] + lines['dreb']
    period_box['reb'] = period_box['oreb'] + period_box['dreb']
    if (not np.isfinite(minutes).all() or (minutes < 0).any()
            or (minutes[~available] != 0).any()
            or any((values[~available] != 0).any() for values in box.values())):
        raise ValueError('unavailable players or invalid minutes in capture')
    if np.any((final_period == 4) & (periods[:, :, 4].sum(axis=1) != 0)):
        raise ValueError('overtime scores without an overtime period')
    for team in (0, 1):
        if not np.array_equal(period_box['pts'][:, side == team].sum(axis=1), periods[:, team]):
            raise ValueError('player and team scores do not reconcile')
    return {
        'worlds': worlds, 'stats': list(views.WORLD_STATS), 'players': list(map(str, ids)),
        'side': side.astype(int).tolist(),
        'lines': packed_bytes(np.stack([lines[stat] for stat in views.WORLD_STATS], axis=2)),
        'team_periods': packed_bytes(periods),
        'availability': packed_bytes(available),
        'played': packed_bytes(exact_minutes > 0),
        'minutes_f64_le': base64.b64encode(np.ascontiguousarray(exact_minutes, dtype='<f8').tobytes()).decode('ascii'),
        'period_stats': list(views.WORLD_STATS[1:]),
        'period_lines': packed_bytes(np.stack([period_box[stat] for stat in views.WORLD_STATS[1:]], axis=3)),
        'period_minutes_f64_le': base64.b64encode(np.ascontiguousarray(minutes, dtype='<f8').tobytes()).decode('ascii'),
        'final_period': packed_bytes(final_period),
        'periods': ['q1', 'q2', 'q3', 'q4', 'ot'],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an existing browser fixture')
    report = json.loads(args.report.read_text())
    a1_branch_persist_audit.audit(report)
    branches = a1_expected.selected_branches(report, {})
    records = []
    roster = None
    for branch, weight in branches:
        with np.load(branch['capture'], allow_pickle=False) as data:
            packed = pack_capture(data)
        this_roster = (packed['players'], packed['side'])
        if roster is not None and roster != this_roster:
            raise ValueError('branch rosters differ')
        roster = this_roster
        records.append({'branch_id': branch['branch_id'], 'assignments': branch['assignments'],
                        'weight': a1_expected.fraction_json(weight), 'capture_sha256': branch['capture_sha256'],
                        'worlds': packed})
    write_json(args.output, {
        'kind': 'isolated research fixture; not a forecast or serving contract',
        'source': str(args.report), 'source_sha256': sha256_file(args.report),
        'algorithm_sha256': sha256_file(Path(__file__)), 'game': report['game'], 'origin': report['origin'],
        'selected_players': report['selected'], 'weight_assumptions': report['weight_assumptions'],
        'limitations': ['Availability probabilities are not calibrated.',
                        'Joint availability independence is unvalidated.',
                        'Not integrated into any served dashboard or bundle.'],
        'branches': records,
    }, pretty=False)
    print(f"{len(records)} branches, {sum(r['worlds']['worlds'] for r in records)} worlds; isolated fixture")


if __name__ == '__main__':
    main()
