#!/usr/bin/env python3
"""Paired run comparison split by the deciding player's sample size (owner: low-sample players should gain from
archetype priors). Buckets of the actor's (or chosen candidate's) pre-game decayed offensive segments (off_segs_eff,
usage family, 15-game half-life; a full-time player sits near 1,000–1,400): < 250 (new or barely used), 250–750
(part-time), 750+ (established). games_eff cannot serve: with the role family's 5-game half-life it caps at ~7.7.

  .venv/bin/python scripts/buckets.py <run A> <run B> --cache data/derived/nodes/<folder> [--nodes who what …]

The cache folder is either run's dataset cache (row order and labels must match; games_eff is read from it).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts import compare  # noqa: E402
from scripts.evaluate import FOLDS  # noqa: E402

EDGES = (250, 750)
LABELS = ('<250 segs', '250-750', '750+')


def bucket_rows(cache: Path, node: str, fold: str):
    z = np.load(cache / f'{node}.npz', allow_pickle=False)
    cols = [str(c) for c in z['columns']]
    col = 'actor_off_segs_eff' if 'actor_off_segs_eff' in cols else 'off_segs_eff' if 'off_segs_eff' in cols else None
    if col is None:
        return None
    _, val_from, val_to = FOLDS[fold]
    date = z['date']
    va = (date >= val_from) & (date <= val_to)
    g = z['X'][va, cols.index(col)]
    if str(z['kind']) == 'candidate':
        g = g[z['y'][va] == 1]
    return np.digitize(np.nan_to_num(g, nan=0.0), EDGES)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('a')
    ap.add_argument('b')
    ap.add_argument('--cache', type=Path, required=True)
    ap.add_argument('--nodes', nargs='*', default=None)
    args = ap.parse_args()
    A, B = compare.load(args.a), compare.load(args.b)
    nodes = args.nodes or sorted({n for n, _ in A}, key=lambda n: [k for k, _ in A].index(n))
    print(f'B = {args.b}  v  A = {args.a}: change in log loss, % of A, by the player\'s off_segs_eff (pooled over folds; z by game)')
    print(f"{'node':15}" + ''.join(f'{lab:>22}' for lab in LABELS))
    for node in nodes:
        cells = []
        diff, base, games, buck = [], [], [], []
        for fold in FOLDS:
            if (node, fold) not in A:
                continue
            b = bucket_rows(args.cache, node, fold)
            if b is None or len(b) != len(A[(node, fold)]['loss']):
                b = None
                break
            diff.append(B[(node, fold)]['loss'].astype(float) - A[(node, fold)]['loss'].astype(float))
            base.append(A[(node, fold)]['loss'].astype(float))
            games.append(A[(node, fold)]['game'].astype(str) + '_' + fold)
            buck.append(b)
        if not buck:
            continue
        d, a, g, k = map(np.concatenate, (diff, base, games, buck))
        for j in range(len(LABELS)):
            m = k == j
            if m.sum() < 100:
                cells.append(f'{"-":>22}')
                continue
            mean, se, _ = compare.paired(np.zeros(m.sum()), d[m], g[m])
            cells.append(f'{100 * mean / a[m].mean():+8.3f}% (z{mean / se if se else 0:+5.1f}) n{m.sum() // 1000:>3}k')
        print(f'{node:15}' + ''.join(cells))


if __name__ == '__main__':
    main()
