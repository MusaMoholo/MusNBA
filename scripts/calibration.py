#!/usr/bin/env python3
"""Calibration by period and by score margin for a training run (TRAINING_PLAN §5; HANDOFF M5 step 2).

scripts/train.py stores, per node and fold, the expected calibration error (ECE) in each bucket — Q1–Q4, OT and the
offence's margin (≤ −15, −14…−6, −5…5, 6…14, ≥ 15) — together with `ece_null`, the ECE the same forecasts would show
if labels were drawn from the forecasts themselves (perfect calibration; small buckets have a larger null). This
prints the **excess ECE** (ECE − null, ×1000, mean over folds) and the largest class bias per bucket (mean forecast −
frequency; for player choices, the favourite's forecast − its hit rate). Excess within noise ≈ 0 means calibrated.

  .venv/bin/python scripts/calibration.py <run>        run = log stem in analysis/experiments/, e.g. 20261119T210000Z_control
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import read_json  # noqa: E402
from scripts.evaluate import EXPERIMENTS  # noqa: E402

BUCKETS = ['Q1', 'Q2', 'Q3', 'Q4', 'OT', 'm<=-15', 'm-14..-6', 'm-5..5', 'm6..14', 'm>=15']
FLAG = 0.003  # excess ECE worth a look (mean over folds)


def summary(run: str) -> dict:
    log = read_json(EXPERIMENTS / f'{run}.json')
    out = {}
    for node, folds in log['results'].items():
        row = {}
        for b in BUCKETS:
            cells = [f['calibration'][b] for f in folds.values() if b in f.get('calibration', {})]
            if not cells:
                continue
            row[b] = {'n': int(np.sum([c['n'] for c in cells])), 'excess': float(np.mean([c['ece'] - c['ece_null'] for c in cells])),
                      'ece': float(np.mean([c['ece'] for c in cells])), 'null': float(np.mean([c['ece_null'] for c in cells])),
                      'bias': float(np.mean([c['bias'] for c in cells]))}
        overall = [f['ece_model'] for f in folds.values()]
        out[node] = {'buckets': row, 'ece': float(np.mean(overall))}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('run')
    args = ap.parse_args()
    s = summary(args.run)
    print(f'{args.run}: excess ECE ×1000 (ECE − perfect-calibration null, mean over folds); * = above {FLAG * 1000:.0f}')
    print(f"{'node':14}" + ''.join(f'{b:>10}' for b in BUCKETS))
    for node, r in s.items():
        cells = ''.join(f"{r['buckets'][b]['excess'] * 1000:+9.1f}{'*' if r['buckets'][b]['excess'] > FLAG else ' '}" if b in r['buckets'] else f"{'':>10}"
                        for b in BUCKETS)
        print(f'{node:14}{cells}')
    print('\nlargest class bias ×1000 (mean forecast − frequency; candidates: favourite forecast − hit rate)')
    print(f"{'node':14}" + ''.join(f'{b:>10}' for b in BUCKETS))
    for node, r in s.items():
        print(f'{node:14}' + ''.join(f"{r['buckets'][b]['bias'] * 1000:+10.1f}" if b in r['buckets'] else f"{'':>10}" for b in BUCKETS))


if __name__ == '__main__':
    main()
