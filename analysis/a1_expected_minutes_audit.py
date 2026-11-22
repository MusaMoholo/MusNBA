#!/usr/bin/env python3
"""Reconstruct an exact-minute conditional from independently audited branch captures."""
from __future__ import annotations

import argparse
import math
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from analysis import a1_branch_persist_audit  # noqa: E402
from basketball_common import read_json, sha256_file, write_json  # noqa: E402
from scripts import a1_expected  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--given-player', required=True)
    parser.add_argument('--minimum-seconds', type=float, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an experiment')
    if not math.isfinite(args.minimum_seconds) or args.minimum_seconds < 0:
        raise ValueError('minimum seconds must be finite and nonnegative')
    report = read_json(args.report)
    a1_branch_persist_audit.audit(report)
    branches = a1_expected.selected_branches(report, {})
    event_mass = condition_mass = joint_mass = Fraction()
    events, conditions, weights = [], [], []
    worlds = 0
    for branch, weight in branches:
        with np.load(branch['capture'], allow_pickle=False) as data:
            indices = np.flatnonzero(data['player_ids'] == args.given_player)
            if len(indices) != 1:
                raise ValueError('given player must be uniquely present')
            scores = data['team_points'].sum(axis=2)
            event = scores[:, 0] > scores[:, 1]
            condition = data['minutes'][:, indices[0], :].sum(axis=1) * 60 >= args.minimum_seconds
        per_world = weight / len(event)
        event_mass += per_world * int(event.sum())
        condition_mass += per_world * int(condition.sum())
        joint_mass += per_world * int(np.count_nonzero(event & condition))
        events.append(event)
        conditions.append(condition)
        weights.append(weight)
        worlds += len(event)
    candidate = a1_expected.weighted_joint(events, conditions, weights)
    def value(key: str) -> Fraction:
        result = candidate[key]
        return Fraction(int(result['numerator']), int(result['denominator']))
    if (value('event') != event_mass or value('condition') != condition_mass or value('joint') != joint_mass
            or (condition_mass and value('given') != joint_mass / condition_mass)):
        raise ValueError('exact-minute conditional masses disagree')
    write_json(args.output, {
        'kind': 'research exact-minute conditional accounting; not a forecast',
        'game': report['game'], 'source_report': str(args.report), 'source_sha256': sha256_file(args.report),
        'audit_sha256': sha256_file(Path(__file__)),
        'algorithm_sha256': sha256_file(ROOT / 'scripts/a1_expected.py'),
        'lineup_conditions': {}, 'event': 'home team wins',
        'given': f'player {args.given_player} has at least {args.minimum_seconds:g} simulated seconds',
        'worlds': worlds, 'branches': len(branches), 'result': candidate,
        'limitations': ['Branch probabilities and their independence remain uncalibrated assumptions.',
                        'This isolated result is not connected to the dashboard.'],
    }, pretty=True)
    print(f'{worlds} worlds: exact-second conditional masses agree')


if __name__ == '__main__':
    main()
