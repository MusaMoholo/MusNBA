#!/usr/bin/env python3
"""Reconcile A1 quarter actuals with retained box scores and end-of-period scoreboards.

  .venv/bin/python scripts/a1_quarter_audit.py --output analysis/experiments/20261122_a1_quarter_audit.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, write_json  # noqa: E402
from scripts import backtest  # noqa: E402
from scripts.evaluate import FOLDS  # noqa: E402


def audit() -> dict:
    spec = json.loads((ROOT / 'models/v1.2d.json').read_text())
    results = {}
    for fold, (_, _, val_to) in FOLDS.items():
        _, _, seg, _, _, box = backtest.load_inputs(spec, fold)
        ids = backtest.eligible_games(seg)
        season = int(val_to[:4]) if val_to[5:7] <= '06' else int(val_to[:4]) + 1
        path = ROOT / f'data/raw/hoopr/play_by_play_{season}.parquet'
        columns = ['game_id', 'period_number', 'sequence_number', 'home_score', 'away_score',
                   'home_team_id', 'away_team_id', 'type_text']
        raw = pd.read_parquet(path, columns=columns)
        raw['game_id'] = raw['game_id'].astype('int64').astype(str)
        raw = raw[raw['game_id'].isin(ids) & (raw['period_number'] >= 1)]
        ends = raw[raw['type_text'].str.contains('End Period|End Game', case=False, na=False)]
        ends = (ends.sort_values(['game_id', 'period_number', 'sequence_number'])
                .groupby(['game_id', 'period_number'], as_index=False).tail(1)
                .sort_values(['game_id', 'period_number']).copy())
        raw_keys = set(zip(raw['game_id'], raw['period_number']))
        end_keys = set(zip(ends['game_id'], ends['period_number']))
        missing_regulation = {(gid, q) for gid in ids for q in range(1, 5)} - end_keys
        missing_periods = raw_keys - end_keys
        period_path = DERIVED / 'history' / str(season) / 'player_periods.csv.gz'
        periods = pd.read_csv(period_path, dtype={'game_id': str, 'team_id': str},
                              usecols=['game_id', 'team_id', 'period', 'pts'])
        periods = periods[periods['game_id'].isin(ids)].groupby(['game_id', 'team_id', 'period'])['pts'].sum()
        period_team = periods.groupby(['game_id', 'team_id']).sum()
        period_team.index = period_team.index.set_names(['game_id', 'team'])
        box_team = box[box['game_id'].isin(ids)].groupby(['game_id', 'team'])['points'].sum()
        totals = box_team.to_frame('box').join(period_team.rename('periods'), how='outer')
        bad_box = totals['box'].isna() | totals['periods'].isna() | totals['box'].ne(totals['periods'])
        mismatches = {}
        for side in ('home', 'away'):
            score = f'{side}_score'
            ends[f'{side}_period'] = ends.groupby('game_id')[score].diff().fillna(ends[score])
            actual = ends[['game_id', 'period_number', f'{side}_team_id', f'{side}_period']].copy()
            actual[f'{side}_team_id'] = actual[f'{side}_team_id'].astype('int64').astype(str)
            actual = actual.rename(columns={'period_number': 'period', f'{side}_team_id': 'team_id'})
            actual = actual.merge(periods.rename('player_period'), on=['game_id', 'team_id', 'period'],
                                  how='left', validate='one_to_one')
            bad = actual['player_period'].isna() | actual[f'{side}_period'].ne(actual['player_period'])
            mismatches[side] = int(bad.sum())
        results[fold] = {'games': len(ids), 'periods_with_end_score': len(ends),
                         'missing_regulation_ends': len(missing_regulation), 'missing_period_ends': len(missing_periods),
                         'team_game_box_mismatches': int(bad_box.sum()), 'team_period_mismatches': mismatches}
    old = pd.read_parquet(DERIVED / 'experiments' / '20261120T162930Z_v1.3_pool_per_world_F4.parquet')
    differences = {}
    for side in ('home', 'away'):
        delta = (old[f'real_{side}_seg'] - old[f'real_{side}']).abs()
        differences[side] = {'games_with_difference': int(delta.ne(0).sum()), 'maximum_absolute_difference': float(delta.max())}
    return {'experiment': 'a1_quarter_actuals_audit', 'population': 'all eligible regular-season F1-F4 games',
            'method': 'sum player-period points; compare final totals with boxes and each period with cumulative '
                      'end-period/end-game scoreboard differences, including overtime',
            'ordering_warning': 'later sequence numbers can be backfilled earlier-clock events; use explicit period-end events',
            'folds': results, 'retained_200_game_segment_vs_box': differences}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--output', type=Path, required=True, help='new report path; existing reports are never overwritten')
    args = ap.parse_args()
    if args.output.exists():
        raise FileExistsError(f'refusing to overwrite {args.output}')
    report = audit()
    write_json(args.output, report, pretty=True)
    print(json.dumps(report, indent=2))
    bad = [name for name, result in report['folds'].items()
           if result['missing_regulation_ends'] or result['missing_period_ends'] or result['team_game_box_mismatches']
           or any(result['team_period_mismatches'].values())]
    if bad:
        raise SystemExit(f'quarter reconciliation failed for {bad}; see {args.output}')


if __name__ == '__main__':
    main()
