#!/usr/bin/env python3
"""Historical play-by-play (ENGINE_PLAN.md M1): sportsdataverse season files → canonical games →
per-period player rows, with the same box-score reconciliation as the live feed.

  .venv/bin/python scripts/history.py --fetch            download missing seasons (2023–2026)
  .venv/bin/python scripts/history.py                    parse every downloaded season

Raw files are kept unmodified under data/raw/hoopr/ with a manifest (source URL, bytes, sha256,
retrieval time). Seasons are hoopR's end years: 2023 = 2022-23 … 2026 = 2025-26. The current season
comes from our own collection, not from these files.
"""
from __future__ import annotations

import argparse
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DATA, DERIVED, atomic_bytes, read_json, sha256_file, utc_now, write_json  # noqa: E402
from scripts import pbp, plays  # noqa: E402

SOURCE = 'https://github.com/sportsdataverse/sportsdataverse-data/releases/download'
FILES = {'pbp': 'espn_nba_pbp/play_by_play_{season}.parquet', 'box': 'espn_nba_player_boxscores/player_box_{season}.parquet'}
SEASONS = (2023, 2024, 2025, 2026)
RAW_DIR = DATA / 'raw' / 'hoopr'
OUT_DIR = DERIVED / 'history'
MANIFEST = RAW_DIR / 'manifest.json'
USER_AGENT = 'MusNBA/0.1 (personal research client)'


def fetch(seasons=SEASONS) -> dict:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest = read_json(MANIFEST) if MANIFEST.exists() else {}
    for season in seasons:
        for kind, template in FILES.items():
            rel = template.format(season=season)
            target = RAW_DIR / Path(rel).name
            if target.exists() and target.name in manifest:
                continue
            url = f'{SOURCE}/{rel}'
            request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
            with urllib.request.urlopen(request, timeout=300) as response:
                data = response.read()
            if data[:4] != b'PAR1':
                raise SystemExit(f'{url} did not return a parquet file')
            atomic_bytes(target, data)
            manifest[target.name] = {'url': url, 'bytes': len(data), 'sha256': sha256_file(target), 'retrieved': utc_now()}
            print(f'downloaded {target.name} · {len(data) / 1e6:.1f} MB', flush=True)
    write_json(MANIFEST, manifest, pretty=True)
    return manifest


def season_games(season: int, season_types=(2, 3, 5)):
    """Yield canonical games for one season: regular season (2), playoffs (3) and play-in (5) by default.
    Game type stays on every row (`season_type`) so models can use it as an input or a weight."""
    import pandas as pd
    pbp_df = pd.read_parquet(RAW_DIR / f'play_by_play_{season}.parquet')
    box_df = pd.read_parquet(RAW_DIR / f'player_box_{season}.parquet')
    pbp_df = pbp_df[pbp_df['season_type'].isin(season_types)]
    box_by_game = defaultdict(list)
    for row in box_df.to_dict('records'):
        box_by_game[str(int(row['game_id']))].append(row)
    for game_id, frame in pbp_df.groupby('game_id', sort=True):
        gid = str(int(game_id))
        if gid not in box_by_game:
            continue
        yield plays.from_hoopr(gid, frame.to_dict('records'), box_by_game[gid])


def build(seasons=SEASONS) -> dict:
    reports = {}
    for season in seasons:
        if not (RAW_DIR / f'play_by_play_{season}.parquet').exists():
            print(f'{season}: not downloaded (run with --fetch)')
            continue
        inference = {'checked': 0, 'agree': 0, 'inferred': 0}
        def counted(games):
            for game in games:
                for k, v in game['points_attempted_inference'].items():
                    inference[k] += v
                yield game
        rows, report = pbp.parse_many(counted(season_games(season)))
        report['points_attempted'] = {**inference, 'agreement_where_known': round(inference['agree'] / inference['checked'], 5) if inference['checked'] else None}
        out = OUT_DIR / str(season)
        import gzip
        atomic_bytes(out / 'player_periods.csv.gz', gzip.compress(pbp.csv_bytes(rows), compresslevel=6, mtime=0))
        write_json(out / 'pbp_report.json', report, pretty=True)
        reports[season] = report
        worst = max(report['mismatch_rates'].items(), key=lambda kv: kv[1], default=('-', 0))
        print(f"{season}: {report['games']} games · {report['rows']:,} player-periods · points {report['mismatch_rates'].get('pts', 0):.2%} · "
              f"minutes {report['mismatch_rates'].get('min', 0):.2%} · worst {worst[0]} {worst[1]:.2%} · inferred shot values {inference['inferred']:,}"
              f" (agreement where known {report['points_attempted']['agreement_where_known']})", flush=True)
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--fetch', action='store_true', help='download missing season files first')
    parser.add_argument('--seasons', type=int, nargs='*', default=list(SEASONS))
    args = parser.parse_args()
    if args.fetch:
        fetch(args.seasons)
    build(args.seasons)


if __name__ == '__main__':
    main()
