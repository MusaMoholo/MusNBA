#!/usr/bin/env python3
"""One play schema for every source (ENGINE_PLAN.md M1).

A canonical game is a plain dict:
  id, date_et, season, season_type (2 regular, 3 playoffs, 5 play-in), home, away (team ids),
  players: [{id, team, name, pos, starter, dnp, reason, box: {min, pts, fgm, fga, fg3m, fg3a,
            ftm, fta, oreb, dreb, reb, ast, stl, blk, tov, pf, pm}}]
  plays:   [{seq, type_id, type_text, text, period, clock, team, participants, shooting, scoring,
            score_value, points_attempted, x, y, home_score, away_score}]

Adapters: `from_summary` (our retained ESPN game summaries) and `from_hoopr` (sportsdataverse season
files built from the same ESPN feed, so athlete and team ids match).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import slate_date  # noqa: E402

BOX_KEYS = ('min', 'pts', 'fgm', 'fga', 'fg3m', 'fg3a', 'ftm', 'fta', 'oreb', 'dreb', 'reb', 'ast', 'stl', 'blk',
            'tov', 'pf', 'pm')


def _num(value):
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(v) else v


def _coord(value):
    v = _num(value)
    return None if v is None or v < -1e6 else v  # ESPN uses -214748340 for "no location"


def _str(value) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ''
    return str(value)


def _id(value):
    v = _num(value)
    return None if v is None else str(int(v))


def infer_points_attempted(type_text: str, text: str, scoring: bool, score_value: int, x, y) -> int:
    """Points a shot was worth when the feed leaves it blank (most shots in 2022-23 and 2023-24).

    Free throws by type; made shots by points scored; misses by "three point" in the text, else by
    location (raw feed coordinates in feet with the basket at (25, 0): 22 ft in the corners within
    14 ft of the baseline, 23.75 ft on the arc). Validated where the field exists (history reports).
    """
    t, words = type_text.lower(), text.lower()
    if 'free throw' in t:
        return 1
    if scoring and score_value in (2, 3):
        return score_value
    if 'three point' in words or '3-pt' in words:
        return 3
    if x is not None and y is not None:
        dx = abs(x - 25)
        if (dx >= 21.8 and y <= 14) or (dx * dx + y * y) ** 0.5 >= 23.6:
            return 3
    return 2


# ---------------------------------------------------------------- ESPN summaries (live collection)

def from_summary(summary: dict) -> dict:
    from scripts.box_scores import parse_line
    c = summary['header']['competitions'][0]
    side = {t['homeAway']: t for t in c['competitors']}
    team_id = lambda t: t['team']['id'] if 'team' in t else t['id']
    players = []
    for block in summary['boxscore']['players']:
        tid = block['team']['id']
        group = block['statistics'][0]
        keys = group.get('keys') or []
        for a in group.get('athletes', []):
            ath = a['athlete']
            dnp = bool(a.get('didNotPlay')) or not a.get('stats')
            line = {} if dnp else parse_line(keys, a['stats'])
            if not dnp and line.get('min') in (None, 0) and not any((line.get(k) or 0) for k in ('pts', 'fga', 'reb', 'ast')):
                dnp = True
            players.append({'id': ath['id'], 'team': tid, 'name': ath.get('displayName', ''),
                            'pos': (ath.get('position') or {}).get('abbreviation', ''),
                            'starter': bool(a.get('starter')), 'dnp': dnp,
                            'reason': (a.get('reason') or '') if dnp else '', 'box': {} if dnp else line})
    plays = []
    for p in summary.get('plays') or []:
        coord = p.get('coordinate') or {}
        plays.append({
            'seq': int(p.get('sequenceNumber') or 0), 'type_id': str((p.get('type') or {}).get('id', '')),
            'type_text': (p.get('type') or {}).get('text') or '', 'text': p.get('text') or '',
            'period': int((p.get('period') or {}).get('number') or 0), 'clock': (p.get('clock') or {}).get('displayValue') or '0',
            'team': (p.get('team') or {}).get('id'),
            'participants': [x['athlete']['id'] for x in p.get('participants') or [] if (x.get('athlete') or {}).get('id')],
            'shooting': bool(p.get('shootingPlay')), 'scoring': bool(p.get('scoringPlay')),
            'score_value': int(p.get('scoreValue') or 0), 'points_attempted': int(p.get('pointsAttempted') or 0),
            'x': _coord(coord.get('x')), 'y': _coord(coord.get('y')),
            'home_score': p.get('homeScore'), 'away_score': p.get('awayScore'),
        })
    plays.sort(key=lambda p: p['seq'])
    season_type = ((summary.get('header') or {}).get('season') or {}).get('type')
    return {'id': c['id'], 'date_et': slate_date(c['date']), 'season': ((summary.get('header') or {}).get('season') or {}).get('year'),
            'season_type': int(season_type) if season_type else 2, 'home': team_id(side['home']), 'away': team_id(side['away']),
            'players': players, 'plays': plays, 'source': 'espn-summary'}


# ---------------------------------------------------------------- sportsdataverse / hoopR season files

HOOPR_BOX = {'minutes': 'min', 'points': 'pts', 'field_goals_made': 'fgm', 'field_goals_attempted': 'fga',
             'three_point_field_goals_made': 'fg3m', 'three_point_field_goals_attempted': 'fg3a',
             'free_throws_made': 'ftm', 'free_throws_attempted': 'fta', 'offensive_rebounds': 'oreb',
             'defensive_rebounds': 'dreb', 'rebounds': 'reb', 'assists': 'ast', 'steals': 'stl', 'blocks': 'blk',
             'turnovers': 'tov', 'fouls': 'pf', 'plus_minus': 'pm'}


def from_hoopr(game_id: str, plays_rows: list[dict], box_rows: list[dict]) -> dict:
    first = plays_rows[0]
    players = []
    for r in box_rows:
        if _id(r.get('athlete_id')) is None or _id(r.get('team_id')) is None:
            continue  # 2025-26 files carry one empty placeholder row in 33 games
        dnp = bool(r.get('did_not_play')) or _num(r.get('minutes')) in (None, 0.0)
        line = {} if dnp else {k: (None if _num(r.get(src)) is None else int(round(_num(r.get(src)))))
                               for src, k in HOOPR_BOX.items()}
        players.append({'id': _id(r['athlete_id']), 'team': _id(r['team_id']), 'name': _str(r.get('athlete_display_name')),
                        'pos': _str(r.get('athlete_position_abbreviation')), 'starter': bool(r.get('starter')),
                        'dnp': dnp, 'reason': _str(r.get('reason')) if dnp else '', 'box': line})
    plays = []
    inference = {'checked': 0, 'agree': 0, 'inferred': 0}
    for r in plays_rows:
        if bool(r.get('shooting_play')):
            guess = infer_points_attempted(_str(r.get('type_text')), _str(r.get('text')), bool(r.get('scoring_play')),
                                           int(_num(r.get('score_value')) or 0), _coord(r.get('coordinate_x_raw')), _coord(r.get('coordinate_y_raw')))
            given = _num(r.get('points_attempted'))
            if given:
                inference['checked'] += 1
                inference['agree'] += int(given) == guess
            else:
                inference['inferred'] += 1
                r = {**r, 'points_attempted': guess}
        plays.append({
            'seq': int(_num(r.get('sequence_number')) or 0), 'type_id': _id(r.get('type_id')) or '',
            'type_text': _str(r.get('type_text')), 'text': _str(r.get('text')),
            'period': int(_num(r.get('period_number')) or 0), 'clock': str(r.get('clock_display_value') or '0'),
            'team': _id(r.get('team_id')),
            'participants': [x for x in (_id(r.get('athlete_id_1')), _id(r.get('athlete_id_2')), _id(r.get('athlete_id_3'))) if x],
            'shooting': bool(r.get('shooting_play')), 'scoring': bool(r.get('scoring_play')),
            'score_value': int(_num(r.get('score_value')) or 0), 'points_attempted': int(_num(r.get('points_attempted')) or 0),
            'x': _coord(r.get('coordinate_x_raw')), 'y': _coord(r.get('coordinate_y_raw')),
            'home_score': r.get('home_score'), 'away_score': r.get('away_score'),
        })
    plays.sort(key=lambda p: p['seq'])
    return {'id': str(game_id), 'date_et': str(first.get('game_date'))[:10], 'season': int(_num(first.get('season')) or 0),
            'season_type': int(_num(first.get('season_type')) or 2), 'home': _id(first.get('home_team_id')),
            'away': _id(first.get('away_team_id')), 'players': players, 'plays': plays, 'source': 'hoopr',
            'points_attempted_inference': inference}
