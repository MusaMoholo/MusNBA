#!/usr/bin/env python3
"""Independently reconstruct development DNP/rest sequence observations."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, NBA_TEAM_IDS, sha256_file, write_json  # noqa: E402
from scripts.evaluate import EXPERIMENTS, TEST_FROM  # noqa: E402

REPORT = EXPERIMENTS / '20261122_a1_s07_sequences.json'
ROWS = DERIVED / 'experiments/20261122_a1_s07_sequences.parquet'
SEASONS = (2023, 2024, 2025, 2026)
KEYS = ['season', 'team', 'player', 'prior_game_id']


def reason(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        return 'missing_reason'
    text = value.strip().upper()
    if 'COACH' in text:
        return 'coach'
    if text == 'REST':
        return 'rest'
    if 'INJURY' in text or 'ILLNESS' in text:
        return 'explicit_injury_or_illness'
    return 'other_recorded_reason'


def reconstruct(season: int) -> tuple[pd.DataFrame, dict, list[Path]]:
    box_path = ROOT / f'data/raw/hoopr/player_box_{season}.parquet'
    segments_path = DERIVED / f'history/{season}/segments.parquet'
    raw = pd.read_parquet(box_path, columns=['season', 'season_type', 'game_id', 'game_date', 'team_id',
                                             'athlete_id', 'did_not_play', 'minutes', 'reason'])
    raw = raw.loc[raw['season_type'].eq(2)].copy()
    missing_schedule = int(raw[['game_id', 'game_date', 'team_id']].isna().any(axis=1).sum())
    raw = raw.dropna(subset=['game_id', 'game_date', 'team_id']).copy()
    raw['game_id'] = raw['game_id'].astype('int64').astype(str)
    raw['team'] = raw['team_id'].astype('int64').astype(str)
    raw = raw.loc[raw['team'].isin(NBA_TEAM_IDS)].copy()
    raw['day'] = pd.to_datetime(raw['game_date'], errors='raise').dt.strftime('%Y-%m-%d')
    if not raw['season'].eq(season).all() or raw['day'].ge(TEST_FROM).any():
        raise ValueError(f'{season}: raw source violates season or protected cutoff')
    sides_box = raw[['season', 'team', 'game_id', 'day']].drop_duplicates()
    seg = pd.read_parquet(segments_path, columns=['game_id', 'date_et', 'season_type', 'offense', 'defense'])
    seg = seg.loc[seg['season_type'].eq(2)].copy()
    sides_segments = pd.concat([
        pd.DataFrame({'season': season, 'team': seg[side].astype(str), 'game_id': seg['game_id'].astype(str),
                      'day': pd.to_datetime(seg['date_et'], errors='raise').dt.strftime('%Y-%m-%d')})
        for side in ('offense', 'defense')
    ]).drop_duplicates()
    sides_segments = sides_segments.loc[sides_segments['team'].isin(NBA_TEAM_IDS)]
    source_join = sides_box.merge(sides_segments, how='outer', indicator=True)
    source_counts = {str(k): int(v) for k, v in source_join['_merge'].value_counts().items()}
    schedule = source_join.drop(columns='_merge').sort_values(['team', 'day', 'game_id']).reset_index(drop=True)
    if (schedule.duplicated(['season', 'team', 'game_id']).any()
            or schedule.duplicated(['season', 'team', 'day']).any()
            or not schedule.groupby('game_id')['team'].nunique().eq(2).all()
            or schedule['day'].ge(TEST_FROM).any()):
        raise ValueError(f'{season}: schedule identity, chronology or cutoff is invalid')
    schedule['team_index'] = schedule.groupby(['season', 'team']).cumcount()
    missing_player = int(raw['athlete_id'].isna().sum())
    raw = raw.dropna(subset=['athlete_id']).copy()
    raw['player'] = raw['athlete_id'].astype('int64').astype(str)
    if raw.duplicated(['game_id', 'player']).any():
        raise ValueError(f'{season}: duplicate player-game box labels')
    dnp = raw['did_not_play'].astype('boolean')
    mins = pd.to_numeric(raw['minutes'], errors='raise')
    if mins.lt(0).any() or (dnp.eq(True).fillna(False) & mins.gt(0)).any():
        raise ValueError(f'{season}: contradictory minutes and DNP')
    raw['status'] = np.select(
        [dnp.eq(True).fillna(False).to_numpy(dtype=bool),
         (dnp.eq(False).fillna(False) & mins.gt(0)).to_numpy(dtype=bool)],
        ['dnp', 'play'], default='unknown')
    raw['reason_check'] = raw['reason'].map(reason)
    raw = raw.merge(schedule, on=['season', 'team', 'game_id', 'day'], validate='many_to_one')
    if raw['team_index'].isna().any():
        raise ValueError(f'{season}: missing team-game index')

    by_team = raw.sort_values(['season', 'team', 'player', 'team_index'], kind='stable').copy()
    player_group = by_team.groupby(['season', 'team', 'player'], sort=False)
    previous_index = player_group['team_index'].shift()
    previous_status = player_group['status'].shift()
    contiguous = by_team['team_index'].eq(previous_index + 1)
    starts = by_team['status'].eq('dnp') & ~(contiguous & previous_status.eq('dnp'))
    by_team['spell_id'] = starts.groupby([by_team['season'], by_team['team'], by_team['player']]).cumsum()
    by_team['start_complete'] = starts & contiguous & previous_status.eq('play')
    dnp_rows = by_team.loc[by_team['status'].eq('dnp')].copy()
    spell_group = dnp_rows.groupby(['season', 'team', 'player', 'spell_id'], sort=False)
    dnp_rows['length_check'] = spell_group.cumcount() + 1
    dnp_rows['complete_check'] = spell_group['start_complete'].transform('first')
    dnp_rows['reason_first'] = spell_group['reason_check'].transform('first')
    by_team = by_team.merge(
        dnp_rows[['season', 'team', 'player', 'game_id', 'length_check', 'complete_check', 'reason_first']],
        on=['season', 'team', 'player', 'game_id'], how='left', validate='one_to_one')

    plays = by_team.loc[by_team['status'].eq('play'),
                        ['season', 'team', 'player', 'team_index', 'minutes']].copy()
    plays['role_mean'] = plays.groupby(['season', 'team', 'player'], sort=False)['minutes'].transform(
        lambda values: values.rolling(5, min_periods=1).mean())
    asof_keys = ['season', 'team', 'player']
    left = by_team.sort_values('team_index', kind='stable')
    right = plays[asof_keys + ['team_index', 'role_mean']].sort_values('team_index', kind='stable')
    by_team = pd.merge_asof(left, right, on='team_index', by=asof_keys, direction='backward')
    means = by_team['role_mean']
    by_team['role_check'] = np.select(
        [means.ge(30), means.ge(18), means.notna()], ['star', 'starter', 'bench'], default='unknown')

    all_players = raw.sort_values(['season', 'player', 'day', 'game_id', 'team'], kind='stable').copy()
    next_group = all_players.groupby(['season', 'player'], sort=False)
    all_players['next_seen_day'] = next_group['day'].shift(-1)
    all_players['next_seen_team'] = next_group['team'].shift(-1)
    future = all_players[['season', 'team', 'player', 'game_id', 'next_seen_day', 'next_seen_team']]
    current = by_team.loc[by_team['status'].isin(['play', 'dnp'])].copy()
    current = current.merge(future, on=['season', 'team', 'player', 'game_id'], validate='one_to_one')
    current['next_index'] = current['team_index'] + 1
    targets = schedule[['season', 'team', 'team_index', 'game_id', 'day']].rename(
        columns={'team_index': 'next_index', 'game_id': 'next_game', 'day': 'next_day'})
    current = current.merge(targets, on=['season', 'team', 'next_index'], how='left', validate='many_to_one')
    actual = raw[['season', 'team', 'player', 'game_id', 'status', 'reason_check']].rename(
        columns={'game_id': 'next_game', 'status': 'actual_status', 'reason_check': 'actual_reason'})
    current = current.merge(actual, on=['season', 'team', 'player', 'next_game'], how='left',
                            validate='many_to_one')
    next_day, seen_day, seen_team = current['next_day'], current['next_seen_day'], current['next_seen_team']
    other = (next_day.notna() & seen_day.notna() & seen_day.le(next_day) & seen_team.ne(current['team'])).fillna(False)
    current['state_check'] = np.select(
        [next_day.isna(), other & seen_day.lt(next_day), other, current['actual_status'].isna()],
        ['season_end', 'team_change_prior', 'same_day_other_team', 'unlisted'],
        default=current['actual_status'].fillna('unlisted'))
    is_dnp = current['status'].eq('dnp')
    complete = current['complete_check'].fillna(False).astype(bool)
    current['cohort_check'] = np.select(
        [~is_dnp, complete], ['rest', 'return'], default='left_censored_return')
    current['reason_prior_check'] = current['reason_first'].where(is_dnp)
    current['duration_check'] = current['length_check'].where(is_dnp)
    duration = np.select([is_dnp & current['length_check'].eq(1), is_dnp & current['length_check'].le(3),
                          is_dnp & current['length_check'].ge(4)], ['1', '2-3', '4+'], default='')
    current['duration_bin_check'] = pd.Series(duration, index=current.index).where(is_dnp)
    current['reason_next_check'] = current['actual_reason'].where(current['state_check'].eq('dnp'))
    current['outcome_check'] = np.nan
    returning = current['cohort_check'].eq('return')
    rest = current['cohort_check'].eq('rest')
    current.loc[returning & current['state_check'].eq('play'), 'outcome_check'] = 1
    current.loc[returning & current['state_check'].eq('dnp'), 'outcome_check'] = 0
    current.loc[rest & current['state_check'].eq('play'), 'outcome_check'] = 0
    known_reason = rest & current['state_check'].eq('dnp') & current['actual_reason'].ne('missing_reason')
    current.loc[known_reason, 'outcome_check'] = current.loc[known_reason, 'actual_reason'].eq('rest').astype(int)
    current = current.rename(columns={'game_id': 'prior_game_id', 'day': 'prior_day_check'})
    counts = {
        'season': season, 'team_games': len(schedule), 'box_player_listings': len(raw),
        'rows_missing_schedule_identity': missing_schedule, 'rows_missing_player_id': missing_player,
        'schedule_source_coverage': source_counts, 'observations': len(current),
    }
    return current, counts, [box_path, segments_path]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f'refusing to overwrite {args.output}')
    report = json.loads(REPORT.read_text())
    for section in ('input_sha256', 'output_sha256'):
        for path, digest in report[section].items():
            if sha256_file(ROOT / path) != digest:
                raise ValueError(f'sequence fingerprint differs: {path}')
    saved = pd.read_parquet(ROWS)
    if saved.duplicated(KEYS).any() or len(saved) != report['rows']:
        raise ValueError('saved sequence keys or count are invalid')
    inputs = [Path(__file__), REPORT, ROWS]
    results = []
    columns = {
        'prior_day': 'prior_day_check', 'game_id': 'next_game', 'date_et': 'next_day',
        'cohort': 'cohort_check', 'prior_role': 'role_check', 'prior_reason': 'reason_prior_check',
        'prior_duration': 'duration_check', 'duration_bin': 'duration_bin_check',
        'next_status': 'state_check', 'next_reason': 'reason_next_check', 'outcome': 'outcome_check',
    }
    for season in SEASONS:
        rebuilt, counts, paths = reconstruct(season)
        original = saved.loc[saved['season'].eq(season)]
        joined = original.merge(rebuilt[KEYS + list(columns.values())], on=KEYS, how='outer',
                                suffixes=('_saved', '_check'), indicator=True, validate='one_to_one')
        if joined['_merge'].ne('both').any():
            raise ValueError(f'{season}: source and saved sequence keys differ')
        for field, check in columns.items():
            left, right = joined[field], joined[check]
            equal = left.eq(right) | (left.isna() & right.isna())
            if not equal.fillna(False).all():
                raise ValueError(f'{season}: {field} differs on {int((~equal.fillna(False)).sum())} observations')
        expected = next(value for value in report['seasons'] if value['season'] == season)
        for field in ('team_games', 'box_player_listings', 'rows_missing_schedule_identity',
                      'rows_missing_player_id', 'schedule_source_coverage'):
            if counts[field] != expected[field]:
                raise ValueError(f'{season}: {field} coverage differs')
        if counts['observations'] != expected['sequence_rows']:
            raise ValueError(f'{season}: observation count differs')
        results.append(counts)
        inputs.extend(paths)
        print(f'{season}: independently checked {len(joined)} sequence observations', flush=True)
    if sum(item['observations'] for item in results) != len(saved):
        raise ValueError('season observations do not cover the saved sequence rows')
    result = {
        'experiment': 'a1_s07_development_recorded_dnp_sequence_independent_audit',
        'rows_checked': len(saved), 'fields_per_row': len(columns), 'seasons': results,
        'limitations': 'Reconstruction uses retained retrospective boxes, not dated pre-tip reports or proven '
                       'physical-availability labels. Censored and left-censored examples remain unscored.',
        'input_sha256': {str(p.relative_to(ROOT)): sha256_file(p) for p in inputs},
    }
    write_json(args.output, result, pretty=True)
    print(f'independently checked {len(saved)} observations and {len(columns)} fields each', flush=True)


if __name__ == '__main__':
    main()
