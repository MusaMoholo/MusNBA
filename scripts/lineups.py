#!/usr/bin/env python3
"""Projected starters: the record of how right they were (owner, 20 Nov: measure projected v actual starters each night).

The engine opens every game with five projected starters (minutes.projected_starters: start share, then priority;
D29) and the app shows them. Each night, for every saved snapshot whose games are now final, this scores the snapshot's
starters against the real ones (our box scores) and keeps one line per slate in data/derived/lineups/accuracy.json.

External projected-lineup sources (owner, 20 Nov; FINDINGS §1): RotoWire and Lineups.com are blocked on the work network;
Basketball Monster's and CBS Sports' terms forbid scraping; DailyFantasyFuel has no NBA lineup page (its projections page
is a 25-player preview); FantasyPros' terms allow "a single copy made for personal use" and are silent on automated
access — owner decision. Until a source is approved, our own projection is the yardstick it must beat: Jan–Apr 2026,
known availability, 89.4% of starter slots right, all five in 53.5% of team-games.

  .venv/bin/python scripts/lineups.py --score        score every finished snapshot (also run by nightly.py)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, LINEUP_TIMING_POLICY, forecast_meta, verified_pre_tip, write_json  # noqa: E402

SNAPSHOTS = ROOT / 'data' / 'snapshots'
OUT = DERIVED / 'lineups' / 'accuracy.json'


def score_day(day: str, box: pd.DataFrame) -> dict | None:
    path = SNAPSHOTS / day / 'games.json'
    if not path.exists():
        return None
    games = json.loads(path.read_text())
    meta = json.loads((SNAPSHOTS / day / 'meta.json').read_text()) if (SNAPSHOTS / day / 'meta.json').exists() else {}
    if meta.get('kind') != 'prospective':
        return None
    slots = right = teams = all_five = 0
    misses, provenance = [], {}
    for gid, g in games.items():
        source = forecast_meta(meta, gid)
        if source.get('kind') != 'prospective' or verified_pre_tip(source, gid) is not True:
            continue
        real = box[box['game_id'] == str(gid)]
        if real.empty:
            continue
        for side in ('home', 'away'):
            proj = {str(p['id']) for p in g[side]['players'] if p.get('starter')}
            team_ids = {str(p['id']) for p in g[side]['players']}
            actual = set(real.loc[(real['starter'] == '1') & real['player_id'].isin(team_ids), 'player_id'])
            if len(actual) != 5 or len(proj) != 5:
                continue
            provenance[gid] = {'model': (source.get('model') or {}).get('id'),
                               'completed_at': source.get('completed_at')}
            k = len(proj & actual)
            slots, right, teams, all_five = slots + 5, right + k, teams + 1, all_five + (k == 5)
            misses += [{'game_id': gid, 'side': side, 'projected_not_started': sorted(proj - actual), 'started_not_projected': sorted(actual - proj)}] if k < 5 else []
    if not teams:
        return None
    out = {'slate': day, 'model': (meta.get('model') or {}).get('id'), 'completed_at': meta['completed_at'],
           'team_games': teams, 'slot_accuracy': round(right / slots, 4),
           'all_five': round(all_five / teams, 4), 'misses': misses}
    if meta.get('game_provenance_schema') is not None:
        models = {source['model'] for source in provenance.values()}
        times = {source['completed_at'] for source in provenance.values()}
        out.update({'model': next(iter(models)) if len(models) == 1 else 'mixed',
                    'completed_at': next(iter(times)) if len(times) == 1 else None,
                    'game_provenance': provenance})
    return out


def score(days=None) -> dict:
    box = pd.read_csv(DERIVED / 'player_games.csv', dtype=str, usecols=['game_id', 'player_id', 'starter'])
    record: dict[str, Any] = json.loads(OUT.read_text()) if OUT.exists() else {'slates': {}}
    if record.get('timing_policy') != LINEUP_TIMING_POLICY:
        record['legacy_unverified_slates'] = record.get('slates', {})
        if record.get('overall') is not None:
            record['legacy_unverified_overall'] = record['overall']
        record['slates'] = {}
        record.pop('overall', None)
    record['timing_policy'] = LINEUP_TIMING_POLICY
    for day in days or sorted(p.name for p in SNAPSHOTS.glob('20*') if p.is_dir()):
        r = score_day(day, box)
        if r is not None:
            record['slates'][day] = r
    sl = list(record['slates'].values())
    if sl:
        n = sum(r['team_games'] for r in sl)
        record['overall'] = {'slates': len(sl), 'team_games': n,
                             'slot_accuracy': round(sum(r['slot_accuracy'] * r['team_games'] for r in sl) / n, 4),
                             'all_five': round(sum(r['all_five'] * r['team_games'] for r in sl) / n, 4)}
    else:
        record.pop('overall', None)
    write_json(OUT, record, pretty=True)
    return record


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--score', action='store_true')
    args = ap.parse_args()
    if args.score:
        r = score()
        print(json.dumps({k: v for k, v in r.items() if k != 'slates'}, indent=1))
        for d, x in r['slates'].items():
            print(d, x['model'], x['team_games'], x['slot_accuracy'], x['all_five'])


if __name__ == '__main__':
    main()
