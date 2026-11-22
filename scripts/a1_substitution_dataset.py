#!/usr/bin/env python3
"""Build cutoff-safe target/state candidates for historical substitution research."""
from __future__ import annotations

import argparse
import json
import sys
import time
from bisect import bisect_left
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import atomic_bytes, sha256_file, write_json  # noqa: E402
from scripts import pbp  # noqa: E402
from scripts.evaluate import TEST_FROM  # noqa: E402

TARGET_COLUMNS = ['game_id', 'team', 'player', 'date_et', 'prior_day', 'prior_profile_date',
                  'tier', 'control_mean']


def event_history(raw: pd.DataFrame, game_ids: set[str]) -> tuple[dict, dict, dict]:
    events = raw.copy()
    events['game_id'] = events['game_id'].astype('int64').astype(str)
    events = events[events['game_id'].isin(game_ids)].copy()
    events['clock'] = events['clock_display_value'].map(pbp.clock_seconds)
    events = events.rename(columns={'period_number': 'period', 'sequence_number': 'seq'})
    keys = ['game_id', 'period', 'clock', 'seq']
    if events.duplicated(keys).any():
        raise ValueError('duplicate raw event at a clock')
    events = events.sort_values(keys, ascending=[True, True, False, True], kind='stable')
    events['position'] = events.groupby('game_id').cumcount()
    positions, fouls, ejections = {}, defaultdict(list), defaultdict(list)
    for event in events.to_dict('records'):
        key = tuple(event[column] for column in keys)
        positions[key] = int(event['position'])
        name = str(event['type_text'])
        personal = pbp.is_personal_foul({'type_text': name})
        ejection = name.lower() == 'ejection'
        if personal or ejection:
            if pd.isna(event['athlete_id_1']):
                raise ValueError('personal foul or ejection lacks an identified player')
            player_key = (event['game_id'], str(int(event['athlete_id_1'])))
            if personal:
                fouls[player_key].append(int(event['position']))
            if ejection:
                ejections[player_key].append(int(event['position']))
    return positions, dict(fouls), dict(ejections)


def build(windows: pd.DataFrame, targets: pd.DataFrame, raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    if windows.empty or windows['window_id'].duplicated().any():
        raise ValueError('timeout windows are empty or duplicated')
    targets = targets.copy()
    if targets.duplicated(['game_id', 'player']).any():
        raise ValueError('prior target roster contains duplicate player-games')
    if (targets['prior_day'].isna() | targets['date_et'].isna()
            | targets['prior_day'].ge(targets['date_et'])).any():
        raise ValueError('prior roster dates must precede the game')
    profile_dates = pd.to_datetime(targets['prior_profile_date'], errors='raise')
    game_dates = pd.to_datetime(targets['date_et'], errors='raise')
    if (profile_dates.notna() & profile_dates.ge(game_dates)).any():
        raise ValueError('prior profile dates must precede the game')
    targets['prior_profile_date'] = profile_dates
    if targets['date_et'].ge(TEST_FROM).any():
        raise ValueError('protected final-test games are not eligible')
    values = pd.to_numeric(targets['control_mean'], errors='raise').to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError('prior target proxies must be finite and non-negative')
    if not targets['tier'].isin(['star', 'starter', 'bench', 'unknown']).all():
        raise ValueError('prior profile tier is invalid')

    positions, fouls, ejections = event_history(raw, set(windows['game_id'].unique()))
    target_map = {}
    rosters: dict[tuple[str, str], set[str]] = defaultdict(set)
    for item in targets.to_dict('records'):
        key = (item['game_id'], item['team'], item['player'])
        target_map[key] = item
        rosters[(item['game_id'], item['team'])].add(item['player'])

    rows = []
    counts = Counter()
    started = time.monotonic()
    for index, window in enumerate(windows.to_dict('records'), 1):
        gid = window['game_id']
        trigger = (gid, window['period'], window['clock'], window['trigger_seq'])
        if trigger not in positions:
            raise ValueError(f"{window['window_id']}: timeout trigger is absent from raw events")
        position = positions[trigger]
        changes = json.loads(window['changes_json'])
        visible = {}
        states = {}
        for side in ('home', 'away'):
            team = window[side]
            if len(rosters[(gid, team)]) < 5:
                raise ValueError(f"{window['window_id']}: prior roster has fewer than five candidates")
            fields = ('players', 'seconds_before', 'fouls_before', 'stint_before', 'rest_before')
            vectors = [window[f'{side}_{field}'] for field in fields]
            if len({len(vector) for vector in vectors}) != 1:
                raise ValueError(f"{window['window_id']}: player state vectors are misaligned")
            five = set(window[f'{side}_five_before'])
            if len(five) != 5:
                raise ValueError(f"{window['window_id']}: pre-substitution lineup is not five")
            for player, seconds, foul_count, stint, rest in zip(*vectors):
                if not np.isfinite(seconds) or seconds < 0:
                    raise ValueError(f"{window['window_id']}: invalid pre-window player seconds")
                states[(team, player)] = (float(seconds), int(foul_count), stint, rest)
                if player in five or seconds > 0:
                    if player in visible and visible[player] != team:
                        raise ValueError(f"{window['window_id']}: player observed for both teams")
                    visible[player] = team
            if not five.issubset({player for t, player in states if t == team}):
                raise ValueError(f"{window['window_id']}: on-court player is missing state")

        for side in ('home', 'away'):
            team = window[side]
            five = set(window[f'{side}_five_before'])
            outgoing = {change['player_out'] for change in changes if change['team'] == team}
            incoming = {change['player_in'] for change in changes if change['team'] == team}
            candidates = rosters[(gid, team)] | {player for player, observed_team in visible.items()
                                                 if observed_team == team}
            wrong_team = {player for player in candidates if player in visible and visible[player] != team}
            counts['prior_candidates_removed_after_other_team_observed'] += len(wrong_team)
            candidates -= wrong_team
            off_court = candidates - five
            counts['incoming_outside_pre_window_candidates'] += len(incoming - off_court)
            for decision, players in (('out', five), ('in', off_court)):
                for player in sorted(players):
                    observed = visible.get(player) == team
                    prior = target_map.get((gid, team, player))
                    if prior is not None and prior['date_et'] != window['date_et']:
                        raise ValueError(f"{window['window_id']}: target date differs from the game")
                    before_fouls = bisect_left(fouls.get((gid, player), []), position)
                    ejected = bool(bisect_left(ejections.get((gid, player), []), position))
                    if observed:
                        seconds, recorded_fouls, stint, rest = states[(team, player)]
                        if recorded_fouls != before_fouls:
                            raise ValueError(f"{window['window_id']}: earlier personal fouls do not reconcile")
                    else:
                        seconds, stint, rest = 0.0, None, None
                    ineligible = before_fouls >= 6 or ejected
                    if decision == 'in' and player in incoming and ineligible:
                        raise ValueError(f"{window['window_id']}: observed entrant is already disqualified")
                    if decision == 'out' and ejected:
                        raise ValueError(f"{window['window_id']}: ejected player remains on court")
                    target = float(prior['control_mean']) if prior is not None else None
                    deficit = (target * float(window['t']) / 2880 - seconds / 60
                               if target is not None and window['period'] <= 4 else None)
                    profile = prior['prior_profile_date'] if prior is not None else None
                    prior_profile = None if profile is None or pd.isna(profile) else str(profile.date())
                    label = (player in outgoing) if decision == 'out' else (True if player in incoming else None)
                    eligibility = ('on_court_observed' if decision == 'out' else
                                   'known_ineligible' if ineligible else
                                   'previously_observed_current_unknown' if observed else 'current_unknown')
                    rows.append({
                        'window_id': window['window_id'], 'game_id': gid, 'date_et': window['date_et'],
                        'team': team, 'player': player, 'decision': decision, 'label': label,
                        'eligibility': eligibility, 'period': window['period'], 'clock': window['clock'],
                        'elapsed': window['t'], 'margin': window['margin_home'] if side == 'home' else -window['margin_home'],
                        'fouls_before': before_fouls, 'ejected_before': ejected, 'seconds_before': seconds,
                        'stint_before': stint if decision == 'out' else None,
                        'rest_before': rest if decision == 'in' and observed else None,
                        'prior_roster': prior is not None, 'prior_day': prior['prior_day'] if prior is not None else None,
                        'prior_profile_date': prior_profile, 'prior_tier': prior['tier'] if prior is not None else 'unknown',
                        'target_mean_proxy': target, 'target_deficit': deficit,
                    })
            counts['windows_team_sides'] += 1
        if index % max(1, len(windows) // 10) == 0 or index == len(windows):
            print(f'windows {index}/{len(windows)} {time.monotonic() - started:.1f}s', flush=True)

    result = pd.DataFrame(rows)
    if result.empty or result.duplicated(['window_id', 'team', 'player', 'decision']).any():
        raise ValueError('substitution candidates are empty or duplicated')
    result['label'] = result['label'].astype('boolean')
    outgoing = result[result['decision'].eq('out')]
    incoming = result[result['decision'].eq('in')]
    if len(outgoing) != 10 * len(windows) or outgoing['label'].isna().any():
        raise ValueError('outgoing labels do not cover the observed fives')
    expected_subs = int((windows['home_subs'] + windows['away_subs']).sum())
    if int(outgoing['label'].sum()) != expected_subs:
        raise ValueError('outgoing labels do not reconcile with substitutions')
    if int(incoming['label'].sum()) + counts['incoming_outside_pre_window_candidates'] != expected_subs:
        raise ValueError('incoming labels and missing candidates do not reconcile')
    counts.update({
        'windows': len(windows), 'games': int(windows['game_id'].nunique()), 'out_rows': len(outgoing),
        'out_positive': int(outgoing['label'].sum()), 'in_rows': len(incoming),
        'in_positive': int(incoming['label'].sum()), 'in_unknown_labels': int(incoming['label'].isna().sum()),
        'known_ineligible_in_rows': int(incoming['eligibility'].eq('known_ineligible').sum()),
        'out_missing_target': int(outgoing['target_mean_proxy'].isna().sum()),
        'in_missing_target': int(incoming['target_mean_proxy'].isna().sum()),
        'overtime_rows': int(result['period'].gt(4).sum()),
    })
    return result, dict(counts)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('opportunities', type=Path)
    parser.add_argument('target_audit', type=Path)
    parser.add_argument('--windows', type=Path, required=True)
    parser.add_argument('--targets', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--rows-output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.rows_output.exists():
        raise FileExistsError('refusing to overwrite an existing substitution dataset')
    paths = [args.opportunities.resolve(), args.target_audit.resolve(), args.windows.resolve(), args.targets.resolve(),
             Path(__file__), Path(pbp.__file__)]
    if any(not path.is_relative_to(ROOT) for path in paths + [args.rows_output.resolve()]):
        raise ValueError('dataset inputs and output must be inside the repository')
    source = json.loads(args.opportunities.read_text())
    for path, digest in source['input_sha256'].items():
        if sha256_file(ROOT / path) != digest:
            raise ValueError(f'opportunity input changed: {path}')
    for report, path in ((source, args.windows), (json.loads(args.target_audit.read_text()), args.targets)):
        key = str(path.resolve().relative_to(ROOT))
        if report['output_sha256'].get(key) != sha256_file(path):
            raise ValueError(f'dataset input does not match its independently accounted output: {key}')
    pilots = [path for path in source['input_sha256'] if Path(path).name == '20261122_a1_s06_sequence_pilot_v2.json']
    if len(pilots) != 1:
        raise ValueError('opportunity provenance must identify exactly one sequence pilot')
    pilot = json.loads((ROOT / pilots[0]).read_text())
    raw_path = ROOT / 'data/raw/hoopr' / f"play_by_play_{pilot['season']}.parquet"
    raw_columns = ['game_id', 'period_number', 'clock_display_value', 'sequence_number', 'type_text', 'athlete_id_1']
    raw = pd.read_parquet(raw_path, columns=raw_columns)
    windows = pd.read_parquet(args.windows)
    targets = pd.read_parquet(args.targets, columns=TARGET_COLUMNS)
    targets = targets[targets['game_id'].isin(windows['game_id'].unique())].copy()
    result, counts = build(windows, targets, raw)
    paths.append(raw_path)
    report = {
        'experiment': 'a1_s06_prior_target_substitution_candidates',
        'counts': counts,
        'method': 'Combine independently reconciled timeout states with strictly earlier prior-box rosters and '
                  'the S05 all-active 1,000-draw mean target proxy. Candidates are prior members or players '
                  'already observed in game; target deficits use only elapsed regulation time and seconds.',
        'limitations': 'Prior boxes do not prove historical availability or publication time. Unconfirmed '
                       'incoming non-entries remain unknown, not negative labels. The target is a proxy, '
                       'period lineups are inferred, and the selected timeout sample is not an unbiased hazard.',
        'input_sha256': {str(path.relative_to(ROOT)): sha256_file(path) for path in paths},
    }
    atomic_bytes(args.rows_output, result.to_parquet(index=False))
    report['output_sha256'] = {str(args.rows_output.resolve().relative_to(ROOT)): sha256_file(args.rows_output)}
    write_json(args.output, report, pretty=True)
    print(f"saved {counts['out_rows']} out and {counts['in_rows']} in candidates across {counts['games']} games",
          flush=True)


if __name__ == '__main__':
    main()
