#!/usr/bin/env python3
"""Nightly pipeline: collect → master fixtures → box scores → snapshot(s) → views.

  .venv/bin/python scripts/nightly.py                 collect, project today (ET; D50), rebuild views
  .venv/bin/python scripts/nightly.py --offline       reuse retained raw data
  .venv/bin/python scripts/nightly.py --backfill-days 7
        also build retrospective snapshots for the previous seven slate dates (cutoff-safe stats,
        no injury news: labelled retrospective in the app)
  .venv/bin/python scripts/nightly.py --views-only    rebuild presentation views, no simulation

A snapshot for slate date D reads only games final before D. Replacing an existing snapshot
archives it outside the repo first.

Engine horizon (D50): the possession engine projects today's games only; later games use the team pathway.
Before it runs, the engine's inputs are rebuilt from every final before today — current-season
segments → rotations → player and team profiles — so form and roles carry over from the last game (`--no-rebuild` skips).
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import os
for _thread_limit in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_thread_limit] = '1'
import json
import shutil
import sys
import time
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import (CONFERENCE_OF, DERIVED, DIVISION_OF, MASTER_CSV, SEASON_LABEL, SNAPSHOTS,  # noqa: E402
                               archive_paths, day_shift, forecast_meta, parse_utc, read_json, sha256_file, today_et, utc_now,
                               verified_pre_tip, write_json)
from scripts import box_scores, master_fixtures, pbp, player_worlds as player_worlds_io, projection, views  # noqa: E402
from scripts.fetch_espn import collect, latest_run  # noqa: E402
from scripts.season_stats import period_profiles, player_table, team_table  # noqa: E402
from scripts.world_mass import WorldMass  # noqa: E402


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


def forecast_availability_report(game: dict, registry: dict) -> dict:
    """Freeze roster and report status as used for this forecast, including ruled-out players."""
    report = {}
    for side in ('home', 'away'):
        tid = str(game[f'{side}_id'])
        report[side] = []
        for pid, row in registry.items():
            if not row.get('on_roster') or str(row.get('team')) != tid:
                continue
            status = (row.get('status') or '').strip() or 'Unknown'
            report[side].append({'id': str(pid), 'name': row.get('name'), 'status': status,
                                 'reported_status': row.get('reported_status'), 'status_source': row.get('status_source'),
                                 'injury': deepcopy(row.get('injury')), 'availability': projection.availability(status)})
    return report


def completed_live_tasks(tasks, runtime, median):
    """Keep all generation/finalisation in the worker budget; parent loads large arrays afterwards."""
    from scripts import live_forecast
    if runtime.get('rotation_fit') == 'independent-v1':
        yield from live_forecast.run(tasks, runtime, median, workers=10,
                                     chunk_worlds=runtime.get('chunk_worlds',1000))
    else:
        with ProcessPoolExecutor(max_workers=min(8,len(tasks)), initializer=live_forecast.initialise,
                                 initargs=(runtime,)) as pool:
            for future in as_completed([pool.submit(live_forecast.project,task) for task in tasks]):
                yield future.result()


def project_slate(day: str, teams: dict, master: list[dict], team_rows: list[dict], player_rows: list[dict],
                  registry: dict, prospective: bool, sims: int, period_rows=None, engine_worlds: int = 0,
                  origin: str | None = None, retained: dict | None = None) -> dict:
    """One slate's games. engine_worlds > 0 (prospective slates only — the engine reads latest profiles, so past dates
    would leak): games come from the possession engine (D22, the default) and each game's per-world, per-period points
    are kept for the team pathway (D25: universe k plays engine world k); the placeholder's results are kept beside them
    (games_placeholder.json) for comparison. Retrospective backfills always use the placeholder."""
    origin = day if origin is None else origin
    if origin > day:
        raise ValueError(f'forecast origin {origin} is after slate {day}')
    if retained and (not prospective or not engine_worlds):
        raise ValueError('retained engine forecasts require a prospective engine slate')
    started = time.time()
    T, lg = team_table(team_rows, origin, teams)
    if lg['teams_gp'] < 20:
        raise SystemExit(f'Too few completed games before {origin} to project ({lg["games"]}).')
    P = player_table(player_rows, origin)
    Q, priors = period_profiles(period_rows if period_rows is not None else pbp.load(), player_rows, origin, team_rows, blowout=15)
    slate = [r for r in master if r['date_et'] == day]
    generated = utc_now()
    games, placeholder, worlds, player_worlds = {}, {}, {}, {}
    live_tasks, live_dirs = [], {}
    from scripts import live_forecast
    source_hashes = live_forecast.fingerprints() if engine_worlds and prospective else {}
    live_root = DERIVED / "live_runs" / (day + "-" + str(time.time_ns()))
    eng = engine_mod = None
    if engine_worlds and prospective:
        from scripts import engine as engine_mod
        if any(game['game_id'] not in (retained or {}) for game in slate):
            eng = engine_mod.Engine()
    for game in slate:
        gid = game['game_id']
        if retained and gid in retained:
            saved = retained[gid]
            games[gid], placeholder[gid] = deepcopy(saved['game']), deepcopy(saved['placeholder'])
            worlds[gid], player_worlds[gid] = saved['worlds'], saved['players']
            if saved.get('live_dir'):
                live_dirs[gid] = saved['live_dir']
            continue
        result = projection.simulate_game(game, T, lg, P, registry, day, prospective, sims, Q, priors)
        if eng is not None:
            assert engine_mod is not None
            placeholder[game['game_id']] = result
            g = engine_mod.inputs_for(game, day, T, lg, P, registry, Q, priors, origin=origin)
            from scripts import a1_lineup_branches
            selected, _ = a1_lineup_branches.live_selection(g, registry, engine_mod._MINUTES[origin], T, lg, P, Q, priors)
            live_tasks.append((g, selected, engine_worlds, str(live_root / gid), {'origin': origin, 'sources': source_hashes, 'registry_run': read_json(DERIVED / 'players.json')['run']}))
            continue
        if prospective:
            result['availability_report'] = forecast_availability_report(game, registry)
        games[game['game_id']] = result
    if live_tasks:
        from scripts import live_forecast
        if any(os.environ.get(key) != '1' for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS')):
            raise ValueError('Nightly workers require OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1')
        live_tasks.sort(key=lambda task: (-2**len(task[1]), task[0].game['game_id']))
        completed_dirs = []
        for directory in completed_live_tasks(live_tasks,engine_mod.ENGINE,eng.m.median):
            folder = Path(directory)
            completed_dirs.append(folder)
            print(f"engine {len(completed_dirs)}/{len(live_tasks)} complete games; {folder.name} in {time.time()-started:.1f}s",flush=True)
        # The pool has shut down: decompression here cannot become an eleventh compute worker.
        for folder in completed_dirs:
            gid = folder.name
            result = read_json(folder/'game.json')
            game = next(row for row in slate if row['game_id']==gid)
            result['availability_report'] = forecast_availability_report(game,registry)
            games[gid] = result
            with np.load(folder/'points.npz',allow_pickle=False) as z:
                worlds[gid] = z['points']
            with np.load(folder/'players.npz',allow_pickle=False) as z:
                player_worlds[gid] = {key:z[key] for key in z.files}
            live_dirs[gid] = folder
        if live_forecast.fingerprints() != source_hashes:
            raise ValueError('Live runtime/model sources changed during generation; refusing publication')
    if engine_mod is not None:
        assert engine_mod is not None
        model = {**engine_mod.ENGINE, 'sims': engine_worlds, 'season_sims': sims}
        engine_inputs = ({'engine_inputs_sha256': {n: sha256_file(f) for n, f in (
            ('latest', engine_mod.features_dir() / 'latest.parquet'), ('team_latest', engine_mod.features_dir() / 'team_latest.parquet'),
            ('stints', DERIVED / 'rotations' / 'stints.parquet'), ('on_court', DERIVED / 'rotations' / 'on_court.parquet'),
            ('models', DERIVED.parent / 'models' / engine_mod.ENGINE.get('models', engine_mod.ENGINE['version']) / 'config.json'))}}
            if eng is not None else {})
    else:
        model, engine_inputs = projection.MODEL, {}
    return {'day': day, 'origin': origin, 'T': T, 'lg': lg, 'P': P, 'slate': slate, 'games': games, 'placeholder': placeholder, 'worlds': worlds,
            'player_worlds': player_worlds, 'live_dirs': live_dirs,
            'prospective': prospective, 'generated': generated, 'started': started, 'model': model,
            'sims': engine_worlds if engine_mod is not None else sims, 'season_sims': sims, 'engine_inputs': engine_inputs,
            'retained': retained or {}}


def tip_is_future(game: dict, completed: str) -> bool | None:
    if game.get('time_valid') not in (True, 1, '1'):
        return None
    completion = parse_utc(completed)
    try:
        tip = datetime.fromisoformat(game['tip_utc'].replace('Z', '+00:00'))
        if tip.utcoffset() is None:
            raise ValueError('tip time needs a timezone')
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"{game['game_id']}: invalid valid tip time") from exc
    status = game.get('status')
    if status not in ('scheduled', 'live', 'final'):
        return None
    return status == 'scheduled' and completion < tip


def retained_game_ids(target: Path, slate: list[dict], prospective: bool, completed: str) -> set[str]:
    """Identify verified pre-tip games that cannot safely be replaced."""
    previous = target.with_name(f'.{target.name}.previous')
    if previous.exists():
        if target.exists():
            raise ValueError(f'{previous}: previous and active snapshots both exist; review interrupted publication')
        previous.rename(target)
    meta_path = target / 'meta.json'
    if not meta_path.exists():
        return set()
    old = read_json(meta_path)
    if old.get('kind') != 'prospective' or views.discarded_preview(old.get('slate_date', target.name), old):
        return set()
    games = {game['game_id']: game for game in slate}
    retained = set()
    for gid in old.get('games', []):
        if verified_pre_tip(old, gid) is not True:
            continue
        game = games.get(gid)
        if not prospective or game is None:
            raise ValueError(f'{gid}: refusing to replace a retained pre-tip forecast with a missing or retrospective forecast')
        try:
            pre_tip = tip_is_future(game, completed)
        except ValueError as exc:
            raise ValueError(f'{gid}: refusing to replace a retained pre-tip forecast: {exc}') from exc
        if pre_tip is not True:
            retained.add(gid)
    return retained


def protect_pre_tip(target: Path, slate: list[dict], prospective: bool, completed: str,
                    retained: set[str] | None = None) -> None:
    """Do not replace a retained pre-tip forecast with a later or missing forecast."""
    unsafe = retained_game_ids(target, slate, prospective, completed) - (retained or set())
    if unsafe:
        raise ValueError(f'{", ".join(sorted(unsafe))}: refusing to replace a retained pre-tip forecast with a later or unknown forecast')


def load_retained(target: Path, slate: list[dict], completed: str) -> dict:
    """Load complete original forecasts that cannot safely be regenerated after tip."""
    ids = retained_game_ids(target, slate, True, completed)
    if not ids:
        return {}
    meta = read_json(target / 'meta.json')
    games = read_json(target / 'games.json')
    placeholder = read_json(target / 'games_placeholder.json')
    fixtures = {game['game_id']: game for game in slate}
    out = {}
    with np.load(target / 'engine_worlds.npz', allow_pickle=False) as worlds, \
            np.load(target / 'engine_players.npz', allow_pickle=False) as players:
        for gid in ids:
            source_meta = forecast_meta(meta, gid)
            game, base = games[gid], placeholder[gid]
            team_worlds = worlds[gid]
            player_worlds = player_worlds_io.read_player_worlds(players, gid)
            n = game['sims']
            mass = WorldMass(n, player_worlds.get('weights'))
            lines, player_ids, sides = player_worlds['lines'], player_worlds['ids'], player_worlds['side']
            if (source_meta.get('kind') != 'prospective' or verified_pre_tip(source_meta, gid) is not True
                    or source_meta.get('slate_date') != target.name or game.get('game_id') != gid
                    or source_meta.get('saved_worlds', {}).get(gid, n) != n
                    or (not game.get('lineups') and n != source_meta['sims'])
                    or game.get('probability_mass', n) != mass.total
                    or game.get('model') != source_meta.get('model', {}).get('id')
                    or any(str(game[side]['team_id']) != str(fixtures[gid][f'{side}_id'])
                           for side in ('home', 'away'))
                    or team_worlds.shape != (n, 2, 5) or lines.ndim != 3 or lines.shape[:2] != (n, len(player_ids))
                    or lines.shape[2] < 2 or player_ids.ndim != 1 or sides.shape != (len(player_ids),)
                    or len(set(player_ids.tolist())) != len(player_ids) or not np.isin(sides, [0, 1]).all()
                    or not all((sides == side).any() for side in (0, 1))
                    or team_worlds.dtype.kind not in 'iu' or lines.dtype.kind not in 'iu'
                    or (team_worlds < 0).any() or (lines < 0).any()):
                raise ValueError(f'{gid}: retained forecast, fixture or world dimensions do not match')
            scores = team_worlds.sum(axis=2)
            for side, name in enumerate(('home', 'away')):
                points = lines[:, sides == side, 1].astype(np.int64).sum(axis=1)
                if not np.array_equal(points, scores[:, side]):
                    raise ValueError(f'{gid}: retained player points do not sum to team worlds')
                if abs(float(mass.mean(scores[:, side])) - game['periods']['fg'][name]['pts']['mean']) > 0.00051:
                    raise ValueError(f'{gid}: retained team mean does not match game worlds')
            win = round(float(mass.mean(scores[:, 0] > scores[:, 1])), 4)
            if game['periods']['fg']['home']['win'] != win:
                raise ValueError(f'{gid}: retained win probability does not match game worlds')
            folder = target / 'lineups' / gid
            if game.get('lineups') and not folder.is_dir():
                raise ValueError(f'{gid}: retained lineup replay inputs are missing')
            out[gid] = {'game': game, 'placeholder': base, 'worlds': team_worlds,
                        'players': player_worlds, 'meta': deepcopy(source_meta),
                        'live_dir': folder if folder.is_dir() else None}
    return out


def validate_retained(part: dict, season: dict, target: Path, completed: str) -> None:
    retained = part.get('retained') or {}
    protect_pre_tip(target, part['slate'], part['prospective'], completed, set(retained))
    if not retained:
        return
    current = load_retained(target, part['slate'], completed)
    if not set(retained) <= set(current):
        raise ValueError('retained source forecasts changed during refresh')
    if read_json(target / 'stats.json') != {'teams': part['T'], 'league': part['lg'], 'players': part['P']}:
        raise ValueError('retained forecast statistics differ from the new season context')
    season_rows = {row['game_id']: row for row in season['games']}
    if not part.get('season_worlds') and season['sims'] != part['sims']:
        raise ValueError('retained forecasts and season require the same world count')
    for gid, saved in retained.items():
        original = current[gid]
        meta = original['meta']
        if (meta.get('origin') != part['origin'] or meta.get('model') != part['model']
                or saved['meta'] != meta or saved['game'] != original['game']
                or saved['placeholder'] != original['placeholder'] or part['games'].get(gid) != original['game']
                or part['placeholder'].get(gid) != original['placeholder']
                or not np.array_equal(part['worlds'][gid], original['worlds'])
                or set(part['player_worlds'][gid]) != set(original['players'])
                or any(not np.array_equal(part['player_worlds'][gid][key], value)
                       for key, value in original['players'].items())):
            raise ValueError(f'{gid}: retained forecast, model, origin or worlds changed')
        scores = original['worlds'].sum(axis=2)
        mass = WorldMass(len(scores), original['players'].get('weights'))
        if part.get('season_worlds'):
            weights = part['season_weights']
            season_mass = WorldMass(season['sims'], weights)
            indices = part['season_indices'][gid]
            if (indices.shape != (season['sims'],) or indices.dtype.kind not in 'iu'
                    or (indices < 0).any() or (indices >= len(scores)).any()
                    or not np.array_equal(part['season_worlds'][gid], original['worlds'][indices])):
                raise ValueError(f'{gid}: retained season world identities differ')
            counts = np.zeros(len(scores), np.int64)
            np.add.at(counts, indices, weights)
            original_weights = np.ones(len(scores), np.int64) if mass.weights is None else mass.weights
            if not np.array_equal(counts.astype(object)*mass.total, original_weights.astype(object)*season_mass.total):
                raise ValueError(f'{gid}: retained season probability masses differ')
        elif mass.weights is not None:
            raise ValueError(f'{gid}: retained weighted game requires season identity sidecars')
        expected = {'p_home': round(float(mass.mean(scores[:, 0] > scores[:, 1])), 4),
                    'mu_home': round(float(mass.mean(scores[:, 0])), 2),
                    'mu_away': round(float(mass.mean(scores[:, 1])), 2)}
        if (gid not in season_rows or season_rows[gid].get('source') != 'engine'
                or any(season_rows[gid].get(key) != value for key, value in expected.items())):
            raise ValueError(f'{gid}: season does not use retained game worlds')


def write_snapshot(part: dict, season: dict, archive_root=None) -> dict:
    """Stage a slate, archive the previous snapshot, and retain it for rollback during publication."""
    day, T, lg, slate, prospective = part['day'], part['T'], part['lg'], part['slate'], part['prospective']
    origin = part['origin']
    if season['as_of'] != origin:
        raise ValueError(f'season origin {season["as_of"]} differs from forecast origin {origin}')
    target = SNAPSHOTS / day
    meta = {
        'schema': 1, 'season': SEASON_LABEL, 'slate_date': day, 'origin': origin, 'cutoff': day_shift(origin, -1),
        'kind': 'prospective' if prospective else 'retrospective', 'generated': part['generated'],
        'started_at': part['generated'], 'completed_at': None,
        'model': part['model'], 'sims': part['sims'], 'season_sims': season['sims'],
        'saved_worlds': {gid: game['sims'] for gid, game in part['games'].items()},
        'season_model': {'id': season['model'], 'as_of': season['as_of'], 'label': season['pathway']['label']},
        'seeds': 'sha256(model|slate date|game) per game; (season model|as-of date|season)',
        'games': [g['game_id'] for g in slate], 'pre_tip': {g['game_id']: False for g in slate},
        'inputs': {'master_sha256': sha256_file(MASTER_CSV),
                   'player_games_sha256': sha256_file(DERIVED / 'player_games.csv'),
                   'team_games_sha256': sha256_file(DERIVED / 'team_games.csv'),
                   'player_periods_sha256': sha256_file(DERIVED / 'player_periods.csv'),
                   'registry_run': read_json(DERIVED / 'players.json')['run'] if prospective else None,
                   'completed_games_used': lg['games'], **part['engine_inputs']},
        'notes': ([] if prospective else ['Retrospective reconstruction: built after the fact from cutoff-safe box scores; '
                                          'injury news from that date was not retained.']),
        'seconds': None,
    }
    staging = SNAPSHOTS / f'.{day}.partial'
    if staging.exists():
        shutil.rmtree(staging)
    write_json(staging / 'games.json', part['games'])
    if part['placeholder']:
        write_json(staging / 'games_placeholder.json', part['placeholder'])
    if part['worlds']:  # per-world engine points: the season re-simulates from them (smoke); views never read them
        np.savez_compressed(staging / 'engine_worlds.npz', **part['worlds'])
    if part.get('player_worlds'):  # per-world player lines (app: joint and conditional outcomes; views packs them per game)
        player_path = staging / 'engine_players.npz'
        np.savez_compressed(player_path, **{f'{gid}__{k}': v for gid, d in part['player_worlds'].items() for k, v in d.items()})
        with np.load(player_path, allow_pickle=False) as archive:
            for gid in part['player_worlds']:
                player_worlds_io.read_player_worlds(archive, gid)
    for gid, folder in part.get('live_dirs', {}).items():
        shutil.copytree(folder, staging / 'lineups' / gid)
    if part.get('season_worlds'):
        np.savez_compressed(staging / 'season_engine_worlds.npz', weights=part['season_weights'], **part['season_worlds'])
        np.savez_compressed(staging / 'season_player_indices.npz', weights=part['season_weights'], **part['season_indices'])
    write_json(staging / 'season.json', season)
    write_json(staging / 'stats.json', {'teams': T, 'league': lg, 'players': part['P']})
    completed = utc_now()
    meta['generated'] = meta['completed_at'] = completed
    meta['pre_tip'] = {g['game_id']: tip_is_future(g, completed) for g in slate}
    meta['seconds'] = round(time.time() - part['started'], 2)
    validate_retained(part, season, target, completed)
    if part.get('retained'):
        fresh = deepcopy(meta)
        meta['game_provenance_schema'] = 1
        meta['game_provenance'] = {
            g['game_id']: deepcopy(part['retained'][g['game_id']]['meta'])
            if g['game_id'] in part['retained'] else deepcopy(fresh)
            for g in slate
        }
    write_json(staging / 'meta.json', meta, pretty=True)
    if target.exists():
        saved = archive_paths([target], archive_root)
        print(f'archived previous snapshot {day} -> {saved}', flush=True)
        completed = utc_now()
        validate_retained(part, season, target, completed)
        meta['generated'] = meta['completed_at'] = completed
        meta['pre_tip'] = {g['game_id']: tip_is_future(g, completed) for g in slate}
        meta['seconds'] = round(time.time() - part['started'], 2)
        if part.get('retained'):
            fresh = {key: value for key, value in meta.items()
                     if key not in ('game_provenance', 'game_provenance_schema')}
            for game in slate:
                if game['game_id'] not in part['retained']:
                    meta['game_provenance'][game['game_id']] = deepcopy(fresh)
        write_json(staging / 'meta.json', meta, pretty=True)
        previous = target.with_name(f'.{target.name}.previous')
        target.rename(previous)
        try:
            staging.rename(target)
        finally:
            if not target.exists():
                previous.rename(target)
        shutil.rmtree(previous)
    else:
        staging.rename(target)
    print(f'snapshot {day} ({meta["kind"]}, {meta["model"]["id"]}): {len(slate)} games, {meta["sims"]:,} sims each, '
          f'season {len(season["games"])} games as of {season["as_of"]} ({season["model"]}) · {meta["seconds"]}s', flush=True)
    return meta


def build_snapshot(day: str, teams: dict, master: list[dict], team_rows: list[dict], player_rows: list[dict],
                   registry: dict, prospective: bool, sims: int, archive_root=None, period_rows=None, engine_worlds: int = 0) -> dict:
    """One slate on its own (retrospective backfills): its games, and the season from its own cutoff."""
    part = project_slate(day, teams, master, team_rows, player_rows, registry, prospective, sims, period_rows, engine_worlds)
    season = projection.simulate_season(part['T'], part['lg'], master, day, teams, part['worlds'] or None, sims)
    return write_snapshot(part, season, archive_root)


def rebuild_engine_inputs(day: str) -> dict:
    """D26: the engine plays with inputs that carry every final before `day` — current-season segments
    (possessions.py), rotations (rotations.py, the replay templates) and profiles (features.py: latest.parquet,
    team_latest.parquet). Games dated `day` or later are left out (cutoff safety), even if already final."""
    from scripts import features, possessions, rotations
    started = time.time()
    seg = possessions.build_current(before=day)
    rot = rotations.build(possessions.current_games(before=day), DERIVED / 'rotations')
    feat = features.build()
    from scripts import engine as engine_mod  # the serving engine's profile variant (v1.3: defence + shot types, D30)
    spec_path = ROOT / 'models' / f"{engine_mod.ENGINE['version']}.json"
    variant = json.loads(spec_path.read_text()).get('features_variant') if spec_path.exists() else None
    real = None
    if (DERIVED.parent / 'raw' / 'nbastats' / 'boxscorematchupsv3').exists():  # D32/D37: matchups → ESPN ids, pair history
        try:  # (the Matchup view's who-guards-whom and the engine variants that use them; games before `day` only)
            real = refresh_real_matchups()
        except Exception as e:  # noqa: BLE001 — the engine never depends on it unless its variant uses real matchups
            print(f'real matchups refresh failed ({type(e).__name__}: {e})', file=sys.stderr, flush=True)
            if variant and variant.get('real_matchups'):
                raise
    if variant:
        features.build(ROOT / variant['out'], defence=variant.get('defence', False), defence_k_scale=variant.get('defence_k_scale', 1.0),
                       matchup=ROOT / variant['matchup'] if variant.get('matchup') else None, shot_types=variant.get('shot_types', False),
                       real_matchups=ROOT / variant['real_matchups'] if variant.get('real_matchups') else None)
        if variant.get('assign'):  # the version's assignment θ for mu_* (nodes.Chain, engine) — kept on the rebuilt report
            rep_path = ROOT / variant['out'] / 'features_report.json'
            rep = json.loads(rep_path.read_text())
            rep['assign'] = variant['assign']
            write_json(rep_path, rep, pretty=True)
    out = {'games': seg['games'], 'segments': seg['segments'], 'games_flagged': seg['games_flagged'], 'stints': rot['stints'],
           'player_games': feat['player_games'], 'real_matchups': real, 'seconds': round(time.time() - started, 1)}
    print(f"engine inputs rebuilt through {day_shift(day, -1)}: {out['games']} games · {out['segments']:,} segments · "
          f"{out['stints']:,} stints · {out['player_games']:,} player-games profiled · {out['seconds']}s", flush=True)
    return out


def fetch_nba_stats() -> dict:
    """D32: today's copy of the NBA Stats season logs and the matchups of finals not yet retained (polite; ~10 requests).
    A failure never stops the nightly: the engine then plays with the matchups already retained."""
    from scripts import fetch_nbastats
    try:
        r = fetch_nbastats.recent(fetch_nbastats.Client())
        m = r['matchups']
        print(f"NBA Stats: {r['logs']['requests']} season logs · {m['requests']} new matchup games ({m['skipped']} retained)", flush=True)
        return r
    except Exception as e:  # noqa: BLE001 — unofficial source; keep going with what is retained
        print(f'NBA Stats fetch failed ({type(e).__name__}: {e}); continuing with retained matchups', file=sys.stderr, flush=True)
        return {'error': f'{type(e).__name__}: {e}'}


def refresh_real_matchups() -> dict:
    """Crosswalk, matchups in ESPN ids and the per-game pair history from the retained NBA Stats files."""
    from scripts import nbastats, realmatch
    T, P = nbastats.nba_tables()
    E = nbastats.espn_tables()
    cw = nbastats.crosswalk(T, P, E)
    mt = nbastats.build_matchups()
    h = realmatch.build_history()
    realmatch._CACHE.clear()
    out = {'games_matched': cw['games']['matched'], 'player_match_rate': cw['players']['match_rate'], 'matchup_games': mt.get('games_kept'),
           'pair_rows': h['rows']}
    print(f"real matchups: {out['matchup_games']} games · players matched {out['player_match_rate']:.3%} · {out['pair_rows']:,} pair rows", flush=True)
    return out


def engine_days(day: str, slate_dates, ahead: int) -> list[str]:
    """D50: write today's snapshot even when no games are scheduled."""
    if ahead != 0:
        raise ValueError('possession forecasts are limited to today; --ahead must be 0')
    return [day]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--date', help='Slate date (ET), default today ET')
    parser.add_argument('--offline', action='store_true', help='Skip collection; use retained raw data')
    parser.add_argument('--views-only', action='store_true', help='Only rebuild presentation views')
    parser.add_argument('--backfill-days', type=int, default=0)
    parser.add_argument('--rebuild', action='store_true', help='Rebuild existing backfill snapshots too')
    parser.add_argument('--sims', type=int, default=projection.MODEL['sims'])
    parser.add_argument('--engine', type=int, default=10000, metavar='WORLDS',
                        help="worlds per game for today's slate from the possession engine (default 10,000, D36; D22: the default model)")
    parser.add_argument('--placeholder', action='store_true',
                        help='project today with the placeholder baseline-v1 instead of the engine (backfills always use it)')
    parser.add_argument('--archive-root', type=Path)
    parser.add_argument('--no-rebuild', action='store_true',
                        help="skip rebuilding the engine's inputs (segments, rotations, profiles) from today's finals")
    parser.add_argument('--ahead', type=int, default=0, metavar='DAYS',
                        help='must be 0: possession forecasts are limited to today (D50)')
    args = parser.parse_args()
    if args.ahead != 0:
        parser.error('possession forecasts are limited to today; --ahead must be 0')
    day = args.date or today_et()
    if args.views_only:
        views.build()
        return 0
    if day == today_et() and MASTER_CSV.exists():
        existing_slate = [g for g in master_fixtures.load() if g['date_et'] == day]
        retained_game_ids(SNAPSHOTS / day, existing_slate, True, utc_now())
    if not args.offline:
        report = collect(day)
        if report['failures']:
            print(f'{len(report["failures"])} collection failures (see run report); continuing with retained data',
                  file=sys.stderr)
        fetch_nba_stats()  # D32 (after ESPN: the crosswalk needs ESPN's finals)
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
    prospective = day == today_et()
    if prospective and not args.placeholder and not args.no_rebuild:
        rebuild_engine_inputs(day)
    days = engine_days(day, slate_dates, args.ahead)
    if day not in slate_dates:
        print(f'No games scheduled on {day}; building the team-pathway season without game simulations.', flush=True)
    retained = load_retained(SNAPSHOTS / day, [g for g in master if g['date_et'] == day], utc_now()) if prospective else {}
    if retained and args.placeholder:
        raise ValueError('cannot replace retained engine forecasts with placeholder forecasts')
    parts = [project_slate(d, teams, master, team_rows, player_rows, registry, prospective, args.sims, period_rows,
                           engine_worlds=0 if args.placeholder else args.engine, origin=day, retained=retained)
             for d in days]
    if parts:  # D25/D26: one season from today — universe k plays engine world k of every engine game, then the pathway
        T, lg = team_table(team_rows, day, teams)
        worlds = {gid: w for part in parts for gid, w in part['worlds'].items()}
        if any(part.get('live_dirs') and any('weights' in p for p in part['player_worlds'].values()) for part in parts):
            from scripts import a1_season_mixture, live_forecast
            pieces = {gid: live_forecast.pieces(part['live_dirs'][gid], w) if gid in part['live_dirs'] else [(w, __import__('fractions').Fraction(1))]
                      for part in parts for gid, w in part['worlds'].items()}
            coupled = a1_season_mixture.couple(pieces, projection.seed_for('live-season-mixture-v1', day))
            season = projection.simulate_season(T, lg, master, day, teams, coupled['games'], len(coupled['numerators']), weights=coupled['numerators'])
            for part in parts:
                part['season_worlds'], part['season_weights'] = coupled['games'], coupled['numerators']
                part['season_indices'] = coupled['indices']
        else:
            season = projection.simulate_season(T, lg, master, day, teams, worlds or None, args.sims)
        for part in parts:
            write_snapshot(part, season, args.archive_root)
    try:  # owner (20 Nov): projected v actual starters for every finished slate (scripts/lineups.py)
        from scripts import lineups
        acc = lineups.score().get('overall')
        if acc:
            print(f"projected starters so far: {acc['slot_accuracy']:.1%} of slots, all five {acc['all_five']:.1%} ({acc['team_games']} team-games)", flush=True)
    except Exception as exc:  # measurement only: never blocks the nightly
        print(f'lineup scoring skipped: {exc}', flush=True)
    views.build()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
