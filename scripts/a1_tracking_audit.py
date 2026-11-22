#!/usr/bin/env python3
"""Reconstruct prior defender histories independently and audit every saved shot feature."""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, sha256_file, write_json  # noqa: E402
from scripts import a1_tracking_coverage, fetch_nbastats, nbastats, nodes  # noqa: E402
from scripts.evaluate import FOLDS, TEST_FROM  # noqa: E402

BUCKETS = {'rim': 'Less Than 6Ft', 'three': '3 Pointers'}
SEASONS = tuple(season for season in fetch_nbastats.SEASONS if season != '2026-27')


def sources() -> tuple[dict, int]:
    _, logs = nbastats.nba_tables(list(SEASONS))
    logs = logs.loc[logs['date'] < TEST_FROM, ['date', 'PLAYER_ID', 'TEAM_ABBREVIATION']].drop_duplicates()
    if logs.duplicated(['date', 'PLAYER_ID']).any():
        raise ValueError('auditor found ambiguous NBA player/day teams')
    day_teams = {(str(r.date), int(r.PLAYER_ID)): str(r.TEAM_ABBREVIATION) for r in logs.itertuples(index=False)}
    people = pd.read_parquet(DERIVED / 'nbastats/players.parquet')
    if people[['person', 'player']].isna().any().any() or people['person'].duplicated().any() or people['player'].duplicated().any():
        raise ValueError('auditor found an invalid identity crosswalk')
    mapping = dict(zip(people['person'].astype(int), people['player'].astype(str)))
    games = fetch_nbastats.logged_games(list(SEASONS))
    result: dict[str, list[tuple[str, str, float, float]]] = defaultdict(list)
    files = 0
    for season in SEASONS:
        days = sorted({day for game_season, _, _, day in games if game_season == season and day < TEST_FROM})
        folder = fetch_nbastats.NBA_RAW / 'leaguedashptdefend' / season
        manifest = json.loads((folder / 'manifest.json').read_text())
        for day in days:
            for bucket, category in BUCKETS.items():
                key = f'{category.lower().replace(" ", "")}_{day}'
                path = folder / f'{key}.json.gz'
                _, source = a1_tracking_coverage.decode(path, manifest[key], season, day, category)
                made_field, attempts_field = a1_tracking_coverage.ATTEMPT_FIELDS[category]
                seen = set()
                for row in source:
                    person = int(row['CLOSE_DEF_PERSON_ID'])
                    if person in seen or (day, person) not in day_teams or person not in mapping or row['GP'] != 1:
                        raise ValueError(f'{path}: duplicate or unresolved source identity')
                    seen.add(person)
                    made, attempted = float(row[made_field]), float(row[attempts_field])
                    if not np.isfinite(made) or not np.isfinite(attempted) or not 0 <= made <= attempted:
                        raise ValueError(f'{path}: invalid defended-shot counts')
                    result[day].append((mapping[person], bucket, made, attempted))
                files += 1
    return result, files


def audit() -> dict:
    report_path = ROOT / 'analysis/experiments/20261122_a1_s04_tracking_features.json'
    feature_path = DERIVED / 'experiments/20261122_a1_s04_tracking_features.parquet'
    report = json.loads(report_path.read_text())
    if sha256_file(feature_path) != report['rows_sha256']:
        raise ValueError('saved tracking shot features do not match their report')
    for path, digest in report['input_sha256'].items():
        if sha256_file(ROOT / path) != digest:
            raise ValueError(f'tracking feature input changed: {path}')
    source, files = sources()
    if files != report['source']['files']:
        raise ValueError('independently counted source files differ')
    seg = nodes.load_segments()
    shots = seg.loc[(seg['end_type'] == 'shot') & ~seg['heave'] & seg['zone'].isin(nodes.ZONES)].copy()
    if 'lineup_valid' in shots:
        shots = shots.loc[shots['lineup_valid']]
    shots = shots.reset_index(drop=True)
    saved = pd.read_parquet(feature_path)
    result = np.where(shots['made'] == 1, np.where(shots['and_one'], 2, 1), 0)
    for name, actual in (('game_id', shots['game_id']), ('date_et', shots['date_et']),
                         ('zone', shots['zone']), ('outcome', result)):
        if not np.array_equal(saved[name], actual):
            raise ValueError(f'tracking shot {name} rows do not align')
    pregame = pd.read_parquet(
        DERIVED / f'variants/a1_scheduled_{next(iter(FOLDS))}_20261122_v3/features/pregame.parquet',
        columns=['game_id', 'player', 'team']).astype(str)
    if pregame.duplicated(['game_id', 'player']).any():
        raise ValueError('auditor found duplicate dated roster identities')
    teams = {(r.game_id, r.player): r.team for r in pregame.itertuples(index=False)}
    defender_columns = [f'def_{i}' for i in range(1, 6)]
    columns = ['game_id', 'date_et', 'defense', *defender_columns]
    unique = shots[columns].drop_duplicates().sort_values('date_et').reset_index(drop=True)
    history: dict[tuple[str, str], list[float]] = defaultdict(lambda: [0.0, 0.0])
    source_days = sorted(source)
    cursor = 0
    expected = []
    started = time.monotonic()
    for index, row in enumerate(unique.itertuples(index=False, name=None), 1):
        game, day, defence, *players = row
        while cursor < len(source_days) and source_days[cursor] < day:
            source_day = source_days[cursor]
            for player, bucket, made, attempted in source[source_day]:
                state = history[(player, bucket)]
                state[0] += made
                state[1] += attempted
            cursor += 1
        if cursor and source_days[cursor - 1] >= day:
            raise ValueError('auditor included a same-day or future tracking response')
        complete_five = all(pd.notna(player) for player in players) and len(set(players)) == 5
        values = [complete_five]
        for bucket in BUCKETS:
            rates = []
            for player in players:
                if pd.isna(player) or teams.get((str(game), str(player))) != str(defence):
                    rates.append(np.nan)
                    continue
                made, attempted = history[(str(player), bucket)]
                rates.append(made / attempted if attempted > 0 else np.nan)
            known = int(np.isfinite(rates).sum())
            values.extend((known, float(np.mean(rates)) if complete_five and known == 5 else np.nan))
        expected.append(values)
        if index % max(1, len(unique) // 10) == 0 or index == len(unique):
            print(f'tracking audit lineups {index}/{len(unique)} {time.monotonic() - started:.1f}s', flush=True)
    expected_columns = ['valid_five', 'rim_known_defenders', 'rim_five_mean',
                        'three_known_defenders', 'three_five_mean']
    for i, name in enumerate(expected_columns):
        unique[name] = [row[i] for row in expected]
    reconstructed = shots[columns].merge(unique, on=columns, how='left', validate='many_to_one', sort=False)
    if len(reconstructed) != len(saved):
        raise ValueError('independent lineup join changed the shot population')
    for name in expected_columns:
        if not np.allclose(reconstructed[name].to_numpy(dtype=float), saved[name].to_numpy(dtype=float),
                           rtol=0, atol=1e-12, equal_nan=True):
            raise ValueError(f'independently reconstructed {name} differs')
    return {'experiment': 'a1_s04_tracking_independent_accounting', 'source_files': files,
            'source_dates': len(source_days), 'unique_game_fives': len(unique), 'shots': len(saved),
            'checked_values': len(saved) * len(expected_columns),
            'feature_report_sha256': sha256_file(report_path), 'feature_rows_sha256': sha256_file(feature_path),
            'auditor_sha256': sha256_file(Path(__file__)),
            'limitations': 'dated raw responses and crosswalk may have been revised after their historic dates'}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f'refusing to overwrite {args.output}')
    print('independently rebuilding chronological defender histories and lineups', flush=True)
    result = audit()
    write_json(args.output, result, pretty=True)
    print(json.dumps(result, indent=1), flush=True)


if __name__ == '__main__':
    main()
