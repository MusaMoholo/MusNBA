#!/usr/bin/env python3
"""Existing paired scorecard plus integrated discrete coverage; retain the legacy PIT diagnostic."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from basketball_common import sha256_file, write_json
from scripts import a1_compare, release_gate

legacy_distribution = a1_compare.distribution


def distribution(rows, stat, game_ids, weights, player):
    result = legacy_distribution(rows, stat, game_ids, weights, player)
    if 'coverage' not in result:
        return result
    result['coverage_legacy_randomised_pit'] = result['coverage']
    known = np.isfinite(rows[stat + '_actual_control'].to_numpy(float))
    work = rows.loc[known, ['game_id']].copy()
    for side in ('control', 'candidate'):
        values = rows.loc[known, f'{stat}_coverage_expected_{side}'].to_numpy(float)
        if not np.isfinite(values).all() or ((values < 0) | (values > 1)).any():
            raise ValueError('invalid expected coverage')
        work[side] = values
    work['n'] = 1
    grouped = work.groupby('game_id').sum().reindex(game_ids, fill_value=0)
    totals = grouped.sum()
    a, b = float(totals['control'] / totals['n']), float(totals['candidate'] / totals['n'])
    boot = None
    if result['status'] == 'ok':
        replicate = weights @ grouped.to_numpy(float)
        c = {name: i for i, name in enumerate(grouped.columns)}
        aa, bb = (replicate[:, c[side]] / replicate[:, c['n']] for side in ('control', 'candidate'))
        boot = np.abs(bb - .8) - np.abs(aa - .8)
    result['coverage'] = a1_compare._result(a, b, boot, lambda x: abs(x - .8))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.with_name(args.output.stem + '_gate.json').exists():
        raise FileExistsError('fresh score/gate paths required')
    with patch.object(a1_compare, 'distribution', side_effect=distribution):
        report = a1_compare.compare(args.run + '_control', args.run + '_candidate')
    report['method']['coverage'] = 'expected randomised PIT in [0.1, 0.9], integrating the auxiliary uniform; legacy retained separately'
    report['input_sha256'] = {str(p.relative_to(ROOT)): sha256_file(p) for p in
                              (Path(__file__), ROOT / 'scripts/a1_compare.py',
                               ROOT / f'analysis/experiments/{args.run}.json',
                               *(ROOT / f'data/derived/experiments/{args.run}_{side}{tail}.parquet'
                                 for side in ('control', 'candidate') for tail in ('', '_players')))}
    write_json(args.output, report, pretty=True)
    gate = release_gate.assess(report, 'mechanics')
    gate['comparison_sha256'] = sha256_file(args.output)
    write_json(args.output.with_name(args.output.stem + '_gate.json'), gate, pretty=True)
    print(gate['decision'], gate['core']['established'], '/', gate['core']['checks'])


if __name__ == '__main__':
    main()
