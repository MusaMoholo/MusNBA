#!/usr/bin/env python3
"""Rebuild a research-only today-only season and independently audit its team score distributions."""
from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, MASTER_CSV, SNAPSHOTS, read_json, sha256_file, today_et, write_json  # noqa: E402
from scripts import master_fixtures, pathway, projection, views  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scratch', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.scratch.exists() or args.output.exists():
        raise FileExistsError('refusing to overwrite an existing preview')
    day = today_et()
    snapshot = SNAPSHOTS / day
    meta = read_json(snapshot / 'meta.json')
    if meta.get('origin') != day or meta['kind'] != 'prospective':
        raise ValueError('today requires a same-origin prospective snapshot')
    if sha256_file(MASTER_CSV) != meta['inputs']['master_sha256']:
        raise ValueError('master differs from the retained forecast origin')
    master = master_fixtures.load()
    today_games = {r['game_id'] for r in master if r['date_et'] == day}
    if set(meta['games']) != today_games:
        raise ValueError('retained games differ from today’s scheduled slate')
    stats, teams = read_json(snapshot / 'stats.json'), read_json(DERIVED / 'teams.json')
    with np.load(snapshot / 'engine_worlds.npz', allow_pickle=False) as archive:
        worlds = {key: archive[key] for key in archive.files}
    if set(worlds) != today_games or any(len(w) != 10000 for w in worlds.values()):
        raise ValueError('retained today worlds are incomplete')
    started = time.monotonic()
    season = projection.simulate_season(stats['teams'], stats['league'], master, day, teams, worlds, 10000)
    generation_seconds = time.monotonic() - started
    if set(season['engine_games']) != today_games:
        raise ValueError('season uses a different set of possession games')
    remaining = sorted((r for r in master if r['date_et'] >= day),
                       key=lambda r: (r['date_et'], r['tip_utc'], r['game_id']))
    rng = projection.rng_for(pathway.PATHWAY['id'], day, 'season')
    played = pathway.play(stats['teams'], stats['league'], remaining, 10000, rng, worlds)
    distributions = 0
    for index, (game, row) in enumerate(zip(remaining, season['games'], strict=True)):
        if game['game_id'] != row['game_id']:
            raise ValueError('season game order differs')
        expected_source = 'engine' if game['game_id'] in today_games else 'pathway'
        if row['source'] != expected_source:
            raise ValueError(f"{game['game_id']}: wrong engine source")
        if expected_source != 'pathway':
            continue
        h, a = played['points'][:, index, 0], played['points'][:, index, 1]
        for key, values in (('home', h), ('away', a), ('total', h + a), ('margin', h - a)):
            dist = row['regulation'][key]
            bins = np.bincount(values - values.min()).tolist()
            ordered = np.sort(values)
            quantiles = [int(ordered[max(0, int(np.ceil(q * len(values))) - 1)])
                         for q in (0.1, 0.25, 0.5, 0.75, 0.9)]
            if (dist['min'] != int(values.min()) or dist['hist'] != bins or dist['q'] != quantiles
                    or dist['mean'] != round(float(values.mean()), 3)
                    or dist['sd'] != round(float(values.std()), 3)):
                raise ValueError(f"{game['game_id']}: {key} distribution differs")
            distributions += 1
        if row['p_home'] != round(float(played['home_win'][:, index].mean()), 4):
            raise ValueError(f"{game['game_id']}: season win probability differs")
    args.scratch.mkdir(parents=True)
    copy = args.scratch / 'snapshot'
    shutil.copytree(snapshot, copy)
    write_json(copy / 'season.json', season)
    snaps = views.load_snapshots()
    snaps[day] = {'meta': meta, 'path': copy}
    with patch.object(views, 'load_snapshots', return_value=snaps):
        built = views.build(args.scratch / 'views')
    future = [r for r in remaining if r['date_et'] > day]
    for game in future:
        view = read_json(args.scratch / 'views/api/game' / f"{game['game_id']}.json")
        if view['projection'] is not None or not view['team_model'].get('regulation'):
            raise ValueError(f"{game['game_id']}: future game view is not team-only")
    for gid in today_games:
        view = read_json(args.scratch / 'views/api/game' / f'{gid}.json')
        if not view['projection'] or view['projection']['origin'] != day:
            raise ValueError(f'{gid}: today projection was lost')
    write_json(args.output, {
        'kind': 'isolated today-only season and dashboard accounting; not production delivery',
        'origin': day, 'today_engine_games': len(today_games), 'future_games': len(future),
        'distribution_checks': distributions, 'season_sims': season['sims'],
        'generation_seconds': round(generation_seconds, 3),
        'total_seconds': round(time.monotonic() - started, 3), 'view_files': built['files'],
        'source_sha256': {str(p.relative_to(ROOT)): sha256_file(p) for p in (
            Path(__file__), ROOT / 'scripts/projection.py', ROOT / 'scripts/pathway.py', ROOT / 'scripts/views.py')},
        'snapshot_meta_sha256': sha256_file(snapshot / 'meta.json'), 'master_sha256': sha256_file(MASTER_CSV),
        'worlds_sha256': sha256_file(snapshot / 'engine_worlds.npz'),
        'scratch': str(args.scratch),
        'limitations': ['Retained inputs only; no live collection or new possession forecasts.',
                        'Team pathway scores are regulation scores; ties resolve without overtime points.'],
    }, pretty=True)


if __name__ == '__main__':
    main()
