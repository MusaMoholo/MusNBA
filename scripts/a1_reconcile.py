#!/usr/bin/env python3
"""Audit retained NBA/ESPN crosswalk, player outcomes and possession conventions by season.

  .venv/bin/python scripts/a1_reconcile.py --output analysis/experiments/new-reconciliation.json
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, sha256_file, today_et, write_json  # noqa: E402
from scripts import nbastats  # noqa: E402


def quarantine_mapping(games: pd.DataFrame, mapping: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    if games[['nba_game', 'espn_game']].isna().any().any():
        raise ValueError('game crosswalk has missing IDs')
    if games['nba_game'].duplicated().any() or games['espn_game'].duplicated().any():
        raise ValueError('game crosswalk is not one-to-one')
    if mapping[['nba_game', 'person', 'espn_game']].isna().any().any():
        raise ValueError('player crosswalk has missing game or NBA person IDs')
    if mapping.duplicated(['nba_game', 'person']).any():
        raise ValueError('NBA player-game occurs more than once in crosswalk')
    valid_id = mapping['player'].astype('string').str.fullmatch(r'\d+', na=False)
    invalid = mapping.loc[~valid_id, ['nba_game', 'person', 'espn_game', 'player', 'stage']].copy()
    invalid = invalid.astype(object).where(invalid.notna(), None).to_dict('records')
    clean = mapping.loc[valid_id].copy()
    if clean.duplicated(['espn_game', 'player']).any():
        raise ValueError('ESPN player-game occurs more than once in crosswalk')
    linked = clean[['nba_game', 'espn_game']].merge(
        games[['nba_game', 'espn_game']], on=['nba_game', 'espn_game'], how='left', indicator=True)
    if linked['_merge'].ne('both').any():
        raise ValueError('player crosswalk references an inconsistent game pair')
    return clean, invalid


def differences(left: pd.Series, right: pd.Series) -> dict:
    known = left.notna() & right.notna()
    return {'known': int(known.sum()), 'missing_either': int((~known).sum()),
            'different': int(left[known].ne(right[known]).sum())}


def seconds_difference(nba: pd.Series, on_court: pd.Series) -> dict:
    known = nba.notna() & on_court.notna()
    delta = (on_court[known] - nba[known]).abs()
    return {'known': int(known.sum()), 'missing_either': int((~known).sum()),
            'median_abs_seconds': float(delta.median()) if len(delta) else None,
            'p90_abs_seconds': float(delta.quantile(0.9)) if len(delta) else None,
            'over_30_seconds': int(delta.gt(30).sum()), 'over_60_seconds': int(delta.gt(60).sum())}


def possession_summary(team_games: pd.DataFrame) -> dict:
    missing = team_games['poss'].isna()
    flagged = team_games['ok'].eq(False).fillna(False)  # noqa: E712
    valid = ~missing & team_games['ok'].eq(True).fillna(False) & team_games['POSS'].notna()  # noqa: E712
    delta = team_games.loc[valid, 'poss'] - team_games.loc[valid, 'POSS']
    return {'team_games': len(team_games), 'without_segments': int(missing.sum()),
            'parser_flagged_team_games': int(flagged.sum()), 'compared_team_games': int(valid.sum()),
            'nba_mean': float(team_games.loc[valid, 'POSS'].mean()) if len(delta) else None,
            'segment_mean': float(team_games.loc[valid, 'poss'].mean()) if len(delta) else None,
            'segment_minus_nba_mean': float(delta.mean()) if len(delta) else None,
            'absolute_difference_over_2': int(delta.abs().gt(2).sum()),
            'absolute_difference_over_5': int(delta.abs().gt(5).sum()),
            'games_without_segments': sorted(team_games.loc[missing, 'espn_game'].astype(str).unique()),
            'parser_flagged_games': sorted(team_games.loc[flagged, 'espn_game'].astype(str).unique())}


def input_hashes() -> dict:
    paths = [DERIVED / 'nbastats' / 'games.parquet', DERIVED / 'nbastats' / 'player_games_map.parquet',
             DERIVED / 'player_games.csv', DERIVED / 'segments.parquet', DERIVED / 'rotations' / 'on_court.parquet']
    paths += sorted((ROOT / 'data' / 'raw' / 'hoopr').glob('player_box_*.parquet'))
    paths += sorted((ROOT / 'data' / 'raw' / 'nbastats' / 'gamelogs').glob('*/*.json.gz'))
    paths += sorted((DERIVED / 'history').glob('*/on_court.parquet'))
    paths += sorted((DERIVED / 'history').glob('*/segments.parquet'))
    return {str(path.relative_to(ROOT)): sha256_file(path) for path in paths}


def audit() -> dict:
    as_of = today_et()
    team, players = nbastats.nba_tables()
    espn = nbastats.espn_tables()
    games = pd.read_parquet(DERIVED / 'nbastats' / 'games.parquet')
    mapping = pd.read_parquet(DERIVED / 'nbastats' / 'player_games_map.parquet')
    team = team[team['date'] < as_of].copy()
    players = players[players['date'] < as_of].copy()
    games = games[games['date'].astype(str) < as_of].copy()
    mapping = mapping[mapping['nba_game'].isin(games['nba_game'])].copy()
    clean, invalid = quarantine_mapping(games, mapping)

    p = players.rename(columns={'GAME_ID': 'nba_game', 'PLAYER_ID': 'person'})
    matched = clean.merge(p, on=['nba_game', 'person'], how='left', validate='one_to_one', indicator=True)
    if matched['_merge'].ne('both').any():
        raise ValueError('player crosswalk references an absent NBA player-game')
    matched = matched.drop(columns='_merge')
    matched = matched.merge(
        espn[['game_id', 'player', 'pts', 'min', 'fga', 'reb', 'ast', 'did_not_play']].rename(
            columns={'game_id': 'espn_game'}), on=['espn_game', 'player'], how='left', validate='one_to_one',
        indicator='espn_join')
    on_court = nbastats._on_court().rename(columns={'game_id': 'espn_game'})
    matched = matched.merge(on_court, on=['espn_game', 'player'], how='left', validate='one_to_one')

    t = team.rename(columns={'GAME_ID': 'nba_game'}).merge(
        games[['nba_game', 'espn_game', 'home_tc', 'away_tc', 'home_team', 'away_team']],
        on='nba_game', how='left', validate='many_to_one', indicator='game_join')
    mapped_t = t[t['game_join'].eq('both')].copy()
    home = mapped_t['TEAM_ABBREVIATION'].eq(mapped_t['home_tc'])
    away = mapped_t['TEAM_ABBREVIATION'].eq(mapped_t['away_tc'])
    if (~(home | away)).any() or (home & away).any():
        raise ValueError('NBA team does not match exactly one ESPN game side')
    mapped_t['offense'] = np.where(home, mapped_t['home_team'], mapped_t['away_team']).astype(str)
    segments = nbastats._segment_poss().rename(columns={'game_id': 'espn_game'})
    mapped_t = mapped_t.merge(segments, on=['espn_game', 'offense'], how='left', validate='one_to_one')

    results = {}
    for season in sorted(team['season'].unique()):
        pg = matched[matched['season'].eq(season)]
        tg = t[t['season'].eq(season)]
        tm = mapped_t[mapped_t['season'].eq(season)]
        eligible = players[players['season'].eq(season)]
        results[season] = {
            'nba_games': int(tg['nba_game'].nunique()), 'game_crosswalk_missing_team_games': int(tg['game_join'].ne('both').sum()),
            'nba_player_games': len(eligible), 'mapped_player_games_with_id': len(pg),
            'nba_player_games_without_usable_mapping': len(eligible) - len(pg),
            'mapped_player_games_missing_espn_row': int(pg['espn_join'].ne('both').sum()),
            'points': differences(pg['PTS'], pg['pts']), 'field_goal_attempts': differences(pg['FGA'], pg['fga']),
            'rebounds': differences(pg['REB'], pg['reb']), 'assists': differences(pg['AST'], pg['ast']),
            'on_court_vs_nba': seconds_difference(pg['sec_nba'], pg['sec']),
            'espn_zero_minutes_but_nba_positive_seconds': int((pg['min'].eq(0) & pg['sec_nba'].gt(0)).sum()),
            'espn_dnp_but_nba_positive_seconds': int((pg['did_not_play'].eq(True) & pg['sec_nba'].gt(0)).sum()),  # noqa: E712
            'possessions': possession_summary(tm),
        }
    return {'experiment': 'a1_data_reconciliation', 'as_of_et': as_of,
            'population': 'logged NBA regular season, playoffs, play-in and Cup games strictly before as_of_et; '
                          'matched ESPN boxes and retained parser outputs, not model forecasts',
            'possessions_convention': 'NBA team POSS versus distinct ESPN segment possession IDs; only parser '
                                      'game_ok team-games are compared, and convention differences are not errors',
            'quarantined_crosswalk_rows': invalid, 'seasons': results, 'input_sha256': input_hashes()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output', type=Path, required=True, help='new report path; existing reports are never overwritten')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f'refusing to overwrite {args.output}')
    report = audit()
    write_json(args.output, report, pretty=True)
    print(f"saved {args.output}: {len(report['quarantined_crosswalk_rows'])} invalid player IDs quarantined")


if __name__ == '__main__':
    main()
