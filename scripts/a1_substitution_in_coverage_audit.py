#!/usr/bin/env python3
"""Independently account for the incoming-eligibility and prior-position coverage report."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, sha256_file, write_json  # noqa: E402
from scripts.a1_minutes_fold_eval import CAUSAL_PROFILES  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS  # noqa: E402
from scripts.features import known_group  # noqa: E402

REPORT = EXPERIMENTS / '20261122_a1_s06_in_coverage.json'


def verify(name: str, expected: dict, positions: dict[tuple[str, str], str | None]) -> int:
    stem = f'20261122_a1_s06_fold_{name}_v3'
    rows = pd.read_parquet(DERIVED / 'experiments' / f'{stem}.parquet')
    windows = pd.read_parquet(DERIVED / 'experiments' / f'{stem}_windows.parquet')
    incoming = rows.loc[rows['decision'].eq('in')]
    games, groups, labels = set(), defaultdict(set), Counter()
    candidates, positions_count = defaultdict(set), Counter()
    participants = {}
    outside = 0
    for window in windows.to_dict('records'):
        changes = json.loads(window['changes_json'])
        for side in ('home', 'away'):
            key = (window['window_id'], window[side])
            participants[key] = set(map(str, window[f'{side}_players']))
            groups[key] = set()
            for change in changes:
                if change['team'] == window[side]:
                    groups[key].add(change['player_in'])
    observed_groups = Counter()
    for row in incoming.to_dict('records'):
        key = (row['window_id'], row['team'])
        if key not in participants:
            raise ValueError(f'{name}: incoming candidate has no matching team window')
        games.add(row['game_id'])
        candidates[key].add(row['player'])
        is_entry = not pd.isna(row['label']) and bool(row['label'])
        is_unknown = pd.isna(row['label'])
        if is_entry and row['player'] not in groups[key]:
            raise ValueError(f'{name}: positive label does not match the recorded entry')
        observed_groups[key] += int(is_entry)
        labels['observed_entries'] += int(is_entry)
        labels['unknown_nonentries'] += int(is_unknown)
        labels['known_ineligible'] += int(row['eligibility'] == 'known_ineligible')
        previous = row['eligibility'] == 'previously_observed_current_unknown'
        labels['previously_observed_current_unknown'] += int(previous)
        labels['previously_observed_entries'] += int(previous and is_entry)
        labels['unknown_nonentries_eventually_participating'] += int(
            is_unknown and row['player'] in participants[key])
        date = row['prior_profile_date']
        if date is not None and not pd.isna(date):
            if date >= row['date_et'] or (row['player'], date) not in positions:
                raise ValueError(f'{name}: position source is missing or not strictly prior')
            position = positions[(row['player'], date)]
        else:
            position = None
        positions_count[position or 'unknown'] += 1
        labels['known_prior_position_rows'] += int(position is not None)
        labels['known_prior_position_entries'] += int(position is not None and is_entry)
    for key, actual in groups.items():
        outside += len(actual - candidates[key])
    actual = {
        'games': len(games), 'incoming_rows': len(incoming),
        **{key: int(labels[key]) for key in ('observed_entries', 'unknown_nonentries', 'known_ineligible',
            'previously_observed_current_unknown', 'previously_observed_entries',
            'unknown_nonentries_eventually_participating', 'known_prior_position_rows',
            'known_prior_position_entries')},
        'entries_outside_prior_candidates': outside,
        'prior_position_counts': dict(positions_count),
        'team_windows': len(candidates),
        'team_windows_with_entries_in_pool': sum(value > 0 for value in observed_groups.values()),
        'team_windows_with_multiple_entries_in_pool': sum(value > 1 for value in observed_groups.values()),
    }
    if actual != expected:
        raise ValueError(f'{name}: independent incoming coverage differs: {actual} != {expected}')
    return len(incoming)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=EXPERIMENTS / '20261122_a1_s06_in_coverage_audit.json')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite the incoming coverage audit')
    report = json.loads(REPORT.read_text())
    for path, digest in report['input_sha256'].items():
        if sha256_file(ROOT / path) != digest:
            raise ValueError(f'incoming coverage input changed: {path}')
    profiles = pd.read_parquet(CAUSAL_PROFILES, columns=['date_et', 'player', 'pos'])
    positions = {}
    for row in profiles.to_dict('records'):
        key = (row['player'], str(row['date_et'])[:10])
        if key in positions:
            raise ValueError('duplicate player/date position profile')
        positions[key] = known_group(row['pos'])
    checked = {}
    for name in ('seed', *FOLDS):
        checked[name] = verify(name, report['populations'][name], positions)
        print(f'{name}: independently counted {checked[name]} incoming candidates', flush=True)
    result = {'experiment': 'a1_s06_incoming_coverage_independent_audit', 'rows_checked': checked,
              'input_sha256': {str(path.relative_to(ROOT)): sha256_file(path)
                               for path in (Path(__file__), REPORT, CAUSAL_PROFILES)}}
    write_json(args.output, result, pretty=True)


if __name__ == '__main__':
    main()
