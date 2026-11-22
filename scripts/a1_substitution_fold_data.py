#!/usr/bin/env python3
"""Reconcile earlier training and fixed-fold timeout substitution datasets."""
from __future__ import annotations

import argparse
import json
import sys
import time
from bisect import bisect_left
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, NBA_TEAM_IDS, atomic_bytes, sha256_file, write_json  # noqa: E402
from scripts import (a1_availability_cohort, a1_minutes_fold_eval, a1_minutes_unconditional,
                     a1_substitution_audit, a1_substitution_dataset, a1_substitution_dataset_audit,
                     a1_substitution_opportunities, a1_substitutions, history, minutes, pbp, projection)  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS, TEST_FROM  # noqa: E402

SEED_START = '2023-01-01'
SEED_END = '2023-04-14'
SEED_FIT_BEFORE = '2022-12-01'
SEED = 20261122
RAW_COLUMNS = ['game_id', 'period_number', 'clock_display_value', 'sequence_number', 'type_id', 'type_text',
               'home_score', 'away_score', 'team_id', 'athlete_id_1', 'athlete_id_2']


def seed_games(segments: pd.DataFrame) -> pd.DataFrame:
    selected = segments.loc[
        segments['date_et'].between(SEED_START, SEED_END) & segments['game_ok']
        & segments['season_type'].eq(2) & segments['offense'].astype(str).isin(NBA_TEAM_IDS)
        & segments['defense'].astype(str).isin(NBA_TEAM_IDS)
    ].copy()
    selected['game_id'] = selected['game_id'].astype(str)
    selected['home'] = np.where(selected['off_home'], selected['offense'], selected['defense']).astype(str)
    selected['away'] = np.where(selected['off_home'], selected['defense'], selected['offense']).astype(str)
    games = selected[['game_id', 'date_et', 'home', 'away']].drop_duplicates().sort_values('game_id')
    if games['game_id'].duplicated().any() or len(games) < 200 or games['home'].eq(games['away']).any():
        raise ValueError('seed schedule has ambiguous sides or fewer than 200 eligible games')
    chosen = np.random.default_rng(SEED).choice(len(games), 200, replace=False)
    return games.iloc[chosen].sort_values(['date_et', 'game_id'], kind='stable').reset_index(drop=True)


def seed_targets(games: pd.DataFrame) -> pd.DataFrame:
    if games.empty or not games['date_et'].between(SEED_START, SEED_END).all():
        raise ValueError('seed origins lie outside the frozen training window')
    box = pd.read_parquet(ROOT / 'data/raw/hoopr/player_box_2023.parquet',
                          columns=['game_date', 'athlete_id', 'team_id', 'season_type'])
    box = box.loc[box['season_type'].eq(2)].dropna(subset=['game_date', 'athlete_id', 'team_id']).copy()
    box['day'] = pd.to_datetime(box['game_date'], errors='raise').dt.strftime('%Y-%m-%d')
    box['player'] = box['athlete_id'].astype('int64').astype(str)
    box['team'] = box['team_id'].astype('int64').astype(str)
    box, _ = a1_availability_cohort.nba_team_records(
        box, set(json.loads((DERIVED / 'teams.json').read_text())))
    parts = []
    for day, day_games in games.groupby('date_et', sort=True):
        members, _ = a1_availability_cohort.prior_membership(box, str(day))
        for game in day_games.itertuples(index=False):
            for team in (game.home, game.away):
                group = members.loc[members['team'].eq(team), ['prior_day', 'player', 'team']].copy()
                if len(group) < 5:
                    raise ValueError(f'{game.game_id} {team}: prior roster has fewer than five candidates')
                parts.append(group.assign(game_id=game.game_id, date_et=str(day)))
    roster = pd.concat(parts, ignore_index=True)
    if roster.duplicated(['game_id', 'player']).any() or roster['prior_day'].ge(roster['date_et']).any():
        raise ValueError('seed roster contains duplicate or non-prior player records')
    profiles = pd.read_parquet(a1_minutes_fold_eval.CAUSAL_PROFILES,
                               columns=['date_et', 'player', 'usage', 'start_share'])
    roster = a1_minutes_unconditional.attach_prior_roles(roster, profiles)
    roster['date_et'] = pd.to_datetime(roster['date_et'], errors='raise').dt.strftime('%Y-%m-%d')
    fit = minutes.build(SEED_FIT_BEFORE, include_current=False, upto=SEED_START)
    coach = minutes.coach_dnps(include_current=False)
    output = []
    started = time.monotonic()
    done, next_report = 0, 20
    for day, day_rows in roster.groupby('date_et', sort=True):
        model = a1_minutes_unconditional.as_of_model(fit, str(day), coach)
        for (game_id, team), part in day_rows.groupby(['game_id', 'team'], sort=True):
            part = part.sort_values('player', kind='stable')
            states = [minutes.player_state(model, str(team), str(player), str(day)) for player in part['player']]
            means = minutes.game_targets(states)
            sd = minutes.sd_for(fit['sd'], means)
            if not np.isfinite(means).all() or not np.isfinite(sd).all():
                raise ValueError(f'{game_id} {team}: non-finite target or residual spread')
            seed = projection.seed_for('a1_s06_seed_targets', str(game_id), str(team))
            samples = minutes.redraw(means, [state['cap'] for state in states], sd, 1000,
                                     np.random.default_rng(seed))
            if not np.isfinite(samples).all():
                raise ValueError(f'{game_id} {team}: non-finite target draw')
            out = part[['game_id', 'team', 'player', 'date_et', 'prior_day', 'prior_profile_date', 'tier']].copy()
            out['control_mean'] = samples.mean(axis=0)
            output.append(out)
        done += int(day_rows['game_id'].nunique())
        while done >= next_report:
            print(f'seed targets {done}/{len(games)} games {time.monotonic() - started:.1f}s', flush=True)
            next_report += 20
    result = pd.concat(output, ignore_index=True)
    if set(result['game_id']) != set(games['game_id']):
        raise ValueError('seed target output is missing selected games')
    return result


def replay(games: pd.DataFrame, season: int, raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    wanted = set(games['game_id'])
    dates = games.set_index('game_id')['date_et'].to_dict()
    seen, rows, rejected = set(), [], []
    counts = Counter()
    started = time.monotonic()
    next_report = max(1, len(wanted) // 10)
    for game in history.season_games(season):
        gid = game['id']
        if gid not in wanted:
            continue
        if gid in seen or game['date_et'] != dates[gid] or game['date_et'] >= TEST_FROM:
            raise ValueError(f'{gid}: duplicate, mismatched or protected game origin')
        seen.add(gid)
        try:
            found, accounting = a1_substitutions.windows_for_game(game)
        except a1_substitutions.InvalidGame as error:
            rejected.append({'game_id': gid, 'reason': str(error)})
        else:
            rows.extend(found)
            counts.update({key: value for key, value in accounting.items() if isinstance(value, int)})
        if len(seen) >= next_report:
            print(f'replay {len(seen)}/{len(wanted)} games {time.monotonic() - started:.1f}s', flush=True)
            next_report += max(1, len(wanted) // 10)
    if seen != wanted or not rows:
        raise ValueError(f'replay is missing selected games: {sorted(wanted - seen)}')
    windows = pd.DataFrame(rows)
    report = {'requested_games': len(wanted), 'rejected_games': rejected, 'counts': dict(counts),
              'no_substitution_windows': int((windows['home_subs'] + windows['away_subs']).eq(0).sum())}
    independent = a1_substitution_audit.audit(windows, raw, report)
    return windows, {'replay': report, 'independent_sequence': independent}


def exclude_unidentified_ejections(windows: pd.DataFrame, raw: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    unknown = raw.loc[raw['type_text'].fillna('').str.lower().eq('ejection')
                      & raw['athlete_id_1'].isna(),
                      ['game_id', 'period_number', 'clock_display_value', 'sequence_number']].copy()
    unknown['game_id'] = unknown['game_id'].astype('int64').astype(str)
    unknown = unknown.loc[unknown['game_id'].isin(windows['game_id'].unique())]
    unknown = unknown.sort_values(['game_id', 'period_number', 'sequence_number'], kind='stable')
    excluded = set(unknown['game_id'])
    return windows.loc[~windows['game_id'].isin(excluded)].copy(), unknown.to_dict('records')


def exclude_ejected_on_court(windows: pd.DataFrame, raw: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    positions, _, ejections = a1_substitution_dataset.event_history(raw, set(windows['game_id'].unique()))
    conflicts = []
    for window in windows.to_dict('records'):
        gid = window['game_id']
        position = positions[(gid, window['period'], window['clock'], window['trigger_seq'])]
        for side in ('home', 'away'):
            for player in window[f'{side}_five_before']:
                if bisect_left(ejections.get((gid, player), []), position):
                    conflicts.append({'game_id': gid, 'window_id': window['window_id'], 'player': player})
    excluded = {item['game_id'] for item in conflicts}
    return windows.loc[~windows['game_id'].isin(excluded)].copy(), conflicts


def paths_for(population: str) -> tuple[Path, Path, Path, Path | None]:
    stem = f'20261122_a1_s06_fold_{population}_v2'
    report = EXPERIMENTS / f'{stem}.json'
    rows = DERIVED / 'experiments' / f'{stem}.parquet'
    windows = DERIVED / 'experiments' / f'{stem}_windows.parquet'
    targets = DERIVED / 'experiments' / f'{stem}_targets.parquet' if population == 'seed' else None
    return report, rows, windows, targets


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--population', choices=['seed', 'F1', 'F2', 'F3', 'F4'], required=True)
    args = parser.parse_args()
    report_path, rows_path, windows_path, target_output = paths_for(args.population)
    outputs = [report_path, rows_path, windows_path] + ([target_output] if target_output else [])
    if any(path.exists() for path in outputs):
        raise FileExistsError('refusing to overwrite an existing fold dataset')
    manifest_path = a1_minutes_fold_eval.PREREG
    manifest = json.loads(manifest_path.read_text())
    season = {'seed': 2023, 'F1': 2024, 'F2': 2025, 'F3': 2026, 'F4': 2026}[args.population]
    segments_path = DERIVED / f'history/{season}/segments.parquet'
    if args.population == 'seed':
        columns = ['game_id', 'date_et', 'game_ok', 'season_type', 'offense', 'defense', 'off_home']
        games = seed_games(pd.read_parquet(segments_path, columns=columns))
    else:
        games = a1_minutes_fold_eval.fold_games(manifest, args.population)
    raw_path = ROOT / f'data/raw/hoopr/play_by_play_{season}.parquet'
    raw = pd.read_parquet(raw_path, columns=RAW_COLUMNS)
    windows, accounting = replay(games, season, raw)
    opportunities, selection = a1_substitution_opportunities.timeout_opportunities(windows, raw)
    opportunities, unknown_ejections = exclude_unidentified_ejections(opportunities, raw)
    opportunities, stale_ejections = exclude_ejected_on_court(opportunities, raw)
    target_audit = EXPERIMENTS / '20261122_a1_s05_minutes_screen_accounting_corrected.json'
    if args.population == 'seed':
        targets = seed_targets(games)
        target_path = None
    else:
        target_path = DERIVED / 'experiments' / f'20261122_a1_s05_unconditional_{args.population}_corrected.parquet'
        audit = json.loads(target_audit.read_text())
        if audit['output_sha256'].get(str(target_path.relative_to(ROOT))) != sha256_file(target_path):
            raise ValueError('fold target rows differ from their independently audited fingerprint')
        targets = pd.read_parquet(target_path, columns=a1_substitution_dataset.TARGET_COLUMNS)
    covered = set(targets['game_id'])
    missing_roster = sorted(set(games['game_id']) - covered)
    opportunities = opportunities.loc[opportunities['game_id'].isin(covered)].copy()
    if opportunities.empty:
        raise ValueError('no audited timeout opportunities have a pre-origin target roster')
    targets = targets.loc[targets['game_id'].isin(opportunities['game_id'].unique())].copy()
    rows, counts = a1_substitution_dataset.build(opportunities, targets, raw)
    independent = a1_substitution_dataset_audit.audit(rows, opportunities, targets, raw)
    if independent['raw_substitutions'] != counts['out_positive']:
        raise ValueError('independent fold accounting does not match the candidate substitutions')
    sources = [manifest_path, segments_path, raw_path, ROOT / f'data/raw/hoopr/player_box_{season}.parquet',
               Path(__file__), Path(history.__file__), Path(pbp.__file__), Path(minutes.__file__),
               Path(a1_substitutions.__file__), Path(a1_substitution_audit.__file__),
               Path(a1_substitution_opportunities.__file__), Path(a1_substitution_dataset.__file__),
               Path(a1_substitution_dataset_audit.__file__)]
    if target_path is not None:
        sources.extend([target_path, target_audit])
    else:
        sources.extend([a1_minutes_fold_eval.CAUSAL_PROFILES, DERIVED / 'teams.json',
                        Path(a1_availability_cohort.__file__), Path(a1_minutes_unconditional.__file__),
                        Path(projection.__file__)])
        sources.extend(sorted((DERIVED / 'history').glob('*/on_court.parquet')))
        sources.extend(sorted((ROOT / 'data/raw/hoopr').glob('player_box_*.parquet')))
    sources = list(dict.fromkeys(sources))
    report = {
        'experiment': 'a1_s06_fold_timeout_candidates',
        'population': args.population, 'season': season, 'requested_game_ids': sorted(games['game_id'].tolist()),
        'seed_fit_before': SEED_FIT_BEFORE if args.population == 'seed' else None,
        'fold_validation_start': FOLDS[args.population][1] if args.population != 'seed' else None,
        'games_without_prior_target_roster': missing_roster,
        'unidentified_ejections_excluded': unknown_ejections,
        'ejected_on_court_conflicts_excluded': stale_ejections,
        **accounting, 'timeout_selection': selection, 'candidate_counts': counts,
        'independent_candidate_accounting': independent,
        'method': 'Replay fixed games, independently reconcile every raw substitution, select conservative full '
                  'timeouts and combine with strictly earlier prior-box targets. Seed targets use 1,000 D29 draws '
                  'with ramp/spread fitted before 2022-12-01; other targets are audited S05 fold outputs.',
        'limitations': 'Selected timeouts are outcome-dependent, not a population-wide substitution hazard. '
                       'Prior boxes do not prove availability or publication times; period starters are inferred. '
                       'Unknown incoming non-entries remain unknown and targets are all-active mean proxies.',
        'input_sha256': {str(path.relative_to(ROOT)): sha256_file(path) for path in sources},
    }
    atomic_bytes(rows_path, rows.to_parquet(index=False))
    atomic_bytes(windows_path, opportunities.to_parquet(index=False))
    if target_output is not None:
        atomic_bytes(target_output, targets.to_parquet(index=False))
    saved = [rows_path, windows_path] + ([target_output] if target_output else [])
    report['output_sha256'] = {str(path.relative_to(ROOT)): sha256_file(path) for path in saved}
    write_json(report_path, report, pretty=True)
    print(f"{args.population}: {counts['games']} games, {counts['out_rows']} out rows and "
          f"{counts['in_unknown_labels']} unknown incoming labels saved", flush=True)


if __name__ == '__main__':
    main()
