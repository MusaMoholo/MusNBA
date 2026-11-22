#!/usr/bin/env python3
"""Reconstruct a weighted Given/Joint example independently from saved branch worlds."""
from __future__ import annotations

import argparse
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import read_json, sha256_file, write_json  # noqa: E402
from analysis import a1_branch_persist_audit  # noqa: E402
from scripts import a1_expected  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--given-player', required=True, help='player whose positive simulated minutes are conditioned on')
    parser.add_argument('--lineup-sits', help='fix this selected player unavailable, or omit to marginalise all branches')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an experiment')
    report = read_json(args.report)
    a1_branch_persist_audit.audit(report)
    conditions = {args.lineup_sits: False} if args.lineup_sits else {}
    branches = a1_expected.selected_branches(report, conditions)
    event, given, weights = [], [], []
    independent_joint = independent_condition = independent_event = Fraction()
    raw_weights = []
    for branch in report['branches']:
        assignments = {str(player): plays for _, player, plays in branch['assignments']}
        if all(assignments.get(pid) == plays for pid, plays in conditions.items()):
            raw_weights.append((branch, Fraction(int(branch['weight']['numerator']),
                                                 int(branch['weight']['denominator']))))
    selected_mass = sum((weight for _, weight in raw_weights), Fraction())
    if not selected_mass or [r['branch_id'] for r, _ in branches] != [r['branch_id'] for r, _ in raw_weights]:
        raise ValueError('independent selected-branch inventory mismatch')
    total_worlds = 0
    for (branch, weight), (source, raw) in zip(branches, raw_weights, strict=True):
        if weight != raw / selected_mass:
            raise ValueError('branch reweighting mismatch')
        with np.load(source['capture'], allow_pickle=False) as data:
            ids = data['player_ids']
            index = np.flatnonzero(ids == args.given_player)
            if len(index) != 1:
                raise ValueError('given player must be uniquely present')
            points = data['team_points'].sum(axis=2)
            won = points[:, 0] > points[:, 1]
            played = data['minutes'][:, index[0], :].sum(axis=1) > 0
        n = len(won)
        total_worlds += n
        for home_win, has_minutes in zip(won, played, strict=True):
            per_world = raw / selected_mass / n
            independent_event += per_world * int(home_win)
            independent_condition += per_world * int(has_minutes)
            independent_joint += per_world * int(home_win and has_minutes)
        event.append(won)
        given.append(played)
        weights.append(weight)
    candidate = a1_expected.weighted_joint(event, given, weights)
    def value(key: str) -> Fraction:
        row = candidate[key]
        return Fraction(int(row['numerator']), int(row['denominator']))
    if (value('event') != independent_event or value('condition') != independent_condition
            or value('joint') != independent_joint
            or (independent_condition and value('given') != independent_joint / independent_condition)
            or (not independent_condition and candidate['given'] is not None)):
        raise ValueError('independent weighted conditional or joint reconstruction failed')
    write_json(args.output, {
        'kind': 'research conditional accounting; not a forecast or availability calibration',
        'game': report['game'], 'source_report': str(args.report), 'source_sha256': sha256_file(args.report),
        'algorithm_sha256': sha256_file(ROOT / 'scripts/a1_expected.py'),
        'audit_sha256': sha256_file(Path(__file__)), 'lineup_conditions': conditions,
        'event': 'home team wins', 'given': f'player {args.given_player} has positive simulated minutes',
        'worlds': total_worlds, 'branches': len(branches), 'result': candidate,
        'limitations': ['Branch availability is not the same as positive simulated minutes.',
                        'Branch probabilities and their independence remain uncalibrated assumptions.',
                        'This isolated result is not connected to the dashboard.'],
    }, pretty=True)
    print(f'{total_worlds} worlds, {len(branches)} branches: exact event, given and joint masses agree', flush=True)


if __name__ == '__main__':
    main()
