#!/usr/bin/env python3
"""Reconstruct ordered historical substitution windows without using later scores."""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import atomic_bytes, sha256_file, write_json  # noqa: E402
from scripts import history, pbp, rotations  # noqa: E402
from scripts.evaluate import TEST_FROM  # noqa: E402


class InvalidGame(ValueError):
    """The retained events cannot support a reliable sequential replay."""


def windows_for_game(game: dict) -> tuple[list[dict], dict]:
    """Return observed stoppages and ordered substitutions, conditional on the game's participants."""
    ordered = []
    for event in game['plays']:
        if event['seq'] <= 0 or event['period'] < 1:
            raise InvalidGame('missing sequence number or invalid period')
        try:
            clock = pbp.clock_seconds(event['clock'])
        except (TypeError, ValueError) as error:
            raise InvalidGame('invalid event clock') from error
        if not math.isfinite(clock) or not 0 <= clock <= pbp.period_length(event['period']):
            raise InvalidGame('event clock outside its period')
        ordered.append((event['period'], -clock, event['seq'], event))
    keys = [item[:3] for item in ordered]
    if not ordered or len(keys) != len(set(keys)):
        raise InvalidGame('missing events or duplicate sequence numbers at the same clock')
    events = [item[3] for item in sorted(ordered, key=lambda item: item[:3])]
    team_of, starters, box, teams, by_minutes = pbp.game_context(game)
    home, away = game['home'], game['away']
    if len(teams) != 2 or set(teams) != {home, away}:
        raise InvalidGame('roster does not contain exactly the home and away teams')
    participants = {team: sorted(player for player, tid in team_of.items()
                                 if tid == team and player in box) for team in teams}
    if any(len(participants[team]) < 5 for team in teams):
        raise InvalidGame('fewer than five observed participants')
    score = {home: 0, away: 0}
    fouls = Counter()
    seconds = {player: 0.0 for players in participants.values() for player in players}
    on_since: dict[str, float] = {}
    off_since = {player: 0.0 for player in seconds}
    lineup = {team: set() for team in teams}
    closing = {team: list(starters[team]) for team in teams}
    now = 0.0
    result: list[dict] = []
    pending = None
    period_issues = Counter()
    scoreboard_checks = 0

    def advance(target: float) -> None:
        nonlocal now
        if target < now:
            raise InvalidGame('game clock moves backwards in sequence order')
        elapsed = target - now
        for team in teams:
            for player in lineup[team]:
                seconds[player] += elapsed
        now = target

    def verify_score(event: dict) -> None:
        nonlocal scoreboard_checks
        for label, team in (('home', home), ('away', away)):
            reported = event[f'{label}_score']
            if reported is not None and not pd.isna(reported):
                scoreboard_checks += 1
                if float(reported) != score[team]:
                    raise InvalidGame('running points disagree with the reported scoreboard')

    def snapshot(period: int, clock: float, seq: int, kind: str) -> dict:
        record = {'game_id': str(game['id']), 'date_et': game['date_et'], 'season': game['season'],
                  'season_type': game['season_type'], 'period': period, 'clock': clock, 't': now,
                  'trigger_seq': seq, 'kind': kind, 'home': home, 'away': away,
                  'home_score': score[home], 'away_score': score[away], 'margin_home': score[home] - score[away],
                  'changes': [], 'touched': set()}
        for label, team in (('home', home), ('away', away)):
            players = participants[team]
            record[f'{label}_players'] = list(players)
            record[f'{label}_five_before'] = sorted(lineup[team])
            record[f'{label}_seconds_before'] = [seconds[player] for player in players]
            record[f'{label}_fouls_before'] = [fouls[player] for player in players]
            record[f'{label}_stint_before'] = [now - on_since[player] if player in lineup[team] else None
                                               for player in players]
            record[f'{label}_rest_before'] = [now - off_since[player] if player not in lineup[team] else None
                                              for player in players]
        return record

    def flush() -> None:
        nonlocal pending
        if pending is None:
            return
        for label, team in (('home', home), ('away', away)):
            pending[f'{label}_five_after'] = sorted(lineup[team])
            pending[f'{label}_subs'] = sum(change['team'] == team for change in pending['changes'])
        pending['changes_json'] = json.dumps(pending.pop('changes'), separators=(',', ':'))
        pending.pop('touched')
        pending['window_id'] = f"{game['id']}:{len(result)}"
        result.append(pending)
        pending = None

    previous_period = 0
    for period in sorted({event['period'] for event in events}):
        if period != previous_period + 1:
            raise InvalidGame('periods are missing or out of sequence')
        part = [event for event in events if event['period'] == period]
        start = float(rotations.period_base(period))
        advance(start)
        issues = Counter()
        inferred = pbp.period_starters(part, period, teams, team_of, starters, closing, by_minutes, issues)
        period_issues.update(issues)
        if issues['period_lineup_filled'] or issues['period_lineup_over_five']:
            raise InvalidGame('period starters require a filled or over-five lineup')
        for team in teams:
            new = set(inferred[team])
            if len(new) != 5 or not new.issubset(participants[team]):
                raise InvalidGame('period starters are not five observed teammates')
            for player in lineup[team] - new:
                off_since[player] = now
                on_since.pop(player)
            for player in new - lineup[team]:
                on_since[player] = now
                off_since.pop(player, None)
            lineup[team] = new
        for event in part:
            clock = pbp.clock_seconds(event['clock'])
            advance(rotations.game_time(period, clock))
            if event['type_id'] == pbp.SUB:
                if event['scoring'] or event['score_value'] != 0:
                    raise InvalidGame('substitution carries scoring points')
                verify_score(event)
                if len(event['participants']) < 2:
                    raise InvalidGame('substitution has fewer than two participants')
                enter, leave = event['participants'][:2]
                team = team_of.get(enter)
                if team not in teams or team_of.get(leave) != team:
                    raise InvalidGame('substitution players lack a common team')
                if leave not in lineup[team] or enter in lineup[team] or enter not in participants[team]:
                    raise InvalidGame('substitution does not replace an on-court player with an eligible participant')
                if pending is None or pending['clock'] != clock:
                    flush()
                    pending = snapshot(period, clock, event['seq'], 'observed_sub_only')
                if enter in pending['touched'] or leave in pending['touched']:
                    flush()
                    pending = snapshot(period, clock, event['seq'], 'sequential_sub_only')
                pending['changes'].append({'seq': event['seq'], 'team': team, 'player_in': enter,
                                           'player_out': leave})
                pending['touched'].update((enter, leave))
                lineup[team].remove(leave)
                lineup[team].add(enter)
                off_since[leave] = now
                on_since.pop(leave)
                on_since[enter] = now
                off_since.pop(enter, None)
                continue
            flush()
            parts = event['participants']
            if pbp.is_personal_foul(event):
                if not parts or parts[0] not in team_of:
                    raise InvalidGame('personal foul has no identified player')
                fouls[parts[0]] += 1
            if event['scoring']:
                if event['team'] not in teams or event['score_value'] <= 0:
                    raise InvalidGame('scoring event has no valid team or points')
                score[event['team']] += event['score_value']
            elif event['score_value'] != 0:
                raise InvalidGame('non-scoring event carries points')
            verify_score(event)
            kind = rotations.window_kind(event)
            if kind:
                pending = snapshot(period, clock, event['seq'], kind)
        flush()
        advance(float(rotations.period_base(period) + pbp.period_length(period)))
        closing = {team: sorted(lineup[team]) for team in teams}
        previous_period = period
    mismatched_minutes = []
    for player, actual in box.items():
        if player not in seconds:
            continue
        recorded = actual.get('min')
        if recorded is not None and abs(seconds[player] / 60 - recorded) > 1.01:
            mismatched_minutes.append(player)
    if mismatched_minutes:
        raise InvalidGame('replayed player minutes disagree with the box score')
    if not scoreboard_checks:
        raise InvalidGame('no recorded scoreboards to reconcile')
    return result, {'events': len(events), 'windows': len(result), 'scoreboard_checks': scoreboard_checks,
                    'periods': previous_period, 'substitutions': sum(row['home_subs'] + row['away_subs'] for row in result),
                    'period_issues': dict(period_issues)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--season', type=int, required=True)
    parser.add_argument('--game-ids', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--rows-output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.rows_output.exists():
        raise FileExistsError('refusing to overwrite an existing sequence replay')
    requested = json.loads(args.game_ids.read_text())
    if not isinstance(requested, list) or not requested or any(not isinstance(gid, str) or not gid.isdigit() for gid in requested):
        raise ValueError('game IDs must be a non-empty list of digit strings')
    if len(requested) != len(set(requested)):
        raise ValueError('requested game IDs must be unique')
    wanted = set(requested)
    seen = set()
    rows = []
    rejected = []
    kinds = Counter()
    counts = Counter()
    started = time.monotonic()
    for game in history.season_games(args.season):
        gid = game['id']
        if gid not in wanted:
            continue
        seen.add(gid)
        if game['date_et'] >= TEST_FROM:
            raise ValueError(f'{gid}: protected final-test game is not eligible')
        try:
            found, accounting = windows_for_game(game)
        except InvalidGame as error:
            rejected.append({'game_id': gid, 'reason': str(error)})
        else:
            rows.extend(found)
            kinds.update(row['kind'] for row in found)
            counts.update({key: value for key, value in accounting.items() if isinstance(value, int)})
        if len(seen) % max(1, len(wanted) // 10) == 0 or len(seen) == len(wanted):
            print(f'games {len(seen)}/{len(wanted)} {time.monotonic() - started:.1f}s', flush=True)
    missing = sorted(wanted - seen)
    if missing:
        raise ValueError(f'requested games absent from retained history: {missing}')
    if not rows:
        raise ValueError('no games yielded reconciled substitution windows')
    frame = pd.DataFrame(rows)
    if frame['window_id'].duplicated().any():
        raise ValueError('reconstructed window IDs are not unique')
    inputs = [args.game_ids, ROOT / 'data/raw/hoopr' / f'play_by_play_{args.season}.parquet',
              ROOT / 'data/raw/hoopr' / f'player_box_{args.season}.parquet',
              ROOT / 'scripts/history.py', ROOT / 'scripts/plays.py', ROOT / 'scripts/pbp.py',
              ROOT / 'scripts/rotations.py', Path(__file__)]
    if any(not path.resolve().is_relative_to(ROOT) for path in inputs):
        raise ValueError('sequence-replay inputs must be inside the repository')
    report = {
        'experiment': 'a1_s06_sequence_substitution_windows',
        'season': args.season, 'requested_games': len(requested), 'retained_games': len(requested) - len(rejected),
        'rejected_games': rejected, 'counts': dict(counts), 'window_kinds': dict(kinds),
        'no_substitution_windows': int((frame['home_subs'] + frame['away_subs']).eq(0).sum()),
        'multiple_substitution_windows': int((frame['home_subs'] + frame['away_subs']).gt(1).sum()),
        'method': 'Replay canonical events by period and descending clock, using sequence numbers within each clock; '
                  'take score, fouls, elapsed minutes and five-player lineups immediately before each observed '
                  'substitution group. Split same-clock reversals.',
        'limitations': 'Only recorded stoppages are represented; their labels do not establish that all were legal '
                       'substitution opportunities or that every legal opportunity was recorded. Rosters contain '
                       'actual participants and later period starters are inferred retrospectively. They are not '
                       'pre-game availability forecasts. Period-break transitions are not represented as windows.',
        'input_sha256': {str(path.resolve().relative_to(ROOT)): sha256_file(path) for path in inputs},
    }
    atomic_bytes(args.rows_output, frame.to_parquet(index=False))
    write_json(args.output, report, pretty=True)
    print(f"saved {report['retained_games']}/{report['requested_games']} games, {len(frame)} windows; "
          f"{len(rejected)} games quarantined", flush=True)


if __name__ == '__main__':
    main()
