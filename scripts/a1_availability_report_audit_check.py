#!/usr/bin/env python3
"""Independently verify retained report origins, status counts and final-box coverage."""
from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import RAW, sha256_file, write_json  # noqa: E402
from scripts.evaluate import EXPERIMENTS, TEST_FROM  # noqa: E402


def read(path: Path) -> dict:
    if path.suffix == '.gz':
        with gzip.open(path, 'rt', encoding='utf-8') as stream:
            return json.load(stream)
    with path.open(encoding='utf-8') as stream:
        return json.load(stream)


def stamp(text: str) -> datetime:
    if len(text) == 16:
        return datetime.strptime(text, '%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc)
    result = datetime.fromisoformat(text.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('timestamp has no offset')
    return result.astimezone(timezone.utc)


def check_run(item: dict) -> tuple[dict, list[tuple[str, str, str, str]]]:
    run = RAW / 'runs' / item['run']
    if item.get('status') in ('missing_report', 'missing_origin_timestamp_or_slate'):
        return {'run': item['run'], 'status': item['status']}, []
    report = read(run / 'report.json')
    finished = stamp(report['finished'])
    if stamp(report['started']) > finished or report['run'] != run.name:
        raise ValueError(f'{run.name}: invalid collection times or identity')
    team_doc = read(run / 'teams.json.gz') if (run / 'teams.json.gz').exists() else None
    expected_teams = ({str(row['team']['id']) for row in team_doc['sports'][0]['leagues'][0]['teams']}
                      if team_doc is not None else None)
    rows, teams = [], set()
    for path in sorted((run / 'roster').glob('*.json.gz')):
        doc = read(path)
        team = str(doc['team']['id'])
        if team in teams:
            raise ValueError('duplicate roster team')
        teams.add(team)
        for player in doc['athletes']:
            injuries = player.get('injuries') or []
            rows.append((str(player['id']), team, (injuries[0].get('status') if injuries else 'Active')))
    counts = Counter(player for player, _, _ in rows)
    ambiguous = {player for player, count in counts.items() if count > 1}
    roster = {player: {'team': team, 'status': status} for player, team, status in rows}
    injuries_path = run / 'injuries.json.gz'
    injury_status, matching, injury_ids = Counter(), Counter(), Counter()
    if injuries_path.exists():
        doc = read(injuries_path)
        for group in doc.get('injuries', []):
            team = str(group.get('id', ''))
            for entry in group.get('injuries', []):
                injury_status[str(entry.get('status') or 'Unknown')] += 1
                links = (entry.get('athlete') or {}).get('links') or []
                matches = [re.search(r'/id/(\d+)/', link.get('href', '')) for link in links]
                player = next((match.group(1) for match in matches if match), None)
                if player:
                    injury_ids[player] += 1
                    if player in roster:
                        roster[player]['status'] = entry.get('status') or roster[player]['status']
                if player is None:
                    matching['missing_player_id'] += 1
                elif player in ambiguous:
                    matching['ambiguous_multiple_rosters'] += 1
                elif player not in roster:
                    matching['not_in_collected_rosters'] += 1
                elif roster[player]['team'] != team:
                    matching['different_roster_team'] += 1
                else:
                    matching['matched_roster_team'] += 1
        expected_injuries = {'statuses': dict(injury_status), 'matching': dict(matching),
                             'duplicate_player_ids': sum(n - 1 for n in injury_ids.values() if n > 1)}
    else:
        expected_injuries = None
    roster = {player: value for player, value in roster.items() if player not in ambiguous}
    statuses = Counter(str(value['status'] or 'Unknown') for value in roster.values())
    paths = run / f"scoreboard_{report['slate_date']}.json.gz"
    origins, snapshots, game_ids = Counter(), [], set()
    if paths.exists():
        for event in read(paths).get('events', []):
            gid = str(event['id'])
            if gid in game_ids:
                raise ValueError('duplicate scoreboard game')
            game_ids.add(gid)
            comp = event['competitions'][0]
            date = event.get('date')
            if not date or comp.get('timeValid') is not True:
                origins['unknown_tip'] += 1
                continue
            tip = stamp(date)
            day = tip.astimezone(ZoneInfo('America/New_York')).date().isoformat()
            if finished >= tip:
                origins['at_or_after_tip'] += 1
                continue
            if day != report['slate_date']:
                raise ValueError('scoreboard game is outside the ET slate')
            origins['pre_tip'] += 1
            sides = {str(side['team']['id']) for side in comp['competitors']}
            if len(sides) != 2:
                raise ValueError('game does not have two teams')
            final = RAW / 'final' / f'{gid}.json.gz'
            box = None
            if final.exists():
                summary = read(final)
                header = summary['header']['competitions'][0]
                if str(header['id']) != gid or not header['status']['type']['completed']:
                    raise ValueError('invalid final summary')
                box = set()
                for block in summary['boxscore']['players']:
                    team = str(block['team']['id'])
                    for player in block['statistics'][0].get('athletes', []):
                        key = (team, str(player['athlete']['id']))
                        if key in box:
                            raise ValueError('duplicate final box player')
                        box.add(key)
            for player, info in roster.items():
                team = info['team']
                if team in sides:
                    state = ('final_box_missing' if box is None else
                             'listed_in_final_box' if (team, player) in box else 'unlisted_in_final_box')
                    snapshots.append((gid, team, player, state))
    expected = {
        'slate_date': report['slate_date'],
        'period': 'protected_final_season' if report['slate_date'] >= TEST_FROM else 'development',
        'expected_teams': len(expected_teams) if expected_teams is not None else None,
        'roster_teams': len(teams),
        'missing_roster_team_ids': sorted(expected_teams - teams) if expected_teams is not None else None,
        'unexpected_roster_team_ids': sorted(teams - expected_teams) if expected_teams is not None else None,
        'duplicate_roster_player_ids': sum(n - 1 for n in counts.values() if n > 1),
        'ambiguous_roster_players_excluded': len(ambiguous), 'roster_players': len(roster),
        'effective_roster_statuses': dict(statuses), 'injury_report': expected_injuries,
        'scoreboard_present': paths.exists(), 'scoreboard_games': len(game_ids),
        'game_origins': dict(origins), 'pre_tip_roster_player_snapshots': len(snapshots),
        'pre_tip_final_box_coverage': dict(Counter(row[3] for row in snapshots)),
    }
    for key, value in expected.items():
        if item[key] != value:
            raise ValueError(f'{run.name}: independent {key} differs')
    return {'run': run.name, 'checked_fields': len(expected), 'pre_tip_snapshots': len(snapshots)}, snapshots


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, default=EXPERIMENTS / '20261122_a1_s07_report_coverage.json')
    parser.add_argument('--output', type=Path, default=EXPERIMENTS / '20261122_a1_s07_report_coverage_audit.json')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an existing report coverage check')
    report = read(args.report)
    for path, digest in report['input_sha256'].items():
        if sha256_file(ROOT / path) != digest:
            raise ValueError(f'coverage audit input changed: {path}')
    runs, all_snapshots = [], []
    for item in report['run_inventory']:
        checked, snapshots = check_run(item)
        runs.append(checked)
        all_snapshots.extend(snapshots)
    unique: dict[tuple[str, str, str], str] = {}
    for gid, team, player, coverage in all_snapshots:
        key = (gid, team, player)
        if key in unique and unique[key] != coverage:
            raise ValueError('inconsistent final-box coverage across snapshots')
        unique[key] = coverage
    aggregate = {
        'runs': len(runs),
        'pre_tip_games_with_roster_snapshots': len({row[0] for row in all_snapshots}),
        'pre_tip_roster_player_snapshots': len(all_snapshots),
        'unique_pre_tip_roster_player_games': len(unique),
        'unique_roster_player_game_final_box_coverage': dict(Counter(unique.values())),
    }
    for key, value in aggregate.items():
        if report[key] != value:
            raise ValueError(f'independent aggregate {key} differs')
    output = {'experiment': 'a1_s07_report_coverage_independent_check', 'aggregate': aggregate, 'runs': runs,
              'input_sha256': {str(path.relative_to(ROOT)): sha256_file(path)
                               for path in (Path(__file__), args.report)}}
    write_json(args.output, output, pretty=True)
    print(f"{aggregate['runs']} archives, {aggregate['pre_tip_roster_player_snapshots']} snapshots and "
          f"{aggregate['unique_pre_tip_roster_player_games']} unique player-games independently verified", flush=True)


if __name__ == '__main__':
    main()
