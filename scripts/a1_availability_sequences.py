#!/usr/bin/env python3
"""Build censored development-only DNP/return and recorded-rest sequences."""
from __future__ import annotations

import argparse
import sys
from collections import Counter, deque
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, NBA_TEAM_IDS, atomic_bytes, sha256_file, write_json  # noqa: E402
from scripts.a1_availability_labels_audit import reason_category  # noqa: E402
from scripts.evaluate import TEST_FROM  # noqa: E402

SEASONS = (2023, 2024, 2025, 2026)
KEYS = ['season', 'team', 'player', 'game_id']


def reason(value: object) -> str:
    category = reason_category(value)
    if category in ('explicit_injury', 'illness', 'injury_or_illness'):
        return 'explicit_injury_or_illness'
    return category


def role(positive_minutes: deque[float]) -> str:
    if not positive_minutes:
        return 'unknown'
    mean = sum(positive_minutes) / len(positive_minutes)
    return 'star' if mean >= 30 else 'starter' if mean >= 18 else 'bench'


def duration_bin(length: int) -> str:
    if length <= 0:
        raise ValueError('recorded DNP duration must be positive')
    return '1' if length == 1 else '2-3' if length <= 3 else '4+'


def construct(box: pd.DataFrame, schedule: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Construct next-team-game observations without filling unknown outcomes."""
    box_columns = KEYS + ['day', 'team_index', 'status', 'reason', 'minutes']
    schedule_columns = ['season', 'team', 'game_id', 'day', 'team_index']
    if set(box_columns) - set(box) or set(schedule_columns) - set(schedule):
        raise ValueError('sequence inputs are missing required columns')
    if box.duplicated(KEYS).any() or schedule.duplicated(['season', 'team', 'team_index']).any():
        raise ValueError('duplicate player listing or team-game index')
    if schedule.duplicated(['season', 'team', 'game_id']).any():
        raise ValueError('a team appears twice in one scheduled game')
    if not box['status'].isin(['play', 'dnp', 'unknown']).all():
        raise ValueError('a box outcome is not play, DNP or unknown')
    records = box[box_columns].to_dict('records')
    listings = {(int(row['season']), str(row['team']), str(row['player']), str(row['game_id'])): row
                for row in records}
    scheduled = {(int(str(row.season)), str(row.team), int(str(row.team_index))): (str(row.game_id), str(row.day))
                 for row in schedule[schedule_columns].itertuples(index=False)}
    for row in records:
        key = (int(row['season']), str(row['team']), int(row['team_index']))
        if scheduled.get(key) != (str(row['game_id']), str(row['day'])):
            raise ValueError('player listing does not match the retained team schedule')

    player_order = box.sort_values(['season', 'player', 'day', 'game_id', 'team'], kind='stable').copy()
    player_order['next_seen_day'] = player_order.groupby(['season', 'player'])['day'].shift(-1)
    player_order['next_seen_team'] = player_order.groupby(['season', 'player'])['team'].shift(-1)
    next_seen: dict[tuple[int, str, str, str], tuple[str | None, str | None]] = {}
    for row in player_order.itertuples(index=False):
        key = (int(str(row.season)), str(row.team), str(row.player), str(row.game_id))
        if pd.isna(row.next_seen_day):
            next_seen[key] = (None, None)
        else:
            next_seen[key] = (str(row.next_seen_day), str(row.next_seen_team))
    rows = []
    counts: Counter[str] = Counter()
    ordered = box.sort_values(['season', 'team', 'player', 'team_index'], kind='stable')
    for (raw_season, raw_team, raw_player), group in ordered.groupby(['season', 'team', 'player'], sort=False):
        season, team, player = int(str(raw_season)), str(raw_team), str(raw_player)
        positive: deque[float] = deque(maxlen=5)
        previous_index, previous_status = None, None
        spell_length, spell_reason, spell_role, spell_complete = 0, None, None, False
        for item in group.to_dict('records'):
            index, status = int(item['team_index']), item['status']
            consecutive = previous_index is not None and index == previous_index + 1
            if status == 'play':
                minutes = float(item['minutes'])
                if not np.isfinite(minutes) or minutes <= 0:
                    raise ValueError('known play has invalid positive minutes')
                positive.append(minutes)
                cohort, prior_role = 'rest', role(positive)
                spell_length, spell_reason, spell_role, spell_complete = 0, None, None, False
            elif status == 'dnp':
                if consecutive and previous_status == 'dnp':
                    spell_length += 1
                else:
                    spell_length = 1
                    spell_complete = bool(consecutive and previous_status == 'play')
                    spell_reason, spell_role = reason(item['reason']), role(positive)
                cohort = 'return' if spell_complete else 'left_censored_return'
                prior_role = spell_role
            else:
                counts['unknown_prior_listings'] += 1
                previous_index, previous_status = index, status
                spell_length, spell_reason, spell_role, spell_complete = 0, None, None, False
                continue

            next_game = scheduled.get((season, team, index + 1))
            next_row = None
            if next_game is None:
                state, target_game, target_day = 'season_end', None, None
            else:
                target_game, target_day = next_game
                if target_day <= item['day']:
                    raise ValueError('next team-game origin is not strictly after the prior listing')
                target_key = (season, team, player, target_game)
                next_row = listings.get(target_key)
                seen_day, seen_team = next_seen[(season, team, player, str(item['game_id']))]
                other_team = seen_day is not None and seen_day <= target_day and seen_team != team
                if other_team:
                    state = 'team_change_prior' if seen_day is not None and seen_day < target_day else 'same_day_other_team'
                elif next_row is None:
                    state = 'unlisted'
                else:
                    state = str(next_row['status'])
            counts[f'{cohort}_{state}'] += 1

            known_next = state in ('play', 'dnp')
            outcome = None
            if cohort == 'return' and known_next:
                outcome = int(state == 'play')
            elif cohort == 'rest' and known_next:
                if state == 'play':
                    outcome = 0
                elif next_row is not None and reason(next_row['reason']) != 'missing_reason':
                    outcome = int(reason(next_row['reason']) == 'rest')
            rows.append({
                'season': season, 'team': team, 'player': player,
                'prior_game_id': item['game_id'], 'prior_day': item['day'],
                'game_id': target_game, 'date_et': target_day, 'cohort': cohort,
                'prior_role': prior_role, 'prior_reason': spell_reason if status == 'dnp' else None,
                'prior_duration': spell_length if status == 'dnp' else None,
                'duration_bin': duration_bin(spell_length) if status == 'dnp' else None,
                'next_status': state, 'next_reason': reason(next_row['reason']) if state == 'dnp' and next_row else None,
                'outcome': outcome,
            })
            previous_index, previous_status = index, status
    result = pd.DataFrame(rows)
    if not result.empty:
        dated = result['date_et'].notna()
        if result.loc[dated, 'prior_day'].ge(result.loc[dated, 'date_et']).any():
            raise ValueError('a sequence feature is not strictly before its origin')
        if result.loc[dated, 'date_et'].ge(TEST_FROM).any():
            raise ValueError('a sequence origin reaches the protected season')
        if result.loc[result['cohort'].eq('left_censored_return'), 'outcome'].notna().any():
            raise ValueError('left-censored spells cannot become known return labels')
    return result, dict(sorted(counts.items()))


def load_season(season: int) -> tuple[pd.DataFrame, pd.DataFrame, dict, list[Path]]:
    box_path = ROOT / f'data/raw/hoopr/player_box_{season}.parquet'
    segments_path = DERIVED / f'history/{season}/segments.parquet'
    raw = pd.read_parquet(box_path, columns=['season', 'season_type', 'game_id', 'game_date', 'team_id',
                                             'athlete_id', 'did_not_play', 'minutes', 'reason'])
    raw = raw.loc[raw['season_type'].eq(2)].copy()
    if not raw['season'].eq(season).all():
        raise ValueError(f'{season}: box file includes another season')
    missing_schedule = int(raw[['game_id', 'game_date', 'team_id']].isna().any(axis=1).sum())
    raw = raw.dropna(subset=['game_id', 'game_date', 'team_id']).copy()
    for source, target in (('game_id', 'game_id'), ('team_id', 'team')):
        raw[target] = raw[source].astype('int64').astype(str)
    raw = raw.loc[raw['team'].isin(NBA_TEAM_IDS)].copy()
    raw['day'] = pd.to_datetime(raw['game_date'], errors='raise').dt.strftime('%Y-%m-%d')
    if raw['day'].ge(TEST_FROM).any():
        raise ValueError(f'{season}: raw data reaches the protected season')
    box_sides = raw[['season', 'team', 'game_id', 'day']].drop_duplicates()

    seg = pd.read_parquet(segments_path, columns=['game_id', 'date_et', 'season_type', 'offense', 'defense'])
    seg = seg.loc[seg['season_type'].eq(2)].copy()
    seg['game_id'] = seg['game_id'].astype(str)
    sides = pd.concat([
        seg[['game_id', 'date_et', 'offense']].rename(columns={'date_et': 'day', 'offense': 'team'}),
        seg[['game_id', 'date_et', 'defense']].rename(columns={'date_et': 'day', 'defense': 'team'}),
    ], ignore_index=True)
    sides['team'] = sides['team'].astype(str)
    sides['day'] = pd.to_datetime(sides['day'], errors='raise').dt.strftime('%Y-%m-%d')
    sides['season'] = season
    sides = sides.loc[sides['team'].isin(NBA_TEAM_IDS), ['season', 'team', 'game_id', 'day']].drop_duplicates()
    merged = box_sides.merge(sides, how='outer', indicator=True)
    source_coverage = {str(k): int(v) for k, v in merged['_merge'].value_counts().items()}
    schedule = merged.drop(columns='_merge').sort_values(['team', 'day', 'game_id'], kind='stable').reset_index(drop=True)
    if schedule['day'].ge(TEST_FROM).any():
        raise ValueError(f'{season}: retained schedule reaches the protected season')
    if schedule.duplicated(['season', 'team', 'game_id']).any():
        raise ValueError(f'{season}: sources disagree on a team-game date')
    if schedule.duplicated(['season', 'team', 'day']).any():
        raise ValueError(f'{season}: same-day team games do not have a safe date-only order')
    teams_per_game = schedule.groupby('game_id')['team'].nunique()
    if not teams_per_game.eq(2).all():
        raise ValueError(f'{season}: retained schedule has a game without exactly two NBA sides')
    schedule['team_index'] = schedule.groupby(['season', 'team']).cumcount()

    missing_player = int(raw['athlete_id'].isna().sum())
    raw = raw.dropna(subset=['athlete_id']).copy()
    raw['player'] = raw['athlete_id'].astype('int64').astype(str)
    if raw.duplicated(['game_id', 'player']).any():
        raise ValueError(f'{season}: duplicate raw player-game listings')
    dnp = raw['did_not_play'].astype('boolean')
    mins = pd.to_numeric(raw['minutes'], errors='raise')
    if mins.lt(0).any() or (dnp.eq(True).fillna(False) & mins.gt(0)).any():
        raise ValueError(f'{season}: contradictory DNP/minutes values')
    raw['status'] = np.select(
        [dnp.eq(True).fillna(False).to_numpy(dtype=bool),
         (dnp.eq(False).fillna(False) & mins.gt(0)).to_numpy(dtype=bool)],
        ['dnp', 'play'], default='unknown')
    box = raw.merge(schedule, on=['season', 'team', 'game_id', 'day'], how='left', validate='many_to_one')
    if box['team_index'].isna().any():
        raise ValueError(f'{season}: a box listing is absent from the combined schedule')
    coverage = {
        'season': season, 'team_games': len(schedule), 'box_player_listings': len(box),
        'rows_missing_schedule_identity': missing_schedule, 'rows_missing_player_id': missing_player,
        'schedule_source_coverage': source_coverage,
    }
    return box, schedule, coverage, [box_path, segments_path]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--rows-output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.rows_output.exists() or args.output.resolve() == args.rows_output.resolve():
        raise FileExistsError('sequence output paths must be distinct and new')
    frames, reports, inputs = [], [], [
        Path(__file__), ROOT / 'scripts/a1_availability_labels_audit.py',
        ROOT / 'scripts/evaluate.py', ROOT / 'basketball_common.py',
    ]
    for season in SEASONS:
        box, schedule, coverage, sources = load_season(season)
        rows, counts = construct(box, schedule)
        frames.append(rows)
        reports.append({**coverage, 'sequence_states': counts, 'sequence_rows': len(rows)})
        inputs.extend(sources)
        print(f'{season}: {len(schedule)} team-games, {len(box)} listings, {len(rows)} prior-state observations',
              flush=True)
    all_rows = pd.concat(frames, ignore_index=True)
    if all_rows.duplicated(['season', 'team', 'player', 'prior_game_id']).any():
        raise ValueError('sequence outputs repeat a prior player/team/game')
    atomic_bytes(args.rows_output, all_rows.to_parquet(index=False))
    result = {
        'experiment': 'a1_s07_development_recorded_dnp_sequences',
        'seasons': reports, 'rows': len(all_rows),
        'limitations': 'Raw historical boxes and DNP reasons lack publication timestamps. Missing next listings, '
                       'team changes, season ends, ambiguous outcomes and left-censored spells remain unknown; '
                       'recorded play/rest/DNP outcomes do not establish physical availability or recovery.',
        'input_sha256': {str(p.relative_to(ROOT)): sha256_file(p) for p in inputs},
        'output_sha256': {str(args.rows_output.resolve().relative_to(ROOT)): sha256_file(args.rows_output)},
    }
    write_json(args.output, result, pretty=True)
    print(f'saved {len(all_rows)} prior-state observations', flush=True)


if __name__ == '__main__':
    main()
