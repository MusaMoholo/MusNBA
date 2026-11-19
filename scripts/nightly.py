#!/usr/bin/env python3
"""Nightly pipeline: collect → master fixtures → box scores → snapshot(s) → views.

  .venv/bin/python scripts/nightly.py                 collect, project today (ET), rebuild views
  .venv/bin/python scripts/nightly.py --offline       reuse retained raw data
  .venv/bin/python scripts/nightly.py --backfill-days 7
        also build retrospective snapshots for the previous seven slate dates (cutoff-safe stats,
        no injury news: labelled retrospective in the app)
  .venv/bin/python scripts/nightly.py --views-only    rebuild presentation views, no simulation

A snapshot for slate date D reads only games final before D. Replacing an existing snapshot
archives it outside the repo first.
"""
from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import (CONFERENCE_OF, DERIVED, DIVISION_OF, MASTER_CSV, SEASON_LABEL, SNAPSHOTS,  # noqa: E402
                               archive_paths, day_shift, parse_utc, read_json, sha256_file, today_et, utc_now,
                               write_json)
from scripts import box_scores, master_fixtures, pbp, projection, views  # noqa: E402
from scripts.fetch_espn import collect, latest_run  # noqa: E402
from scripts.season_stats import period_profiles, player_table, team_table  # noqa: E402


def team_registry(run: Path) -> dict:
    teams = {}
    for item in read_json(run / 'teams.json.gz')['sports'][0]['leagues'][0]['teams']:
        t = item['team']
        abbr = t['abbreviation']
        if abbr not in CONFERENCE_OF:
            raise SystemExit(f'Unknown team abbreviation {abbr}: update DIVISIONS in basketball_common.py')
        teams[t['id']] = {'id': t['id'], 'abbr': abbr, 'name': t.get('displayName'), 'short': t.get('shortDisplayName'),
                          'nickname': t.get('name'), 'location': t.get('location'),
                          'color': t.get('color'), 'alt': t.get('alternateColor'),
                          'conf': CONFERENCE_OF[abbr], 'div': DIVISION_OF[abbr]}
    if len(teams) != 30:
        raise SystemExit(f'Expected 30 teams, found {len(teams)}')
    write_json(DERIVED / 'teams.json', teams)
    return teams


def build_snapshot(day: str, teams: dict, master: list[dict], team_rows: list[dict], player_rows: list[dict],
                   registry: dict, prospective: bool, sims: int, archive_root=None, period_rows=None, engine_worlds: int = 0) -> dict:
    """engine_worlds > 0 (prospective slates only — the engine reads latest profiles, so past dates would leak): games
    come from the possession engine (D22, the default); the placeholder's results are kept beside them
    (games_placeholder.json) for comparison. Retrospective backfills always use the placeholder."""
    started = time.time()
    T, lg = team_table(team_rows, day, teams)
    if lg['teams_gp'] < 20:
        raise SystemExit(f'Too few completed games before {day} to project ({lg["games"]}).')
    P = player_table(player_rows, day)
    Q, priors = period_profiles(period_rows if period_rows is not None else pbp.load(), player_rows, day, team_rows, blowout=15)
    slate = [r for r in master if r['date_et'] == day]
    generated = utc_now()
    games, probs, pre_tip, placeholder = {}, {}, {}, {}
    eng = None
    if engine_worlds and prospective and slate:
        from scripts import engine as engine_mod
        eng = engine_mod.Engine()
    for game in slate:
        result = projection.simulate_game(game, T, lg, P, registry, day, prospective, sims, Q, priors)
        if eng is not None:
            placeholder[game['game_id']] = result
            g = engine_mod.inputs_for(game, day, T, lg, P, registry, Q, priors)
            result = eng.simulate(g, engine_worlds, projection.seed_for(engine_mod.ENGINE['id'], day, game['game_id']))
            print(f"  engine {game['game_id']}: {result['periods']['fg']['home']['pts']['mean']:.1f}–{result['periods']['fg']['away']['pts']['mean']:.1f}", flush=True)
        games[game['game_id']] = result
        probs[game['game_id']] = result['periods']['fg']['home']['win']
        pre_tip[game['game_id']] = parse_utc(generated) < parse_utc(game['tip_utc'])
    season = projection.simulate_season(T, lg, master, day, teams, probs, sims)
    target = SNAPSHOTS / day
    meta = {
        'schema': 1, 'season': SEASON_LABEL, 'slate_date': day, 'cutoff': day_shift(day, -1),
        'kind': 'prospective' if prospective else 'retrospective', 'generated': generated,
        'model': ({**engine_mod.ENGINE, 'sims': engine_worlds, 'season_sims': sims} if eng is not None else projection.MODEL),
        'sims': engine_worlds if eng is not None else sims, 'season_sims': sims,
        'seeds': 'sha256(model|slate date|game) per game; (model|date|season)',
        'games': [g['game_id'] for g in slate], 'pre_tip': pre_tip,
        'inputs': {'master_sha256': sha256_file(MASTER_CSV),
                   'player_games_sha256': sha256_file(DERIVED / 'player_games.csv'),
                   'team_games_sha256': sha256_file(DERIVED / 'team_games.csv'),
                   'player_periods_sha256': sha256_file(DERIVED / 'player_periods.csv'),
                   'registry_run': read_json(DERIVED / 'players.json')['run'] if prospective else None,
                   'completed_games_used': lg['games'],
                   **({'engine_inputs_sha256': {n: sha256_file(f) for n, f in (
                       ('latest', DERIVED / 'features' / 'latest.parquet'), ('team_latest', DERIVED / 'features' / 'team_latest.parquet'),
                       ('stints', DERIVED / 'rotations' / 'stints.parquet'), ('models', DERIVED.parent / 'models' / 'v1' / 'config.json'))}}
                      if eng is not None else {})},
        'notes': ([] if prospective else ['Retrospective reconstruction: built after the fact from cutoff-safe box scores; '
                                          'injury news from that date was not retained.']),
        'seconds': None,
    }
    if target.exists():
        saved = archive_paths([target], archive_root)
        print(f'archived previous snapshot {day} -> {saved}', flush=True)
        shutil.rmtree(target)
    staging = SNAPSHOTS / f'.{day}.partial'
    if staging.exists():
        shutil.rmtree(staging)
    write_json(staging / 'games.json', games)
    if placeholder:
        write_json(staging / 'games_placeholder.json', placeholder)
    write_json(staging / 'season.json', season)
    write_json(staging / 'stats.json', {'teams': T, 'league': lg, 'players': P})
    meta['seconds'] = round(time.time() - started, 2)
    write_json(staging / 'meta.json', meta, pretty=True)
    staging.rename(target)
    print(f'snapshot {day} ({meta["kind"]}, {meta["model"]["id"]}): {len(slate)} games, {meta["sims"]:,} sims each, '
          f'season {len(season["games"])} games · {meta["seconds"]}s', flush=True)
    return meta


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--date', help='Slate date (ET), default today ET')
    parser.add_argument('--offline', action='store_true', help='Skip collection; use retained raw data')
    parser.add_argument('--views-only', action='store_true', help='Only rebuild presentation views')
    parser.add_argument('--backfill-days', type=int, default=0)
    parser.add_argument('--rebuild', action='store_true', help='Rebuild existing backfill snapshots too')
    parser.add_argument('--sims', type=int, default=projection.MODEL['sims'])
    parser.add_argument('--engine', type=int, default=2000, metavar='WORLDS',
                        help="worlds per game for today's slate from the possession engine (default 2,000; D22: the default model)")
    parser.add_argument('--placeholder', action='store_true',
                        help='project today with the placeholder baseline-v1 instead of the engine (backfills always use it)')
    parser.add_argument('--archive-root', type=Path)
    args = parser.parse_args()
    day = args.date or today_et()
    if args.views_only:
        views.build()
        return 0
    if not args.offline:
        report = collect(day)
        if report['failures']:
            print(f'{len(report["failures"])} collection failures (see run report); continuing with retained data',
                  file=sys.stderr)
    run = latest_run()
    teams = team_registry(run)
    master_fixtures.write(master_fixtures.build(run))
    box_scores.build(run)
    report = pbp.build()
    print(f'play-by-play: {report["games"]} games · {report["rows"]:,} player-periods · '
          f'points mismatch {report["mismatch_rates"].get("pts", 0):.2%} · minutes {report["mismatch_rates"].get("min", 0):.2%}', flush=True)
    master = master_fixtures.load()
    team_rows, player_rows = box_scores.load_csv('team_games.csv'), box_scores.load_csv('player_games.csv')
    period_rows = pbp.load()
    registry = read_json(DERIVED / 'players.json')['players']
    slate_dates = sorted({r['date_et'] for r in master})
    for back in range(args.backfill_days, 0, -1):
        d = day_shift(day, -back)
        if d not in slate_dates:
            continue
        if (SNAPSHOTS / d).exists() and not args.rebuild:
            continue
        build_snapshot(d, teams, master, team_rows, player_rows, registry, False, args.sims, args.archive_root, period_rows)
    if day in slate_dates:
        build_snapshot(day, teams, master, team_rows, player_rows, registry, day == today_et(), args.sims, args.archive_root, period_rows,
                       engine_worlds=0 if args.placeholder else args.engine)
    else:
        print(f'No games scheduled on {day}; views still rebuilt.', flush=True)
    views.build()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
