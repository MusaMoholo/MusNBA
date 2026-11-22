#!/usr/bin/env python3
"""Audit segment-start lineups against event participants and separately reconstructed court time.

  .venv/bin/python -m scripts.a1_lineup_audit --output analysis/experiments/new-lineups.json
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, sha256_file, today_et, write_json  # noqa: E402
from scripts import features  # noqa: E402

OFF = [f'off_{i}' for i in range(1, 6)]
DEF = [f'def_{i}' for i in range(1, 6)]


def present(rows: pd.DataFrame, participant: str, lineup: list[str]) -> pd.Series:
    return rows[lineup].astype('string').eq(rows[participant].astype('string'), axis=0).fillna(False).any(axis=1)


def participant_summary(seg: pd.DataFrame, participant: str, side: list[str]) -> dict:
    rows = seg[seg[participant].notna()]
    missing = ~present(rows, participant, side)
    return {'known': len(rows), 'not_on_recorded_lineup': int(missing.sum()),
            'affected_games': int(rows.loc[missing, 'game_id'].nunique()),
            'by_end_type': rows.loc[missing, 'end_type'].value_counts().to_dict()}


def seconds_summary(seg: pd.DataFrame, on: pd.DataFrame) -> dict:
    if on.duplicated(['game_id', 'player']).any():
        raise ValueError('duplicate reconstructed on-court player-game')
    parts = []
    for column in OFF + DEF:
        p = seg[['game_id', column, 'duration']].dropna(subset=[column]).rename(columns={column: 'player'})
        parts.append(p.groupby(['game_id', 'player'], as_index=False)['duration'].sum())
    credited = pd.concat(parts, ignore_index=True).groupby(['game_id', 'player'], as_index=False)['duration'].sum()
    joined = credited.merge(on[['game_id', 'player', 'sec']], on=['game_id', 'player'], how='outer',
                            validate='one_to_one', indicator=True)
    known = joined['duration'].notna() & joined['sec'].notna()
    delta = (joined.loc[known, 'duration'] - joined.loc[known, 'sec']).abs()
    return {'compared_player_games': int(known.sum()), 'segment_only_player_games': int(joined['_merge'].eq('left_only').sum()),
            'on_court_only_player_games': int(joined['_merge'].eq('right_only').sum()),
            'median_abs_seconds': float(delta.median()) if len(delta) else None,
            'p90_abs_seconds': float(delta.quantile(.9)) if len(delta) else None,
            'over_30_seconds': int(delta.gt(30).sum()), 'over_60_seconds': int(delta.gt(60).sum())}


def lineup_summary(seg: pd.DataFrame, on: pd.DataFrame) -> dict:
    off, defense = seg[OFF].astype('string'), seg[DEF].astype('string')
    def unique_five(side: pd.DataFrame) -> pd.Series:
        valid = side.notna().all(axis=1)
        for i in range(5):
            for j in range(i + 1, 5):
                valid &= side.iloc[:, i].ne(side.iloc[:, j]).fillna(False)
        return valid
    valid_off, valid_def = unique_five(off), unique_five(defense)
    offensive_fouls = seg['end_type'].eq('turnover')
    fouls = seg[seg['fouler'].notna()]
    fouler_present = present(fouls, 'fouler', DEF)
    foul_turnover = offensive_fouls.loc[fouls.index]
    fouler_present.loc[foul_turnover] = present(fouls.loc[foul_turnover], 'fouler', OFF)
    return {'games': int(seg['game_id'].nunique()), 'segments': len(seg),
            'invalid_offensive_lineups': int((~valid_off).sum()), 'invalid_defensive_lineups': int((~valid_def).sum()),
            'negative_durations': int(seg['duration'].lt(0).sum()),
            'missing_durations': int(seg['duration'].isna().sum()),
            'actor': participant_summary(seg, 'actor', OFF),
            'assister': participant_summary(seg, 'assister', OFF),
            'blocker': participant_summary(seg, 'blocker', DEF),
            'stealer': participant_summary(seg, 'stealer', DEF),
            'fouler': {'known': len(fouls), 'not_on_expected_lineup': int((~fouler_present).sum())},
            'segment_seconds_vs_rotations': seconds_summary(seg, on)}


def audit() -> dict:
    as_of = today_et()
    results, hashes = {}, {}
    for seg_path, on_path in features.sources():
        seg = pd.read_parquet(seg_path)
        seg = seg[seg['date_et'].astype(str).lt(as_of) & seg['game_ok']].copy()
        if seg.empty:
            continue
        on = pd.read_parquet(on_path)
        on = on[on['game_id'].isin(seg['game_id'].unique())].copy()
        season = str(int(seg['season'].iloc[0]))
        if seg['season'].nunique() != 1 or season in results:
            raise ValueError('input path contains mixed or duplicate seasons')
        results[season] = lineup_summary(seg, on)
        hashes.update({str(path.relative_to(ROOT)): sha256_file(path) for path in (seg_path, on_path)})
    if not results:
        raise ValueError('no eligible segment files')
    return {'experiment': 'a1_segment_lineup_integrity', 'as_of_et': as_of,
            'population': 'retained reconciled ESPN segment games strictly before as_of_et; '
                          'lineups are snapshots at segment start, not necessarily event time',
            'seconds_note': 'segment-start credited seconds versus independent rotation reconstruction; '
                            'differences are not uniquely attributable to substitutions',
            'seasons': results, 'input_sha256': hashes}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output', type=Path, required=True, help='new report path; existing reports are never overwritten')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f'refusing to overwrite {args.output}')
    report = audit()
    write_json(args.output, report, pretty=True)
    print(f"saved {args.output}: {len(report['seasons'])} season summaries")


if __name__ == '__main__':
    main()
