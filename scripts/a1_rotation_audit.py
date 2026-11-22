#!/usr/bin/env python3
"""Audit recorded substitution opportunities and NBA matchup attempt totals by season.

  .venv/bin/python -m scripts.a1_rotation_audit --output analysis/experiments/new-rotation-audit.json
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, sha256_file, today_et, write_json  # noqa: E402
from scripts import a1_reconcile, nbastats  # noqa: E402

WINDOW_KEY = ['game_id', 'period', 'clock']


def window_summary(windows: pd.DataFrame, subs: pd.DataFrame) -> dict:
    if windows[WINDOW_KEY].isna().any().any() or subs[WINDOW_KEY].isna().any().any():
        raise ValueError('substitution window or event has a missing game, period or clock')
    if windows.duplicated(WINDOW_KEY).any():
        raise ValueError('substitution window key is not unique')
    if windows[['subs_home', 'subs_away']].isna().any().any():
        raise ValueError('substitution window has missing team counts')
    counts = subs.groupby(WINDOW_KEY).size().rename('actual').reset_index()
    joined = windows.merge(counts, on=WINDOW_KEY, how='outer', validate='one_to_one', indicator=True)
    orphans = joined['_merge'].eq('right_only')
    expected = joined['subs_home'] + joined['subs_away']
    actual = joined['actual'].fillna(0)
    mismatch = joined['_merge'].ne('right_only') & expected.ne(actual)
    n = windows['subs_home'] + windows['subs_away']
    repeated = subs.duplicated(WINDOW_KEY + ['team', 'player_in'], keep=False)
    return {'games': int(windows['game_id'].nunique()), 'windows': len(windows), 'substitutions': len(subs),
            'no_substitution_windows': int(n.eq(0).sum()), 'multiple_substitution_windows': int(n.gt(1).sum()),
            'both_teams_substitute_windows': int((windows['subs_home'].gt(0) & windows['subs_away'].gt(0)).sum()),
            'unclassified_substitution_windows': int((windows['kind'].eq('other') & n.gt(0)).sum()),
            'orphan_substitution_windows': int(orphans.sum()), 'window_count_mismatches': int(mismatch.sum()),
            'repeated_entering_player_rows_at_same_clock': int(repeated.sum())}


def matchup_summary(matchups: pd.DataFrame, players: pd.DataFrame) -> dict:
    key = ['nba_game', 'off_person', 'def_person']
    if matchups[key + ['fga']].isna().any().any():
        raise ValueError('matchup row has missing game, player or attempt count')
    duplicate = matchups.duplicated(key, keep=False)
    grouped = matchups.groupby(['nba_game', 'off_person'], as_index=False).agg(
        matchup_fga=('fga', 'sum'), matchup_pts=('pts', 'sum'))
    joined = grouped.merge(
        players[['GAME_ID', 'PLAYER_ID', 'FGA', 'PTS']].rename(
            columns={'GAME_ID': 'nba_game', 'PLAYER_ID': 'off_person'}),
        on=['nba_game', 'off_person'], how='left', validate='one_to_one', indicator=True)
    known = joined['FGA'].notna()
    matched = joined[known]
    denominator = matched['FGA'].sum()
    return {'matchup_rows': len(matchups), 'duplicate_attacker_defender_rows': int(duplicate.sum()),
            'attacker_games': len(joined), 'attacker_games_missing_nba_box': int((~known).sum()),
            'compared_attacker_games': len(matched), 'official_fga': int(denominator),
            'summed_matchup_fga': float(matched['matchup_fga'].sum()),
            'summed_matchup_fga_per_official_fga': float(matched['matchup_fga'].sum() / denominator) if denominator else None,
            'attacker_games_above_box_fga': int(matched['matchup_fga'].gt(matched['FGA']).sum()),
            'attacker_games_zero_box_fga_but_positive_matchup_fga':
                int((matched['FGA'].eq(0) & matched['matchup_fga'].gt(0)).sum())}


def audit() -> dict:
    as_of = today_et()
    _, players = nbastats.nba_tables()
    players = players[players['date'] < as_of]
    matchups = pd.read_parquet(DERIVED / 'nbastats' / 'matchups.parquet')
    season_by_game = players[['GAME_ID', 'season']].drop_duplicates()
    if season_by_game['GAME_ID'].duplicated().any():
        raise ValueError('one NBA game belongs to multiple seasons')
    matchups = matchups.merge(season_by_game, left_on='nba_game', right_on='GAME_ID', how='inner', validate='many_to_one')
    results = {}
    paths = [DERIVED / 'nbastats' / 'matchups.parquet']
    for season in sorted(players['season'].unique()):
        end_year = int(season[:4]) + 1
        folder = DERIVED / 'history' / str(end_year) if end_year < 2027 else DERIVED / 'rotations'
        window_path, sub_path = folder / 'windows.parquet', folder / 'subs.parquet'
        paths += [window_path, sub_path]
        windows, subs = pd.read_parquet(window_path), pd.read_parquet(sub_path)
        windows = windows[windows['date_et'].astype(str) < as_of]
        subs = subs[subs['date_et'].astype(str) < as_of]
        results[season] = {'windows': window_summary(windows, subs),
                           'matchups': matchup_summary(matchups[matchups['season'].eq(season)],
                                                       players[players['season'].eq(season)])}
    hashes = a1_reconcile.input_hashes()
    hashes.update({str(path.relative_to(ROOT)): sha256_file(path) for path in paths})
    return {'experiment': 'a1_rotation_and_matchup_integrity', 'as_of_et': as_of,
            'window_population': 'retained canonical ESPN games before as_of_et, including playoffs/play-in; '
                                 'recorded clock-grouped windows are not proof that every legal opportunity is observed',
            'matchup_population': 'retained NBA matchup attacker/defender rows joined to logged player-games before as_of_et',
            'unclassified_window_note': 'other marks feed windows without a recognised dead-ball type; it does not '
                                        'prove an illegal substitution',
            'seasons': results, 'input_sha256': hashes}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output', type=Path, required=True, help='new report path; existing reports are never overwritten')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f'refusing to overwrite {args.output}')
    report = audit()
    write_json(args.output, report, pretty=True)
    print(f"saved {args.output}: {len(report['seasons'])} season summaries")


if __name__ == '__main__':
    main()
