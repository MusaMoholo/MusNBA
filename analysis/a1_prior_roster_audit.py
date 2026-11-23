#!/usr/bin/env python3
"""Independently reconstruct the A1 prior-roster census from earlier raw identity/date records."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from basketball_common import read_json, sha256_file, write_json  # noqa: E402


def audit_fold(task: tuple[str, str, dict]) -> dict:
    fold, rows_file, expected = task
    rows = pd.read_parquet(ROOT / rows_file)
    rows = rows.loc[rows['fold'].eq(fold)].copy()
    original = pd.read_parquet(ROOT / f'data/derived/experiments/20261122_a1_s05_no_report_{fold}_corrected.parquet',
                               columns=['game_id', 'team', 'player', 'date_et', 'prior_day',
                                        'prior_profile_date', 'availability_fallback'])
    years = {'F1': 2024, 'F2': 2025, 'F3': 2026, 'F4': 2026}
    raw = pd.read_parquet(ROOT / f'data/raw/hoopr/player_box_{years[fold]}.parquet',
                          columns=['game_date', 'athlete_id', 'team_id', 'season_type'])
    raw = raw.loc[raw['season_type'].eq(2)].dropna(subset=['game_date', 'athlete_id', 'team_id']).copy()
    raw['day'] = pd.to_datetime(raw['game_date'], errors='raise').dt.strftime('%Y-%m-%d')
    raw['player'] = raw['athlete_id'].astype('int64').astype(str)
    raw['team'] = raw['team_id'].astype('int64').astype(str)
    teams = set(read_json(ROOT / 'data/derived/teams.json'))
    raw = raw.loc[raw['team'].isin(teams), ['day', 'team', 'player']].drop_duplicates()
    profiles = pd.read_parquet(ROOT / 'data/derived/variants/a1_causal_base_20261122_v2/features/pregame.parquet',
                               columns=['date_et', 'player', 'pos'])
    position = {(str(r.date_et), str(r.player)): r.pos for r in profiles.itertuples()}
    reconstructed_teams = []
    for (gid, team), part in rows.groupby(['game_id', 'team'], sort=True):
        day = part['date_et'].iloc[0]
        past = raw.loc[raw['day'].lt(day)]
        newest = past.sort_values('day').drop_duplicates('player', keep='last')[['player', 'day']]
        latest = newest.merge(past, on=['player', 'day'])
        ambiguous = set(latest.groupby('player')['team'].nunique().loc[lambda x: x.gt(1)].index)
        members = latest.loc[latest['team'].eq(team) & ~latest['player'].isin(ambiguous)].drop_duplicates('player')
        actual = set(zip(part['player'], part['prior_day']))
        truth = set(zip(members['player'], members['day']))
        if actual != truth:
            raise ValueError(f'{fold} {gid} {team}: prior raw membership differs')
        sure = part.loc[part['availability_fallback'].ge(.9)]
        pool = sure if len(sure) >= 5 else part.loc[part['availability_fallback'].gt(0)]
        bad = []
        for row in part.itertuples():
            pos = position.get((str(row.prior_profile_date), str(row.player)))
            known = isinstance(pos, str) and pos.strip().upper() in ('PG', 'SG', 'SF', 'PF', 'C', 'G', 'F', 'G-F', 'F-C')
            if bool(row.known_position) != known:
                raise ValueError(f'{fold} {gid} {row.player}: position interpretation differs: {pos!r}')
            if row.prior_day >= row.date_et or (pd.notna(row.prior_profile_date) and row.prior_profile_date >= row.date_et):
                raise ValueError('late input entered retained output')
            if row.player in set(pool['player']) and not known:
                bad.append(row.player)
        reconstructed_teams.append({'game': gid, 'team': team, 'supported': len(pool) >= 5 and not bad,
                                    'bad_positions': len(bad)})
    lookup = {(r['game_id'], r['team']): r for r in expected['teams']}
    for row in reconstructed_teams:
        reference = lookup[(row['game'], row['team'])]
        if (row['supported'] != reference['supported_starter_pool'] or
                row['bad_positions'] != len(reference['starter_pool_missing_positions'])):
            raise ValueError('reconstructed starter-pool accounting differs')
    keys = ['game_id', 'team', 'player']
    if set(map(tuple, original[keys].to_numpy())) != set(map(tuple, rows[keys].to_numpy())):
        raise ValueError('saved output lost or added candidates')
    return {'fold': fold, 'raw_memberships_checked': len(rows), 'team_pools_checked': len(lookup),
            'missing_roster_games': expected['missing_roster_games'],
            'supported_games': expected['supported_starter_pool_games']}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite independent audit')
    source = read_json(args.report)
    if sha256_file(ROOT / source['rows']) != source['rows_sha256']:
        raise ValueError('census output fingerprint differs')
    for path, digest in source['fingerprints'].items():
        if sha256_file(ROOT / path) != digest:
            raise ValueError(f'census input/source fingerprint differs: {path}')
    with ProcessPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(audit_fold, [(item['fold'], source['rows'], item) for item in source['folds']]))
    write_json(args.output, {'kind': 'independent prior raw membership and starter-pool census audit',
                            'source': str(args.report), 'source_sha256': sha256_file(args.report),
                            'auditor_sha256': sha256_file(Path(__file__)), 'folds': results,
                            'status': 'passed', 'no_accuracy_or_injury_calibration_claim': True}, pretty=True)
    print(results)


if __name__ == '__main__':
    main()
