#!/usr/bin/env python3
"""Extract conservatively reconciled full-timeout substitution opportunities."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import atomic_bytes, sha256_file, write_json  # noqa: E402
from scripts import pbp  # noqa: E402


def timeout_opportunities(windows: pd.DataFrame, raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    if windows['window_id'].duplicated().any():
        raise ValueError('duplicate reconstructed window ID')
    raw = raw.copy()
    raw['game_id'] = raw['game_id'].astype('int64').astype(str)
    raw = raw[raw['game_id'].isin(windows['game_id'].unique())].copy()
    raw['clock'] = raw['clock_display_value'].map(pbp.clock_seconds)
    raw = raw.rename(columns={'period_number': 'period', 'sequence_number': 'seq'})
    if raw.duplicated(['game_id', 'period', 'clock', 'seq']).any():
        raise ValueError('duplicate raw event at a clock')

    timeout_keys = set()
    timeout_counts = Counter()
    substitutions: dict[tuple, set] = defaultdict(set)
    for event in raw.to_dict('records'):
        clock_key = (event['game_id'], event['period'], event['clock'])
        if event['type_text'] == 'Full Timeout':
            timeout_counts[clock_key] += 1
            timeout_keys.add((*clock_key, event['seq']))
        if event['type_id'] == 584:
            substitutions[clock_key].add(event['seq'])

    timeouts = windows[windows['kind'].eq('timeout')]
    reconstructed = {(row['game_id'], row['period'], row['clock'], row['trigger_seq'])
                     for row in timeouts.to_dict('records')}
    if len(reconstructed) != len(timeouts) or reconstructed != timeout_keys:
        raise ValueError('full-timeout triggers do not match the retained raw events')

    kept = []
    counts = Counter()
    for row in timeouts.to_dict('records'):
        clock_key = (row['game_id'], row['period'], row['clock'])
        changes = json.loads(row['changes_json'])
        sequences = {change['seq'] for change in changes}
        if len(sequences) != len(changes) or len(changes) != row['home_subs'] + row['away_subs']:
            raise ValueError(f"{row['window_id']}: substitution labels do not reconcile")
        if timeout_counts[clock_key] != 1:
            counts['multiple_timeouts_at_clock'] += 1
        elif substitutions[clock_key] != sequences:
            counts['other_substitutions_at_clock'] += 1
        else:
            row['home_changed'] = bool(row['home_subs'])
            row['away_changed'] = bool(row['away_subs'])
            kept.append(row)
            counts['with_substitution' if sequences else 'without_substitution'] += 1
    result = pd.DataFrame(kept)
    if result.empty or len(result) + counts['multiple_timeouts_at_clock'] + counts['other_substitutions_at_clock'] != len(timeouts):
        raise ValueError('conservative timeout accounting is empty or incomplete')
    team_counts = Counter()
    for row in kept:
        team_counts['changed'] += int(row['home_changed']) + int(row['away_changed'])
        team_counts['unchanged'] += int(not row['home_changed']) + int(not row['away_changed'])
    return result, {'timeout_windows': len(timeouts), 'retained_windows': len(result),
                    'retained_games': int(result['game_id'].nunique()), 'window_counts': dict(counts),
                    'team_decisions': dict(team_counts)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pilot', type=Path)
    parser.add_argument('audit', type=Path)
    parser.add_argument('--rows', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--rows-output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.rows_output.exists():
        raise FileExistsError('refusing to overwrite an existing opportunity report')
    pilot = json.loads(args.pilot.read_text())
    audit = json.loads(args.audit.read_text())
    inputs = [args.pilot.resolve(), args.audit.resolve(), args.rows.resolve(), Path(__file__), Path(pbp.__file__)]
    if any(not path.is_relative_to(ROOT) for path in inputs):
        raise ValueError('opportunity inputs must be inside the repository')
    for report in (pilot, audit):
        for path, digest in report['input_sha256'].items():
            if sha256_file(ROOT / path) != digest:
                raise ValueError(f'audited input changed: {path}')
    for path in (args.pilot.resolve(), args.rows.resolve()):
        key = str(path.relative_to(ROOT))
        if audit['input_sha256'].get(key) != sha256_file(path):
            raise ValueError(f'supplied input is not the independently audited artifact: {key}')
    raw_path = ROOT / 'data/raw/hoopr' / f"play_by_play_{pilot['season']}.parquet"
    columns = ['game_id', 'period_number', 'clock_display_value', 'sequence_number', 'type_id', 'type_text']
    raw = pd.read_parquet(raw_path, columns=columns)
    rows = pd.read_parquet(args.rows)
    if audit['counts']['windows'] != len(rows) or audit['games'] != rows['game_id'].nunique():
        raise ValueError('independent audit does not cover the supplied windows')
    kept, accounting = timeout_opportunities(rows, raw)
    inputs.append(raw_path)
    result = {
        'experiment': 'a1_s06_conservative_full_timeout_opportunities',
        **accounting,
        'method': 'Use recorded full timeouts with one timeout at the clock; require the reconstructed '
                  'immediate changes to equal all raw substitutions at that clock. Verify both positive and '
                  'no-substitution labels against the retained feed and the independent sequence audit.',
        'limitations': 'This conservative subset excludes ambiguous same-clock events and all other stoppage '
                       'types; it is not an exhaustive or unbiased sample of legal opportunities. Rosters are '
                       'retrospective actual participants, not pre-game availability. It does not establish a '
                       'deployable substitution hazard or causal game-state effects.',
        'input_sha256': {str(path.relative_to(ROOT)): sha256_file(path) for path in inputs},
    }
    atomic_bytes(args.rows_output, kept.to_parquet(index=False))
    write_json(args.output, result, pretty=True)
    print(f"retained {accounting['retained_windows']}/{accounting['timeout_windows']} timeout windows "
          f"across {accounting['retained_games']} games", flush=True)


if __name__ == '__main__':
    main()
