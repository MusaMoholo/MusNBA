#!/usr/bin/env python3
"""Reconstruct a weighted minutes/score grid and correlation from branch captures."""
from __future__ import annotations

import argparse
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
    parser.add_argument('--player', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an experiment')
    report = read_json(args.report)
    a1_branch_persist_audit.audit(report)
    pieces = []
    cells = [[Fraction(), Fraction()], [Fraction(), Fraction()]]
    for branch, weight in a1_expected.selected_branches(report, {}):
        with np.load(branch['capture'], allow_pickle=False) as data:
            player = np.flatnonzero(data['player_ids'] == args.player)
            if len(player) != 1:
                raise ValueError('player must be uniquely present')
            x = data['minutes'][:, player[0], :].sum(axis=1)
            y = data['team_points'][:, 0, :].sum(axis=1)
        per_world = weight / len(x)
        for row in (0, 1):
            for col in (0, 1):
                cells[row][col] += per_world * int(np.count_nonzero(((y >= 115) == bool(row))
                                                                     & ((x >= 30) == bool(col))))
        pieces.append((x, y, float(per_world)))
    mx = sum(float(x.sum()) * weight for x, _, weight in pieces)
    my = sum(float(y.sum()) * weight for _, y, weight in pieces)
    xx = sum(float(np.square(x - mx).sum()) * weight for x, _, weight in pieces)
    yy = sum(float(np.square(y - my).sum()) * weight for _, y, weight in pieces)
    xy = sum(float(((x - mx) * (y - my)).sum()) * weight for x, y, weight in pieces)
    if xx <= 0 or yy <= 0 or sum(sum(row, Fraction()) for row in cells) != 1:
        raise ValueError('grid population is degenerate or incomplete')
    write_json(args.output, {
        'kind': 'research weighted minutes/score grid reference; not a forecast',
        'game': report['game'], 'player': args.player, 'source': str(args.report),
        'source_sha256': sha256_file(args.report), 'analysis_sha256': sha256_file(Path(__file__)),
        'worlds': sum(len(x) for x, _, _ in pieces), 'x_threshold_minutes': 30,
        'y_threshold_home_points': 115,
        'cells': [[a1_expected.fraction_json(cell) for cell in row] for row in cells],
        'correlation': xy / (xx * yy) ** 0.5,
        'limitations': ['Uncalibrated branch probabilities; not a served forecast.',
                        'One research game; not an accuracy or dependence validation.'],
    }, pretty=True)
    print(f"{sum(len(x) for x, _, _ in pieces)} worlds: weighted grid reference saved")


if __name__ == '__main__':
    main()
