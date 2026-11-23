#!/usr/bin/env python3
"""Audit each saved game's availability against its own retained ESPN collection."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import RAW, day_shift, forecast_meta, parse_utc, read_json, sha256_file, slate_date, verified_pre_tip, write_json  # noqa: E402
from scripts.a1_snapshot_availability_audit import check_report  # noqa: E402


def origin_roster(run: Path) -> tuple[dict, list[Path]]:
    files = sorted((run / 'roster').glob('*.json.gz'))
    if not files:
        raise ValueError(f'{run.name}: no retained rosters')
    injury_path = run / 'injuries.json.gz'
    has_report = injury_path.is_file()
    roster, ambiguous, teams = {}, set(), set()
    for path in files:
        document = read_json(path)
        if document['team']['id'] is None:
            raise ValueError(f'{run.name}: roster team ID is missing')
        team = str(document['team']['id'])
        if team in teams:
            raise ValueError(f'{run.name}: duplicate team roster')
        teams.add(team)
        for player in document['athletes']:
            if player['id'] is None:
                raise ValueError(f'{run.name}: roster player ID is missing')
            pid = str(player['id'])
            if pid in ambiguous:
                continue
            if pid in roster:
                if roster[pid]['team'] == team:
                    raise ValueError(f'{run.name}: duplicate player on one roster')
                roster.pop(pid)
                ambiguous.add(pid)
                continue
            injuries = player.get('injuries') or []
            reported = ((injuries[0].get('status') or '').strip() or None) if injuries else None
            roster[pid] = {'team': team, 'name': player.get('displayName', ''),
                           'status': reported or ('Unknown' if injuries or not has_report else 'Active'),
                           'reported_status': reported,
                           'status_source': ('roster_injury' if injuries else
                                             'not_listed_assumption' if has_report else 'missing_report'),
                           'injury': None}
    if has_report:
        document = read_json(injury_path)
        if not isinstance(document.get('injuries'), list):
            raise ValueError(f'{run.name}: missing injury-report team list')
        matched, conflicts = set(), set()
        for group in document['injuries']:
            if not isinstance(group.get('injuries'), list):
                raise ValueError(f'{run.name}: missing team injury list')
            for entry in group['injuries']:
                links = (entry.get('athlete') or {}).get('links') or []
                match = next((found for link in links if (found := re.search(r'/id/(\d+)/', link.get('href', '')))), None)
                if match is None:
                    raise ValueError(f'{run.name}: injury entry lacks player ID')
                pid = match.group(1)
                if pid not in roster:
                    continue
                if str(group.get('id', '')) != roster[pid]['team']:
                    conflicts.add(pid)
                    continue
                if pid in matched:
                    raise ValueError(f'{run.name}: duplicate injury status')
                matched.add(pid)
                detail = entry.get('details') or {}
                reported = (entry.get('status') or '').strip() or None
                roster[pid].update({'status': reported or 'Unknown', 'reported_status': reported,
                                    'status_source': 'injury_report',
                                    'injury': {'status': entry.get('status'), 'date': entry.get('date'),
                                               'comment': entry.get('shortComment') or '', 'type': detail.get('type'),
                                               'detail': detail.get('detail'), 'return': detail.get('returnDate')}})
        for pid in conflicts - matched:
            roster[pid].update({'status': 'Unknown', 'reported_status': None, 'status_source': 'team_conflict',
                                'injury': None})
    return roster, [*files, *([injury_path] if has_report else [])]


def origin_events(run: Path) -> tuple[dict, list[Path]]:
    files = sorted((run / 'schedule').glob('*.json.gz'))
    if not files:
        raise ValueError(f'{run.name}: no retained schedules')
    events = {}
    for path in files:
        for event in read_json(path).get('events', []):
            events[str(event['id'])] = event
    return events, files


def audit(snapshot: Path, runs: Path) -> tuple[dict, list[Path]]:
    meta = read_json(snapshot / 'meta.json')
    games = read_json(snapshot / 'games.json')
    if len(meta['games']) != len(games) or set(games) != set(map(str, meta['games'])):
        raise ValueError('snapshot games and metadata disagree')
    cache, paths = {}, [snapshot / 'meta.json', snapshot / 'games.json']
    entries = pre_tip = 0
    for gid, game in games.items():
        source = forecast_meta(meta, gid)
        if (source.get('kind') != 'prospective' or source.get('slate_date') != snapshot.name
                or not isinstance(source.get('origin'), str)
                or source.get('origin') != meta.get('origin') or source.get('model') != meta.get('model')
                or source.get('origin') > snapshot.name or source.get('cutoff') != day_shift(source['origin'], -1)
                or source.get('generated') != source.get('completed_at') or game.get('game_id') != gid
                or source.get('sims') != game.get('sims') or source['model']['id'] != game.get('model')):
            raise ValueError(f'{gid}: source metadata differs from the saved game')
        run_id = source['inputs']['registry_run']
        if not isinstance(run_id, str) or not re.fullmatch(r'\d{8}T\d{6}Z', run_id):
            raise ValueError(f'{gid}: invalid collection ID')
        if run_id not in cache:
            run = runs / run_id
            report_path = run / 'report.json'
            report = read_json(report_path)
            if report.get('run') != run_id or report.get('slate_date') != snapshot.name:
                raise ValueError(f'{gid}: collection identity differs')
            roster, roster_paths = origin_roster(run)
            events, event_paths = origin_events(run)
            cache[run_id] = (report, roster, events)
            paths.extend([report_path, *roster_paths, *event_paths])
        report, roster, events = cache[run_id]
        if (parse_utc(report['started']) > parse_utc(report['finished'])
                or parse_utc(report['finished']) > parse_utc(source['started_at'])
                or parse_utc(source['started_at']) > parse_utc(source['completed_at'])):
            raise ValueError(f'{gid}: collection does not precede forecast start')
        event = events[gid]
        competition = event['competitions'][0]
        competitors = competition['competitors']
        sides = {side['homeAway']: str(side['team']['id']) for side in competitors}
        if (len(competitors) != 2 or set(sides) != {'home', 'away'} or slate_date(event['date']) != snapshot.name
                or any(str(game[side]['team_id']) != sides[side] for side in sides)):
            raise ValueError(f'{gid}: original fixture differs')
        status = (competition.get('status') or event.get('status') or {}).get('type') or {}
        if status.get('name') not in ('STATUS_SCHEDULED', 'STATUS_IN_PROGRESS', 'STATUS_HALFTIME',
                                      'STATUS_END_PERIOD', 'STATUS_FINAL'):
            raise ValueError(f'{gid}: source game status cannot establish pre-tip timing')
        expected_tip = (None if competition.get('timeValid') is not True else
                        status.get('name') not in ('STATUS_IN_PROGRESS', 'STATUS_HALFTIME', 'STATUS_END_PERIOD', 'STATUS_FINAL')
                        and parse_utc(source['completed_at']) < parse_utc(event['date']))
        if verified_pre_tip(source, gid) is not expected_tip:
            raise ValueError(f'{gid}: original pre-tip label differs from source timing')
        pre_tip += expected_tip is True
        for side in ('home', 'away'):
            expected = {pid: row for pid, row in roster.items() if row['team'] == sides[side]}
            entries += check_report(gid, side, game['availability_report'][side], expected)
    return {'games': len(games), 'report_entries': entries, 'pre_tip_games': pre_tip,
            'origin_collections': len(cache),
            'limitations': ['Collection and staged completion are not independent proof of publication.',
                            'Roster and injury data are source reports, not confirmed health or predictive validation.']}, paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f'{args.output}: refusing to overwrite the audit report')
    result, paths = audit(args.snapshot, RAW / 'runs')
    result['input_sha256'] = {
        ('snapshot/' + str(path.relative_to(args.snapshot)) if path.is_relative_to(args.snapshot)
         else str(path.relative_to(ROOT))): sha256_file(path)
        for path in [*paths, Path(__file__).resolve()]
    }
    write_json(args.output, result, pretty=True)
    print(f"{result['games']} games, {result['report_entries']} report entries from "
          f"{result['origin_collections']} origin collections; {result['pre_tip_games']} marked pre-tip")


if __name__ == '__main__':
    main()
