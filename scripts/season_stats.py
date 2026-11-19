#!/usr/bin/env python3
"""Cutoff-safe team and player season statistics.

Everything here reads only games whose ET date is before the requested slate date, so a
snapshot for date D never sees results from D or later. Rates are raw; shrinkage belongs to
the model that consumes them.
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

BOX = ('pts', 'fgm', 'fga', 'fg3m', 'fg3a', 'ftm', 'fta', 'oreb', 'dreb', 'reb', 'ast', 'stl', 'blk', 'tov', 'pf')


def num(value, default=0.0):
    if value in (None, ''):
        return default
    return float(value)


def ratio(a, b):
    return a / b if b else None


def team_table(team_rows: list[dict], day: str, teams: dict) -> tuple[dict, dict]:
    """teams: id -> {'abbr', 'conf', 'div'}. Returns (per-team stats, league averages)."""
    rows = [r for r in team_rows if r['date_et'] < day]
    by_game = defaultdict(dict)
    for r in rows:
        by_game[r['game_id']][r['team_id']] = r
    acc = defaultdict(lambda: defaultdict(float))
    games = defaultdict(list)
    for gid, pair in by_game.items():
        if len(pair) != 2:
            continue
        (a, ra), (b, rb) = pair.items()
        for tid, me, opp in ((a, ra, rb), (b, rb, ra)):
            s = acc[tid]
            s['gp'] += 1
            s['w'] += int(me['win'])
            minutes = 48 + 5 * max(0, int(me['periods'] or 4) - 4)
            s['minutes'] += minutes
            for k in BOX + ('poss',):
                s[k] += num(me[k])
                s['opp_' + k] += num(opp[k])
            for q in ('q1', 'q2', 'q3', 'q4'):
                s[q] += num(me[q])
                s['opp_' + q] += num(opp[q])
            home = int(me['home'])
            s['home_w' if home else 'away_w'] += int(me['win'])
            s['home_gp' if home else 'away_gp'] += 1
            same_conf = teams.get(tid, {}).get('conf') == teams.get(opp['team_id'], {}).get('conf')
            if same_conf:
                s['conf_gp'] += 1
                s['conf_w'] += int(me['win'])
            games[tid].append((me['date_et'], gid, int(me['win']), int(num(me['pts'])), int(num(opp['pts'])),
                               opp['team_id'], home))
    league = defaultdict(float)
    for tid, s in acc.items():
        for k, v in s.items():
            league[k] += v
    out = {}
    for tid in teams:
        s = acc.get(tid, defaultdict(float))
        gp = s['gp']
        g = sorted(games.get(tid, []))
        last10 = g[-10:]
        streak = ''
        if g:
            kind, n = g[-1][2], 0
            for item in reversed(g):
                if item[2] != kind:
                    break
                n += 1
            streak = ('W' if kind else 'L') + str(n)
        poss_g = ratio((s['poss'] + s['opp_poss']) / 2, gp)
        out[tid] = {
            'gp': int(gp), 'w': int(s['w']), 'l': int(gp - s['w']),
            'home': [int(s['home_w']), int(s['home_gp'] - s['home_w'])],
            'away': [int(s['away_w']), int(s['away_gp'] - s['away_w'])],
            'conf_rec': [int(s['conf_w']), int(s['conf_gp'] - s['conf_w'])],
            'last10': [sum(x[2] for x in last10), len(last10) - sum(x[2] for x in last10)], 'streak': streak,
            'pts': ratio(s['pts'], gp), 'opp_pts': ratio(s['opp_pts'], gp),
            'ortg': ratio(100 * s['pts'], s['poss']), 'drtg': ratio(100 * s['opp_pts'], s['opp_poss']),
            'pace': ratio(48 * (s['poss'] + s['opp_poss']) / 2, s['minutes']) if s['minutes'] else None,
            'poss_g': poss_g,
            'efg': ratio(s['fgm'] + 0.5 * s['fg3m'], s['fga']), 'opp_efg': ratio(s['opp_fgm'] + 0.5 * s['opp_fg3m'], s['opp_fga']),
            'tov_pct': ratio(s['tov'], s['poss']), 'opp_tov_pct': ratio(s['opp_tov'], s['opp_poss']),
            'oreb_pct': ratio(s['oreb'], s['oreb'] + s['opp_dreb']), 'dreb_pct': ratio(s['dreb'], s['dreb'] + s['opp_oreb']),
            'ftr': ratio(s['fta'], s['fga']), 'opp_ftr': ratio(s['opp_fta'], s['opp_fga']),
            'fg3a_rate': ratio(s['fg3a'], s['fga']), 'fg3_pct': ratio(s['fg3m'], s['fg3a']), 'ft_pct': ratio(s['ftm'], s['fta']),
            'ast_rate': ratio(s['ast'], s['fgm']),
            'per_game': {k: ratio(s[k], gp) for k in BOX},
            'opp_per_game': {k: ratio(s['opp_' + k], gp) for k in BOX},
            'quarters': [ratio(s[q], gp) for q in ('q1', 'q2', 'q3', 'q4')],
            'opp_quarters': [ratio(s['opp_' + q], gp) for q in ('q1', 'q2', 'q3', 'q4')],
            'games': [{'date': d, 'game_id': gid, 'win': w, 'pts': p, 'opp_pts': o, 'opp': opp, 'home': h}
                      for d, gid, w, p, o, opp, h in g],
        }
        net = None if out[tid]['ortg'] is None or out[tid]['drtg'] is None else out[tid]['ortg'] - out[tid]['drtg']
        out[tid]['net'] = net
    qsum = sum(league[q] for q in ('q1', 'q2', 'q3', 'q4'))
    lg = {
        'teams_gp': int(league['gp']), 'games': int(league['gp'] // 2),
        'ortg': ratio(100 * league['pts'], league['poss']), 'pace': ratio(48 * league['poss'], league['minutes']),
        'pts': ratio(league['pts'], league['gp']), 'poss_g': ratio(league['poss'], league['gp']),
        'efg': ratio(league['fgm'] + 0.5 * league['fg3m'], league['fga']), 'tov_pct': ratio(league['tov'], league['poss']),
        'oreb_pct': ratio(league['oreb'], league['oreb'] + league['dreb']), 'ftr': ratio(league['fta'], league['fga']),
        'fg3a_rate': ratio(league['fg3a'], league['fga']), 'fg3_pct': ratio(league['fg3m'], league['fg3a']),
        'fg2_pct': ratio(league['fgm'] - league['fg3m'], league['fga'] - league['fg3a']),
        'ft_pct': ratio(league['ftm'], league['fta']), 'ast_rate': ratio(league['ast'], league['fgm']),
        'quarter_share': [ratio(league[q], qsum) for q in ('q1', 'q2', 'q3', 'q4')],
        'home_margin': None, 'ot_rate': None,
        'per_game': {k: ratio(league[k], league['gp']) for k in BOX},
    }
    pairs = [p for p in by_game.values() if len(p) == 2]
    if pairs:
        margins, ots = [], 0
        for p in pairs:
            home = next(r for r in p.values() if int(r['home']))
            away = next(r for r in p.values() if not int(r['home']))
            margins.append(num(home['pts']) - num(away['pts']))
            ots += int(int(home['periods'] or 4) > 4)
        lg['home_margin'] = sum(margins) / len(margins)
        lg['ot_rate'] = ots / len(pairs)
    for key, rank_desc in (('ortg', True), ('drtg', False), ('net', True), ('pace', True)):
        ordered = sorted((t for t in out if out[t][key] is not None), key=lambda t: (-out[t][key] if rank_desc else out[t][key], t))
        for i, t in enumerate(ordered, 1):
            out[t].setdefault('ranks', {})[key] = i
    return out, lg


PERIOD_STATS = ('sec', 'pts', 'fgm', 'fga', 'fg3m', 'fg3a', 'ftm', 'fta', 'oreb', 'dreb', 'ast', 'stl', 'blk', 'tov', 'pf')


def period_profiles(period_rows: list[dict], player_rows: list[dict], day: str,
                    team_rows: list[dict] | None = None, blowout: int | None = None) -> tuple[dict, dict]:
    """Per-player sums by quarter (index 0-3) and overtime (4) from play-by-play, through the cutoff,
    plus league quarter-minute shares for starters and bench players (priors for shrinkage).

    With `blowout`, games whose margin after three quarters exceeds it are left out: the simulation
    applies its own blowout rotation, so profiles should describe competitive games."""
    skip = set()
    if blowout is not None and team_rows:
        by_game = defaultdict(list)
        for r in team_rows:
            if r['date_et'] < day and r['q3'] not in ('', None):
                by_game[r['game_id']].append(sum(num(r[q]) for q in ('q1', 'q2', 'q3')))
        skip = {g for g, v in by_game.items() if len(v) == 2 and abs(v[0] - v[1]) > blowout}
    starter = {(r['game_id'], r['player_id']): r['starter'] == '1' for r in player_rows if r['date_et'] < day}
    out = defaultdict(lambda: {k: [0.0] * 5 for k in PERIOD_STATS})
    games = defaultdict(set)
    role = {True: [0.0] * 4, False: [0.0] * 4}
    for r in period_rows:
        if r['date_et'] >= day or r['game_id'] in skip:
            continue
        k = min(int(r['period']), 5) - 1
        acc = out[r['player_id']]
        for stat in PERIOD_STATS:
            acc[stat][k] += num(r[stat])
        games[r['player_id']].add(r['game_id'])
        if k < 4:
            role[starter.get((r['game_id'], r['player_id']), False)][k] += num(r['sec'])
    priors = {('starter' if is_starter else 'bench'): [x / max(1e-9, sum(v)) for x in v] for is_starter, v in role.items()}
    for pid, acc in out.items():
        acc['games'] = len(games[pid])
    return dict(out), priors


def player_table(player_rows: list[dict], day: str) -> dict:
    """Season aggregates and game logs per player through the cutoff (dnp rows retained)."""
    rows = [r for r in player_rows if r['date_et'] < day]
    by_player = defaultdict(list)
    for r in rows:
        by_player[r['player_id']].append(r)
    team_games = defaultdict(set)
    for r in rows:
        team_games[r['team_id']].add((r['date_et'], r['game_id']))
    out = {}
    for pid, items in by_player.items():
        items.sort(key=lambda r: (r['date_et'], r['game_id']))
        played = [r for r in items if not int(r['dnp'])]
        tot = {k: sum(num(r[k]) for r in played) for k in BOX + ('min',)}
        tot['pm'] = sum(num(r['pm']) for r in played)
        gp = len(played)
        teams = list(dict.fromkeys(r['team_id'] for r in items))
        last = items[-1]
        # Minutes trend over games played: half-life of four appearances.
        ewma, weight = 0.0, 0.0
        for i, r in enumerate(reversed(played)):
            w = 0.5 ** (i / 4)
            ewma += w * num(r['min'])
            weight += w
        current_team = last['team_id']
        recent_team_games = sorted(team_games[current_team])[-5:]
        recent_ids = {gid for _, gid in recent_team_games}
        mine = {r['game_id']: r for r in items if r['team_id'] == current_team}
        recent = [mine.get(gid) for _, gid in recent_team_games]
        out[pid] = {
            'gp': gp, 'gs': sum(int(r['starter']) for r in played), 'dnp': len(items) - gp,
            'teams': teams, 'team': current_team, 'name': last['name'], 'pos': last['pos'],
            'totals': {k: round(v, 1) for k, v in tot.items()},
            'min_ewma': round(ewma / weight, 2) if weight else None,
            'recent_played': sum(1 for r in recent if r and not int(r['dnp'])),
            'recent_started': sum(1 for r in recent if r and int(r['starter']) and not int(r['dnp'])),
            'recent_window': len(recent_ids),
            'last_played': played[-1]['date_et'] if played else None,
            'log': [{'date': r['date_et'], 'game_id': r['game_id'], 'team': r['team_id'], 'opp': r['opp_id'],
                     'home': int(r['home']), 'starter': int(r['starter']), 'dnp': int(r['dnp']),
                     'reason': r['dnp_reason'], **({k: int(num(r[k])) for k in BOX + ('min', 'pm')} if not int(r['dnp']) else {})}
                    for r in items],
        }
    return out
