#!/usr/bin/env python3
"""Player bodies (owner, PLAN §9 item 4): height, weight and date of birth for every player in the profiles.

Current players come from the retained team rosters (`data/raw/espn/runs/*/roster/`, latest run first); players no
longer on a roster from one polite request each to ESPN's athlete endpoint, kept raw under `data/raw/espn/athletes/`
(written once). Output: `data/derived/athletes.parquet` — player, height_in, weight_lb, birth_date, source.

  .venv/bin/python scripts/athletes.py [--fetch]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, RAW, read_json, write_json  # noqa: E402

ATHLETE = 'https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/athletes/{id}'
FOLDER = RAW / 'athletes'
OUT = DERIVED / 'athletes.parquet'


def profile_players() -> set:
    return set(pd.read_parquet(DERIVED / 'features' / 'pregame.parquet', columns=['player'])['player'].astype(str).unique())


def from_rosters() -> dict:
    out = {}
    for run in sorted((p for p in (RAW / 'runs').iterdir() if p.is_dir()), reverse=True):  # latest first
        for f in sorted((run / 'roster').glob('*.json.gz')):
            for a in read_json(f).get('athletes', []):
                out.setdefault(str(a['id']), {'height_in': a.get('height'), 'weight_lb': a.get('weight'),
                                              'birth_date': (a.get('dateOfBirth') or '')[:10] or None, 'source': f'roster {run.name}'})
    return out


def fetch(missing) -> int:
    from scripts.fetch_espn import Client, save
    client = Client(delay=1.0)
    todo = [pid for pid in sorted(missing) if not (FOLDER / f'{pid}.json.gz').exists()]
    for i, pid in enumerate(todo, 1):
        try:
            save(FOLDER / f'{pid}.json.gz', client.json(ATHLETE.format(id=pid)))
        except Exception as error:  # keep going; the player stays missing (never imputed here)
            print(f'  {pid}: {error!r}', flush=True)
        if i % 20 == 0 or i == len(todo):
            print(f'athletes {i}/{len(todo)}', flush=True)
    return client.count


def build() -> dict:
    players = profile_players()
    rows = from_rosters()
    for f in sorted(FOLDER.glob('*.json.gz')):
        d = read_json(f)
        rows.setdefault(f.name.split('.')[0], {'height_in': d.get('height'), 'weight_lb': d.get('weight'),
                                               'birth_date': (d.get('dateOfBirth') or '')[:10] or None, 'source': 'athlete'})
    df = pd.DataFrame([{'player': pid, **rows[pid]} for pid in sorted(players) if pid in rows])
    df.to_parquet(OUT, index=False)
    report = {'players_in_profiles': len(players), 'with_body': int(df[['height_in', 'weight_lb']].notna().all(axis=1).sum()),
              'missing': sorted(players - set(df['player'])),
              'height_in': {'mean': round(float(df['height_in'].mean()), 2), 'min': float(df['height_in'].min()), 'max': float(df['height_in'].max())},
              'weight_lb': {'mean': round(float(df['weight_lb'].mean()), 1), 'min': float(df['weight_lb'].min()), 'max': float(df['weight_lb'].max())},
              'by_source': df['source'].str.split(' ').str[0].value_counts().to_dict()}
    write_json(DERIVED / 'athletes_report.json', report, pretty=True)
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--fetch', action='store_true', help='fetch players missing from the rosters (one polite request each)')
    args = ap.parse_args()
    if args.fetch:
        missing = profile_players() - set(from_rosters())
        print(f'players not on a retained roster: {len(missing)}', flush=True)
        print(f'requests: {fetch(missing)}', flush=True)
    r = build()
    print({k: v for k, v in r.items() if k != 'missing'}, 'missing:', len(r['missing']))


if __name__ == '__main__':
    main()
