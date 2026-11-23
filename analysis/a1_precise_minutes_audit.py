#!/usr/bin/env python3
"""Independently audit exact-minute research summaries against original captures."""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import sha256_file, write_json  # noqa: E402
from scripts import a1_expected, projection  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('probe', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an experiment')
    probe = json.loads(args.probe.read_text())
    for path, key in (('analysis/a1_branch_world_source.mjs', 'source_sha256'),
                      ('scripts/webapp/weighted-worlds.mjs', 'arithmetic_sha256'),
                      ('scripts/webapp/precise-minutes.mjs', 'algorithm_sha256'),
                      ('analysis/a1_precise_minutes_probe.mjs', 'probe_sha256')):
        if sha256_file(ROOT / path) != probe[key]:
            raise ValueError(f'{path}: algorithm hash differs')
    fixture_path, output_path = Path(probe['fixture']), Path(probe['output'])
    if sha256_file(fixture_path) != probe['fixture_sha256'] or sha256_file(output_path) != probe['output_sha256']:
        raise ValueError('fixture or output hash differs')
    fixture, output = json.loads(fixture_path.read_text()), json.loads(output_path.read_text())
    if (output['fixture'] != probe['fixture'] or output['fixture_sha256'] != probe['fixture_sha256']
            or output['choices'] != probe['choices']):
        raise ValueError('fixture or selections differ')
    report_path = Path(fixture['source'])
    if sha256_file(report_path) != fixture['source_sha256']:
        raise ValueError('source report hash differs')
    report = json.loads(report_path.read_text())
    all_branches = a1_expected.selected_branches(report, {})
    denominator = math.lcm(*(weight.denominator * b['worlds'] // math.gcd(weight.numerator, weight.denominator * b['worlds'])
                             for b, weight in all_branches))
    selected_ids = {b['branch_id'] for b, _ in a1_expected.selected_branches(report, output['choices'])}
    loaded, units = [], []
    for branch, weight in all_branches:
        if branch['branch_id'] not in selected_ids:
            continue
        path = Path(branch['capture'])
        if sha256_file(path) != branch['capture_sha256']:
            raise ValueError('capture hash differs')
        with np.load(path, allow_pickle=False) as data:
            loaded.append((data['player_ids'], data['minutes'], data['side'], data['team_points']))
        if not np.array_equal(loaded[0][0], loaded[-1][0]):
            raise ValueError('capture rosters differ')
        if not np.array_equal(loaded[0][2], loaded[-1][2]):
            raise ValueError('capture sides differ')
        unit = weight * denominator / branch['worlds']
        if unit.denominator != 1:
            raise ValueError('non-integral world mass')
        units.append(int(unit))
    players = [str(x) for x in loaded[0][0]]
    expected_keys = {(player, period) for player in players for period in projection.PERIODS}
    rows = output['rows']
    if len(rows) != len(expected_keys) or {(r['player'], r['period']) for r in rows} != expected_keys:
        raise ValueError('missing or duplicate player-period distribution')
    mass = sum(a.shape[0] * u for (_, a, _, _), u in zip(loaded, units, strict=True))
    worlds = sum(a.shape[0] for _, a, _, _ in loaded)
    for row in rows:
        index, cols = players.index(row['player']), projection.SLICES[row['period']]
        arrays = [a[:, index, cols].sum(axis=1) for _, a, _, _ in loaded]
        if row['mass'] != mass or row['worlds'] != worlds:
            raise ValueError('selected mass or world count differs')
        mean = sum(float(a.sum()) * u for a, u in zip(arrays, units, strict=True)) / mass
        if not math.isclose(row['mean'], mean, rel_tol=1e-10, abs_tol=1e-9):
            raise ValueError('mean differs')
        values = np.concatenate(arrays)
        weights = np.concatenate([np.full(len(a), u, dtype=np.int64) for a, u in zip(arrays, units, strict=True)])
        order = np.argsort(values)
        ordered, cumulative = values[order], np.cumsum(weights[order])
        for actual, q in zip(row['quantiles'], (Fraction(1, 10), Fraction(1, 4), Fraction(1, 2),
                                                Fraction(3, 4), Fraction(9, 10)), strict=True):
            target = (mass * q.numerator + q.denominator - 1) // q.denominator
            expected = ordered[np.searchsorted(cumulative, target)]
            if not math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-9):
                raise ValueError('quantile differs')
        if set(row['thresholds']) != {'0', '10', '20', '30', '30.25', '40', '48'}:
            raise ValueError('minute thresholds missing or unexpected')
        for text, counts in row['thresholds'].items():
            line = float(text)
            expected = {'below': int(weights[values < line].sum()), 'equal': int(weights[values == line].sum()),
                        'above': int(weights[values > line].sum())}
            if counts != expected:
                raise ValueError(f'{row["player"]} {row["period"]}: threshold {line} differs')
        side = int(loaded[0][2][index])
        won = np.concatenate([scores[:, side, :].sum(axis=1) > scores[:, 1 - side, :].sum(axis=1)
                              for _, _, _, scores in loaded])
        win_mass = int(weights[won].sum())
        expected_win = {'mass': win_mass, 'above': int(weights[won & (values > 30.25)].sum())} if win_mass else None
        if row['win'] != expected_win:
            raise ValueError(f'{row["player"]} {row["period"]}: given-win threshold differs')
        bins: dict[int, list[int]] = defaultdict(lambda: [0, 0])
        for value, weight in zip(values, weights, strict=True):
            bins[math.floor(value)][int(value > 30.25)] += int(weight)
        expected_bins = [{'minute': minute, 'atOrBelow': pair[0], 'above': pair[1]}
                         for minute, pair in sorted(bins.items())]
        if row['bins'] != expected_bins:
            raise ValueError(f'{row["player"]} {row["period"]}: display-bin mass differs')
    write_json(args.output, {'kind': 'independent exact-minute accounting; not a forecast or predictive test',
                             'probe': str(args.probe), 'probe_sha256': sha256_file(args.probe),
                             'audit_sha256': sha256_file(Path(__file__)), 'distributions': len(rows),
                             'selected_worlds': worlds, 'selected_mass': mass,
                             'thresholds_per_distribution': 7, 'minute_bins_split_at': 30.25,
                             'conditional_win_thresholds': len(rows)}, pretty=True)
    print(f'Audited {len(rows)} exact-minute distributions from {worlds:,} selected worlds')


if __name__ == '__main__':
    main()
