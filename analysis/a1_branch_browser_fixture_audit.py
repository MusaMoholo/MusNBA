#!/usr/bin/env python3
"""Independently decode and reconcile an isolated branch browser fixture."""
from __future__ import annotations

import argparse
import base64
import json
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import sha256_file, write_json  # noqa: E402

STATS = ('min', 'pts', 'reb', 'ast', 'fg3m', 'stl', 'blk', 'tov', 'fgm', 'fga', 'fg3a', 'fta', 'oreb', 'dreb', 'ftm')


def decode(value: str, shape: tuple[int, ...]) -> np.ndarray:
    return np.frombuffer(base64.b64decode(value, validate=True), dtype=np.uint8).reshape(shape)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fixture', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an existing audit')
    fixture = json.loads(args.fixture.read_text())
    source = Path(fixture['source'])
    if sha256_file(source) != fixture['source_sha256']:
        raise ValueError('branch manifest hash differs')
    report = json.loads(source.read_text())
    if (fixture['game'] != report['game'] or fixture['origin'] != report['origin']
            or fixture['selected_players'] != report['selected']
            or fixture['weight_assumptions'] != report['weight_assumptions']
            or len(fixture['branches']) != len(report['branches'])):
        raise ValueError('fixture metadata differs from branch manifest')
    total_weight = Fraction()
    worlds = line_values = availability_values = period_values = 0
    for branch, original in zip(fixture['branches'], report['branches'], strict=True):
        if any(branch[key] != original[key] for key in ('branch_id', 'assignments', 'weight', 'capture_sha256')):
            raise ValueError('fixture branch metadata differs')
        weight = branch['weight']
        total_weight += Fraction(int(weight['numerator']), int(weight['denominator']))
        if sha256_file(Path(original['capture'])) != original['capture_sha256']:
            raise ValueError('source capture hash differs')
        packed = branch['worlds']
        if packed['stats'] != list(STATS) or packed['periods'] != ['q1', 'q2', 'q3', 'q4', 'ot']:
            raise ValueError('fixture columns differ from the browser contract')
        W, P = packed['worlds'], len(packed['players'])
        if W != original['worlds']:
            raise ValueError('fixture world count differs')
        lines = decode(packed['lines'], (W, P, len(STATS)))
        availability = decode(packed['availability'], (W, P))
        periods = decode(packed['team_periods'], (W, 2, 5))
        with np.load(original['capture'], allow_pickle=False) as data:
            if (packed['players'] != data['player_ids'].tolist() or packed['side'] != data['side'].tolist()
                    or not np.array_equal(availability, data['available'])
                    or not np.array_equal(periods, data['team_points'])):
                raise ValueError('fixture roster, availability or team periods differ')
            for col, stat in enumerate(STATS):
                if stat == 'min':
                    expected = np.rint(data['minutes'].sum(axis=2))
                elif stat == 'reb':
                    expected = data['box_oreb'].sum(axis=2) + data['box_dreb'].sum(axis=2)
                else:
                    expected = data[f'box_{stat}'].sum(axis=2)
                if not np.array_equal(lines[:, :, col], expected):
                    raise ValueError(f'fixture {stat} differs from source capture')
        worlds += W
        line_values += lines.size
        availability_values += availability.size
        period_values += periods.size
    if total_weight != 1:
        raise ValueError('fixture branch weights do not total one')
    write_json(args.output, {
        'kind': 'independent research browser fixture accounting; not a forecast',
        'fixture': str(args.fixture), 'fixture_sha256': sha256_file(args.fixture),
        'fixture_bytes': args.fixture.stat().st_size, 'source': str(source),
        'source_sha256': sha256_file(source), 'audit_sha256': sha256_file(Path(__file__)),
        'branches': len(fixture['branches']), 'worlds': worlds, 'player_stat_values': line_values,
        'availability_values': availability_values, 'team_period_values': period_values,
        'exact_total_weight': str(total_weight),
    }, pretty=True)
    print(f'{worlds} worlds, {line_values} player-stat values, availability and scores reconciled')


if __name__ == '__main__':
    main()
