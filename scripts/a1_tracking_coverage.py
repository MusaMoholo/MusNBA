#!/usr/bin/env python3
"""Audit retained NBA tracking-defence dates, response parameters and player joins.

  .venv/bin/python -m scripts.a1_tracking_coverage --output analysis/experiments/new-tracking-audit.json
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, sha256_file, today_et, write_json  # noqa: E402
from scripts import a1_reconcile, fetch_nbastats, nbastats  # noqa: E402

REQUIRED = ('CLOSE_DEF_PERSON_ID', 'PLAYER_LAST_TEAM_ABBREVIATION', 'GP')
ATTEMPT_FIELDS = {'Overall': ('D_FGM', 'D_FGA'), 'Less Than 6Ft': ('FGM_LT_06', 'FGA_LT_06'),
                  '3 Pointers': ('FG3M', 'FG3A')}


def decode(path: Path, entry: dict, season: str, day: str, category: str) -> tuple[dict, list[dict]]:
    body = gzip.decompress(path.read_bytes())
    if entry.get('sha256') != hashlib.sha256(body).hexdigest() or entry.get('bytes') != len(body):
        raise ValueError(f'{path}: manifest hash or length mismatch')
    doc = json.loads(body)
    params = doc['parameters']
    expected_date = datetime.strptime(day, '%Y-%m-%d').strftime('%m/%d/%Y')
    if (params.get('Season') != season or params.get('DateFrom') != expected_date or
            params.get('DateTo') != expected_date or params.get('DefenseCategory') != category):
        raise ValueError(f'{path}: response parameters do not match its date, season and category')
    result = doc['resultSets'][0]
    headers = result['headers']
    if category not in ATTEMPT_FIELDS:
        raise ValueError(f'{path}: unsupported tracking category {category!r}')
    if len(set(headers)) != len(headers) or not set(REQUIRED + ATTEMPT_FIELDS[category]).issubset(headers):
        raise ValueError(f'{path}: missing or duplicate tracking response columns')
    rows = result['rowSet']
    if any(len(row) != len(headers) for row in rows):
        raise ValueError(f'{path}: tracking response row has the wrong length')
    return params, [dict(zip(headers, row)) for row in rows]


def audit() -> dict:
    as_of = today_et()
    games = [g for g in fetch_nbastats.logged_games(fetch_nbastats.SEASONS) if g[3] < as_of]
    _, players = nbastats.nba_tables()
    players = players[players['date'] < as_of]
    people = pd.read_parquet(DERIVED / 'nbastats' / 'players.parquet')
    if people['person'].isna().any() or people['person'].duplicated().any():
        raise ValueError('NBA-to-ESPN people crosswalk has missing or repeated NBA person IDs')
    mapped_people = set(people['person'].astype(int))
    player_teams = {}
    for row in players.itertuples(index=False):
        key = (str(row.date), int(row.PLAYER_ID))
        if key in player_teams and player_teams[key] != row.TEAM_ABBREVIATION:
            raise ValueError(f'NBA day log gives multiple teams for player {key}')
        player_teams[key] = row.TEAM_ABBREVIATION
    by_season = {}
    manifests = []
    for season in fetch_nbastats.SEASONS:
        expected: dict[str, set[str]] = defaultdict(set)
        for game_season, season_type, _, day in games:
            if game_season == season:
                expected[day].add(season_type)
        folder = fetch_nbastats.NBA_RAW / 'leaguedashptdefend' / season
        manifest_path = folder / 'manifest.json'
        if not manifest_path.is_file():
            raise FileNotFoundError(f'{manifest_path}: cannot verify tracking provenance')
        manifests.append(manifest_path)
        manifest = json.loads(manifest_path.read_text())
        categories = {}
        for category in fetch_nbastats.PTDEFEND_CATEGORIES:
            prefix = category.lower().replace(' ', '')
            missing, missing_types, unknown_provenance = [], [], []
            counts: Counter = Counter()
            for day, types in sorted(expected.items()):
                key = f'{prefix}_{day}'
                path = folder / f'{key}.json.gz'
                if not path.is_file():
                    missing.append(day)
                    continue
                if key not in manifest:
                    raise ValueError(f'{path}: retained response is absent from the manifest')
                entry = manifest[key]
                if not entry.get('url') or not entry.get('fetched_utc'):
                    unknown_provenance.append(day)
                params, rows = decode(path, entry, season, day, category)
                if types - {params.get('SeasonType')}:
                    missing_types.append({'date': day, 'expected_types': sorted(types),
                                          'retained_type': params.get('SeasonType')})
                counts['files'] += 1
                counts['empty_files'] += not rows
                counts['rows'] += len(rows)
                made_field, attempted_field = ATTEMPT_FIELDS[category]
                seen = set()
                for row in rows:
                    person = row['CLOSE_DEF_PERSON_ID']
                    if person is None:
                        counts['missing_person_id'] += 1
                        continue
                    person = int(person)
                    counts['duplicate_person_rows'] += person in seen
                    seen.add(person)
                    counts['person_not_in_global_crosswalk'] += person not in mapped_people
                    team = player_teams.get((day, person))
                    counts['person_not_in_nba_day_logs'] += team is None
                    counts['team_disagrees_with_nba_day_log'] += team is not None and team != row['PLAYER_LAST_TEAM_ABBREVIATION']
                    counts['games_not_one'] += row['GP'] != 1
                    made, attempted = row[made_field], row[attempted_field]
                    counts['missing_or_invalid_attempts'] += (made is None or attempted is None or
                                                              made < 0 or attempted < 0 or made > attempted)
            categories[category] = {'expected_game_dates': len(expected), **dict(counts),
                                    'missing_dates': missing, 'missing_season_types': missing_types,
                                    'missing_url_or_fetch_time_dates': unknown_provenance}
        by_season[season] = {'multiple_season_types_same_date':
                             [{'date': day, 'types': sorted(types)} for day, types in sorted(expected.items()) if len(types) > 1],
                             'categories': categories}
    hashes = a1_reconcile.input_hashes()
    hashes[str((DERIVED / 'nbastats' / 'players.parquet').relative_to(ROOT))] = sha256_file(DERIVED / 'nbastats' / 'players.parquet')
    hashes.update({str(path.relative_to(ROOT)): sha256_file(path) for path in manifests})
    return {'experiment': 'a1_tracking_defence_coverage', 'as_of_et': as_of,
            'population': 'logged NBA game dates strictly before as_of_et, by retained response date/category',
            'join_rule': 'tracking responses for game date D can enter a forecast only after D; use person identity and '
                         'the dated NBA team, not a future team or the target game',
            'provenance_limit': 'fetch time records collection, not source publication or historical revision time; '
                                'a retained historical snapshot does not prove its contents were available unchanged '
                                'at an earlier forecast origin',
            'seasons': by_season, 'input_sha256': hashes}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output', type=Path, required=True, help='new report path; existing reports are never overwritten')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f'refusing to overwrite {args.output}')
    report = audit()
    write_json(args.output, report, pretty=True)
    print(f"saved {args.output}: {len(report['seasons'])} seasons audited")


if __name__ == '__main__':
    main()
