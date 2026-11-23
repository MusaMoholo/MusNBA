#!/usr/bin/env python3
"""Paired node comparison on the same declared held-out panels (MODEL.md).

Each run of scripts/train.py stores every held-out decision's log loss (data/derived/experiments/<run>.npz).
For each node and fold this prints the change in mean log loss from run A to run B, as a percentage of A, with a
z-score whose standard error is clustered by game (decisions within a game are not independent). The last row,
"chain", sums every node's change per game: the change in the log-likelihood of whole games, in nats per game.

Noise has two sources: the held-out sample (the game-clustered z) and training randomness, which z does not see — a
change of seed alone has produced |z| up to 3.4 on some nodes. `--noise A0 A1` (two runs that differ only in
seed) measures the second per node: noise = RMS over folds of the seed-to-seed change, in % of loss.

Verdict per node (the owner's rule: keep a change only if the mean over folds improves and no fold gets worse by
more than noise):
  better   mean change < −noise, pooled z ≤ −2, and no fold worse by more than 2 × noise with z > 2
  worse    mean change > +noise with pooled z ≥ 2, or a fold worse by more than 2 × noise with z > 2
  neutral  anything else (keep the simpler setting)
Without --noise, noise = 0 (z only — too lenient for small nodes).
Nonzero constant differences retain their direction when estimated SE is zero; z is undefined, not zero.
Unmatched panels and invalid losses fail explicitly. Partial comparisons require --nodes/--folds scope.

  .venv/bin/python scripts/compare.py <run A> <run B> [--noise <seed run A0> <seed run A1>]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED  # noqa: E402

LOSSES = DERIVED / 'experiments'


def load(run: str) -> dict:
    path = Path(run) if run.endswith('.npz') else LOSSES / f'{run}.npz'
    z = np.load(path, allow_pickle=False)
    out = {}
    for key in z.files:
        node, fold, field = key.split('__')
        out.setdefault((node, fold), {})[field] = z[key]
    return out


def paired(a_loss, b_loss, games):
    """Mean of b − a and its game-clustered standard error."""
    a_loss, b_loss, games = np.asarray(a_loss, float), np.asarray(b_loss, float), np.asarray(games)
    if (a_loss.ndim != 1 or b_loss.shape != a_loss.shape or games.shape != a_loss.shape
            or not len(a_loss) or not np.isfinite(a_loss).all() or not np.isfinite(b_loss).all()
            or pd.isna(games).any() or len(np.unique(games)) < 2):
        raise ValueError('finite nonempty matched losses and at least two game clusters required')
    d = pd.Series(b_loss - a_loss)
    by_game = d.groupby(games).agg(['sum', 'size'])
    n, G = len(d), len(by_game)
    mean = d.sum() / n
    resid = by_game['sum'] - by_game['size'] * mean
    se = np.sqrt(G / max(G - 1, 1) * (resid ** 2).sum()) / n
    return float(mean), float(se), by_game['sum']


def seed_noise(run_a: str, run_b: str, *, nodes=None, folds=None) -> dict:
    """Per node: RMS over folds of the relative change between two runs that differ only in seed."""
    r = compare(run_a, run_b, nodes=nodes, folds=folds)
    return {node: float(np.sqrt(np.mean([f['rel'] ** 2 for f in t['folds'].values()]))) for node, t in r['nodes'].items()}


def compare(run_a: str, run_b: str, noise: dict | None = None, *, nodes=None, folds=None) -> dict:
    noise = noise or {}
    A, B = load(run_a), load(run_b)
    scope = {'nodes': sorted(nodes) if nodes is not None else None,
             'folds': sorted(folds) if folds is not None else None}
    A, B = ({k: v for k, v in source.items()
             if (nodes is None or k[0] in nodes) and (folds is None or k[1] in folds)} for source in (A, B))
    if not A or set(A) != set(B):
        raise ValueError(f'unmatched or empty node/fold panels: only A={sorted(set(A)-set(B))}, '
                         f'only B={sorted(set(B)-set(A))}; declare an explicit common scope')
    if ((nodes is not None and set(nodes) != {k[0] for k in A})
            or (folds is not None and set(folds) != {k[1] for k in A})):
        raise ValueError('requested node/fold scope is missing')
    keys = list(A)
    nodes = list(dict.fromkeys(k[0] for k in keys))
    folds = sorted({k[1] for k in keys})
    table, chain = {}, {f: [] for f in folds}
    for node in nodes:
        row = {}
        for fold in folds:
            if (node, fold) not in A or (node, fold) not in B:
                continue
            a, b = A[(node, fold)], B[(node, fold)]
            if len(a['loss']) != len(b['loss']) or not np.array_equal(a['game'], b['game']):
                raise ValueError(f'{node} {fold}: runs do not share held-out rows')
            mean, se, per_game = paired(a['loss'], b['loss'], a['game'])
            base = float(a['loss'].mean())
            if not np.isfinite(base) or base <= 0:
                raise ValueError(f'{node} {fold}: positive baseline loss required for relative comparison')
            row[fold] = {'delta': mean, 'se': se, 'rel': mean / base,
                         'z': z_value(mean, se), 'zero_se': se == 0, 'base': base}
            chain[fold].append(per_game)
        rel = np.mean([r['rel'] for r in row.values()])
        pooled = np.mean([r['delta'] for r in row.values()])
        pooled_se = np.sqrt(np.sum([r['se'] ** 2 for r in row.values()])) / len(row)
        zp = z_value(pooled, pooled_se)
        worst = None if any(r['z'] is None for r in row.values()) else max(r['z'] for r in row.values())
        nz = noise.get(node, 0.0)
        if not np.isfinite(nz) or nz < 0:
            raise ValueError('training noise must be finite and nonnegative')
        bad_fold = any(r['delta'] > 2 * r['se'] and r['rel'] > 2 * nz for r in row.values())
        verdict = ('better' if rel < -nz and pooled <= -2 * pooled_se and not bad_fold else
                   'worse' if (rel > nz and pooled >= 2 * pooled_se) or bad_fold else 'neutral')
        table[node] = {'folds': row, 'mean_rel': float(rel), 'pooled_z': zp,
                       'pooled_delta': float(pooled), 'pooled_se': float(pooled_se),
                       'worst_fold_z': worst, 'noise': float(nz), 'verdict': verdict}
    chain_rows = {}
    for fold, parts in chain.items():
        if not parts:
            continue
        s = pd.concat(parts, axis=1).fillna(0).sum(axis=1)
        G = len(s)
        chain_rows[fold] = {'nats_per_game': float(s.mean()), 'se': float(s.std(ddof=1) / np.sqrt(G)), 'games': G}
    return {'a': run_a, 'b': run_b, 'scope': scope, 'panels': [list(k) for k in keys],
            'nodes': table, 'chain': chain_rows}


def z_value(delta, se):
    """None distinguishes a constant nonzero change from no change; JSON stays finite."""
    return float(delta / se) if se > 0 else 0.0 if delta == 0 else None


def format_z(value):
    return 'const' if value is None else f'{value:+5.1f}'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('run_a')
    ap.add_argument('run_b')
    ap.add_argument('--noise', nargs=2, metavar=('SEED_A', 'SEED_B'), help='two runs differing only in seed (training noise)')
    ap.add_argument('--nodes', nargs='+', help='explicit partial node scope')
    ap.add_argument('--folds', nargs='+', help='explicit partial fold scope')
    args = ap.parse_args()
    noise = seed_noise(*args.noise, nodes=args.nodes, folds=args.folds) if args.noise else None
    r = compare(args.run_a, args.run_b, noise, nodes=args.nodes, folds=args.folds)
    folds = sorted({f for n in r['nodes'].values() for f in n['folds']})
    print(f'B = {args.run_b}  v  A = {args.run_a}   (change in log loss, % of A; z clustered by game; negative = B better)')
    print(f"{'node':14}" + ''.join(f'{f:>17}' for f in folds) + f"{'mean':>10}{'pooled z':>10}{'noise':>9}  verdict")
    for node, t in r['nodes'].items():
        cells = ''.join(f"{t['folds'][f]['rel']:+9.3%} ({format_z(t['folds'][f]['z'])})" if f in t['folds'] else f"{'':>17}" for f in folds)
        print(f"{node:14}{cells}{t['mean_rel']:+10.3%}{format_z(t['pooled_z']):>10}{t['noise']:9.3%}  {t['verdict']}")
    cells = ''.join(f"{r['chain'][f]['nats_per_game']:+9.3f} ({format_z(z_value(r['chain'][f]['nats_per_game'], r['chain'][f]['se']))})" for f in folds)
    total = np.mean([c['nats_per_game'] for c in r['chain'].values()])
    print(f"{'chain':14}{cells}{total:+10.3f}  nats per game (all nodes summed)")


if __name__ == '__main__':
    main()
