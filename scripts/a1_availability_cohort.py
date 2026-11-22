#!/usr/bin/env python3
"""Build the preregistered prior-box membership diagnostic, not an official roster forecast.

  .venv/bin/python scripts/a1_availability_cohort.py RUN --output report.json --rows-output cohort.parquet
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, atomic_bytes, write_json  # noqa: E402
from scripts import a1_compare  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS  # noqa: E402


def prior_membership(history: pd.DataFrame, day: str) -> tuple[pd.DataFrame, list[str]]:
    past = history.loc[history['day'] < day, ['day', 'player', 'team']]
    latest = past.groupby('player')['day'].transform('max')
    last = past.loc[past['day'].eq(latest)].drop_duplicates()
    team_counts = last.groupby('player')['team'].nunique()
    ambiguous = sorted(team_counts[team_counts > 1].index.tolist())
    members = last.loc[~last['player'].isin(ambiguous)].drop_duplicates('player')
    return members.rename(columns={'day': 'prior_day'}), ambiguous


def participation(box: pd.DataFrame) -> pd.Series:
    dnp = box['did_not_play'].astype('boolean')
    minutes = pd.to_numeric(box['minutes'], errors='raise')
    if minutes.lt(0).any():
        raise ValueError('box contains negative minutes')
    is_dnp = dnp.eq(True).fillna(False)
    if (is_dnp & minutes.gt(0)).any():
        raise ValueError('box marks a player DNP with positive minutes')
    played = dnp.eq(False).fillna(False) & minutes.gt(0)
    return pd.Series(np.select([is_dnp.to_numpy(dtype=bool), played.to_numpy(dtype=bool)],
                               [0.0, 1.0], default=np.nan), index=box.index)


def build(control: str) -> tuple[dict, pd.DataFrame]:
    log = json.loads((EXPERIMENTS / f'{control}.json').read_text())
    _, val_from, val_to = FOLDS[log['fold']]
    season = int(val_to[:4]) if val_to[5:7] <= '06' else int(val_to[:4]) + 1
    games = pd.read_parquet(DERIVED / 'experiments' / f'{control}.parquet',
                            columns=['game_id', 'date_et', 'home', 'away'])
    a1_compare._unique(games, ['game_id'], 'control games')
    if games.empty or not games['date_et'].between(val_from, val_to).all():
        raise ValueError('control games are empty or outside the declared fold dates')
    box = pd.read_parquet(ROOT / f'data/raw/hoopr/player_box_{season}.parquet',
                          columns=['game_id', 'game_date', 'athlete_id', 'team_id', 'season_type',
                                   'did_not_play', 'minutes', 'starter'])
    box = box.loc[box['season_type'].eq(2)].copy()
    if box[['game_id', 'game_date']].isna().any().any():
        raise ValueError('regular-season box contains missing game IDs or dates')
    box['game_id'] = box['game_id'].astype('int64').astype(str)
    box['day'] = pd.to_datetime(box['game_date'], errors='raise').dt.strftime('%Y-%m-%d')
    selected_raw = box.loc[box['game_id'].isin(games['game_id'])]
    missing_ids = int(selected_raw['athlete_id'].isna().sum())
    missing_teams = int(selected_raw['team_id'].isna().sum())
    box = box.dropna(subset=['athlete_id', 'team_id']).copy()
    box['player'] = box['athlete_id'].astype('int64').astype(str)
    box['team'] = box['team_id'].astype('int64').astype(str)
    a1_compare._unique(box, ['game_id', 'player'], 'regular-season box')
    box['played'] = participation(box)
    current = box.loc[box['game_id'].isin(games['game_id'])].copy()
    if set(current['game_id']) != set(games['game_id']):
        raise ValueError('one or more selected games are missing player boxes')
    dates = current[['game_id', 'day']].drop_duplicates()
    a1_compare._unique(dates, ['game_id'], 'box game dates')
    date_check = games.merge(dates, on='game_id', validate='one_to_one')
    if date_check['date_et'].ne(date_check['day']).any():
        raise ValueError('box dates do not match the control game dates')
    sides = current.merge(games[['game_id', 'home', 'away']], on='game_id', validate='many_to_one')
    if (~sides['team'].eq(sides['home']) & ~sides['team'].eq(sides['away'])).any():
        raise ValueError('a box player has a team outside the selected game')

    frames = []
    ambiguous_by_day = {}
    empty_teams = []
    for day_value, day_games in games.groupby('date_et', sort=True):
        day = str(day_value)
        members, ambiguous = prior_membership(box, day)
        ambiguous_by_day[day] = len(ambiguous)
        for game in day_games.itertuples():
            for team in (game.home, game.away):
                group = members.loc[members['team'].eq(team)].copy()
                if group.empty:
                    empty_teams.append({'game_id': game.game_id, 'team': team})
                frames.append(group.assign(game_id=game.game_id, date_et=day))
    candidates = pd.concat(frames, ignore_index=True)
    a1_compare._unique(candidates, ['game_id', 'player'], 'pre-game inferred membership')
    if candidates['prior_day'].ge(candidates['date_et']).any():
        raise ValueError('candidate membership includes a same-day or future record')
    joined = candidates.merge(current[['game_id', 'player', 'team', 'played', 'minutes', 'starter']],
                              on=['game_id', 'player', 'team'], how='left', validate='one_to_one', indicator=True)
    joined['listed_in_box'] = joined.pop('_merge').eq('both')
    realised = current.merge(candidates[['game_id', 'player', 'team']], on=['game_id', 'player', 'team'],
                             how='left', validate='one_to_one', indicator=True)
    outside = realised.loc[realised['_merge'].eq('left_only')]
    unseen = outside.loc[outside['played'].eq(1)]
    day_teams = box[['day', 'player', 'team']].drop_duplicates()
    day_teams = day_teams.groupby(['day', 'player'])['team'].agg(list).reset_index()
    later = joined.merge(day_teams, left_on=['date_et', 'player'], right_on=['day', 'player'],
                         how='left', suffixes=('', '_same_day'), validate='many_to_one')
    conflicting = later.apply(lambda r: isinstance(r['team_same_day'], list) and len(r['team_same_day']) == 1
                               and r['team_same_day'][0] != r['team'], axis=1)
    counts = joined.groupby('game_id').agg(candidates=('player', 'size'),
                                            listed=('listed_in_box', 'sum'),
                                            labelled=('played', 'count')).reset_index()
    report = {
        'experiment': 'a1_prior_box_availability_coverage',
        'control_run': control, 'fold': log['fold'], 'season': season, 'games': len(games),
        'method': 'Construct each game/team candidate universe from same-season box records strictly before its date; '
                  'assign each player to their latest uniquely observed team, then join the current box for coverage only.',
        'labels': 'DNP is not played; non-DNP positive box minutes is played; zero/missing minutes and unlisted '
                  'players remain unknown. No probability or predictive accuracy is evaluated.',
        'candidate_player_games': len(joined), 'known_play_labels': int(joined['played'].notna().sum()),
        'played_labels': int(joined['played'].eq(1).sum()), 'dnp_labels': int(joined['played'].eq(0).sum()),
        'unlisted_candidates': int((~joined['listed_in_box']).sum()),
        'listed_unknown_play_labels': int((joined['listed_in_box'] & joined['played'].isna()).sum()),
        'observed_box_player_games': len(current), 'box_player_games_outside_universe': len(outside),
        'unseen_positive_minute_player_games': len(unseen),
        'games_with_unseen_positive_minute_players': int(unseen['game_id'].nunique()),
        'outside_universe_dnp_player_games': int(outside['played'].eq(0).sum()),
        'outside_universe_unknown_play_labels': int(outside['played'].isna().sum()),
        'same_day_conflicting_team_listings': int(conflicting.sum()),
        'raw_box_rows_without_player_id': missing_ids,
        'raw_box_rows_without_team_id': missing_teams,
        'team_games_without_prior_candidates': empty_teams,
        'origin_dates_with_ambiguous_latest_teams': {k: v for k, v in ambiguous_by_day.items() if v},
        'per_game': counts.to_dict(orient='records'),
        'limitations': 'Prior boxes are retrospectively retained, without historical publication/correction timestamps; '
                       'inferred membership is not an official dated roster or injury report. Unlisted players and '
                       'zero/missing minutes remain unknown; later listings are diagnostic only.',
    }
    return report, joined


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('control')
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--rows-output', type=Path, required=True)
    args = ap.parse_args()
    if args.output.resolve() == args.rows_output.resolve():
        raise ValueError('report and cohort rows must use different output paths')
    for path in (args.output, args.rows_output):
        if path.exists():
            raise FileExistsError(f'refusing to overwrite {path}')
    report, rows = build(args.control)
    report['rows_output'] = str(args.rows_output)
    data = rows.to_parquet(index=False)
    atomic_bytes(args.rows_output, data)
    write_json(args.output, report, pretty=True)
    print(json.dumps({k: v for k, v in report.items() if k != 'per_game'}, indent=2))


if __name__ == '__main__':
    main()
