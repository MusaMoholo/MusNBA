#!/usr/bin/env python3
"""Compare an isolated substitution-split parser against retained pinned F4 games.

  .venv/bin/python -m scripts.a1_subsplit_audit --limit 3 --output analysis/experiments/new-split-audit.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, sha256_file, write_json  # noqa: E402
from scripts import a1_lineup_audit, history, plays, possessions  # noqa: E402

MANIFEST = ROOT / 'analysis' / 'experiments' / '20261122_a1_manifest.json'
PBP = history.RAW_DIR / 'play_by_play_2026.parquet'
BOX = history.RAW_DIR / 'player_box_2026.parquet'
STORED = DERIVED / 'history' / '2026' / 'segments.parquet'
ON = DERIVED / 'history' / '2026' / 'on_court.parquet'
EVENT_COLS = ['game_id', 'period', 'poss', 'offense', 'defense', 'end_type', 'actor', 'value', 'zone',
              'made', 'assister', 'blocker', 'stealer', 'fouler', 'fta', 'ftm', 'ft_seq', 'rebound', 'rebounder', 'points']


def audit(limit: int) -> dict:
    manifest = json.loads(MANIFEST.read_text())
    game_ids = [str(g['game_id']) for g in manifest['control']['games'][:limit]]
    if limit < 1 or len(game_ids) != limit or len(set(game_ids)) != limit:
        raise ValueError('limit must select distinct games from the fixed control panel')
    filters = [('game_id', 'in', [int(g) for g in game_ids])]
    pbp = pd.read_parquet(PBP, filters=filters)
    box = pd.read_parquet(BOX, filters=filters)
    games, boxes = {str(int(k)): v for k, v in pbp.groupby('game_id')}, \
                   {str(int(k)): v for k, v in box.groupby('game_id')}
    if set(games) != set(game_ids) or set(boxes) != set(game_ids):
        raise ValueError('missing selected raw PBP or box game')
    old_rows, new_rows, old_issues, new_issues = [], [], {}, {}
    started = time.monotonic()
    step = max(1, (limit + 9) // 10)
    for i, gid in enumerate(game_ids, 1):
        game = plays.from_hoopr(gid, games[gid].to_dict('records'), boxes[gid].to_dict('records'))
        old, old_report = possessions.parse_many([game])
        new, new_report = possessions.parse_many([game], split_substitutions=True)
        if old_report['games_flagged'] != new_report['games_flagged']:
            raise ValueError(f'{gid}: parser reconciliation status changed')
        old_rows.extend(old)
        new_rows.extend(new)
        for key, value in old_report['issues'].items():
            old_issues[key] = old_issues.get(key, 0) + value
        for key, value in new_report['issues'].items():
            new_issues[key] = new_issues.get(key, 0) + value
        if i % step == 0 or i == limit:
            print(f'games {i}/{limit} {time.monotonic() - started:.1f}s', flush=True)
    old, new = possessions.to_frame(old_rows), possessions.to_frame(new_rows)
    retained = pd.read_parquet(STORED)
    retained = retained[retained['game_id'].astype(str).isin(game_ids)]
    sort_cols = ['game_id', 'period']
    retained = retained.sort_values(sort_cols, kind='stable').reset_index(drop=True)
    old = old.sort_values(sort_cols, kind='stable').reset_index(drop=True)
    new = new.sort_values(sort_cols, kind='stable').reset_index(drop=True)
    pd.testing.assert_frame_equal(old[retained.columns], retained, check_dtype=False, check_like=False)
    actual = new[~new['sub_prefix']].reset_index(drop=True)
    pd.testing.assert_frame_equal(old[EVENT_COLS], actual[EVENT_COLS], check_dtype=False, check_like=False)
    court = pd.read_parquet(ON)
    court = court[court['game_id'].astype(str).isin(game_ids)]
    before = a1_lineup_audit.lineup_summary(old, court)
    after = a1_lineup_audit.lineup_summary(new, court)
    quarantined = new[~new['lineup_valid']]
    reasons = quarantined['lineup_issues'].str.split(';').explode().value_counts().to_dict()
    examples = quarantined[['game_id', 'period', 'start_clock', 'action_clock', 'end_type', 'actor', 'lineup_issues']].head(20)
    examples = examples.astype(object).where(examples.notna(), None).to_dict('records')
    paths = [MANIFEST, PBP, BOX, STORED, ON, ROOT / 'scripts' / 'possessions.py', ROOT / 'scripts' / 'features.py']
    return {'experiment': 'a1_substitution_split_pilot', 'game_ids': game_ids,
            'population': 'fixed F4 control games; retrospective data-quality comparison, not model evaluation',
            'source_reparse_matches_retained_segments': True, 'event_identity_points_and_possessions_match': True,
            'new_action_free_prefix_segments': int(new['sub_prefix'].sum()),
            'quarantined_segments': len(quarantined), 'quarantined_prefix_segments': int(quarantined['sub_prefix'].sum()),
            'quarantine_reasons': reasons, 'quarantine_examples': examples,
            'before': before, 'candidate': after, 'old_parser_issues': old_issues, 'candidate_parser_issues': new_issues,
            'limitations': 'candidate remains isolated; substitutions after an action or within a free-throw/rebound '
                           'sequence are not split, and future-fitted feature safety is not established',
            'input_sha256': {str(p.relative_to(ROOT)): sha256_file(p) for p in paths}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--limit', type=int, default=3, help='number of fixed control games, in manifest order')
    parser.add_argument('--output', type=Path, required=True, help='new report path; existing reports are never overwritten')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f'refusing to overwrite {args.output}')
    report = audit(args.limit)
    write_json(args.output, report, pretty=True)
    print(f'saved {args.output}')


if __name__ == '__main__':
    main()
