#!/usr/bin/env python3
"""Independent branch manifest and saved box-score accounting."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from fractions import Fraction
from itertools import product
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import sha256_file  # noqa: E402


def audit(report: dict) -> dict:
    selected, records = report['selected'], report['branches']
    if not selected or len({p['player_id'] for p in selected}) != len(selected):
        raise ValueError('selected players must be nonempty and unique')
    if selected != sorted(selected, key=lambda p: (p['team_id'], p['player_id'])):
        raise ValueError('selected players are not in canonical order')
    choices = (list(product((True, False), repeat=len(selected))) if len(selected) <= 2 else
               [tuple(i != missing for i in range(len(selected))) for missing in range(-1, len(selected))])
    if len(records) != len(choices):
        raise ValueError('branch coverage does not match the selection')
    weights = []
    snapshots = 0
    for record, choice in zip(records, choices):
        assignments = [[p['team_id'], p['player_id'], plays] for p, plays in zip(selected, choice)]
        branch_id = 'lineup-v1:' + ','.join(f'{team}/{player}={"plays" if plays else "sits"}'
                                           for team, player, plays in assignments)
        expected_seed = int.from_bytes(hashlib.sha256(
            '|'.join(('lineup-v1', report['engine'], report['origin'], report['slate_date'],
                      report['game'], branch_id)).encode()).digest()[:8], 'little')
        if record['assignments'] != assignments or record['branch_id'] != branch_id or record['seed'] != str(expected_seed):
            raise ValueError('branch assignment or seed does not match the manifest')
        expected_weight = None
        if len(selected) <= 2:
            expected_weight = Fraction(1)
            for p, plays in zip(selected, choice):
                probability = Fraction(str(p['probability']))
                expected_weight *= probability if plays else 1 - probability
            weight = record['weight']
            if weight is None or Fraction(int(weight['numerator']), int(weight['denominator'])) != expected_weight:
                raise ValueError('branch weight does not match the exact independent product')
            weights.append(expected_weight)
        elif record['weight'] is not None:
            raise ValueError('non-exhaustive sensitivities cannot carry a mixture weight')
        path = Path(record['capture'])
        if sha256_file(path) != record['capture_sha256']:
            raise ValueError('branch capture hash differs from its manifest')
        with np.load(path, allow_pickle=False) as data:
            ids, sides = data['player_ids'], data['side']
            available, mins, points = data['available'], data['minutes'], data['player_points']
            W = report['worlds_per_branch']
            if available.shape != (W, len(ids)) or record['worlds'] != W:
                raise ValueError('branch has the wrong number of worlds or roster size')
            for p, plays in zip(selected, choice):
                positions = np.flatnonzero(ids == p['player_id'])
                if len(positions) != 1 or not np.all(available[:, positions[0]] == plays):
                    raise ValueError('selected player availability differs from the branch assignment')
            box = {key[4:]: data[key] for key in data.files if key.startswith('box_')}
            if not np.array_equal(points, box['pts']) or not np.array_equal(data['player_fouls'], box['pf']):
                raise ValueError('captured box totals differ from the audited points or fouls')
            if any(values.shape != mins.shape or (values < 0).any() for values in box.values()):
                raise ValueError('box-score dimensions or values are invalid')
            if not np.array_equal(points, 2 * box['fgm'] + box['fg3m'] + box['ftm']):
                raise ValueError('player shooting does not reconcile to points')
            if ((box['fgm'] > box['fga']).any() or (box['fg3m'] > box['fg3a']).any()
                    or (box['fg3m'] > box['fgm']).any() or (box['fg3a'] > box['fga']).any()
                    or (box['ftm'] > box['fta']).any()):
                raise ValueError('shot makes exceed attempts or overall field goals')
            for side in (0, 1):
                if not np.array_equal(points[:, sides == side].sum(axis=1), data['team_points'][:, side]):
                    raise ValueError('player and team period points differ')
            if any((values[~available] != 0).any() for values in box.values()) or (mins[~available] != 0).any():
                raise ValueError('unavailable players accumulated minutes or box stats')
            snapshots += len(data['trace_world'])
    if weights and sum(weights) != 1:
        raise ValueError('exhaustive branch weights do not total exactly one')
    return {'branches': len(records), 'worlds': len(records) * report['worlds_per_branch'],
            'lineup_snapshots': snapshots, 'weight_total': str(sum(weights)) if weights else None}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(json.loads(args.report.read_text())), sort_keys=True))


if __name__ == '__main__':
    main()
