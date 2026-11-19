#!/usr/bin/env python3
"""Per-period player box scores and on-court seconds from play-by-play (canonical games, scripts/plays.py).

Lineups: Q1 starters come from the box score; later periods infer who started the period from
players who act (or are substituted out) before being substituted in, filling gaps from the
previous period's closing lineup. Substitutions ([entering, leaving]) then move players on and
off; the countdown clock gives seconds on court.

Participant conventions (checked on retained games): shots [shooter, assister|blocker],
turnovers [player, stealer], rebounds [rebounder] (team rebounds have none), fouls [fouler].

Outputs data/derived/player_periods.csv and pbp_report.json (validation against box scores).
"""
from __future__ import annotations

import csv
import sys
from collections import Counter, defaultdict
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, RAW, atomic_bytes, read_json, write_json  # noqa: E402
from scripts import plays as schema  # noqa: E402

COLUMNS = ['game_id', 'date_et', 'team_id', 'player_id', 'period', 'sec', 'pts', 'fgm', 'fga', 'fg3m', 'fg3a',
           'ftm', 'fta', 'oreb', 'dreb', 'ast', 'stl', 'blk', 'tov', 'pf']
STATS = COLUMNS[5:]
SUB = '584'
TURNOVER_WORDS = ('turnover', 'traveling', 'double dribble', 'discontinued dribble', 'backcourt', 'offensive goaltending',
                  'palming', 'inbound', 'step out')
TEAM_TURNOVERS = ('shot clock', '8-second')          # charged to the team, not a player, in box scores
NOT_ON_COURT = ('technical', 'ejection', 'timeout', 'delay', 'review', 'end period', 'end game')


def period_length(period: int) -> int:
    return 720 if period <= 4 else 300


def clock_seconds(text: str) -> float:
    text = (text or '0').strip()
    parts = text.split(':')
    if len(parts) == 3:  # one archived game logs M:SS:hundredths
        return int(parts[0]) * 60 + int(parts[1]) + int(parts[2]) / 100
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    return float(text)


def participants(play):
    return play['participants']


def kind(play) -> str:
    return play['type_text'].lower()


def is_turnover(play) -> bool:
    k = kind(play)
    return any(w in k for w in TURNOVER_WORDS) and not any(w in k for w in TEAM_TURNOVERS)


def is_personal_foul(play) -> bool:
    k = kind(play)
    # An offensive foul is usually logged twice (foul + turnover) and sometimes only as the turnover:
    # count it once, from the turnover record (see parse_game).
    return 'foul' in k and 'technical' not in k and k != 'offensive foul'


def game_context(game: dict):
    """Rosters from the box score: team of each player, starters, box lines, teams, players by minutes."""
    team_of, starters, box, minutes = {}, defaultdict(list), {}, defaultdict(list)
    for pl in game['players']:
        pid, tid = pl['id'], pl['team']
        team_of[pid] = tid
        if not pl['dnp']:
            box[pid] = pl['box']
            minutes[tid].append((-(box[pid].get('min') or 0), pid))
            if pl['starter']:
                starters[tid].append(pid)
    teams = list(dict.fromkeys(team_of.values()))
    by_minutes = {t: [pid for _, pid in sorted(minutes[t])] for t in teams}
    return team_of, starters, box, teams, by_minutes


def period_starters(events, period, teams, team_of, starters, closing, by_minutes, issues):
    """Who starts a period: box-score starters in Q1; later, players who act (or are substituted out)
    before being substituted in, filled from the previous closing lineup, trimmed to five."""
    if period == 1:
        lineup = {t: list(starters[t]) for t in teams}
    else:
        lineup = {t: [] for t in teams}
        seen, entered = set(), set()
        # Events logged at the same clock as a player's own sub-in are ordering glitches, not proof
        # that he started the period.
        sub_ins = {(participants(e)[0], e['clock']) for e in events
                   if e['type_id'] == SUB and len(participants(e)) >= 2}
        for e in events:
            if any(w in kind(e) for w in NOT_ON_COURT):
                continue
            parts = [x for x in participants(e) if x in team_of]
            if e['type_id'] != SUB:
                parts = [x for x in parts if (x, e['clock']) not in sub_ins or x in seen]
            if e['type_id'] == SUB and len(parts) >= 2:
                enter, leave = parts[0], parts[1]
                if leave not in seen:
                    lineup[team_of[leave]].append(leave)
                if enter not in seen:
                    entered.add(enter)
                seen.update((enter, leave))
            else:
                for pid in parts:
                    if pid not in seen:
                        lineup[team_of[pid]].append(pid)
                        seen.add(pid)
        for t in teams:
            if len(lineup[t]) < 5:
                issues['period_lineup_filled'] += 1
                for pid in closing.get(t, []) + by_minutes.get(t, []):
                    if len(lineup[t]) >= 5:
                        break
                    if pid not in lineup[t] and pid not in entered:
                        lineup[t].append(pid)
            if len(lineup[t]) > 5:
                issues['period_lineup_over_five'] += 1
                lineup[t] = lineup[t][:5]
    return lineup


def parse_game(game: dict):
    """Canonical game (scripts/plays.py) -> per-period player rows, lineup issues, box-score checks."""
    gid, day = game['id'], game['date_et']
    team_of, starters, box, teams, by_minutes = game_context(game)
    plays = game['plays']
    stats = defaultdict(lambda: defaultdict(float))
    issues = Counter()
    closing = {t: list(starters[t]) for t in teams}
    for period in sorted({p['period'] for p in plays}):
        events = [p for p in plays if p['period'] == period]
        length = period_length(period)
        lineup = period_starters(events, period, teams, team_of, starters, closing, by_minutes, issues)
        opened = {pid: float(length) for t in teams for pid in lineup[t]}
        sub_ins_all = {(participants(e)[0], e['clock']) for e in events
                       if e['type_id'] == SUB and len(participants(e)) >= 2}
        offensive_turnovers = {(e['clock'], (participants(e) or [None])[0]) for e in events if kind(e) == 'offensive foul turnover'}
        for index, e in enumerate(events):
            parts = participants(e)
            clock = clock_seconds(e['clock'])
            if e['type_id'] == SUB and len(parts) >= 2:
                enter, leave = parts[0], parts[1]
                if leave in opened:
                    stats[(leave, period)]['sec'] += opened.pop(leave) - clock
                else:
                    issues['sub_out_not_on_court'] += 1
                    if not any(pid == leave for pid, _ in sub_ins_all) and stats[(leave, period)]['sec'] == 0:
                        stats[(leave, period)]['sec'] += length - clock  # on since the period began
                if enter in opened:
                    issues['sub_in_already_on'] += 1
                    stats[(enter, period)]['sec'] += opened[enter] - clock
                opened[enter] = clock
                continue
            known = [p for p in parts if p in team_of]
            if not known:
                continue
            actor = known[0] if parts and parts[0] in team_of else None
            text = e['text'].lower()
            attempted = e['points_attempted']
            made = e['scoring']
            if e['shooting'] and attempted in (2, 3) and actor:
                s = stats[(actor, period)]
                if 'heave' in kind(e) and not made:
                    continue  # end-of-period heaves are excluded from box-score attempts
                s['fga'] += 1
                s['fg3a'] += attempted == 3
                if made:
                    s['fgm'] += 1
                    s['fg3m'] += attempted == 3
                    s['pts'] += e['score_value'] or attempted
                    if len(parts) >= 2 and parts[1] in team_of and 'assist' in text:
                        stats[(parts[1], period)]['ast'] += 1
                elif len(parts) >= 2 and parts[1] in team_of and 'block' in text:
                    stats[(parts[1], period)]['blk'] += 1
            elif e['shooting'] and attempted == 1 and actor:
                stats[(actor, period)]['fta'] += 1
                if made:
                    stats[(actor, period)]['ftm'] += 1
                    stats[(actor, period)]['pts'] += e['score_value'] or 1
            elif e['type_id'] in ('155', '156') and actor:
                stats[(actor, period)]['dreb' if e['type_id'] == '155' else 'oreb'] += 1
            elif is_turnover(e) and actor:
                stats[(actor, period)]['tov'] += 1
                if kind(e) == 'offensive foul turnover':
                    stats[(actor, period)]['pf'] += 1
                if len(parts) >= 2 and parts[1] in team_of and 'steal' in text:
                    stats[(parts[1], period)]['stl'] += 1
            elif kind(e) == 'offensive foul' and actor:
                if (e['clock'], actor) not in offensive_turnovers:
                    stats[(actor, period)]['pf'] += 1
            elif is_personal_foul(e) and actor:
                for pid in (known if 'double' in kind(e) else [actor]):
                    stats[(pid, period)]['pf'] += 1
            elif any(w in kind(e) for w in TEAM_TURNOVERS) and actor and 'steal' in text and len(parts) >= 2:
                stats[(parts[1], period)]['stl'] += 1
        for pid, start in opened.items():
            stats[(pid, period)]['sec'] += start
        closing = {t: [pid for pid in opened if team_of.get(pid) == t] for t in teams}
        for t in teams:
            on = sum(stats[(pid, period)]['sec'] for pid in team_of if team_of[pid] == t)
            if abs(on - 5 * length) > 1:
                issues['team_seconds_off'] += 1
    rows = []
    for (pid, period), s in stats.items():
        if pid not in team_of:
            continue
        row = {'game_id': gid, 'date_et': day, 'team_id': team_of[pid], 'player_id': pid, 'period': period}
        row.update({k: round(s.get(k, 0), 1) if k == 'sec' else int(s.get(k, 0)) for k in STATS})
        rows.append(row)
    # Validation against the box score (the authority for game totals).
    totals = defaultdict(lambda: defaultdict(float))
    for r in rows:
        for k in STATS:
            totals[r['player_id']][k] += r[k]
    checks = Counter()
    for pid, line in box.items():
        t = totals.get(pid, {})
        for k in ('pts', 'fgm', 'fga', 'fg3m', 'fg3a', 'ftm', 'fta', 'oreb', 'dreb', 'ast', 'stl', 'blk', 'tov', 'pf'):
            checks[k + '_checked'] += 1
            if line.get(k) is not None and int(t.get(k, 0)) != line[k]:
                checks[k + '_mismatch'] += 1
        checks['min_checked'] += 1
        if line.get('min') is not None and abs(t.get('sec', 0) / 60 - line['min']) > 1.01:
            checks['min_mismatch'] += 1
    return rows, issues, checks


def parse_many(games):
    """Parse canonical games; returns (sorted rows, report)."""
    rows, issues, checks = [], Counter(), Counter()
    count = 0
    for game in games:
        r, i, c = parse_game(game)
        rows += r
        issues.update(i)
        checks.update(c)
        count += 1
    rows.sort(key=lambda r: (r['date_et'], r['game_id'], r['team_id'], r['player_id'], r['period']))
    report = {'games': count, 'rows': len(rows), 'issues': dict(issues),
              'mismatch_rates': {k.removesuffix('_mismatch'): round(checks[k] / max(1, checks[k.removesuffix('_mismatch') + '_checked']), 4)
                                 for k in sorted(checks) if k.endswith('_mismatch')},
              'checked_player_games': checks['pts_checked']}
    return rows, report


def csv_bytes(rows) -> bytes:
    out = StringIO()
    writer = csv.DictWriter(out, COLUMNS, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode('utf-8')


def build():
    games = (schema.from_summary(read_json(path)) for path in sorted((RAW / 'final').glob('*.json.gz')))
    rows, report = parse_many(games)
    atomic_bytes(DERIVED / 'player_periods.csv', csv_bytes(rows))
    write_json(DERIVED / 'pbp_report.json', report, pretty=True)
    return report


def load():
    with open(DERIVED / 'player_periods.csv', newline='', encoding='utf-8') as stream:
        return list(csv.DictReader(stream))


if __name__ == '__main__':
    import json
    print(json.dumps(build(), indent=1))
