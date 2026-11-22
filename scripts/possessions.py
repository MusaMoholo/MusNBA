#!/usr/bin/env python3
"""Segments and possessions from canonical games (ENGINE_PLAN.md M2).

A segment runs from a start (period start, inbound after a make, rebound, steal, dead ball, jump ball)
to the next start. Offensive rebounds and defensive fouls without free throws start a new segment of the
same possession; every other start hands the ball over. Durations partition each period's game clock,
so the ten players on court in a segment are credited with exactly its seconds.

Each segment records: offence/defence, both lineups, start type and clock, time to the terminal action
and to the next start, what happened (who; shot value, zone, make/miss, assist, block, and-one; turnover
live/dead, stealer; foul, fouler; free throws), the rebound (side and player), points, and the game state
at the start (score, team fouls in the period).

  .venv/bin/python scripts/possessions.py            current season (retained summaries)
  .venv/bin/python scripts/possessions.py --history  every downloaded historical season
  … --rebound-clock miss --out DIR                   the 2026-27 feed's rebound convention, into a variant folder

Rebound clock (M5b, FINDINGS §3k). Through 2025-26 ESPN stamps a rebound when it happens (2.4 s after a missed shot on
average); from 2026-27 every rebound carries the clock of the miss it follows. `feed` (the default) keeps the clocks as
stamped, so history and the live season differ; `miss` (the default since v1.1, D23) starts every rebound segment at
the miss's clock for every source — exact for both, and a no-op on 2026-27 data. v1's data (feed clocks) is kept in
data/derived/variants/rebound_feed/.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, RAW, read_json, write_json  # noqa: E402
from scripts import pbp, plays  # noqa: E402

NEW_POSSESSION = {'period_start', 'made_fg', 'made_ft', 'dreb', 'steal', 'dead_turnover', 'jump_ball', 'other'}
IGNORE = ('timeout', 'ejection', 'review', 'delay', 'instant replay', 'coach', 'jumpball violation', 'jump ball violation',
          'lane', 'defensive 3-seconds', 'technical', 'double technical', 'hanging technical', 'flopping', 'taunting')
TRIP = re.compile(r'(\d) of (\d)')


def zone(x, y, value):
    if x is None or y is None:
        return 'unknown'
    dx = abs(x - 25)
    if value == 3:
        return 'corner3' if dx >= 21.8 and y <= 14 else 'above3'
    if (dx * dx + y * y) ** 0.5 <= 4.0:
        return 'rim'
    if dx <= 8 and y <= 19:
        return 'paint'
    return 'mid'


REBOUND_CLOCKS = ('feed', 'miss')


def lineup_issues(seg: dict) -> list[str]:
    off, defense = seg['lineup_off'], seg['lineup_def']
    issues = []
    if len(off) != 5 or len(set(off)) != 5 or not all(off):
        issues.append('invalid_offense')
    if len(defense) != 5 or len(set(defense)) != 5 or not all(defense):
        issues.append('invalid_defense')
    if set(off) & set(defense):
        issues.append('overlapping_lineups')
    for participant, side, label in (
            ('actor', off, 'actor_not_offense'), ('assister', off, 'assister_not_offense'),
            ('blocker', defense, 'blocker_not_defense'), ('stealer', defense, 'stealer_not_defense')):
        if seg[participant] is not None and seg[participant] not in side:
            issues.append(label)
    if seg['fouler'] is not None:
        side = off if seg['end_type'] == 'turnover' else defense
        if seg['fouler'] not in side:
            issues.append('fouler_not_expected_side')
    if seg['rebounder'] is not None and seg['rebound'] in ('off', 'def'):
        side = off if seg['rebound'] == 'off' else defense
        if seg['rebounder'] not in side:
            issues.append('rebounder_not_expected_side')
    return issues


def parse_game(game: dict, rebound_clock: str = 'miss', split_substitutions: bool = False):
    assert rebound_clock in REBOUND_CLOCKS, rebound_clock
    team_of, starters, box, teams, by_minutes = pbp.game_context(game)
    issues = Counter()
    if len(teams) != 2:
        issues['not_two_teams'] += 1
        return [], issues, {}
    other = {teams[0]: teams[1], teams[1]: teams[0]}
    home = game['home']
    score = {t: 0 for t in teams}
    other_points = Counter()
    segments = []
    poss = -1
    closing = {t: list(starters[t]) for t in teams}
    for period in sorted({p['period'] for p in game['plays']}):
        events = [p for p in game['plays'] if p['period'] == period]
        # Late-logged plays (e.g. a challenge overturned into a turnover) can follow the period's end in the
        # feed's order; order by game clock, keeping the feed's order within a second.
        events.sort(key=lambda p: -pbp.clock_seconds(p['clock']))
        length = pbp.period_length(period)
        lineup = pbp.period_starters(events, period, teams, team_of, starters, closing, by_minutes, issues)
        on = {t: list(lineup[t]) for t in teams}
        team_fouls = {t: 0 for t in teams}
        seg = None
        pending = None  # 'rebound' after a miss, 'ft' while a free-throw trip is unfinished
        miss_clock = None  # clock of the segment's latest missed shot or free throw (rebound_clock='miss')

        def open_seg(clock, start_type, offense, sub_continuation=False):
            nonlocal seg, poss, pending, miss_clock
            miss_clock = None
            if start_type in NEW_POSSESSION and not sub_continuation:
                poss += 1
            d = other[offense]
            seg = {'game_id': game['id'], 'date_et': game['date_et'], 'season': game['season'], 'season_type': game['season_type'],
                   'period': period, 'poss': poss, 'offense': offense, 'defense': d, 'off_home': offense == home,
                   'start_type': start_type, 'start_clock': clock, 'action_clock': None, 'end_clock': None,
                   'score_off': score[offense], 'score_def': score[d], 'fouls_off': team_fouls[offense], 'fouls_def': team_fouls[d],
                   'lineup_off': sorted(on[offense]), 'lineup_def': sorted(on[d]),
                   'end_type': None, 'actor': None, 'value': None, 'zone': None, 'x': None, 'y': None, 'made': None,
                   'heave': False, 'and_one': False, 'assister': None, 'blocker': None, 'stealer': None, 'fouler': None,
                   'turnover': None, 'fta': 0, 'ftm': 0, 'ft_seq': '', 'rebound': None, 'rebounder': None, 'points': 0}
            if split_substitutions:
                seg.update({'sub_prefix': False, 'sub_continuation': sub_continuation})
            pending = None

        def close_seg(clock, end_type=None):
            nonlocal seg
            if seg is None:
                return
            seg['end_clock'] = clock
            if seg['end_type'] is None:
                seg['end_type'] = end_type or 'unknown'
            if seg['action_clock'] is None:
                seg['action_clock'] = clock
            if split_substitutions:
                problems = lineup_issues(seg)
                seg['lineup_valid'] = not problems
                seg['lineup_issues'] = ';'.join(problems)
            segments.append(seg)
            seg = None

        def ensure(team, clock, why):
            """The acting team must be on offence; otherwise a hand-over was missed in the feed."""
            if team not in other:
                return False
            if seg is None:
                open_seg(float(length) if not segments or segments[-1]['period'] != period else clock,
                         'period_start' if not segments or segments[-1]['period'] != period else 'other', team)
            elif seg['offense'] != team:
                issues['implicit_change_' + why] += 1
                close_seg(clock, 'unknown')
                open_seg(clock, 'other', team)
            return True

        for i, e in enumerate(events):
            k = e['type_text'].lower()
            text = e['text'].lower()
            parts = e['participants']
            team = e['team']
            clock = pbp.clock_seconds(e['clock'])
            if e['type_id'] == pbp.SUB and len(parts) >= 2:
                enter, leave = parts[0], parts[1]
                t = team_of.get(enter) or team_of.get(leave)
                if t in on:
                    old_lineup = set(on[t])
                    if leave in on[t]:
                        on[t].remove(leave)
                    if enter not in on[t]:
                        on[t].append(enter)
                    if split_substitutions and set(on[t]) != old_lineup and seg is not None \
                            and seg['end_type'] is None and pending is None:
                        if clock < seg['start_clock']:
                            offense, start_type = seg['offense'], seg['start_type']
                            seg['sub_prefix'] = True
                            close_seg(clock, 'unknown')
                            open_seg(clock, start_type, offense, sub_continuation=True)
                        elif clock == seg['start_clock']:
                            seg['lineup_off'] = sorted(on[seg['offense']])
                            seg['lineup_def'] = sorted(on[seg['defense']])
                        else:
                            issues['sub_before_segment_clock'] += 1
                continue
            if e['type_id'] in ('412', '402') or 'end period' in k or 'end game' in k:
                close_seg(0.0, 'end_period')
                continue
            if e['shooting'] and e['points_attempted'] == 1:
                if 'technical' in k:
                    if team in score:
                        other_points[team] += e['score_value']
                        score[team] += e['score_value']
                    continue
                if not ensure(team, clock, 'free_throw'):
                    continue
                seg['fta'] += 1
                seg['ft_seq'] += '1' if e['scoring'] else '0'  # real make/miss order within the trip
                if seg['actor'] is None:
                    seg['actor'] = parts[0] if parts else None
                if seg['end_type'] is None:
                    seg['end_type'] = 'fouled'
                if seg['action_clock'] is None:
                    seg['action_clock'] = clock
                if e['scoring']:
                    seg['ftm'] += 1
                    seg['points'] += e['score_value']
                    score[team] += e['score_value']
                m = TRIP.search(k)
                last = not m or m.group(1) == m.group(2)
                retain = 'flagrant' in k or 'clear path' in k
                if not last:
                    pending = 'ft'
                elif e['scoring']:
                    close_seg(clock)
                    open_seg(clock, 'foul' if retain else 'made_ft', team if retain else other[team])
                else:
                    pending = 'rebound'
                    miss_clock = clock
                continue
            if e['shooting'] and e['points_attempted'] in (2, 3):
                if not ensure(team, clock, 'shot'):
                    continue
                if seg['end_type'] in ('shot', 'fouled') and pending is None and seg['made'] is not None:
                    issues['second_shot_in_segment'] += 1
                seg.update({'end_type': 'shot', 'actor': parts[0] if parts else None, 'value': e['points_attempted'],
                            'x': e['x'], 'y': e['y'], 'zone': zone(e['x'], e['y'], e['points_attempted']), 'made': e['scoring'],
                            'heave': 'heave' in k, 'action_clock': clock})
                if e['scoring']:
                    seg['points'] += e['score_value']
                    score[team] += e['score_value']
                    if len(parts) >= 2 and 'assist' in text:
                        seg['assister'] = parts[1]
                    and_one = any(n['clock'] == e['clock'] and n['shooting'] and n['points_attempted'] == 1 and '1 of 1' in n['type_text'].lower()
                                  and (n['participants'] or [None])[0] == seg['actor'] for n in events[i + 1:i + 6])
                    if and_one:
                        seg['and_one'] = True
                        pending = 'ft'
                    else:
                        close_seg(clock)
                        open_seg(clock, 'made_fg', other[team])
                else:
                    if len(parts) >= 2 and 'block' in text:
                        seg['blocker'] = parts[1]
                    pending = 'rebound'
                    miss_clock = clock
                continue
            if e['type_id'] in ('155', '156') or 'rebound' in k:
                if pending == 'ft':
                    continue  # dead-ball team rebound after a missed non-final free throw
                if seg is None or team not in other:
                    issues['rebound_without_segment'] += 1
                    continue
                offensive = team == seg['offense']
                seg['rebound'] = ('off' if offensive else 'def') if parts else ('team_off' if offensive else 'team_def')
                seg['rebounder'] = parts[0] if parts else None
                offense = seg['offense']
                at = miss_clock if rebound_clock == 'miss' and miss_clock is not None else clock
                close_seg(at)
                open_seg(at, 'oreb' if offensive else 'dreb', offense if offensive else other[offense])
                continue
            if pbp.is_turnover(e) or any(w in k for w in pbp.TEAM_TURNOVERS):
                if not ensure(team, clock, 'turnover'):
                    continue
                live = 'steal' in text and len(parts) >= 2
                seg.update({'end_type': 'turnover', 'actor': parts[0] if parts and 'team' not in k else (parts[0] if parts else None),
                            'turnover': 'live' if live else 'dead', 'stealer': parts[1] if live else None, 'action_clock': clock})
                if k == 'offensive foul turnover':
                    seg['fouler'] = parts[0] if parts else None
                offense = seg['offense']
                close_seg(clock)
                open_seg(clock, 'steal' if live else 'dead_turnover', other[offense])
                continue
            if e['type_id'] == '615' or 'jump ball' in k or 'jumpball' in k:
                if 'violation' in k:
                    continue
                if seg is not None:
                    close_seg(clock, 'jump_ball')
                if team in other:
                    open_seg(clock, 'jump_ball', team)
                continue
            if 'foul' in k and 'technical' not in k and 'offensive' not in k:
                if team in team_fouls:
                    team_fouls[team] += 1
                if seg is None or team != seg['defense']:
                    continue  # offence's loose-ball fouls and similar do not change possession
                if 'shooting' in k:
                    seg['fouler'] = parts[0] if parts else None
                    if seg['made']:
                        continue  # and-one: free throw follows
                    if seg['end_type'] != 'shot':
                        seg['end_type'] = 'fouled'
                    if seg['action_clock'] is None:
                        seg['action_clock'] = clock
                    pending = 'ft'
                    continue
                free_throws = any(n['clock'] == e['clock'] and n['shooting'] and n['points_attempted'] == 1
                                  and 'technical' not in n['type_text'].lower() for n in events[i + 1:i + 6])
                seg['fouler'] = parts[0] if parts else None
                if free_throws:
                    if seg['end_type'] is None:
                        seg['end_type'] = 'foul'
                        seg['action_clock'] = clock
                    pending = 'ft'
                else:
                    seg['end_type'] = 'foul'
                    seg['action_clock'] = clock
                    offense = seg['offense']
                    close_seg(clock)
                    open_seg(clock, 'foul', offense)
                continue
            if 'kicked ball' in k or 'defensive goaltending' in k:
                if seg is not None and team == seg['defense'] and 'kicked' in k:
                    seg['end_type'] = 'violation'
                    seg['action_clock'] = clock
                    offense = seg['offense']
                    close_seg(clock)
                    open_seg(clock, 'foul', offense)
                continue
            if any(w in k for w in IGNORE):
                continue
        close_seg(0.0, 'end_period')
        closing = {t: list(on[t]) for t in teams}
    return segments, issues, {'other_points': dict(other_points)}


def check_game(game, segments, extra, issues, checks) -> bool:
    """Accounting identities per game; updates `checks`; True when points and clock both reconcile."""
    ok = True
    points = defaultdict(int)
    for s in segments:
        points[s['offense']] += s['points']
    final = defaultdict(int)
    for pl in game['players']:
        if not pl['dnp']:
            final[pl['team']] += pl['box'].get('pts') or 0
    for t in final:
        checks['team_games'] += 1
        if points[t] + extra['other_points'].get(t, 0) != final[t]:
            checks['points_off'] += 1
            ok = False
    by_period = defaultdict(float)
    for s in segments:
        by_period[s['period']] += s['start_clock'] - s['end_clock']
    for period, total in by_period.items():
        checks['periods'] += 1
        if abs(total - pbp.period_length(period)) > 0.05:
            checks['clock_off'] += 1
            ok = False
    last = {}
    for s in segments:
        if not s.get('sub_continuation') and s['start_type'] in NEW_POSSESSION and s['start_type'] not in ('period_start', 'jump_ball'):
            prev = last.get(s['period'])
            checks['handovers'] += 1
            if prev is not None and prev == s['offense']:
                checks['not_alternating'] += 1
        if not s.get('sub_continuation') and s['start_type'] in NEW_POSSESSION:
            last[s['period']] = s['offense']
        checks['segments'] += 1
        if len(set(s['lineup_off'])) == 5 and len(set(s['lineup_def'])) == 5:
            checks['lineups_ok'] += 1
    for t in final:
        poss = len({s['poss'] for s in segments if s['offense'] == t})
        box_estimate = sum((pl['box'].get('fga') or 0) - (pl['box'].get('oreb') or 0) + (pl['box'].get('tov') or 0)
                           + 0.44 * (pl['box'].get('fta') or 0) for pl in game['players'] if pl['team'] == t and not pl['dnp'])
        checks['poss'] += poss
        checks['poss_box_estimate'] += box_estimate
    return ok


def parse_many(games, rebound_clock: str = 'miss', split_substitutions: bool = False):
    rows, issues, checks = [], Counter(), Counter()
    for game in games:
        segments, i, extra = parse_game(game, rebound_clock, split_substitutions)
        issues.update(i)
        ok = check_game(game, segments, extra, issues, checks)
        checks['games_flagged'] += not ok
        for seg in segments:
            seg['game_ok'] = ok  # training uses only games whose points and clock reconcile
        rows += segments
    n = lambda a, b: round(checks[a] / checks[b], 4) if checks[b] else None
    report = {'games': checks['team_games'] // 2, 'segments': len(rows),
              'points_off_team_games': n('points_off', 'team_games'), 'clock_off_periods': n('clock_off', 'periods'),
              'not_alternating': n('not_alternating', 'handovers'), 'lineups_ok': n('lineups_ok', 'segments'),
              'possessions_per_team_game': round(checks['poss'] / max(1, checks['team_games']), 2),
              'box_estimate_per_team_game': round(checks['poss_box_estimate'] / max(1, checks['team_games']), 2),
              'games_flagged': checks['games_flagged'], 'rebound_clock': rebound_clock,
              'issues': dict(issues)}
    if split_substitutions:
        report['split_substitutions'] = True
    return rows, report


def to_frame(rows):
    import pandas as pd
    flat = []
    for r in rows:
        r = dict(r)
        for side in ('off', 'def'):
            ids = r.pop('lineup_' + side)
            for j in range(5):
                r[f'{side}_{j + 1}'] = ids[j] if len(ids) == 5 and j < 5 else None
        r['shot_time'] = round(r['start_clock'] - r['action_clock'], 1)
        r['duration'] = round(r['start_clock'] - r['end_clock'], 1)
        flat.append(r)
    return pd.DataFrame(flat)


def current_games(before: str | None = None):
    """This season's final games in the canonical schema. before = an ET date: only games dated earlier (master
    fixtures), so inputs rebuilt for slate D never see a game played on D (cutoff safety for the nightly rebuild)."""
    paths = sorted((RAW / 'final').glob('*.json.gz'))
    if before:
        from scripts import master_fixtures
        dates = {r['game_id']: r['date_et'] for r in master_fixtures.load()}
        paths = [p for p in paths if dates.get(p.name.split('.')[0], '9999') < before]
    return (plays.from_summary(read_json(p)) for p in paths)


def build_current(rebound_clock: str = 'miss', root: Path = DERIVED, before: str | None = None,
                  split_substitutions: bool = False):
    """Current-season segments → root/segments.parquet (root = DERIVED, or a variant folder); before: see current_games."""
    if split_substitutions and root.resolve() == DERIVED.resolve():
        raise ValueError('split-substitution candidate requires an isolated output root')
    if split_substitutions and any((root / name).exists() for name in ('segments.parquet', 'segments_report.json')):
        raise FileExistsError(f'candidate output already exists in {root}')
    rows, report = parse_many(current_games(before), rebound_clock, split_substitutions)
    root.mkdir(parents=True, exist_ok=True)
    to_frame(rows).to_parquet(root / 'segments.parquet', index=False)
    write_json(root / 'segments_report.json', report, pretty=True)
    return report


def build_history(seasons=None, rebound_clock: str = 'miss', root: Path = DERIVED, split_substitutions: bool = False):
    """History segments → root/history/<season>/segments.parquet."""
    from scripts import history
    if split_substitutions and root.resolve() == DERIVED.resolve():
        raise ValueError('split-substitution candidate requires an isolated output root')
    out = {}
    for season in seasons or history.SEASONS:
        if not (history.RAW_DIR / f'play_by_play_{season}.parquet').exists():
            continue
        target = root / 'history' / str(season)
        if split_substitutions and any((target / name).exists() for name in ('segments.parquet', 'segments_report.json')):
            raise FileExistsError(f'candidate output already exists in {target}')
        rows, report = parse_many(history.season_games(season), rebound_clock, split_substitutions)
        target.mkdir(parents=True, exist_ok=True)
        to_frame(rows).to_parquet(target / 'segments.parquet', index=False)
        write_json(target / 'segments_report.json', report, pretty=True)
        out[season] = report
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--history', action='store_true')
    parser.add_argument('--rebound-clock', choices=REBOUND_CLOCKS, default='miss',
                        help="'miss' (default since v1.1, D23): rebound segments start at the miss's clock; 'feed': as stamped")
    parser.add_argument('--out', type=Path, default=DERIVED, help='root folder (default data/derived; variants elsewhere)')
    parser.add_argument('--split-substitutions', action='store_true',
                        help='candidate: split action-free segments at substitutions; requires an isolated --out')
    args = parser.parse_args()
    import json
    if args.history:
        for season, report in build_history(rebound_clock=args.rebound_clock, root=args.out,
                                            split_substitutions=args.split_substitutions).items():
            print(season, json.dumps(report))
    else:
        print(json.dumps(build_current(args.rebound_clock, args.out, split_substitutions=args.split_substitutions), indent=1))


if __name__ == '__main__':
    main()
