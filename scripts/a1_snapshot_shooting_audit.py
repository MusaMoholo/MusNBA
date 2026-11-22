#!/usr/bin/env python3
"""Independently audit stored game and period shooting distributions."""
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import SNAPSHOTS, read_json, sha256_file, write_json  # noqa: E402
from scripts import projection, views  # noqa: E402

PAIRS = {'fgpct': ('fgm', 'fga'), 'fg3pct': ('fg3m', 'fg3a'), 'ftpct': ('ftm', 'fta')}


def histogram(distribution: dict, expected: int, label: str) -> np.ndarray:
    counts = np.asarray(distribution['hist'])
    if (counts.ndim != 1 or counts.size == 0 or not np.issubdtype(counts.dtype, np.integer)
            or (counts < 0).any() or int(counts.sum()) != expected or distribution['min'] != 0):
        raise ValueError(f'{label}: invalid discrete histogram')
    values = np.arange(len(counts))
    mean = float((values * counts).sum() / expected)
    sd = float(np.sqrt(((values - mean) ** 2 * counts).sum() / expected))
    quantiles = np.searchsorted(np.cumsum(counts), np.array([.1, .25, .5, .75, .9]) * expected).tolist()
    if (not np.isfinite(distribution['mean']) or not np.isfinite(distribution['sd'])
            or abs(distribution['mean'] - mean) > .000501 or abs(distribution['sd'] - sd) > .000501
            or distribution['q'] != quantiles):
        raise ValueError(f'{label}: summary does not match its histogram')
    return counts


def check_period(stats: dict, worlds: int, label: str) -> dict[str, int]:
    counts = {}
    for pct, (made, attempted) in PAIRS.items():
        histogram(stats[made], worlds, f'{label} {made}')
        attempts = histogram(stats[attempted], worlds, f'{label} {attempted}')
        defined = worlds - int(attempts[0])
        distribution = stats.get(pct)
        if not defined:
            if distribution is not None:
                raise ValueError(f'{label} {pct}: percentage exists without attempts')
        else:
            if distribution is None or distribution.get('defined') != defined or distribution.get('total') != worlds:
                raise ValueError(f'{label} {pct}: incorrect conditional sample size')
            values = histogram(distribution, defined, f'{label} {pct}')
            if len(values) > 101 and values[101:].any():
                raise ValueError(f'{label} {pct}: percentage exceeds 100')
        counts[pct] = defined
    return counts


def check_full_game(stats: dict, line: np.ndarray, label: str) -> int:
    if line.ndim != 2 or line.shape[1] < len(views.WORLD_STATS):
        raise ValueError(f'{label}: full-game player worlds lack shooting fields')
    checks = 0
    for pct, (made, attempted) in PAIRS.items():
        raw_m = line[:, views.WORLD_STATS.index(made)]
        raw_a = line[:, views.WORLD_STATS.index(attempted)]
        if (not np.isfinite(raw_m).all() or not np.isfinite(raw_a).all()
                or not np.equal(raw_m, np.floor(raw_m)).all() or not np.equal(raw_a, np.floor(raw_a)).all()):
            raise ValueError(f'{label}: non-integer or non-finite shooting worlds')
        m, a = raw_m.astype(np.int64), raw_a.astype(np.int64)
        if (m < 0).any() or (a < 0).any() or (m > a).any():
            raise ValueError(f'{label}: invalid full-game makes/attempts')
        for key, values in ((made, m), (attempted, a)):
            expected = np.bincount(values)
            if not np.array_equal(np.asarray(stats[key]['hist']), expected):
                raise ValueError(f'{label} {key}: histogram differs from retained player worlds')
            checks += 1
        mask = a > 0
        if mask.any():
            values = np.floor(100 * m[mask] / a[mask] + .5).astype(np.int64)
            if not np.array_equal(np.asarray(stats[pct]['hist']), np.bincount(values)):
                raise ValueError(f'{label} {pct}: histogram differs from retained player worlds')
            checks += 1
    return checks


def audit_day(day: str, origin: str, model: str, worlds: int) -> tuple[dict, list[Path]]:
    root = SNAPSHOTS / day
    paths = [root / name for name in ('meta.json', 'games.json', 'engine_players.npz')]
    meta, games = read_json(paths[0]), read_json(paths[1])
    expected_cutoff = (date.fromisoformat(origin) - timedelta(days=1)).isoformat()
    if (meta['slate_date'] != day or meta['origin'] != origin or meta['cutoff'] != expected_cutoff
            or meta['kind'] != 'prospective' or meta['model']['id'] != model
            or meta['sims'] != worlds or set(meta['games']) != set(games)):
        raise ValueError(f'{day}: snapshot origin, model, game IDs or world count differs')
    result = {'games': len(games), 'players_with_periods': 0, 'players_without_periods': 0,
              'period_triplets': 0, 'conditional_distributions': 0, 'no_attempt_period_triplets': 0,
              'partial_no_attempt_period_triplets': 0, 'full_game_world_histograms': 0}
    with np.load(paths[2], allow_pickle=False) as saved:
        for gid, game in games.items():
            if (game.get('shooting_distribution_schema') != 1 or game['sims'] != worlds
                    or game['game_id'] != gid or game['model'] != model):
                raise ValueError(f'{gid}: missing or invalid shooting schema')
            ids = [str(value) for value in saved[f'{gid}__ids']]
            sides = saved[f'{gid}__side']
            lines = saved[f'{gid}__lines']
            if (len(ids) != len(set(ids)) or sides.shape != (len(ids),)
                    or lines.shape[:2] != (worlds, len(ids))):
                raise ValueError(f'{gid}: retained player-world shape or IDs differ')
            index = {pid: i for i, pid in enumerate(ids)}
            seen = set()
            for side_index, side in enumerate(('home', 'away')):
                for player in game[side]['players']:
                    pid = str(player['id'])
                    if pid in seen or pid not in index or sides[index[pid]] != side_index:
                        raise ValueError(f'{gid}: stored player IDs or sides differ')
                    seen.add(pid)
                    line = lines[:, index[pid], :]
                    periods = player.get('periods')
                    if periods is None:
                        if any((line[:, views.WORLD_STATS.index(key)] != 0).any()
                               for pair in PAIRS.values() for key in pair):
                            raise ValueError(f'{gid} {pid}: absent player has simulated shooting counts')
                        result['players_without_periods'] += 1
                        continue
                    if set(periods) != set(projection.SLICES):
                        raise ValueError(f'{gid} {pid}: shooting periods differ')
                    result['players_with_periods'] += 1
                    for period, data in periods.items():
                        label = f'{gid} {pid} {period}'
                        defined = check_period(data['stats'], worlds, label)
                        for made, attempted in PAIRS.values():
                            for key in (made, attempted):
                                if data['mean'][key] != data['stats'][key]['mean']:
                                    raise ValueError(f'{label} {key}: shooting tile and histogram means differ')
                        result['period_triplets'] += len(PAIRS)
                        result['conditional_distributions'] += sum(value > 0 for value in defined.values())
                        result['no_attempt_period_triplets'] += sum(value == 0 for value in defined.values())
                        result['partial_no_attempt_period_triplets'] += sum(0 < value < worlds for value in defined.values())
                    result['full_game_world_histograms'] += check_full_game(periods['fg']['stats'], line, f'{gid} {pid}')
            if seen != set(ids):
                raise ValueError(f'{gid}: stored players do not cover the retained roster')
    return result, paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--days', nargs='+', required=True)
    parser.add_argument('--origin', required=True)
    parser.add_argument('--model', required=True)
    parser.add_argument('--worlds', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.worlds < 1 or len(args.days) != len(set(args.days)) or args.output.exists():
        raise ValueError('worlds, dates or output are invalid')
    days, paths = {}, []
    for day in args.days:
        days[day], sources = audit_day(day, args.origin, args.model, args.worlds)
        paths.extend(sources)
    write_json(args.output, {'origin': args.origin, 'model': args.model, 'worlds': args.worlds, 'days': days,
                             'input_sha256': {str(path.relative_to(ROOT)): sha256_file(path) for path in paths},
                             'limitations': ['period player worlds are not retained; period checks reconcile '
                                             'histogram and no-attempt accounting rather than raw world values']},
               pretty=True)
    print(f'independent shooting audit passed: {sum(day["games"] for day in days.values())} games')


if __name__ == '__main__':
    main()
