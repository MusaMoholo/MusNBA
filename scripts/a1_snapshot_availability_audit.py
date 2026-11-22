#!/usr/bin/env python3
"""Independently check saved prospective availability reports and game/season accounting."""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, MASTER_CSV, SNAPSHOTS, VIEWS, day_shift, parse_utc, read_json, sha256_file, write_json  # noqa: E402
from scripts import master_fixtures, projection  # noqa: E402


def check_report(gid: str, side: str, report: list[dict], roster: dict) -> int:
    ids = [str(row['id']) for row in report]
    if len(ids) != len(set(ids)) or set(ids) != set(roster):
        raise ValueError(f'{gid} {side}: saved report does not match the origin roster')
    for row in report:
        pid = str(row['id'])
        source = roster[pid]
        status = (source.get('status') or '').strip() or 'Unknown'
        expected = {
            'name': source.get('name'), 'status': status, 'reported_status': source.get('reported_status'),
            'status_source': source.get('status_source'), 'injury': source.get('injury'),
            'availability': projection.AVAILABILITY.get(status.lower(), 0.6),
        }
        for field, value in expected.items():
            if field not in row or row[field] != value:
                raise ValueError(f'{gid} {side} {pid}: saved {field} differs from the origin registry')
    return len(ids)


def check_worlds(gid: str, periods: np.ndarray, lines: np.ndarray, side: np.ndarray) -> int:
    if (periods.ndim != 3 or periods.shape[1] != 2 or periods.shape[2] < 4
            or lines.ndim != 3 or lines.shape[0] != periods.shape[0] or lines.shape[2] < 2
            or side.ndim != 1 or side.size != lines.shape[1] or not np.isin(side, (0, 1)).all()):
        raise ValueError(f'{gid}: invalid game-world shape or player side')
    for team in (0, 1):
        if not (side == team).any():
            raise ValueError(f'{gid}: team has no saved players')
        player_points = lines[:, side == team, 1].astype(np.int64).sum(axis=1)
        team_points = periods[:, team, :].astype(np.int64).sum(axis=1)
        if not np.array_equal(player_points, team_points):
            raise ValueError(f'{gid}: saved player and team points differ')
    return periods.shape[0] * 2


def audit_day(day: str, registry_doc: dict, fixtures: dict, expected_model: str, expected_sims: int,
              expected_origin: str) -> tuple[dict, list[Path]]:
    path = SNAPSHOTS / day
    meta = read_json(path / 'meta.json')
    games = read_json(path / 'games.json')
    season = read_json(path / 'season.json')
    stats = read_json(path / 'stats.json')
    if (meta['slate_date'] != day or meta.get('origin') != expected_origin or expected_origin > day
            or meta['cutoff'] != day_shift(expected_origin, -1) or season['as_of'] != expected_origin
            or not meta.get('completed_at') or meta['generated'] != meta['completed_at']
            or parse_utc(meta['started_at']) > parse_utc(meta['completed_at'])
            or meta['kind'] != 'prospective'
            or meta['model']['id'] != expected_model or meta['sims'] != expected_sims
            or meta['season_sims'] != expected_sims or season['sims'] != expected_sims):
        raise ValueError(f'{day}: snapshot origin, model or simulation count differs')
    if meta['inputs']['registry_run'] != registry_doc['run']:
        raise ValueError(f'{day}: current registry is not the snapshot origin registry')
    if meta['inputs']['master_sha256'] != sha256_file(MASTER_CSV):
        raise ValueError(f'{day}: current fixtures are not the snapshot input')
    expected_games = {gid for gid, fixture in fixtures.items()
                      if fixture['status'] == 'final' and fixture['date_et'] < expected_origin}
    team_games = [game for team in stats['teams'].values() for game in team['games']]
    if (any(game['date'] >= expected_origin for game in team_games)
            or Counter(str(game['game_id']) for game in team_games) != {gid: 2 for gid in expected_games}
            or stats['league']['games'] != len(expected_games)
            or meta['inputs']['completed_games_used'] != len(expected_games)):
        raise ValueError(f'{day}: saved team inputs do not match pre-origin finals')
    if any(game['date'] >= expected_origin or str(game['game_id']) not in expected_games
           for player in stats['players'].values() for game in player['log']):
        raise ValueError(f'{day}: saved player inputs include a non-pre-origin game')
    game_ids = list(map(str, meta['games']))
    if len(game_ids) != len(set(game_ids)) or set(game_ids) != set(games):
        raise ValueError(f'{day}: saved game IDs differ from snapshot metadata')
    season_games = {str(row['game_id']): row for row in season['games']}
    if len(season_games) != len(season['games']):
        raise ValueError(f'{day}: duplicate season game ID')
    totals = {'games': len(game_ids), 'report_entries': 0, 'reported_status_missing': 0,
              'ruled_out_entries': 0, 'view_entries': 0, 'player_team_point_checks': 0,
              'season_game_checks': 0}
    paths = [path / name for name in ('meta.json', 'games.json', 'season.json', 'stats.json',
                                      'engine_worlds.npz', 'engine_players.npz')]
    with np.load(path / 'engine_worlds.npz', allow_pickle=False) as worlds, \
            np.load(path / 'engine_players.npz', allow_pickle=False) as players:
        for gid in game_ids:
            fixture = fixtures[gid]
            pre_tip = parse_utc(meta['completed_at']) < parse_utc(fixture['tip_utc'])
            if meta['pre_tip'].get(gid) is not pre_tip:
                raise ValueError(f'{gid}: pre-tip label does not match snapshot completion')
            sim = games[gid]
            report = sim['availability_report']
            view_path = VIEWS / 'api/game' / f'{gid}.json'
            view = read_json(view_path)
            paths.append(view_path)
            if (view['projection']['snapshot'] != day or view['projection']['origin'] != expected_origin
                    or view['projection']['completed_at'] != meta['completed_at']
                    or view['projection']['pre_tip'] is not pre_tip or view['availability']['source'] != 'snapshot'
                    or view['projection']['model']['id'] != expected_model):
                raise ValueError(f'{gid}: saved view does not identify this snapshot and report')
            ids = [str(value) for value in players[f'{gid}__ids']]
            side = players[f'{gid}__side']
            lines, periods = players[f'{gid}__lines'], worlds[gid]
            if len(ids) != len(set(ids)) or periods.shape[0] != expected_sims:
                raise ValueError(f'{gid}: duplicated players or incorrect number of game worlds')
            totals['player_team_point_checks'] += check_worlds(gid, periods, lines, side)
            for team_index, name in enumerate(('home', 'away')):
                roster = {str(pid): row for pid, row in registry_doc['players'].items()
                          if row.get('on_roster') and str(row.get('team')) == str(fixture[f'{name}_id'])}
                entries = report[name]
                totals['report_entries'] += check_report(gid, name, entries, roster)
                totals['reported_status_missing'] += sum(row['reported_status'] is None for row in entries)
                excluded = {str(row['id']) for row in entries if row['availability'] == 0}
                totals['ruled_out_entries'] += len(excluded)
                on_side = {ids[i] for i in np.flatnonzero(side == team_index)}
                simulated = {str(row['id']): row for row in sim[name]['players']}
                if excluded & (on_side | set(simulated)):
                    raise ValueError(f'{gid} {name}: a ruled-out player was simulated')
                if sum(bool(row['starter']) for row in simulated.values()) != 5:
                    raise ValueError(f'{gid} {name}: projected starters do not contain five players')
                expected_view = {}
                for entry in entries:
                    pid = str(entry['id'])
                    player = simulated.get(pid)
                    assumed = player.get('availability') if player else entry['availability']
                    if entry['status'].lower() == 'active' and (assumed is None or assumed >= 1):
                        continue
                    expected_view[pid] = entry
                visible = {str(row['id']): row for row in view['availability'][name]}
                if set(visible) != set(expected_view):
                    raise ValueError(f'{gid} {name}: visible report entries differ from the saved forecast')
                for pid, row in visible.items():
                    if (row['status'] != expected_view[pid]['status']
                            or row.get('status_source') != expected_view[pid]['status_source']):
                        raise ValueError(f'{gid} {name} {pid}: visible status provenance differs')
                totals['view_entries'] += len(visible)
            if gid not in season_games or season_games[gid]['source'] != 'engine':
                raise ValueError(f'{gid}: season is not using the saved game worlds')
            pts = periods.astype(np.int64).sum(axis=2)
            expected = {'p_home': round(float((pts[:, 0] > pts[:, 1]).mean()), 4),
                        'mu_home': round(float(pts[:, 0].mean()), 2),
                        'mu_away': round(float(pts[:, 1].mean()), 2)}
            if any(season_games[gid][key] != value for key, value in expected.items()):
                raise ValueError(f'{gid}: season game probabilities or means differ from the saved worlds')
            totals['season_game_checks'] += 1
    return {'day': day, 'origin': expected_origin, 'cutoff': meta['cutoff'], 'pre_origin_games': len(expected_games),
            'registry_run': registry_doc['run'], 'model': expected_model, 'sims': expected_sims, **totals}, paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--days', nargs='+', required=True)
    parser.add_argument('--origin', required=True)
    parser.add_argument('--expected-model', required=True)
    parser.add_argument('--expected-sims', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.expected_sims < 1:
        raise ValueError('output must be new and expected-sims must be positive')
    registry_path = DERIVED / 'players.json'
    registry = read_json(registry_path)
    rows = master_fixtures.load()
    fixtures = {str(row['game_id']): row for row in rows}
    if len(fixtures) != len(rows):
        raise ValueError('fixture IDs are not unique')
    checked, inputs = [], [registry_path, MASTER_CSV, Path(__file__)]
    for day in args.days:
        result, paths = audit_day(day, registry, fixtures, args.expected_model, args.expected_sims, args.origin)
        checked.append(result)
        inputs.extend(paths)
    report = {'experiment': 'a1_s07_live_snapshot_availability_accounting', 'days': checked,
              'input_sha256': {str(path.relative_to(ROOT)): sha256_file(path) for path in inputs}}
    write_json(args.output, report, pretty=True)
    print(f"audited {sum(row['games'] for row in checked)} games, "
          f"{sum(row['report_entries'] for row in checked)} origin-report entries and "
          f"{sum(row['player_team_point_checks'] for row in checked):,} player/team world totals")


if __name__ == '__main__':
    main()
