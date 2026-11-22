#!/usr/bin/env python3
"""NBA Stats → our ESPN-keyed data (ENGINE_PLAN D32): crosswalk, reconciliation, real matchups.

Reads only the raw retention written by `fetch_nbastats.py` and our ESPN tables; never fetches.

* **Games** by ET date and home/away teams (NBA tricodes ↔ ESPN abbreviations).
* **Players** per matched game and team: normalised name, then first initial + surname, then a unique stat line
  (points, FGA, FGM, rebounds, assists, minutes); one ESPN id per NBA person by majority over his games. Every
  unmatched game and player is logged (`data/derived/nbastats/unmatched.json`).
* **Reconciliation** per player-game (points, minutes to the second v ESPN's box and our on-court seconds) and per
  team-game (NBA `POSS` v our segments' possessions) — `reconcile.json`, rates for FINDINGS.
* **Matchups** (`boxscorematchupsv3`): one row per game, attacker and defender — partial possessions, seconds, the
  attacker's points, FGM/FGA, threes, free throws, turnovers, assists while guarded by him, help blocks, switches —
  in ESPN ids (`matchups.parquet`).

  .venv/bin/python scripts/nbastats.py --crosswalk --reconcile --matchups
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DATA, DERIVED, NBA_TEAM_IDS, read_json, write_json  # noqa: E402
from scripts.fetch_nbastats import NBA_RAW, SEASON_TYPES, SEASONS, latest_log  # noqa: E402

OUT = DERIVED / 'nbastats'
ESPN_TO_NBA = {'NY': 'NYK', 'SA': 'SAS', 'GS': 'GSW', 'NO': 'NOP', 'UTAH': 'UTA', 'WSH': 'WAS'}
ESPN_SEASON = {'2022-23': 2023, '2023-24': 2024, '2024-25': 2025, '2025-26': 2026, '2026-27': 2027}
SUFFIX = re.compile(r'\b(jr|sr|ii|iii|iv|v)\b')


def norm(name: str) -> str:
    s = unicodedata.normalize('NFKD', str(name or '')).encode('ascii', 'ignore').decode().lower()
    s = re.sub(r"[.'`’-]", ' ', s)
    s = SUFFIX.sub(' ', s)
    return ' '.join(s.split())


def initial_surname(n: str) -> str:
    p = n.split()
    return f'{p[0][0]} {p[-1]}' if len(p) >= 2 else n


def tricode(espn_abbr: str) -> str:
    return ESPN_TO_NBA.get(espn_abbr, espn_abbr)


# ---------------------------------------------------------------- loading both sides

def nba_tables(seasons=SEASONS):
    """(team games, player games) from the newest retained season logs, every season type."""
    teams, players = [], []
    for season in seasons:
        for st in SEASON_TYPES:
            got = latest_log(season, st, 'teams_adv')
            if got and got[1]:
                t = pd.DataFrame(got[1], columns=got[0])
                t['season'], t['season_type_nba'] = season, st
                teams.append(t[['season', 'season_type_nba', 'GAME_ID', 'GAME_DATE', 'TEAM_ID', 'TEAM_ABBREVIATION', 'MATCHUP', 'MIN', 'POSS', 'PACE']])
            base, adv = latest_log(season, st, 'players_base'), latest_log(season, st, 'players_adv')
            if base and base[1]:
                b = pd.DataFrame(base[1], columns=base[0])
                b['season'], b['season_type_nba'] = season, st
                b = b[['season', 'season_type_nba', 'GAME_ID', 'GAME_DATE', 'PLAYER_ID', 'PLAYER_NAME', 'TEAM_ABBREVIATION', 'MIN',
                       'MIN_SEC', 'PTS', 'FGM', 'FGA', 'FG3M', 'FG3A', 'FTM', 'FTA', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'PF']]
                if adv and adv[1]:
                    a = pd.DataFrame(adv[1], columns=adv[0])[['GAME_ID', 'PLAYER_ID', 'POSS']]
                    b = b.merge(a, on=['GAME_ID', 'PLAYER_ID'], how='left')
                players.append(b)
    T = pd.concat(teams, ignore_index=True).drop_duplicates(['GAME_ID', 'TEAM_ID'])  # Cup games: Regular Season and IST
    T['date'] = T['GAME_DATE'].astype(str).str[:10]
    T['home'] = T['MATCHUP'].str.contains(' vs. ')
    P = pd.concat(players, ignore_index=True).drop_duplicates(['GAME_ID', 'PLAYER_ID'])
    P['date'] = P['GAME_DATE'].astype(str).str[:10]
    P['sec_nba'] = P['MIN_SEC'].map(_mmss)
    return T, P


def _mmss(v) -> float:
    try:
        m, s = str(v).split(':')
        return int(m) * 60 + int(s)
    except (ValueError, AttributeError):
        return np.nan


def espn_tables():
    """(games, player games) on the ESPN side: hoopR history boxes 2022-23 → 2025-26 plus our live 2026-27 boxes."""
    rows = []
    for f in sorted((DATA / 'raw' / 'hoopr').glob('player_box_*.parquet')):
        b = pd.read_parquet(f, columns=['game_id', 'season', 'season_type', 'game_date', 'athlete_id', 'athlete_display_name',
                                        'athlete_jersey', 'team_id', 'team_abbreviation', 'home_away', 'opponent_team_abbreviation',
                                        'minutes', 'points', 'field_goals_made', 'field_goals_attempted', 'rebounds', 'assists',
                                        'did_not_play'])
        b = b.rename(columns={'athlete_id': 'player', 'athlete_display_name': 'name', 'athlete_jersey': 'jersey',
                              'team_abbreviation': 'abbr', 'opponent_team_abbreviation': 'opp_abbr', 'minutes': 'min',
                              'points': 'pts', 'field_goals_made': 'fgm', 'field_goals_attempted': 'fga', 'rebounds': 'reb',
                              'assists': 'ast', 'game_date': 'date'})
        b['date'] = b['date'].astype(str)
        b['home'] = b['home_away'] == 'home'
        rows.append(b.drop(columns='home_away'))
    H = pd.concat(rows, ignore_index=True)
    H = H[H['team_id'].astype(str).isin(NBA_TEAM_IDS)]
    live = pd.read_csv(DERIVED / 'player_games.csv', dtype={'game_id': str, 'player_id': str})
    teams = read_json(DERIVED / 'teams.json')
    abbr = {k: v['abbr'] for k, v in teams.items()}
    L = pd.DataFrame({'game_id': live['game_id'], 'season': 2027, 'season_type': 2, 'date': live['date_et'], 'player': live['player_id'],
                      'name': live['name'], 'jersey': None, 'team_id': live['team_id'].astype(str), 'abbr': live['team_id'].astype(str).map(abbr),
                      'opp_abbr': live['opp_id'].astype(str).map(abbr), 'home': live['home'] == 1, 'min': live['min'], 'pts': live['pts'],
                      'fgm': live['fgm'], 'fga': live['fga'], 'reb': live['reb'], 'ast': live['ast'], 'did_not_play': live['dnp'] == 1})
    E = pd.concat([H, L], ignore_index=True)
    E['game_id'] = E['game_id'].astype(str)
    E['player'] = E['player'].astype(str).str.replace(r'\.0$', '', regex=True)
    E['team_id'] = E['team_id'].astype(str)
    return E


# ---------------------------------------------------------------- crosswalk

def crosswalk(T: pd.DataFrame, P: pd.DataFrame, E: pd.DataFrame) -> dict:
    out: dict = {}
    # games: ET date and the pair of teams (neutral-site games carry "@" on both sides in NBA logs; home from ESPN)
    ng = T.groupby('GAME_ID').agg(date=('date', 'first'), t1=('TEAM_ABBREVIATION', 'min'), t2=('TEAM_ABBREVIATION', 'max'),
                                  season=('season', 'first'), season_type_nba=('season_type_nba', 'first')).reset_index()
    eg = E.drop_duplicates(['game_id', 'home'])
    eh = eg[eg['home']][['game_id', 'date', 'abbr', 'team_id', 'season', 'season_type']].rename(
        columns={'abbr': 'home_abbr', 'team_id': 'home_team', 'season': 'espn_season', 'season_type': 'espn_type'})
    ea = eg[~eg['home']][['game_id', 'abbr', 'team_id']].rename(columns={'abbr': 'away_abbr', 'team_id': 'away_team'})
    egs = eh.merge(ea, on='game_id')
    egs['home_tc'], egs['away_tc'] = egs['home_abbr'].map(tricode), egs['away_abbr'].map(tricode)
    egs['t1'] = np.minimum(egs['home_tc'], egs['away_tc'])
    egs['t2'] = np.maximum(egs['home_tc'], egs['away_tc'])
    games = egs.merge(ng, on=['date', 't1', 't2'], how='outer', indicator=True)
    un_espn = games[games['_merge'] == 'left_only']
    un_nba = games[games['_merge'] == 'right_only']
    games = games[games['_merge'] == 'both'].drop(columns='_merge').rename(columns={'GAME_ID': 'nba_game', 'game_id': 'espn_game'})
    dup = games['espn_game'].duplicated(keep=False) | games['nba_game'].duplicated(keep=False)
    out['games'] = {'espn': int(egs['game_id'].nunique()), 'nba': int(ng['GAME_ID'].nunique()), 'matched': int(len(games)),
                    'duplicates': int(dup.sum()), 'espn_unmatched': int(len(un_espn)), 'nba_unmatched': int(len(un_nba))}
    unmatched = {'games_espn': un_espn[['game_id', 'date', 'home_abbr', 'away_abbr', 'espn_season', 'espn_type']].astype(str).to_dict('records'),
                 'games_nba': un_nba[['GAME_ID', 'date', 't1', 't2', 'season', 'season_type_nba']].astype(str).to_dict('records')}
    games = games[~dup]

    # players within matched games and teams
    gmap = dict(zip(games['nba_game'], games['espn_game']))
    p = P[P['GAME_ID'].isin(gmap)].copy()
    p['espn_game'] = p['GAME_ID'].map(gmap)
    p['n'] = p['PLAYER_NAME'].map(norm)
    p['tc'] = p['TEAM_ABBREVIATION']
    e = E[E['game_id'].isin(set(gmap.values()))].copy()  # every ESPN row on the team: seconds-long stints round to 0 min there
    e['n'] = e['name'].map(norm)
    e['tc'] = e['abbr'].map(tricode)
    e['key'] = e['espn_game'] = e['game_id']
    e['valid_player_id'] = e['player'].astype('string').str.fullmatch(r'\d+', na=False)
    stages = Counter()
    matches = []
    e_by = {k: g for k, g in e.groupby(['espn_game', 'tc'])}
    for (eg_, tc), grp in p.groupby(['espn_game', 'tc']):
        cand = e_by.get((eg_, tc))
        if cand is None:
            stages['no_espn_team'] += len(grp)
            continue
        left = cand.copy()
        rest = []
        for r in grp.itertuples(index=False):
            hit = left[left['valid_player_id'] & (left['n'] == r.n)]
            stage = 'name'
            if len(hit) != 1:
                hit = left[left['valid_player_id'] & (left['n'].map(initial_surname) == initial_surname(r.n))]
                stage = 'initial_surname'
            if len(hit) != 1:
                rest.append(r)
                continue
            matches.append((r.GAME_ID, r.PLAYER_ID, eg_, hit.iloc[0]['player'], stage))
            stages[stage] += 1
            left = left.drop(hit.index)
        for r in rest:
            hit = left[left['valid_player_id'] & (left['pts'] == r.PTS) & (left['fga'] == r.FGA) & (left['fgm'] == r.FGM) & (left['reb'] == r.REB) &
                       (left['ast'] == r.AST)]
            if len(hit) == 1:
                matches.append((r.GAME_ID, r.PLAYER_ID, eg_, hit.iloc[0]['player'], 'stat_line'))
                stages['stat_line'] += 1
                left = left.drop(hit.index)
            else:
                stages['unmatched'] += 1
                unmatched.setdefault('players', []).append({'nba_game': r.GAME_ID, 'espn_game': eg_, 'team': tc, 'person': int(r.PLAYER_ID),
                                                            'name': r.PLAYER_NAME, 'min_sec': str(r.MIN_SEC), 'pts': None if pd.isna(r.PTS) else int(r.PTS),
                                                            'espn_left': left[['player', 'name']].astype(str).to_dict('records')})
    m = pd.DataFrame(matches, columns=['nba_game', 'person', 'espn_game', 'player', 'stage'])
    # one ESPN id per NBA person (majority); conflicts logged
    votes = m.groupby(['person', 'player']).size().rename('n').reset_index().sort_values(['person', 'n'], ascending=[True, False])
    conflicts = votes[votes['person'].duplicated(keep=False)]
    best = votes.drop_duplicates('person')
    rev = best[best['player'].duplicated(keep=False)]
    people = best.merge(p.drop_duplicates('PLAYER_ID')[['PLAYER_ID', 'PLAYER_NAME']].rename(columns={'PLAYER_ID': 'person'}), on='person', how='left')
    out['players'] = {'nba_player_games': int(len(p)), 'matched_player_games': int(len(m)), 'stages': dict(stages),
                      'match_rate': round(len(m) / max(len(p), 1), 5), 'people': int(len(best)),
                      'people_with_conflicting_ids': int(conflicts['person'].nunique()),
                      'espn_ids_shared_by_two_people': int(rev['player'].nunique()),
                      'espn_played_unmatched': int(len(e[(e['min'].fillna(0) > 0)].merge(m[['espn_game', 'player']], left_on=['game_id', 'player'],
                                                                                          right_on=['espn_game', 'player'], how='left', indicator=True)
                                                        .query('_merge == "left_only"')))}
    unmatched['person_conflicts'] = conflicts.astype(str).to_dict('records')[:200]
    unmatched['espn_id_shared'] = rev.astype(str).to_dict('records')
    OUT.mkdir(parents=True, exist_ok=True)
    games.to_parquet(OUT / 'games.parquet', index=False)
    people[['person', 'player', 'PLAYER_NAME', 'n']].rename(columns={'PLAYER_NAME': 'name', 'n': 'games'}).to_parquet(OUT / 'players.parquet', index=False)
    m.to_parquet(OUT / 'player_games_map.parquet', index=False)
    write_json(OUT / 'unmatched.json', _clean(unmatched), pretty=True)
    return out


def _clean(v):
    """JSON-safe copy: NaN → None (logs keep missing values missing)."""
    if isinstance(v, dict):
        return {k: _clean(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_clean(x) for x in v]
    if isinstance(v, float) and v != v:
        return None
    return v


# ---------------------------------------------------------------- reconciliation

def _on_court() -> pd.DataFrame:
    parts = []
    for f in sorted((DERIVED / 'history').glob('*/on_court.parquet')) + [DERIVED / 'rotations' / 'on_court.parquet']:
        if f.exists():
            parts.append(pd.read_parquet(f, columns=['game_id', 'player', 'sec']))
    o = pd.concat(parts, ignore_index=True)
    o['game_id'], o['player'] = o['game_id'].astype(str), o['player'].astype(str)
    return o.groupby(['game_id', 'player'], as_index=False)['sec'].sum()


def _segment_poss() -> pd.DataFrame:
    parts = []
    for f in sorted((DERIVED / 'history').glob('*/segments.parquet')) + [DERIVED / 'segments.parquet']:
        if f.exists():
            s = pd.read_parquet(f, columns=['game_id', 'offense', 'poss', 'game_ok'])
            parts.append(s.groupby(['game_id', 'offense']).agg(poss=('poss', 'nunique'), ok=('game_ok', 'all')).reset_index())
    s = pd.concat(parts, ignore_index=True)
    s['game_id'], s['offense'] = s['game_id'].astype(str), s['offense'].astype(str)
    return s


def reconcile(T: pd.DataFrame, P: pd.DataFrame, E: pd.DataFrame) -> dict:
    games = pd.read_parquet(OUT / 'games.parquet')
    m = pd.read_parquet(OUT / 'player_games_map.parquet')
    x = m.merge(P[['GAME_ID', 'PLAYER_ID', 'PTS', 'sec_nba', 'MIN', 'POSS', 'FGA', 'FTA', 'REB', 'AST', 'season']].rename(
        columns={'GAME_ID': 'nba_game', 'PLAYER_ID': 'person'}), on=['nba_game', 'person'])
    x = x.merge(E[['game_id', 'player', 'pts', 'min', 'fga', 'reb', 'ast']].rename(columns={'game_id': 'espn_game'}), on=['espn_game', 'player'], how='left')
    oc = _on_court().rename(columns={'game_id': 'espn_game'})
    x = x.merge(oc, on=['espn_game', 'player'], how='left')
    out: dict = {'player_games': int(len(x))}
    def rate(mask):
        return round(float(mask.mean()), 5)
    for season, g in [('all', x)] + list(x.groupby('season')):
        d = {'n': int(len(g)),
             'points_differ': rate(g['PTS'] != g['pts']),
             'fga_differ': rate(g['FGA'] != g['fga']),
             'rebounds_differ': rate(g['REB'] != g['reb']),
             'assists_differ': rate(g['AST'] != g['ast']),
             'box_minutes_differ_gt1': rate((g['MIN'] - g['min']).abs() > 1),
             'on_court_vs_nba_seconds_gt60': rate((g['sec'] - g['sec_nba']).abs() > 60),
             'on_court_vs_nba_seconds_gt30': rate((g['sec'] - g['sec_nba']).abs() > 30),
             'on_court_missing': rate(g['sec'].isna()),
             'on_court_minus_nba_seconds_mean': round(float((g['sec'] - g['sec_nba']).mean()), 2),
             'on_court_minus_nba_seconds_mad': round(float((g['sec'] - g['sec_nba']).abs().median()), 2)}
        out[str(season)] = d
    # team possessions: NBA POSS v our segments
    t = T[['GAME_ID', 'TEAM_ABBREVIATION', 'POSS', 'season']].rename(columns={'GAME_ID': 'nba_game'})
    t = t.merge(games[['nba_game', 'espn_game', 'home_tc', 'home_team', 'away_team']], on='nba_game')
    t['offense'] = np.where(t['TEAM_ABBREVIATION'] == t['home_tc'], t['home_team'], t['away_team'])
    t = t.merge(_segment_poss().rename(columns={'game_id': 'espn_game'}), on=['espn_game', 'offense'], how='left')
    tg = t[t['ok'] == True]  # noqa: E712
    out['team_possessions'] = {'team_games': int(len(t)), 'with_segments': int(t['poss'].notna().sum()), 'reconciled_games_only': int(len(tg)),
                               'nba_mean': round(float(tg['POSS'].mean()), 2), 'segments_mean': round(float(tg['poss'].mean()), 2),
                               'mean_diff': round(float((tg['poss'] - tg['POSS']).mean()), 2),
                               'abs_diff_gt2': rate((tg['poss'] - tg['POSS']).abs() > 2),
                               'abs_diff_gt5': rate((tg['poss'] - tg['POSS']).abs() > 5),
                               'corr': round(float(tg[['poss', 'POSS']].corr().iloc[0, 1]), 4)}
    worst = x.assign(d=(x['sec'] - x['sec_nba']).abs()).sort_values('d', ascending=False).head(25)
    out['worst_minutes'] = worst[['espn_game', 'player', 'sec', 'sec_nba', 'PTS', 'pts']].astype(str).to_dict('records')
    pts_off = x[x['PTS'] != x['pts']]
    out['points_mismatch_examples'] = pts_off[['espn_game', 'player', 'PTS', 'pts']].head(25).astype(str).to_dict('records')
    out = _clean(out)
    write_json(OUT / 'reconcile.json', out, pretty=True)
    return out


# ---------------------------------------------------------------- matchups

STAT = {'matchupMinutesSort': 'seconds', 'partialPossessions': 'pposs', 'playerPoints': 'pts', 'teamPoints': 'team_pts',
        'matchupAssists': 'ast', 'matchupTurnovers': 'tov', 'matchupBlocks': 'blk', 'matchupFieldGoalsMade': 'fgm',
        'matchupFieldGoalsAttempted': 'fga', 'matchupThreePointersMade': 'fg3m', 'matchupThreePointersAttempted': 'fg3a',
        'helpBlocks': 'help_blk', 'helpFieldGoalsMade': 'help_fgm', 'helpFieldGoalsAttempted': 'help_fga',
        'matchupFreeThrowsMade': 'ftm', 'matchupFreeThrowsAttempted': 'fta', 'shootingFouls': 'sfouls', 'switchesOn': 'switches'}


def matchup_rows(js: dict) -> list[dict]:
    b = js.get('boxScoreMatchups') or {}
    rows = []
    for side in ('homeTeam', 'awayTeam'):
        team = b.get(side) or {}
        for off in team.get('players') or []:
            for d in off.get('matchups') or []:
                s = d.get('statistics') or {}
                r = {'nba_game': b.get('gameId'), 'off_tc': team.get('teamTricode'), 'off_home': side == 'homeTeam',
                     'off_person': off.get('personId'), 'def_person': d.get('personId'),
                     'off_jersey': off.get('jerseyNum'), 'def_jersey': d.get('jerseyNum'),
                     'off_name': f"{off.get('firstName', '')} {off.get('familyName', '')}".strip(),
                     'def_name': f"{d.get('firstName', '')} {d.get('familyName', '')}".strip()}
                for k, v in STAT.items():
                    r[v] = s.get(k)
                rows.append(r)
    return rows


def build_matchups() -> dict:
    games = pd.read_parquet(OUT / 'games.parquet')
    people = pd.read_parquet(OUT / 'players.parquet')
    pmap = dict(zip(people['person'].astype(int), people['player'].astype(str)))
    gmap = dict(zip(games['nba_game'], games['espn_game']))
    rows, files, empty = [], 0, 0
    for season in SEASONS:
        folder = NBA_RAW / 'boxscorematchupsv3' / season
        for f in sorted(folder.glob('*.json.gz')):
            files += 1
            r = matchup_rows(json.loads(gzip.decompress(f.read_bytes())))
            if not r:
                empty += 1
            rows += r
    M = pd.DataFrame(rows)
    out = {'files': files, 'empty_games': empty, 'rows': int(len(M))}
    if M.empty:
        return out
    M['espn_game'] = M['nba_game'].map(gmap)
    M['off_player'] = M['off_person'].astype(int).map(pmap)
    M['def_player'] = M['def_person'].astype(int).map(pmap)
    unk = M[M['off_player'].isna() | M['def_player'].isna()]
    out['rows_game_unmatched'] = int(M['espn_game'].isna().sum())
    out['rows_person_unmatched'] = int(len(unk))
    out['pposs_person_unmatched_share'] = round(float(unk['pposs'].sum() / M['pposs'].sum()), 5)
    out['persons_unmatched'] = sorted({(int(p), n) for p, n in zip(unk['off_person'], unk['off_name']) if int(p) not in pmap} |
                                      {(int(p), n) for p, n in zip(unk['def_person'], unk['def_name']) if int(p) not in pmap})[:100]
    M = M.dropna(subset=['espn_game', 'off_player', 'def_player'])
    num = list(STAT.values())
    M[num] = M[num].astype(float)
    M.to_parquet(OUT / 'matchups.parquet', index=False)
    out['rows_kept'] = int(len(M))
    out['games_kept'] = int(M['espn_game'].nunique())
    return out


def reconcile_matchups(T: pd.DataFrame, E: pd.DataFrame) -> dict:
    """Matchups v the box: Σ partial possessions per team-game ≈ 5 × NBA possessions; Σ matched points / FGA per attacker
    v his box line (matchups count only what happened while a defender was matched)."""
    M = pd.read_parquet(OUT / 'matchups.parquet')
    games = pd.read_parquet(OUT / 'games.parquet')
    t = T[['GAME_ID', 'TEAM_ABBREVIATION', 'POSS']].rename(columns={'GAME_ID': 'nba_game', 'TEAM_ABBREVIATION': 'off_tc'})
    pp = M.groupby(['nba_game', 'off_tc'], as_index=False)['pposs'].sum().merge(t, on=['nba_game', 'off_tc'])
    a = M.groupby(['espn_game', 'off_player'], as_index=False)[['pts', 'fga', 'fg3a', 'fta', 'tov', 'seconds']].sum()
    e = E[['game_id', 'player', 'pts', 'fga']].rename(columns={'game_id': 'espn_game', 'player': 'off_player', 'pts': 'box_pts', 'fga': 'box_fga'})
    a = a.merge(e, on=['espn_game', 'off_player'], how='left')
    out = {'team_games': int(len(pp)), 'pposs_over_5poss_mean': round(float((pp['pposs'] / (5 * pp['POSS'])).mean()), 4),
           'pposs_over_5poss_p10_p90': [round(float(q), 4) for q in (pp['pposs'] / (5 * pp['POSS'])).quantile([0.1, 0.9])],
           'attacker_games': int(len(a)),
           'matched_points_share': round(float(a['pts'].sum() / a['box_pts'].sum()), 4),
           'matched_fga_share': round(float(a['fga'].sum() / a['box_fga'].sum()), 4),
           'fga_equal_share': round(float((a['fga'] == a['box_fga']).mean()), 4),
           'pairs_per_attacker_game': round(float(len(M) / max(len(a), 1)), 2),
           'top_defender_pposs_share': round(float(M.groupby(['espn_game', 'off_player'])['pposs'].max().sum() / M['pposs'].sum()), 4)}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--crosswalk', action='store_true')
    ap.add_argument('--reconcile', action='store_true')
    ap.add_argument('--matchups', action='store_true')
    args = ap.parse_args()
    T, P = nba_tables()
    E = espn_tables()
    rep = read_json(OUT / 'report.json') if (OUT / 'report.json').exists() else {}
    if args.crosswalk:
        rep['crosswalk'] = crosswalk(T, P, E)
        print(json.dumps(rep['crosswalk'], indent=1))
    if args.reconcile:
        r = reconcile(T, P, E)
        rep['reconcile'] = {k: v for k, v in r.items() if k not in ('worst_minutes', 'points_mismatch_examples')}
        print(json.dumps(rep['reconcile'], indent=1))
    if args.matchups:
        rep['matchups'] = build_matchups()
        if rep['matchups'].get('rows'):
            rep['matchups_reconcile'] = reconcile_matchups(T, E)
        print(json.dumps({k: rep[k] for k in ('matchups', 'matchups_reconcile') if k in rep}, indent=1, default=str))
    write_json(OUT / 'report.json', _clean(rep), pretty=True)


if __name__ == '__main__':
    main()
