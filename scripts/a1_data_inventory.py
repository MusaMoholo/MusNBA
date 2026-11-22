#!/usr/bin/env python3
"""Inventory retained A1 source coverage and verify the available raw-file manifests.

  .venv/bin/python scripts/a1_data_inventory.py --output analysis/experiments/new-inventory.json
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
import zlib
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DATA, sha256_file, today_et, write_json  # noqa: E402
from scripts import fetch_nbastats  # noqa: E402

ENDPOINTS = ('gamelogs', 'boxscorematchupsv3', 'playbyplayv3', 'leaguedashptdefend')


def nba_folder(folder: Path) -> dict:
    manifest_path = folder / 'manifest.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    files = {path.name.removesuffix('.json.gz'): path for path in folder.glob('*.json.gz')}
    names = set(files)
    keys = set(manifest)
    missing_metadata, mismatches, corrupt = [], [], []
    for key in sorted(keys):
        entry = manifest[key]
        if not entry.get('url') or not entry.get('fetched_utc'):
            missing_metadata.append(key)
        if key not in files:
            continue
        try:
            body = gzip.decompress(files[key].read_bytes())
        except (OSError, EOFError, zlib.error) as error:
            corrupt.append({'key': key, 'error': str(error)})
            continue
        if len(body) != entry['bytes'] or hashlib.sha256(body).hexdigest() != entry['sha256']:
            mismatches.append(key)
    return {'manifest_present': manifest_path.exists(), 'manifest_entries': len(keys), 'files': len(names),
            'unindexed': sorted(names - keys), 'missing_files': sorted(keys - names),
            'missing_url_or_fetch_time': missing_metadata, 'hash_or_size_mismatch': mismatches,
            'corrupt_gzip': corrupt}


def hoopr_inventory() -> dict:
    folder = DATA / 'raw' / 'hoopr'
    manifest = json.loads((folder / 'manifest.json').read_text())
    seasons = {}
    for season in range(2023, 2027):
        record = {}
        games = {}
        for kind in ('play_by_play', 'player_box'):
            name = f'{kind}_{season}.parquet'
            path = folder / name
            entry = manifest[name]
            if not path.is_file():
                raise FileNotFoundError(f'{name} is missing; game coverage cannot be inventoried')
            actual_hash = sha256_file(path)
            if path.stat().st_size != entry['bytes'] or actual_hash != entry['sha256']:
                raise ValueError(f'{name} differs from its retained raw manifest')
            ids = pd.read_parquet(path, columns=['game_id'])['game_id']
            unique = set(ids.dropna().astype('int64').astype(str))
            games[kind] = unique
            record[kind] = {'rows': len(ids), 'missing_game_ids': int(ids.isna().sum()),
                            'unique_games': len(unique), 'bytes': path.stat().st_size,
                            'sha256': actual_hash, 'retrieved': entry.get('retrieved')}
        record['box_only_games'] = sorted(games['player_box'] - games['play_by_play'])
        record['pbp_only_games'] = sorted(games['play_by_play'] - games['player_box'])
        seasons[str(season)] = record
    return {'manifest': str((folder / 'manifest.json').relative_to(ROOT)), 'season_end_year': seasons}


def espn_current_inventory() -> dict:
    folder = DATA / 'raw' / 'espn'
    finals = sorted((folder / 'final').glob('*.json.gz'))
    seasons: Counter[str] = Counter()
    for path in finals:
        header = json.loads(gzip.decompress(path.read_bytes()))['header']
        if str(header['id']) != path.name.removesuffix('.json.gz'):
            raise ValueError(f'{path}: summary header ID does not match the retained file')
        seasons[str(header['season']['year'])] += 1
    runs = []
    for path in sorted((folder / 'runs').glob('*/report.json')):
        report = json.loads(path.read_text())
        runs.append({'run': report['run'], 'slate_date': report['slate_date'],
                     'started': report['started'], 'finished': report.get('finished'),
                     'failures': len(report['failures'])})
    return {'final_summaries_by_season_end_year': dict(sorted(seasons.items())), 'final_summaries': len(finals),
            'final_manifest_present': (folder / 'final' / 'manifest.json').exists(), 'collection_runs': runs,
            'limitation': 'Final summaries have no per-file acquisition/hash manifest; file presence does not prove '
                          'the original publication time or historical availability.'}


def inventory() -> dict:
    day = today_et()
    games = [game for game in fetch_nbastats.logged_games(fetch_nbastats.SEASONS) if game[3] < day]
    if not games:
        raise ValueError('no eligible logged NBA games; cannot establish a history queue')
    by_season = {}
    for season in fetch_nbastats.SEASONS:
        logged = {game[2] for game in games if game[0] == season}
        log_types = {kind: fetch_nbastats.latest_log(season, kind, 'teams_adv') is not None
                     for kind in fetch_nbastats.SEASON_TYPES}
        endpoints = {endpoint: nba_folder(fetch_nbastats.NBA_RAW / endpoint / season) for endpoint in ENDPOINTS}
        folder = fetch_nbastats.NBA_RAW / 'playbyplayv3' / season
        retained = {path.name.removesuffix('.json.gz') for path in folder.glob('*.json.gz')}
        by_season[season] = {'team_advanced_log_types_present': log_types, 'eligible_logged_games': len(logged),
                             'retained_pbp_for_logged_games': len(logged & retained),
                             'missing_pbp_games': sorted(logged - retained),
                             'retained_pbp_not_in_eligible_logs': sorted(retained - logged), 'endpoints': endpoints}
    return {'experiment': 'a1_raw_source_inventory', 'as_of_et': day,
            'cutoff': 'logged game date strictly before as_of_et; retained files are not proof of historical publication',
            'nba': by_season, 'hoopr': hoopr_inventory(), 'espn_current': espn_current_inventory()}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--output', type=Path, required=True, help='new report path; existing reports are never overwritten')
    args = ap.parse_args()
    if args.output.exists():
        raise FileExistsError(f'refusing to overwrite {args.output}')
    report = inventory()
    write_json(args.output, report, pretty=True)
    queue = sum(len(season['missing_pbp_games']) for season in report['nba'].values())
    print(f'saved {args.output}: {queue} logged NBA games missing retained play-by-play')


if __name__ == '__main__':
    main()
