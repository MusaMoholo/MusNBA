#!/usr/bin/env python3
"""Independently account for pre-window substitution candidate features and labels."""
from __future__ import annotations

import argparse
import json
import sys
import time
from bisect import bisect_left
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import sha256_file, write_json  # noqa: E402
from scripts import pbp  # noqa: E402


def audit(rows: pd.DataFrame, windows: pd.DataFrame, targets: pd.DataFrame, raw: pd.DataFrame) -> dict:
    keys = ['window_id', 'team', 'player', 'decision']
    if rows.duplicated(keys).any() or windows['window_id'].duplicated().any():
        raise ValueError('duplicate dataset or window keys')
    expected_targets = targets[['game_id', 'team', 'player', 'date_et', 'prior_day',
                                'prior_profile_date', 'tier', 'control_mean']].copy()
    if expected_targets.duplicated(['game_id', 'team', 'player']).any():
        raise ValueError('duplicate prior target keys')
    joined = rows.merge(expected_targets, on=['game_id', 'team', 'player'], how='left',
                        suffixes=('', '_target'), validate='many_to_one')
    known = joined['control_mean'].notna()
    if not joined['prior_roster'].eq(known).all():
        raise ValueError('prior roster flag differs from the pre-origin target cohort')
    if not np.allclose(joined['target_mean_proxy'], joined['control_mean'], rtol=0, atol=1e-12, equal_nan=True):
        raise ValueError('target proxy differs from the pre-origin cohort')
    if not joined.loc[known, 'date_et'].eq(joined.loc[known, 'date_et_target']).all():
        raise ValueError('target game date differs')
    if not joined['prior_tier'].eq(joined['tier'].fillna('unknown')).all():
        raise ValueError('prior tier differs from the pre-origin cohort')
    for source, target in (('prior_day', 'prior_day_target'), ('prior_profile_date', 'prior_profile_date_target')):
        actual = pd.to_datetime(joined[source], errors='raise')
        expected = pd.to_datetime(joined[target], errors='raise')
        if not (actual.eq(expected) | (actual.isna() & expected.isna())).all():
            raise ValueError(f'{source} differs from the pre-origin cohort')
        if (actual.notna() & actual.ge(pd.to_datetime(joined['date_et'], errors='raise'))).any():
            raise ValueError(f'{source} is not strictly before the game')
    expected_deficit = np.where(joined['period'].le(4) & known,
                                joined['control_mean'] * joined['elapsed'] / 2880 - joined['seconds_before'] / 60,
                                np.nan)
    if not np.allclose(joined['target_deficit'], expected_deficit, rtol=0, atol=1e-12, equal_nan=True):
        raise ValueError('target deficit differs from pre-window elapsed time and seconds')

    events = raw.copy()
    events['game_id'] = events['game_id'].astype('int64').astype(str)
    events = events[events['game_id'].isin(windows['game_id'].unique())].copy()
    events['clock'] = events['clock_display_value'].map(pbp.clock_seconds)
    events = events.rename(columns={'period_number': 'period', 'sequence_number': 'seq'})
    event_keys = ['game_id', 'period', 'clock', 'seq']
    if events.duplicated(event_keys).any():
        raise ValueError('duplicate raw event keys')
    events = events.sort_values(event_keys, ascending=[True, True, False, True], kind='stable')
    events['position'] = events.groupby('game_id').cumcount()
    raw_events = {tuple(event[key] for key in event_keys): event for event in events.to_dict('records')}
    fouls, ejections = defaultdict(list), defaultdict(list)
    for event in raw_events.values():
        name = str(event['type_text']).lower()
        personal = 'foul' in name and 'technical' not in name and name != 'offensive foul'
        ejection = name == 'ejection'
        if personal or ejection:
            if pd.isna(event['athlete_id_1']):
                raise ValueError('raw personal foul or ejection lacks a player')
            player_key = (event['game_id'], str(int(event['athlete_id_1'])))
            if personal:
                fouls[player_key].append(int(event['position']))
            if ejection:
                ejections[player_key].append(int(event['position']))

    prior = defaultdict(set)
    for item in expected_targets.to_dict('records'):
        prior[(item['game_id'], item['team'])].add(item['player'])
    groups = {(window_id, team): group for (window_id, team), group in rows.groupby(['window_id', 'team'])}
    checks = {'windows': 0, 'team_sides': 0, 'player_rows': 0, 'raw_substitutions': 0,
              'incoming_outside_candidates': 0, 'unknown_incoming_labels': 0}
    started = time.monotonic()
    for index, window in enumerate(windows.to_dict('records'), 1):
        gid = window['game_id']
        trigger = raw_events[(gid, window['period'], window['clock'], window['trigger_seq'])]
        if trigger['type_text'] != 'Full Timeout':
            raise ValueError(f"{window['window_id']}: trigger is not a recorded full timeout")
        position = int(trigger['position'])
        changes = json.loads(window['changes_json'])
        for change in changes:
            event = raw_events[(gid, window['period'], window['clock'], change['seq'])]
            if (event['type_id'] != 584 or pd.isna(event['team_id']) or pd.isna(event['athlete_id_1'])
                    or pd.isna(event['athlete_id_2']) or str(int(event['team_id'])) != change['team']
                    or str(int(event['athlete_id_1'])) != change['player_in']
                    or str(int(event['athlete_id_2'])) != change['player_out']):
                raise ValueError(f"{window['window_id']}: raw substitution label differs")
            checks['raw_substitutions'] += 1
        visible, vectors = {}, {}
        for side in ('home', 'away'):
            team = window[side]
            five = set(window[f'{side}_five_before'])
            for player, seconds, stint, rest in zip(window[f'{side}_players'], window[f'{side}_seconds_before'],
                                                    window[f'{side}_stint_before'], window[f'{side}_rest_before']):
                vectors[(team, player)] = (float(seconds), stint, rest)
                if player in five or seconds > 0:
                    if player in visible and visible[player] != team:
                        raise ValueError('pre-window player is observed for both teams')
                    visible[player] = team
        for side in ('home', 'away'):
            team = window[side]
            group = groups.get((window['window_id'], team))
            if group is None:
                raise ValueError(f"{window['window_id']}: missing team candidate group")
            five = set(window[f'{side}_five_before'])
            eligible = (prior[(gid, team)] | {player for player, current_team in visible.items()
                                             if current_team == team})
            eligible = {player for player in eligible if player not in visible or visible[player] == team}
            candidates = eligible - five
            outgoing = {change['player_out'] for change in changes if change['team'] == team}
            incoming = {change['player_in'] for change in changes if change['team'] == team}
            if set(group.loc[group['decision'].eq('out'), 'player']) != five:
                raise ValueError(f"{window['window_id']}: outgoing pool differs from the observed five")
            if set(group.loc[group['decision'].eq('in'), 'player']) != candidates:
                raise ValueError(f"{window['window_id']}: incoming pool uses a non-prior/unobserved candidate")
            checks['incoming_outside_candidates'] += len(incoming - candidates)
            for item in group.to_dict('records'):
                player, decision = item['player'], item['decision']
                if (item['game_id'] != gid or item['date_et'] != window['date_et']
                        or item['period'] != window['period'] or item['clock'] != window['clock']
                        or item['elapsed'] != window['t']
                        or item['margin'] != (window['margin_home'] if side == 'home' else -window['margin_home'])):
                    raise ValueError(f"{window['window_id']}: pre-window game state differs")
                prior_fouls = bisect_left(fouls.get((gid, player), []), position)
                prior_ejected = bisect_left(ejections.get((gid, player), []), position) > 0
                if item['fouls_before'] != prior_fouls or item['ejected_before'] != prior_ejected:
                    raise ValueError(f"{window['window_id']}: prior foul or ejection differs from raw events")
                observed = visible.get(player) == team
                expected_seconds = vectors[(team, player)][0] if observed else 0.0
                if item['seconds_before'] != expected_seconds:
                    raise ValueError(f"{window['window_id']}: earlier player seconds differ")
                expected_stint = vectors[(team, player)][1] if decision == 'out' else None
                expected_rest = vectors[(team, player)][2] if decision == 'in' and observed else None
                for column, expected in (('stint_before', expected_stint), ('rest_before', expected_rest)):
                    actual = item[column]
                    if not ((pd.isna(actual) and pd.isna(expected)) or actual == expected):
                        raise ValueError(f"{window['window_id']}: {column} differs from the pre-window state")
                expected_eligibility = ('on_court_observed' if decision == 'out' else
                                        'known_ineligible' if prior_fouls >= 6 or prior_ejected else
                                        'previously_observed_current_unknown' if observed else 'current_unknown')
                if item['eligibility'] != expected_eligibility:
                    raise ValueError(f"{window['window_id']}: eligibility evidence differs")
                if decision == 'out':
                    if pd.isna(item['label']) or bool(item['label']) != (player in outgoing):
                        raise ValueError(f"{window['window_id']}: outgoing label differs")
                elif player in incoming:
                    if pd.isna(item['label']) or not bool(item['label']):
                        raise ValueError(f"{window['window_id']}: incoming label differs")
                elif not pd.isna(item['label']):
                    raise ValueError(f"{window['window_id']}: unconfirmed incoming negative was labelled")
                else:
                    checks['unknown_incoming_labels'] += 1
                checks['player_rows'] += 1
            checks['team_sides'] += 1
        checks['windows'] += 1
        if index % max(1, len(windows) // 10) == 0 or index == len(windows):
            print(f'windows {index}/{len(windows)} {time.monotonic() - started:.1f}s', flush=True)
    if checks['player_rows'] != len(rows):
        raise ValueError('dataset contains rows outside the audited windows and teams')
    return checks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dataset', type=Path)
    parser.add_argument('--rows', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an existing dataset audit')
    report = json.loads(args.dataset.read_text())
    for path, digest in report['input_sha256'].items():
        if sha256_file(ROOT / path) != digest:
            raise ValueError(f'dataset input changed: {path}')
    rows_path = args.rows.resolve()
    if not rows_path.is_relative_to(ROOT):
        raise ValueError('dataset rows must be inside the repository')
    if report['output_sha256'].get(str(rows_path.relative_to(ROOT))) != sha256_file(rows_path):
        raise ValueError('dataset rows do not match their recorded fingerprint')
    source_paths = report['input_sha256']
    window_paths = [ROOT / path for path in source_paths if path.endswith('_timeout_opportunities_v2.parquet')]
    target_paths = [ROOT / path for path in source_paths if path.endswith('_unconditional_F4_corrected.parquet')]
    raw_paths = [ROOT / path for path in source_paths if '/play_by_play_' in path]
    if any(len(paths) != 1 for paths in (window_paths, target_paths, raw_paths)):
        raise ValueError('dataset provenance does not identify unique windows, targets and raw events')
    windows, targets = pd.read_parquet(window_paths[0]), pd.read_parquet(target_paths[0])
    raw_columns = ['game_id', 'period_number', 'clock_display_value', 'sequence_number', 'type_id', 'type_text',
                   'team_id', 'athlete_id_1', 'athlete_id_2']
    raw = pd.read_parquet(raw_paths[0], columns=raw_columns)
    rows = pd.read_parquet(rows_path)
    result = audit(rows, windows, targets, raw)
    expected = report['counts']
    if (result['windows'] != expected['windows'] or result['raw_substitutions'] != expected['out_positive']
            or result['incoming_outside_candidates'] != expected['incoming_outside_pre_window_candidates']
            or result['unknown_incoming_labels'] != expected['in_unknown_labels']):
        raise ValueError('independent accounting differs from the dataset report')
    inputs = [args.dataset.resolve(), rows_path, *window_paths, *target_paths, *raw_paths, Path(__file__)]
    if any(not path.is_relative_to(ROOT) for path in inputs):
        raise ValueError('dataset audit inputs must be inside the repository')
    write_json(args.output, {'experiment': 'a1_s06_substitution_dataset_independent_accounting', 'checks': result,
                             'input_sha256': {str(path.relative_to(ROOT)): sha256_file(path) for path in inputs}},
               pretty=True)
    print(f"audited {result['player_rows']} player rows and {result['raw_substitutions']} substitutions", flush=True)


if __name__ == '__main__':
    main()
