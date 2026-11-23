#!/usr/bin/env python3
"""Inventory retained pre-tip ESPN reports without scoring protected-season outcomes."""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import RAW, read_json, sha256_file, slate_date, write_json  # noqa: E402
from scripts import box_scores  # noqa: E402
from scripts.evaluate import EXPERIMENTS, TEST_FROM  # noqa: E402


def utc(value: str) -> datetime:
    if not value:
        raise ValueError('missing timestamp')
    if len(value) == 16 and value.endswith('Z') and 'T' in value:
        return datetime.strptime(value, '%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc)
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError(f'timestamp lacks a UTC offset: {value}')
    return parsed.astimezone(timezone.utc)


def game_origin(event: dict, finished: datetime) -> tuple[str, str | None]:
    competition = event['competitions'][0]
    stamp = event.get('date')
    if not stamp or competition.get('timeValid') is not True:
        return 'unknown_tip', None
    tip = utc(str(stamp))
    day = slate_date(str(stamp))
    return ('pre_tip' if finished < tip else 'at_or_after_tip'), day


def report_entries(doc: dict, roster: dict, ambiguous: set[str] | None = None) -> dict:
    statuses, reasons, seen = Counter(), Counter(), Counter()
    ambiguous = ambiguous or set()
    for team in doc.get('injuries', []):
        team_id = str(team.get('id', ''))
        for item in team.get('injuries', []):
            statuses[str(item.get('status') or 'Unknown')] += 1
            links = (item.get('athlete') or {}).get('links') or []
            player = next((match.group(1) for link in links
                           if (match := box_scores.INJURY_ID.search(link.get('href', '')))), None)
            if player is None:
                reasons['missing_player_id'] += 1
            elif player in ambiguous:
                reasons['ambiguous_multiple_rosters'] += 1
            elif player not in roster:
                reasons['not_in_collected_rosters'] += 1
            elif str(roster[player].get('team')) != team_id:
                reasons['different_roster_team'] += 1
            else:
                reasons['matched_roster_team'] += 1
            if player:
                seen[player] += 1
    return {'statuses': dict(statuses), 'matching': dict(reasons),
            'duplicate_player_ids': int(sum(count - 1 for count in seen.values() if count > 1))}


def box_player_keys(summary: dict, gid: str) -> set[tuple[str, str]]:
    competition = summary['header']['competitions'][0]
    status = (competition.get('status') or {}).get('type') or {}
    if str(competition['id']) != gid or not status.get('completed'):
        raise ValueError(f'{gid}: retained summary is not the expected final game')
    keys = []
    for block in summary['boxscore']['players']:
        team = str(block['team']['id'])
        for athlete in block['statistics'][0].get('athletes', []):
            keys.append((team, str(athlete['athlete']['id'])))
    if len(keys) != len(set(keys)):
        raise ValueError(f'{gid}: final box repeats a team/player key')
    return set(keys)


def box_presence(box: set[tuple[str, str]] | None, team: str, player: str) -> str:
    if box is None:
        return 'final_box_missing'
    return 'listed_in_final_box' if (team, player) in box else 'unlisted_in_final_box'


def inventory(run: Path, final_dir: Path) -> tuple[dict, list[Path], list[tuple[str, str, str, str]]]:
    report_path = run / 'report.json'
    if not report_path.exists():
        return {'run': run.name, 'status': 'missing_report'}, [], []
    report = read_json(report_path)
    if not report.get('started') or not report.get('finished') or not report.get('slate_date'):
        return {'run': run.name, 'status': 'missing_origin_timestamp_or_slate'}, [report_path], []
    if report.get('run') != run.name or report.get('started') != run.name:
        raise ValueError(f'{run.name}: collection start does not match the retained directory')
    started, finished = utc(str(report['started'])), utc(str(report['finished']))
    if finished < started:
        raise ValueError(f'{run.name}: collection finished before it started')
    day = str(report['slate_date'])
    paths = [report_path]
    teams_path = run / 'teams.json.gz'
    if teams_path.exists():
        teams_doc = read_json(teams_path)
        expected_teams = {str(item['team']['id'])
                          for item in teams_doc['sports'][0]['leagues'][0]['teams']}
        paths.append(teams_path)
    else:
        expected_teams = None
    roster_files = sorted((run / 'roster').glob('*.json.gz'))
    roster_teams, roster_ids = set(), []
    for path in roster_files:
        document = read_json(path)
        team = str(document['team']['id'])
        if team in roster_teams:
            raise ValueError(f'{run.name}: duplicate team roster')
        roster_teams.add(team)
        roster_ids.extend(str(player['id']) for player in document.get('athletes', []))
    id_counts = Counter(roster_ids)
    ambiguous = {player for player, count in id_counts.items() if count > 1}
    duplicates = sum(count - 1 for count in id_counts.values() if count > 1)
    registry = box_scores.roster_registry(run)
    roster = {player: record for player, record in registry.items() if player not in ambiguous}
    status_counts = Counter(str(item.get('status') or 'Unknown') for item in roster.values())
    paths.extend(roster_files)
    injuries_path = run / 'injuries.json.gz'
    if injuries_path.exists():
        injury_doc = read_json(injuries_path)
        injuries = report_entries(injury_doc, roster, ambiguous)
        paths.append(injuries_path)
    else:
        injuries = None
    scoreboard_path = run / f'scoreboard_{day}.json.gz'
    origins, snapshots, unique_games = Counter(), [], set()
    if scoreboard_path.exists():
        scoreboard = read_json(scoreboard_path)
        paths.append(scoreboard_path)
        for event in scoreboard.get('events', []):
            gid = str(event['id'])
            if gid in unique_games:
                raise ValueError(f'{run.name}: duplicate scoreboard game')
            unique_games.add(gid)
            origin, game_day = game_origin(event, finished)
            origins[origin] += 1
            if origin != 'pre_tip':
                continue
            if game_day != day:
                raise ValueError(f'{run.name}: scoreboard slate and game ET date differ')
            competition = event['competitions'][0]
            team_ids = {str(side['team']['id']) for side in competition['competitors']}
            if len(team_ids) != 2:
                raise ValueError(f'{gid}: scoreboard does not contain two distinct teams')
            final_path = final_dir / f'{gid}.json.gz'
            box = box_player_keys(read_json(final_path), gid) if final_path.exists() else None
            if box is not None:
                paths.append(final_path)
            for player, record in roster.items():
                team = str(record.get('team'))
                if team in team_ids:
                    snapshots.append((gid, team, str(player), box_presence(box, team, str(player))))
    summary = {
        'run': run.name, 'slate_date': day, 'started_utc': started.isoformat(), 'finished_utc': finished.isoformat(),
        'period': 'protected_final_season' if day >= TEST_FROM else 'development',
        'collection_failures': report.get('failures', []),
        'expected_teams': len(expected_teams) if expected_teams is not None else None, 'roster_teams': len(roster_teams),
        'missing_roster_team_ids': sorted(expected_teams - roster_teams) if expected_teams is not None else None,
        'unexpected_roster_team_ids': sorted(roster_teams - expected_teams) if expected_teams is not None else None,
        'duplicate_roster_player_ids': duplicates, 'roster_players': len(roster),
        'ambiguous_roster_players_excluded': len(ambiguous),
        'effective_roster_statuses': dict(status_counts), 'injury_report': injuries,
        'scoreboard_present': scoreboard_path.exists(), 'scoreboard_games': len(unique_games),
        'game_origins': dict(origins), 'pre_tip_roster_player_snapshots': len(snapshots),
        'pre_tip_final_box_coverage': dict(Counter(row[3] for row in snapshots)),
    }
    return summary, paths, snapshots


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=EXPERIMENTS / '20261122_a1_s07_report_coverage.json')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an existing report coverage audit')
    root = RAW / 'runs'
    runs = sorted(path for path in root.iterdir() if path.is_dir()) if root.exists() else []
    results, paths, snapshot_keys = [], [Path(__file__), ROOT / 'scripts/box_scores.py'], []
    for index, run in enumerate(runs, 1):
        result, inputs, snapshots = inventory(run, RAW / 'final')
        results.append(result)
        paths.extend(inputs)
        snapshot_keys.extend(snapshots)
        print(f'report archives {index}/{len(runs)}: {run.name}', flush=True)
    counts = Counter(result.get('period', 'missing_report') for result in results)
    pre_tip_games = {row[0] for row in snapshot_keys}
    player_coverage: dict[tuple[str, str, str], str] = {}
    for gid, team, player, coverage in snapshot_keys:
        key = (gid, team, player)
        if key in player_coverage and player_coverage[key] != coverage:
            raise ValueError(f'{gid}: inconsistent retained final-box coverage across snapshots')
        player_coverage[key] = coverage
    paths = list(dict.fromkeys(paths))
    output = {
        'experiment': 'a1_s07_timestamped_report_coverage', 'runs': len(runs), 'periods': dict(counts),
        'pre_tip_games_with_roster_snapshots': len(pre_tip_games),
        'pre_tip_roster_player_snapshots': len(snapshot_keys),
        'unique_pre_tip_roster_player_games': len(player_coverage),
        'unique_roster_player_game_final_box_coverage': dict(Counter(player_coverage.values())),
        'run_inventory': results,
        'method': 'Use the collection finished timestamp as a conservative capture upper bound and only accept '
                  'strictly pre-tip snapshots. Final boxes are inspected for rostered-player presence only, '
                  'without comparing status to play/start outcomes.',
        'limitations': 'Active with no injury entry is not confirmed healthy; roster and box absence are unknown, '
                       'not DNPs. Protected-season outcomes are not scored or used for model selection. '
                       'Archived runs do not establish official historical report publication times.',
        'input_sha256': {str(path.resolve().relative_to(ROOT)): sha256_file(path) for path in paths},
    }
    write_json(args.output, output, pretty=True)
    print(f"{len(runs)} runs; {len(pre_tip_games)} pre-tip games; {len(player_coverage)} unique roster/player-games",
          flush=True)


if __name__ == '__main__':
    main()
