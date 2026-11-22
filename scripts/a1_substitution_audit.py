#!/usr/bin/env python3
"""Independently reconcile a sequence-window pilot against retained ESPN play-by-play."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import sha256_file, write_json  # noqa: E402
from scripts import pbp  # noqa: E402

KEY = ['game_id', 'period', 'clock', 'seq']


def audit(rows: pd.DataFrame, raw: pd.DataFrame, report: dict) -> dict:
    if rows['window_id'].duplicated().any():
        raise ValueError('duplicate reconstructed window ID')
    expected_games = report['requested_games'] - len(report['rejected_games'])
    if rows['game_id'].nunique() != expected_games or len(rows) != report['counts']['windows']:
        raise ValueError('window population differs from the pilot report')
    raw = raw.copy()
    raw['game_id'] = raw['game_id'].astype('int64').astype(str)
    raw = raw[raw['game_id'].isin(rows['game_id'].unique())].copy()
    raw['clock'] = raw['clock_display_value'].map(pbp.clock_seconds)
    raw = raw.rename(columns={'period_number': 'period', 'sequence_number': 'seq'})
    if raw.duplicated(KEY).any() or len(raw) != report['counts']['events']:
        raise ValueError('retained raw events are duplicated or do not match the report')
    raw = raw.sort_values(['game_id', 'period', 'clock', 'seq'],
                          ascending=[True, True, False, True], kind='stable').reset_index(drop=True)
    raw['position'] = raw.groupby('game_id').cumcount()
    events = raw.to_dict('records')
    indexed = {tuple(event[key] for key in KEY): event for event in events}
    foul_positions = {}
    for event in events:
        kind = str(event['type_text']).lower()
        if 'foul' in kind and 'technical' not in kind and kind != 'offensive foul':
            if pd.isna(event['athlete_id_1']):
                raise ValueError('retained personal foul lacks an identified player')
            player = str(int(event['athlete_id_1']))
            foul_positions.setdefault((event['game_id'], player), []).append(event['position'])
    foul_positions = {key: np.asarray(value, dtype=int) for key, value in foul_positions.items()}
    changes_seen = set()
    counts = {'windows': len(rows), 'scoreboards': 0, 'scoreboards_missing': 0,
              'lineups': 0, 'minute_vectors': 0, 'foul_values': 0, 'substitutions': 0,
              'no_substitution_windows': 0, 'timeout_no_substitution_windows': 0}
    started = time.monotonic()
    for index, row in enumerate(rows.to_dict('records'), 1):
        key = (row['game_id'], row['period'], row['clock'], row['trigger_seq'])
        if key not in indexed:
            raise ValueError(f"{row['window_id']}: trigger event not present in the raw feed")
        trigger = indexed[key]
        if row['kind'] == 'jump_ball':
            name = str(trigger['type_text']).lower()
            if trigger['type_id'] != 615 and 'jumpball' not in name and 'jump ball' not in name:
                raise ValueError(f"{row['window_id']}: non-jump-ball event labelled jump ball")
        for side in ('home', 'away'):
            actual = trigger[f'{side}_score']
            if pd.isna(actual):
                counts['scoreboards_missing'] += 1
            elif float(actual) != row[f'{side}_score']:
                raise ValueError(f"{row['window_id']}: pre-substitution score differs from the raw feed")
            else:
                counts['scoreboards'] += 1
        if row['margin_home'] != row['home_score'] - row['away_score']:
            raise ValueError(f"{row['window_id']}: home margin does not match the score")
        t = ((row['period'] - 1) * 720 + 720 - row['clock'] if row['period'] <= 4 else
             2880 + (row['period'] - 5) * 300 + 300 - row['clock'])
        if abs(row['t'] - t) > 1e-8:
            raise ValueError(f"{row['window_id']}: elapsed time does not match the period and clock")
        lineups = {}
        for side in ('home', 'away'):
            players = list(row[f'{side}_players'])
            five = list(row[f'{side}_five_before'])
            seconds = np.asarray(row[f'{side}_seconds_before'], dtype=float)
            fouls = np.asarray(row[f'{side}_fouls_before'], dtype=int)
            stints = np.asarray(row[f'{side}_stint_before'], dtype=float)
            rests = np.asarray(row[f'{side}_rest_before'], dtype=float)
            if (len(players) != len(set(players)) or len(five) != 5 or len(set(five)) != 5
                    or not set(five).issubset(players)
                    or any(len(values) != len(players) for values in (seconds, fouls, stints, rests))):
                raise ValueError(f"{row['window_id']}: player or lineup vectors are invalid")
            if (not np.isfinite(seconds).all() or (seconds < 0).any()
                    or (seconds > t + 1e-8).any() or abs(seconds.sum() - 5 * t) > 1e-6):
                raise ValueError(f"{row['window_id']}: elapsed player seconds do not reconcile")
            for index, player in enumerate(players):
                on = player in five
                if (on and (not np.isfinite(stints[index]) or not np.isnan(rests[index]))) or (
                        not on and (not np.isfinite(rests[index]) or not np.isnan(stints[index]))):
                    raise ValueError(f"{row['window_id']}: stint or rest status differs from the lineup")
                positions = foul_positions.get((row['game_id'], player), np.empty(0, dtype=int))
                expected = int(np.searchsorted(positions, int(trigger['position']), side='right'))
                if fouls[index] != expected:
                    raise ValueError(f"{row['window_id']}: personal fouls differ from earlier raw events")
                counts['foul_values'] += 1
            lineups[row[side]] = set(five)
            counts['lineups'] += 1
            counts['minute_vectors'] += 1
        changes = json.loads(row['changes_json'])
        if len(changes) != row['home_subs'] + row['away_subs']:
            raise ValueError(f"{row['window_id']}: substitution counts disagree")
        if not changes:
            counts['no_substitution_windows'] += 1
            counts['timeout_no_substitution_windows'] += int(row['kind'] == 'timeout')
        for change in changes:
            sub_key = (row['game_id'], row['period'], row['clock'], change['seq'])
            if sub_key in changes_seen or sub_key not in indexed:
                raise ValueError(f"{row['window_id']}: duplicate or missing raw substitution")
            event = indexed[sub_key]
            if (event['type_id'] != 584 or pd.isna(event['athlete_id_1']) or pd.isna(event['athlete_id_2'])
                    or str(int(event['athlete_id_1'])) != change['player_in']
                    or str(int(event['athlete_id_2'])) != change['player_out']
                    or pd.isna(event['team_id']) or str(int(event['team_id'])) != change['team']):
                raise ValueError(f"{row['window_id']}: substitution differs from the raw feed")
            if (change['team'] not in lineups or change['player_out'] not in lineups[change['team']]
                    or change['player_in'] in lineups[change['team']]):
                raise ValueError(f"{row['window_id']}: substitution is not a valid five-player transition")
            lineups[change['team']].remove(change['player_out'])
            lineups[change['team']].add(change['player_in'])
            changes_seen.add(sub_key)
            counts['substitutions'] += 1
        for side in ('home', 'away'):
            if lineups[row[side]] != set(row[f'{side}_five_after']):
                raise ValueError(f"{row['window_id']}: final lineup does not match the substitutions")
        if index % max(1, len(rows) // 10) == 0 or index == len(rows):
            print(f'windows {index}/{len(rows)} {time.monotonic() - started:.1f}s', flush=True)
    raw_subs = int(raw['type_id'].eq(584).sum())
    if raw_subs != counts['substitutions'] or raw_subs != report['counts']['substitutions']:
        raise ValueError('retained raw substitution count differs from reconstructed changes')
    if counts['no_substitution_windows'] != report['no_substitution_windows']:
        raise ValueError('no-substitution window count differs from the pilot report')
    return {'experiment': 'a1_s06_sequence_window_independent_accounting', 'games': expected_games,
            'counts': counts, 'raw_substitutions': raw_subs,
            'method': 'Join every trigger and substitution directly to retained raw events; independently replay '
                      'each window’s lineup changes and count prior personal fouls. Verify five-player seconds '
                      'against elapsed game time and compare pre-substitution scores to the feed scoreboard.',
            'limitations': 'Reconciliation does not prove that every legal substitution opportunity was observed '
                           'or that the retrospectively inferred participant roster was known before tip.'}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pilot', type=Path)
    parser.add_argument('--rows', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f'refusing to overwrite {args.output}')
    report = json.loads(args.pilot.read_text())
    for path, digest in report['input_sha256'].items():
        if sha256_file(ROOT / path) != digest:
            raise ValueError(f'pilot input changed: {path}')
    raw_path = ROOT / 'data/raw/hoopr' / f"play_by_play_{report['season']}.parquet"
    columns = ['game_id', 'period_number', 'clock_display_value', 'sequence_number', 'type_id', 'type_text',
               'home_score', 'away_score', 'team_id', 'athlete_id_1', 'athlete_id_2']
    raw = pd.read_parquet(raw_path, columns=columns)
    rows = pd.read_parquet(args.rows)
    result = audit(rows, raw, report)
    inputs = [args.pilot.resolve(), args.rows.resolve(), raw_path, Path(__file__), Path(pbp.__file__)]
    if any(not path.is_relative_to(ROOT) for path in inputs):
        raise ValueError('audit inputs must be inside the repository')
    result['input_sha256'] = {str(path.relative_to(ROOT)): sha256_file(path) for path in inputs}
    write_json(args.output, result, pretty=True)
    print(f"reconciled {result['games']} games, {result['counts']['windows']} windows and "
          f"{result['counts']['substitutions']} substitutions", flush=True)


if __name__ == '__main__':
    main()
