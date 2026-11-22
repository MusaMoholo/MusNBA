#!/usr/bin/env python3
"""Inventory incoming-substitution eligibility and strictly prior positional coverage."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, sha256_file, write_json  # noqa: E402
from scripts import a1_minutes_fold_eval  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS  # noqa: E402
from scripts.features import known_group  # noqa: E402


def attach_positions(rows: pd.DataFrame, profiles: pd.DataFrame) -> pd.DataFrame:
    prior = rows['prior_profile_date']
    if (prior.notna() & prior.ge(rows['date_et'])).any():
        raise ValueError('position profile must come from a strictly earlier date')
    lookup = profiles[['player', 'date_et', 'pos']].copy()
    lookup['date_et'] = pd.to_datetime(lookup['date_et'], errors='raise').dt.strftime('%Y-%m-%d')
    if lookup.duplicated(['player', 'date_et']).any():
        raise ValueError('player/date position profiles are not unique')
    lookup = lookup.rename(columns={'date_et': 'prior_profile_date'})
    joined = rows.merge(lookup, on=['player', 'prior_profile_date'], how='left', validate='many_to_one',
                        sort=False, indicator=True)
    if (joined['prior_profile_date'].notna() & joined['_merge'].ne('both')).any():
        raise ValueError('recorded prior position profile is absent')
    joined['prior_position'] = joined['pos'].map(known_group)
    return joined.drop(columns=['pos', '_merge'])


def population(rows: pd.DataFrame, windows: pd.DataFrame, report: dict) -> dict:
    incoming = rows.loc[rows['decision'].eq('in')].copy()
    if incoming.empty or incoming['label'].fillna(False).sum() == 0:
        raise ValueError('incoming population is empty or has no observed entrants')
    members = set()
    for window in windows.to_dict('records'):
        for side in ('home', 'away'):
            for player in window[f'{side}_players']:
                members.add((window['window_id'], window[side], str(player)))
    keys = list(zip(incoming['window_id'], incoming['team'], incoming['player']))
    eventual = pd.Series([key in members for key in keys], index=incoming.index)
    entered = incoming['label'].fillna(False).astype(bool)
    if not eventual[entered].all():
        raise ValueError('an observed entrant is absent from the retrospective participant set')
    unknown = incoming['label'].isna()
    group = incoming.groupby(['window_id', 'team'])
    selected = group['label'].apply(lambda x: int(x.fillna(False).sum()))
    return {
        'games': int(incoming['game_id'].nunique()),
        'incoming_rows': len(incoming),
        'observed_entries': int(entered.sum()),
        'unknown_nonentries': int(unknown.sum()),
        'known_ineligible': int(incoming['eligibility'].eq('known_ineligible').sum()),
        'previously_observed_current_unknown': int(incoming['eligibility'].eq('previously_observed_current_unknown').sum()),
        'previously_observed_entries': int((entered
                                            & incoming['eligibility'].eq('previously_observed_current_unknown')).sum()),
        'unknown_nonentries_eventually_participating': int((unknown & eventual).sum()),
        'entries_outside_prior_candidates': report['candidate_counts']['incoming_outside_pre_window_candidates'],
        'known_prior_position_rows': int(incoming['prior_position'].notna().sum()),
        'known_prior_position_entries': int((entered & incoming['prior_position'].notna()).sum()),
        'prior_position_counts': incoming['prior_position'].fillna('unknown').value_counts().to_dict(),
        'team_windows': len(selected),
        'team_windows_with_entries_in_pool': int(selected.gt(0).sum()),
        'team_windows_with_multiple_entries_in_pool': int(selected.gt(1).sum()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=EXPERIMENTS / '20261122_a1_s06_in_coverage.json')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite the incoming coverage audit')
    profiles_path = a1_minutes_fold_eval.CAUSAL_PROFILES
    profiles = pd.read_parquet(profiles_path, columns=['date_et', 'player', 'pos'])
    paths = [Path(__file__), profiles_path, ROOT / 'scripts/features.py']
    result = {}
    for name in ('seed', *FOLDS):
        stem = f'20261122_a1_s06_fold_{name}_v3'
        report_path = EXPERIMENTS / f'{stem}.json'
        row_path = DERIVED / 'experiments' / f'{stem}.parquet'
        windows_path = DERIVED / 'experiments' / f'{stem}_windows.parquet'
        report = json.loads(report_path.read_text())
        for path in (row_path, windows_path):
            if sha256_file(path) != report['output_sha256'][str(path.relative_to(ROOT))]:
                raise ValueError(f'{name}: incoming coverage input differs from its fingerprint')
        rows = attach_positions(pd.read_parquet(row_path), profiles)
        result[name] = population(rows, pd.read_parquet(windows_path), report)
        paths.extend([report_path, row_path, windows_path])
        print(f"{name}: {result[name]['incoming_rows']} incoming candidates across "
              f"{result[name]['games']} games", flush=True)
    output = {
        'experiment': 'a1_s06_incoming_eligibility_position_coverage',
        'populations': result,
        'limitations': 'Non-entry labels and current physical eligibility remain unknown. Eventual participation '
                       'uses future information and is reported only as retrospective coverage, not as a feature '
                       'or proof of current eligibility. Positions come from a strictly earlier profile date.',
        'input_sha256': {str(path.relative_to(ROOT)): sha256_file(path) for path in paths},
    }
    write_json(args.output, output, pretty=True)


if __name__ == '__main__':
    main()
