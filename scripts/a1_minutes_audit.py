#!/usr/bin/env python3
"""Audit pre-origin minutes/rotation populations on the fixed A1 development games."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, atomic_bytes, sha256_file, write_json  # noqa: E402
from scripts import a1_availability_cohort, a1_compare, a1_signal  # noqa: E402
from scripts.evaluate import EXPERIMENTS  # noqa: E402

CONTROL = '20261122T022323Z_a1_s01_control'
MEMBERSHIP = DERIVED / 'experiments' / '20261122_a1_prior_box_membership_nba_only.parquet'
BOX = ROOT / 'data/raw/hoopr/player_box_2026.parquet'


def prior_join(candidates: pd.DataFrame, events: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Attach the latest strictly earlier player event, never another event on the origin date."""
    left = candidates.copy()
    right = events[['day', 'player', *columns]].copy()
    left['date_et'] = pd.to_datetime(left['date_et'], errors='raise').astype('datetime64[ns]')
    right['day'] = pd.to_datetime(right['day'], errors='raise').astype('datetime64[ns]')
    left = left.sort_values(['date_et', 'player'], kind='stable')
    right = right.sort_values(['day', 'player'], kind='stable')
    if right.duplicated(['day', 'player']).any():
        raise ValueError('prior event stream has multiple records per player and date')
    out = pd.merge_asof(left, right, left_on='date_et', right_on='day', by='player',
                        direction='backward', allow_exact_matches=False)
    if (out['day'].notna() & out['day'].ge(out['date_et'])).any():
        raise ValueError('same-day or future record entered the pre-origin features')
    return out


def historical_features(box: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    teams = box[['day', 'player', 'team']].drop_duplicates().sort_values(
        ['player', 'day', 'team'], kind='stable').copy()
    if teams.duplicated(['day', 'player']).any():
        raise ValueError('ambiguous player team on one date cannot be assigned a transfer history')
    previous = teams.groupby('player')['team'].shift()
    changed = previous.notna() & teams['team'].ne(previous)
    teams['last_team_change'] = teams['day'].where(changed).groupby(teams['player']).ffill()
    teams = teams.rename(columns={'team': 'last_observed_team'})

    appearances = box.loc[box['played'].eq(1), ['day', 'player', 'team', 'minutes']].sort_values(
        ['player', 'day'], kind='stable').copy()
    if appearances.duplicated(['day', 'player']).any():
        raise ValueError('a player has multiple positive-minute appearances on one date')
    appearances['prior_appearances'] = appearances.groupby('player').cumcount() + 1
    appearances['recent_five_minutes'] = (
        appearances.groupby('player')['minutes'].rolling(5, min_periods=1).mean()
        .reset_index(level=0, drop=True).sort_index()
    )
    return teams, appearances


def summarise(rows: pd.DataFrame) -> dict:
    valid_history = rows['prior_appearances'].ge(3)
    fringe = valid_history & rows['recent_five_minutes'].lt(10)
    core = valid_history & rows['recent_five_minutes'].ge(25)
    transfer = rows['days_since_team_change'].between(0, 30)
    returning = rows['played'].eq(1) & core & rows['team_games_since_appearance'].ge(5)
    dnp_core = core & rows['played'].eq(0)
    unknown_core = core & rows['played'].isna()

    def counts(mask: pd.Series) -> dict:
        group = rows.loc[mask]
        return {'player_games': len(group), 'games': int(group['game_id'].nunique()),
                'played': int(group['played'].eq(1).sum()), 'dnp_coach': int(group['dnp_coach'].sum()),
                'other_dnp': int((group['played'].eq(0) & ~group['dnp_coach']).sum()),
                'unknown': int(group['played'].isna().sum())}

    return {
        'all_prior_box_candidates': counts(pd.Series(True, index=rows.index)),
        'fringe_lt_10_recent_minutes': counts(fringe),
        'core_ge_25_recent_minutes': counts(core),
        'recent_team_change_30_days': counts(transfer),
        'core_first_appearance_after_5_team_games': counts(returning),
        'team_games_with_recorded_core_dnp': int(rows.loc[dnp_core, ['game_id', 'team']].drop_duplicates().shape[0]),
        'team_games_with_unknown_core_status': int(rows.loc[unknown_core, ['game_id', 'team']].drop_duplicates().shape[0]),
        'missing_prior_appearance': int(rows['prior_appearances'].isna().sum()),
        'missing_team_change_history': int(rows['last_team_change'].isna().sum()),
    }


def build() -> tuple[dict, pd.DataFrame]:
    manifest = json.loads(a1_signal.MANIFEST.read_text())
    games_path = DERIVED / 'experiments' / f'{CONTROL}.parquet'
    games = a1_signal.fixed_games(pd.read_parquet(games_path), manifest)
    rows = pd.read_parquet(MEMBERSHIP)
    a1_compare._unique(rows, ['game_id', 'player'], 'prior-box membership')
    if set(rows['game_id']) != set(games['game_id']):
        raise ValueError('prior-box cohort and fixed games differ')
    raw = pd.read_parquet(BOX, columns=['game_id', 'game_date', 'athlete_id', 'team_id', 'season_type',
                                      'did_not_play', 'minutes', 'reason'])
    raw = raw.loc[raw['season_type'].eq(2)].dropna(subset=['game_id', 'game_date', 'athlete_id', 'team_id']).copy()
    raw['game_id'] = raw['game_id'].astype('int64').astype(str)
    raw['player'] = raw['athlete_id'].astype('int64').astype(str)
    raw['team'] = raw['team_id'].astype('int64').astype(str)
    raw['day'] = pd.to_datetime(raw['game_date'], errors='raise').dt.normalize()
    raw['minutes'] = pd.to_numeric(raw['minutes'], errors='raise')
    raw, excluded_non_nba = a1_availability_cohort.nba_team_records(
        raw, set(json.loads((DERIVED / 'teams.json').read_text())))
    raw['played'] = a1_availability_cohort.participation(raw)
    a1_compare._unique(raw, ['game_id', 'player'], 'historical raw boxes')

    dates = pd.to_datetime(rows['date_et'], errors='raise')
    rows['date_et'] = dates
    team_events, appearances = historical_features(raw)
    rows = prior_join(rows, team_events, ['last_observed_team', 'last_team_change']).rename(
        columns={'day': 'prior_team_date'})
    if rows['last_observed_team'].isna().any() or rows['last_observed_team'].ne(rows['team']).any():
        raise ValueError('prior team history disagrees with saved inferred membership')
    rows = prior_join(rows, appearances, ['prior_appearances', 'recent_five_minutes']).rename(
        columns={'day': 'prior_appearance_date'})
    rows['days_since_team_change'] = (rows['date_et'] - rows['last_team_change']).dt.days

    team_games = (raw[['day', 'game_id', 'team']].drop_duplicates()
                  .sort_values(['team', 'day', 'game_id'], kind='stable'))
    schedule = {team: np.sort(group['day'].to_numpy()) for team, group in team_games.groupby('team')}
    days_since = []
    for row in rows.itertuples():
        if pd.isna(row.prior_appearance_date):
            days_since.append(np.nan)
            continue
        if not isinstance(row.prior_appearance_date, pd.Timestamp) or not isinstance(row.date_et, pd.Timestamp):
            raise TypeError('historical and origin dates must be timestamps')
        days = schedule[row.team]
        prior = row.prior_appearance_date.to_datetime64()
        origin = row.date_et.to_datetime64()
        days_since.append(int(np.searchsorted(days, origin, side='left') -
                              np.searchsorted(days, prior, side='right')))
    rows['team_games_since_appearance'] = days_since
    labels = raw.loc[raw['game_id'].isin(games['game_id']), ['game_id', 'player', 'team', 'played', 'reason']]
    rows = rows.merge(labels, on=['game_id', 'player', 'team'], how='left', validate='one_to_one',
                      suffixes=('', '_raw'))
    same = rows['played'].eq(rows['played_raw']) | (rows['played'].isna() & rows['played_raw'].isna())
    if not same.all():
        raise ValueError('saved cohort labels do not match the retained raw boxes')
    rows['dnp_coach'] = rows['played'].eq(0) & rows['reason'].fillna('').str.upper().str.contains('COACH')
    report = {
        'experiment': 'a1_s05_prior_minutes_population_audit',
        'control': CONTROL,
        'method': 'Construct roster candidates from saved strictly prior-box membership, then join historical outcomes. '
                  'Pre-origin roles use each player’s last five positive-minute box appearances; recent team change '
                  'uses prior recorded team changes. Returning means a 25+ minute recent role and at least five current '
                  'team games since the prior appearance. No same-day event enters these features.',
        'limitations': 'Prior boxes lack historical publication timestamps and are not official dated rosters. '
                       'Recent minutes are a descriptive proxy, not D29 healthy role. Other DNPs are not rotation '
                       'failures, unknown/unlisted players stay unknown, and core-DNP groups use outcomes post hoc.',
        'games': len(games),
        **excluded_non_nba,
        'counts': summarise(rows),
        'input_sha256': {str(p.relative_to(ROOT)): sha256_file(p)
                         for p in (a1_signal.MANIFEST, games_path, MEMBERSHIP, BOX, Path(__file__))},
    }
    return report, rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=EXPERIMENTS / '20261122_a1_s05_minutes_population.json')
    parser.add_argument('--rows-output', type=Path, default=DERIVED / 'experiments' / '20261122_a1_s05_minutes_population.parquet')
    args = parser.parse_args()
    if args.output.exists() or args.rows_output.exists():
        raise FileExistsError('refusing to overwrite an existing population audit')
    report, rows = build()
    atomic_bytes(args.rows_output, rows.to_parquet(index=False))
    write_json(args.output, report, pretty=True)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
