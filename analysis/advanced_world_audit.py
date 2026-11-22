#!/usr/bin/env python3
"""Reconcile advanced distributions against retained game worlds, without using the view producer."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
STATS = ('min', 'pts', 'reb', 'ast', 'fg3m', 'stl', 'blk', 'tov', 'fgm', 'fga', 'fg3a', 'fta', 'oreb', 'dreb', 'ftm')


def check(saved: dict, key: str, numerator, denominator, percent: bool) -> None:
    if key not in saved:
        raise ValueError(f'missing advanced distribution {key}')
    d = saved[key]
    denominator = np.asarray(denominator, dtype=float)
    numerator = np.asarray(numerator, dtype=float)
    valid = (denominator > 0) & np.isfinite(numerator) & np.isfinite(denominator)
    values = numerator[valid] / denominator[valid] * (100 if percent else 1)
    if (d['defined'], d['total']) != (len(values), len(denominator)):
        raise ValueError(f'{key}: defined-world counts differ')
    if not len(values):
        return
    scale = 1 if percent else 10
    ordered = np.sort(values)
    quantiles = [round(float(ordered[math.ceil(q * len(ordered)) - 1]), 3) for q in (0.1, 0.25, 0.5, 0.75, 0.9)]
    if (d['scale'] != scale or d['exact_mean'] != round(float(values.mean()), 3)
            or d['exact_q'] != quantiles):
        raise ValueError(f'{key}: mean or quantiles differ')
    bins = np.floor(values * scale + 0.5).astype(np.int64)
    observed, counts = np.unique(bins, return_counts=True)
    expected = {int(i + d['min']): count for i, count in enumerate(d['hist']) if count}
    if dict(zip(observed.tolist(), counts.tolist())) != expected:
        raise ValueError(f'{key}: histogram differs')


def audit(saved: dict, box: dict, opponent: dict | None = None) -> int:
    entries = {
        'efg': (('fgm', 'fg3m', 'fga'), lambda a: (a['fgm'] + a['fg3m'] / 2, a['fga']), True),
        'ts': (('pts', 'fga', 'fta'), lambda a: (a['pts'], 2 * (a['fga'] + .44 * a['fta'])), True),
        'two': (('fgm', 'fg3m', 'fga', 'fg3a'), lambda a: (a['fgm'] - a['fg3m'], a['fga'] - a['fg3a']), True),
        'threeShare': (('fg3a', 'fga'), lambda a: (a['fg3a'], a['fga']), True),
        'ftRate': (('fta', 'fga'), lambda a: (a['fta'], a['fga']), True),
        'astTov': (('ast', 'tov'), lambda a: (a['ast'], a['tov']), False),
    }
    checked = 0
    for key, (required, make, percent) in entries.items():
        if all(k in box for k in required):
            check(saved, key, *make(box), percent)
            checked += 1
        elif key in saved:
            raise ValueError(f'{key}: distribution supplied without required world inputs')
    if opponent is None:
        return checked
    a, b = box, opponent
    ap = a['fga'] - a['oreb'] + a['tov'] + .44 * a['fta']
    bp = b['fga'] - b['oreb'] + b['tov'] + .44 * b['fta']
    ar = np.divide(a['pts'], ap, out=np.full_like(ap, np.nan), where=ap > 0)
    br = np.divide(b['pts'], bp, out=np.full_like(bp, np.nan), where=bp > 0)
    for key, numerator, denominator, percent in (
        ('poss', ap, np.ones_like(ap), False), ('ortg', 100 * ar, np.ones_like(ap), False),
        ('drtg', 100 * br, np.ones_like(bp), False), ('net', 100 * (ar - br), np.ones_like(ap), False),
        ('oreb', a['oreb'], a['oreb'] + b['dreb'], True), ('dreb', a['dreb'], a['dreb'] + b['oreb'], True),
        ('assist', a['ast'], a['fgm'], True), ('turnover', a['tov'], ap, True), ('steals', a['stl'], bp, True),
    ):
        check(saved, key, numerator, denominator, percent)
        checked += 1
    return checked


def main() -> None:
    games = players = checks = 0
    for view in sorted((ROOT / 'data/views/api/game').glob('*.json')):
        data = json.loads(view.read_text())
        projection = data.get('projection')
        if not projection:
            continue
        snapshot, gid = ROOT / 'data/snapshots' / projection['snapshot'], view.stem
        path = snapshot / 'engine_players.npz'
        if not path.exists():
            continue
        with np.load(path) as z:
            if f'{gid}__lines' not in z.files:
                continue
            lines = z[f'{gid}__lines'].astype(float)
            ids = [str(x) for x in z[f'{gid}__ids']]
            sides = z[f'{gid}__side']
        columns = {key: lines[:, :, i] for i, key in enumerate(STATS[:lines.shape[2]])}
        sim = projection['sim']
        for side in ('home', 'away'):
            for player in sim[side]['players']:
                fg = (player.get('periods') or {}).get('fg')
                if fg is None or player['id'] not in ids:
                    continue
                i = ids.index(player['id'])
                checks += audit(fg['advanced'], {key: values[:, i] for key, values in columns.items()})
                players += 1
        if all('advanced' in sim[side] for side in ('home', 'away')):
            with np.load(snapshot / 'engine_worlds.npz') as z:
                points = z[gid].astype(float).sum(axis=2)
            boxes = [{key: values[:, sides == side].sum(axis=1) for key, values in columns.items()} for side in (0, 1)]
            for side in (0, 1):
                if not np.array_equal(points[:, side], boxes[side]['pts']):
                    raise ValueError(f'{gid}: player points do not reconcile')
                boxes[side]['pts'] = points[:, side]
            for side, name in enumerate(('home', 'away')):
                checks += audit(sim[name]['advanced'], boxes[side], boxes[1 - side])
        games += 1
    if not games:
        raise ValueError('no retained game worlds were available for the audit')
    print(f'PASS: {games} saved games, {players} player-game distributions, {checks} metric distributions')


if __name__ == '__main__':
    main()
