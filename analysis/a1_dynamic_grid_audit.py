#!/usr/bin/env python3
"""Reconcile adaptive research grid cells with independently read branch captures."""
from __future__ import annotations

import argparse
from fractions import Fraction
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import read_json, sha256_file, write_json  # noqa: E402
from scripts import a1_expected  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('probe', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an existing audit')
    probe = read_json(args.probe)
    source = Path(probe['source'])
    if (sha256_file(source) != probe['source_sha256']
            or sha256_file(Path(probe['fixture'])) != probe['fixture_sha256']):
        raise ValueError('branch manifest or fixture hash differs')
    report = read_json(source)
    edges = []
    for key in ('x_edges', 'y_edges'):
        values = probe[key]
        if (len(values) < 2 or len(values) > 8 or values[0] is not None or values[-1] is not None
                or any(not isinstance(value, (int, float)) or not np.isfinite(value) for value in values[1:-1])):
            raise ValueError('invalid grid edges')
        array = np.array([-np.inf, *values[1:-1], np.inf])
        if np.any(np.diff(array) <= 0):
            raise ValueError('grid edges must increase')
        edges.append(array)
    cells = [[Fraction() for _ in range(len(edges[0]) - 1)] for _ in range(len(edges[1]) - 1)]
    worlds = 0
    for branch, weight in a1_expected.selected_branches(report, {}):
        capture = Path(branch['capture'])
        if sha256_file(capture) != branch['capture_sha256']:
            raise ValueError('capture hash differs')
        with np.load(capture, allow_pickle=False) as data:
            player = np.flatnonzero(data['player_ids'] == probe['player'])
            if len(player) != 1:
                raise ValueError('player is not uniquely present')
            x = data['minutes'][:, player[0], :].sum(axis=1)
            y = data['team_points'][:, 0, :].sum(axis=1)
        column = np.searchsorted(edges[0], x, side='right') - 1
        row = np.searchsorted(edges[1], y, side='right') - 1
        for r in range(len(cells)):
            for c in range(len(cells[0])):
                cells[r][c] += weight * Fraction(int(np.count_nonzero((row == r) & (column == c))), len(x))
        worlds += len(x)
    if worlds != probe['worlds'] or sum((sum(row, Fraction()) for row in cells), Fraction()) != 1:
        raise ValueError('grid population or total mass differs')
    if len(probe['cells']) != len(cells) or any(len(row) != len(cells[0]) for row in probe['cells']):
        raise ValueError('grid dimensions differ')
    for r, row in enumerate(cells):
        for c, expected in enumerate(row):
            if Fraction(probe['cells'][r][c], probe['denominator']) != expected:
                raise ValueError(f'grid cell ({r}, {c}) differs')
    write_json(args.output, {
        'kind': 'independent adaptive grid accounting; not a forecast',
        'probe': str(args.probe), 'probe_sha256': sha256_file(args.probe),
        'source': str(source), 'source_sha256': sha256_file(source), 'audit_sha256': sha256_file(Path(__file__)),
        'worlds': worlds, 'rows': len(cells), 'columns': len(cells[0]),
        'cells_checked': len(cells) * len(cells[0]), 'exact_total_mass': '1',
    }, pretty=True)
    print(f'{worlds} worlds: {len(cells) * len(cells[0])} adaptive grid cells independently reconcile')


if __name__ == '__main__':
    main()
