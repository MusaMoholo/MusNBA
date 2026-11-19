#!/usr/bin/env python3
"""Parse retained final summaries into player and team game logs plus a player registry.

Outputs (data/derived/):
  player_games.csv  one row per rostered player per final game (DNP rows kept, stats blank)
  team_games.csv    one row per team per final game, with quarter scores and a possession estimate
  players.json      athlete registry: latest roster team, position, jersey, status/injury
"""
from __future__ import annotations

import csv
import re
import sys
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, RAW, atomic_bytes, read_json, slate_date, write_json  # noqa: E402
from scripts.fetch_espn import latest_run  # noqa: E402

PLAYER_COLUMNS = ['game_id', 'date_et', 'team_id', 'opp_id', 'home', 'player_id', 'name', 'pos',
                  'starter', 'dnp', 'dnp_reason', 'ejected', 'min', 'pts', 'fgm', 'fga', 'fg3m', 'fg3a',
                  'ftm', 'fta', 'oreb', 'dreb', 'reb', 'ast', 'stl', 'blk', 'tov', 'pf', 'pm']
TEAM_COLUMNS = ['game_id', 'date_et', 'team_id', 'opp_id', 'home', 'pts', 'opp_pts', 'win', 'periods',
                'q1', 'q2', 'q3', 'q4', 'ot', 'fgm', 'fga', 'fg3m', 'fg3a', 'ftm', 'fta', 'oreb', 'dreb',
                'reb', 'ast', 'stl', 'blk', 'tov', 'pf', 'poss']

KEY_MAP = {'minutes': 'min', 'points': 'pts', 'rebounds': 'reb', 'assists': 'ast', 'turnovers': 'tov',
           'steals': 'stl', 'blocks': 'blk', 'offensiveRebounds': 'oreb', 'defensiveRebounds': 'dreb',
           'fouls': 'pf', 'plusMinus': 'pm'}
PAIRS = {'fieldGoalsMade-fieldGoalsAttempted': ('fgm', 'fga'),
         'threePointFieldGoalsMade-threePointFieldGoalsAttempted': ('fg3m', 'fg3a'),
         'freeThrowsMade-freeThrowsAttempted': ('ftm', 'fta')}


def number(text):
    text = str(text).strip()
    if text in ('', '--', '-'):
        return None
    return int(float(text.replace('+', '')))


def parse_line(keys, stats):
    out = {}
    for key, value in zip(keys, stats):
        if key in PAIRS:
            made, att = (value.split('-') + [''])[:2] if value not in ('', '--') else ('', '')
            out[PAIRS[key][0]], out[PAIRS[key][1]] = number(made), number(att)
        elif key in KEY_MAP:
            out[KEY_MAP[key]] = number(value)
    return out


def team_totals(statistics):
    named = {s['name']: s.get('displayValue') for s in statistics}
    out = {}
    for key, (made, att) in PAIRS.items():
        m, a = (named.get(key) or '-').split('-')[:2]
        out[made], out[att] = number(m), number(a)
    for src, dst in (('offensiveRebounds', 'oreb'), ('defensiveRebounds', 'dreb'), ('totalRebounds', 'reb'),
                     ('assists', 'ast'), ('steals', 'stl'), ('blocks', 'blk'), ('fouls', 'pf')):
        out[dst] = number(named.get(src, ''))
    out['tov'] = number(named.get('totalTurnovers', named.get('turnovers', '')))
    return out


def parse_summary(summary: dict):
    c = summary['header']['competitions'][0]
    gid = c['id']
    day = slate_date(c['date'])
    side = {t['homeAway']: t for t in c['competitors']}
    ids = {k: side[k]['team']['id'] if 'team' in side[k] else side[k]['id'] for k in side}
    scores = {k: number((side[k].get('score') or '0')) for k in side}
    lines = {k: [number(x.get('displayValue', x.get('value', ''))) for x in side[k].get('linescores') or []] for k in side}
    teams_box = {t['team']['id']: t for t in summary['boxscore']['teams']}
    players, teams, registry = [], [], {}
    for block in summary['boxscore']['players']:
        tid = block['team']['id']
        home = int(tid == ids['home'])
        opp = ids['away'] if home else ids['home']
        group = block['statistics'][0]
        keys = group.get('keys') or []
        for a in group.get('athletes', []):
            ath = a['athlete']
            dnp = bool(a.get('didNotPlay')) or not a.get('stats')
            row = {c: '' for c in PLAYER_COLUMNS}
            row.update({'game_id': gid, 'date_et': day, 'team_id': tid, 'opp_id': opp, 'home': home,
                        'player_id': ath['id'], 'name': ath.get('displayName', ''),
                        'pos': (ath.get('position') or {}).get('abbreviation', ''),
                        'starter': int(bool(a.get('starter'))), 'dnp': int(dnp),
                        'dnp_reason': (a.get('reason') or '') if dnp else '', 'ejected': int(bool(a.get('ejected')))})
            if not dnp:
                line = parse_line(keys, a['stats'])
                if line.get('min') in (None, 0) and not any((line.get(k) or 0) for k in ('pts', 'fga', 'reb', 'ast')):
                    row['dnp'] = 1
                    row['dnp_reason'] = row['dnp_reason'] or 'DNP'
                else:
                    row.update({k: ('' if v is None else v) for k, v in line.items()})
            players.append(row)
            registry[ath['id']] = {'name': ath.get('displayName', ''), 'short': ath.get('shortName', ''),
                                   'pos': (ath.get('position') or {}).get('abbreviation', ''),
                                   'jersey': ath.get('jersey', ''), 'last_team': tid, 'last_game': day}
    for key in ('home', 'away'):
        tid = ids[key]
        opp_key = 'away' if key == 'home' else 'home'
        box = team_totals(teams_box[tid]['statistics'])
        q = lines[key] + [None] * 4
        row = {'game_id': gid, 'date_et': day, 'team_id': tid, 'opp_id': ids[opp_key], 'home': int(key == 'home'),
               'pts': scores[key], 'opp_pts': scores[opp_key], 'win': int(scores[key] > scores[opp_key]),
               'periods': len(lines[key]), 'q1': q[0], 'q2': q[1], 'q3': q[2], 'q4': q[3],
               'ot': sum(x or 0 for x in lines[key][4:]), **box}
        row['poss'] = round(box['fga'] - box['oreb'] + box['tov'] + 0.44 * box['fta'], 2)
        teams.append(row)
    return players, teams, registry


def csv_bytes(rows, columns):
    out = StringIO()
    writer = csv.DictWriter(out, columns, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode('utf-8')


INJURY_ID = re.compile(r'/id/(\d+)/')


def roster_registry(run: Path) -> dict:
    """Current team, bio and availability per athlete from the latest rosters and injury report."""
    out = {}
    for path in sorted((run / 'roster').glob('*.json.gz')):
        doc = read_json(path)
        tid = doc['team']['id']
        for a in doc.get('athletes', []):
            injuries = a.get('injuries') or []
            out[a['id']] = {'name': a.get('displayName', ''), 'short': a.get('shortName', ''),
                            'pos': (a.get('position') or {}).get('abbreviation', ''), 'jersey': a.get('jersey', ''),
                            'team': tid, 'age': a.get('age'), 'height': a.get('displayHeight', ''),
                            'weight': a.get('displayWeight', ''), 'experience': (a.get('experience') or {}).get('years'),
                            'status': injuries[0].get('status') if injuries else 'Active',
                            'injury': None}
    report = run / 'injuries.json.gz'
    if report.exists():
        for team in read_json(report).get('injuries', []):
            for item in team.get('injuries', []):
                links = (item.get('athlete') or {}).get('links') or []
                pid = next((m.group(1) for l in links if (m := INJURY_ID.search(l.get('href', '')))), None)
                if pid and pid in out:
                    details = item.get('details') or {}
                    out[pid]['status'] = item.get('status') or out[pid]['status']
                    out[pid]['injury'] = {'status': item.get('status'), 'date': item.get('date'),
                                          'comment': item.get('shortComment') or '', 'type': details.get('type'),
                                          'detail': details.get('detail'), 'return': details.get('returnDate')}
    return out


def build(run: Path | None = None):
    run = run or latest_run()
    players, teams, seen = [], [], {}
    for path in sorted((RAW / 'final').glob('*.json.gz')):
        p, t, r = parse_summary(read_json(path))
        players += p
        teams += t
        for pid, info in r.items():
            if pid not in seen or info['last_game'] >= seen[pid]['last_game']:
                seen[pid] = info
    players.sort(key=lambda r: (r['date_et'], r['game_id'], r['team_id'], -int(r['starter']), r['player_id']))
    teams.sort(key=lambda r: (r['date_et'], r['game_id'], r['team_id']))
    roster = roster_registry(run)
    registry = {}
    for pid in sorted(set(seen) | set(roster), key=int):
        base = {'id': pid, **seen.get(pid, {})}
        current = roster.get(pid)
        if current:
            base.update({k: v for k, v in current.items() if v not in (None, '') or k in ('injury',)})
            base['on_roster'] = True
        else:
            base.update({'team': base.get('last_team'), 'status': 'Not on current roster', 'injury': None,
                         'on_roster': False})
        registry[pid] = base
    atomic_bytes(DERIVED / 'player_games.csv', csv_bytes(players, PLAYER_COLUMNS))
    atomic_bytes(DERIVED / 'team_games.csv', csv_bytes(teams, TEAM_COLUMNS))
    write_json(DERIVED / 'players.json', {'run': run.name, 'players': registry})
    return players, teams, registry


def load_csv(name):
    path = DERIVED / name
    with open(path, newline='', encoding='utf-8') as stream:
        return list(csv.DictReader(stream))


def main():
    players, teams, registry = build()
    print(f'player rows {len(players)} · team rows {len(teams)} · games {len(teams) // 2} · registry {len(registry)}')


if __name__ == '__main__':
    main()
