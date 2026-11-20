#!/usr/bin/env python3
"""Adapter and feed parity (PLAN M5b; FINDINGS §3k): live ESPN summaries v the hoopR history.

1. Same games, both adapters: 2025-26 games in the hoopR files, re-fetched as ESPN summaries (kept under
   data/raw/espn/parity/, never in final/), run through plays.py → possessions.py and diffed play by play and segment by
   segment, under both rebound-clock conventions.
2. Same time of season, both seasons: Oct–Nov of the last history season v the live season, segment distributions
   under the feed's clocks and under the `miss` convention (possessions.py --rebound-clock miss --out DIR).

  .venv/bin/python scripts/parity.py [--fetch] [--variant data/derived/variants/rebound_miss]
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, RAW, read_json, write_json  # noqa: E402
from scripts import history, plays, possessions  # noqa: E402
from scripts.evaluate import EXPERIMENTS  # noqa: E402

GAMES = ['401809781', '401809783', '401809788', '401810054', '401810056']  # 10 and 14 Nov 2025, five different matchups
PARITY = RAW / 'parity'
VARIANT = DERIVED / 'variants' / 'rebound_miss'


def fetch(games=GAMES):
    from scripts.fetch_espn import SITE, Client, save
    client = Client(delay=1.0)
    for gid in games:
        if not (PARITY / f'{gid}.json.gz').exists():
            save(PARITY / f'{gid}.json.gz', client.json(f'{SITE}/summary?event={gid}'))
    return client.count


def same_games(games=GAMES) -> dict:
    season = 2026
    pbp_df = pd.read_parquet(history.RAW_DIR / f'play_by_play_{season}.parquet')
    box_df = pd.read_parquet(history.RAW_DIR / f'player_box_{season}.parquet')
    out = {}
    for gid in games:
        live = plays.from_summary(read_json(PARITY / f'{gid}.json.gz'))
        hist = plays.from_hoopr(gid, pbp_df[pbp_df['game_id'] == int(gid)].to_dict('records'),
                                box_df[box_df['game_id'] == int(gid)].to_dict('records'))
        play_diff = Counter(k for a, b in zip(live['plays'], hist['plays']) for k in a if a[k] != b[k])
        row = {'plays': [len(live['plays']), len(hist['plays'])], 'play_field_differences': dict(play_diff)}
        for rc in possessions.REBOUND_CLOCKS:
            a, _, _ = possessions.parse_game(live, rc)
            b, _, _ = possessions.parse_game(hist, rc)
            row[f'segments_{rc}'] = [len(a), len(b)]
            row[f'segment_differences_{rc}'] = sum(x != y for x, y in zip(a, b)) + abs(len(a) - len(b))
        out[gid] = row
    return out


def distribution(seg: pd.DataFrame) -> dict:
    seg = seg[seg['game_ok']]
    games = seg['game_id'].nunique()
    reb = seg[seg['rebound'].notna() & seg['end_type'].isin(['shot', 'fouled', 'foul'])]
    gap = reb['action_clock'] - reb['end_clock']
    timed = seg[(seg['start_clock'] > 24) & ~seg['end_type'].isin(['end_period', 'unknown'])]
    tov = seg[seg['end_type'] == 'turnover']
    per_game = lambda m: round(float(m.sum()) / games, 2)
    return {
        'games': int(games), 'segments_per_game': round(len(seg) / games, 1),
        'rebound_gap_zero_share': round(float((gap == 0).mean()), 3), 'rebound_gap_mean_s': round(float(gap.mean()), 2),
        'oreb_action_within_2s': round(float((timed.loc[timed['start_type'] == 'oreb', 'shot_time'] <= 2).mean()), 3),
        'time_to_action_s': {st: round(float(timed.loc[timed['start_type'] == st, 'shot_time'].mean()), 2)
                             for st in ('made_fg', 'dreb', 'oreb', 'steal', 'dead_turnover', 'made_ft')},
        'team_pace_input_s': round(float(timed.loc[timed['start_type'] != 'oreb', 'shot_time'].clip(lower=0).mean()), 2),
        'non_shooting_def_fouls_per_game': per_game(seg['end_type'] == 'foul'),
        'shooting_fouls_per_game': per_game((seg['end_type'] == 'fouled') | seg['and_one']),
        'and_ones_per_game': per_game(seg['and_one']),
        'live_ball_turnover_share': round(float((tov['turnover'] == 'live').mean()), 3),
        'offensive_foul_turnover_share': round(float(tov['fouler'].notna().mean()), 3),
        'jump_ball_starts_per_game': per_game(seg['start_type'] == 'jump_ball'),
    }


def seasons(variant: Path) -> dict:
    out = {}
    last = max(history.SEASONS)
    for rc, root in (('feed', DERIVED), ('miss', variant)):
        h, c = root / 'history' / str(last) / 'segments.parquet', root / 'segments.parquet'
        if not (h.exists() and c.exists()):
            continue
        hist = pd.read_parquet(h)
        hist = hist[(hist['season_type'] == 2) & (hist['date_et'].astype(str) <= f'{last - 1}-11-30')]
        cur = pd.read_parquet(c)
        out[rc] = {'history_oct_nov': distribution(hist), 'live': distribution(cur)}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--fetch', action='store_true', help='fetch the five ESPN summaries first (five polite requests)')
    ap.add_argument('--variant', type=Path, default=VARIANT, help='segments root built with --rebound-clock miss')
    args = ap.parse_args()
    if args.fetch:
        print(f'fetched: {fetch()} requests')
    record = {'experiment': 'm5b_parity', 'run': datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),
              'same_games': same_games(), 'seasons': seasons(args.variant)}
    for gid, r in record['same_games'].items():
        print(gid, {k: v for k, v in r.items() if k != 'play_field_differences'}, 'play fields differing:', r['play_field_differences'])
    for rc, pops in record['seasons'].items():
        for pop, d in pops.items():
            print(f'{rc:5} {pop:16}', d)
    write_json(EXPERIMENTS / f"{record['run']}_parity.json", record, pretty=True)
    print(f"log: analysis/experiments/{record['run']}_parity.json")


if __name__ == '__main__':
    main()
