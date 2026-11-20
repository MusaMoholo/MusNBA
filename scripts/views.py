#!/usr/bin/env python3
"""Build API-ready presentation views in data/views/api from retained snapshots and data.

Views never fetch, fit or simulate. They join the immutable snapshots (pre-game projections)
with the latest master fixtures and box scores (results). serve.py and the PWA bundle serve
exactly these files, so laptop and phone always show the same responses.
"""
from __future__ import annotations

import shutil
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import (APP_NAME, DERIVED, SEASON_LABEL, SNAPSHOTS, VIEWS, read_json, utc_now,  # noqa: E402
                               write_json)
from scripts import box_scores, master_fixtures, pbp  # noqa: E402
from scripts.season_stats import period_profiles  # noqa: E402

TEAM_FIELDS = ('gp', 'w', 'l', 'home', 'away', 'conf_rec', 'last10', 'streak', 'pts', 'opp_pts', 'ortg', 'drtg', 'net',
               'pace', 'efg', 'opp_efg', 'tov_pct', 'opp_tov_pct', 'oreb_pct', 'dreb_pct', 'ftr', 'opp_ftr',
               'fg3a_rate', 'fg3_pct', 'ft_pct', 'ast_rate', 'quarters', 'opp_quarters', 'ranks', 'per_game')
BOX_TOTALS = ('min', 'pts', 'fgm', 'fga', 'fg3m', 'fg3a', 'ftm', 'fta', 'oreb', 'dreb', 'reb', 'ast', 'stl', 'blk',
              'tov', 'pf', 'pm')
PERIOD_BOX = ('sec', 'pts', 'fgm', 'fga', 'fg3m', 'fg3a', 'ftm', 'fta', 'oreb', 'dreb', 'ast', 'stl', 'blk', 'tov', 'pf')
SLICES = {'q1': [1], 'q2': [2], 'q3': [3], 'q4': [4], 'h1': [1, 2], 'h2': [3, 4]}


def period_lines(rows):
    """Actual per-period lines for one player from play-by-play rows (FG comes from the box score)."""
    by = {int(r['period']): r for r in rows}
    out = {}
    for name, periods in SLICES.items():
        line = {k: 0.0 for k in PERIOD_BOX}
        for q in periods:
            for k in PERIOD_BOX:
                line[k] += float(by[q][k]) if q in by else 0.0
        line = {k: (round(v, 1) if k == 'sec' else int(v)) for k, v in line.items()}
        line['reb'] = line['oreb'] + line['dreb']
        out[name] = line
    out['fg_sec'] = round(sum(float(r['sec']) for r in rows), 1)
    return out


def rounded(value, digits=4):
    if isinstance(value, float):
        return round(value, digits)
    if isinstance(value, dict):
        return {k: rounded(v, digits) for k, v in value.items()}
    if isinstance(value, list):
        return [rounded(v, digits) for v in value]
    return value


def load_snapshots() -> dict:
    out = {}
    if SNAPSHOTS.exists():
        for folder in sorted(p for p in SNAPSHOTS.iterdir() if p.is_dir() and not p.name.startswith('.')):
            if (folder / 'meta.json').exists():
                out[folder.name] = {'meta': read_json(folder / 'meta.json'), 'path': folder}
    return out


def team_slice(T: dict, tid: str) -> dict:
    # Snapshots before 19 Nov 2026 stored the conference record as 'conf'.
    row = {k: T[tid].get(k) for k in TEAM_FIELDS}
    if row['conf_rec'] is None and isinstance(T[tid].get('conf'), list):
        row['conf_rec'] = T[tid]['conf']
    return rounded(row)


def current_snapshot(days) -> str:
    """The snapshot the app treats as current: the newest dated today (ET) or earlier — tomorrow's slate is projected a
    day ahead (D24) without becoming the as-of date for standings, rosters and team schedules."""
    from basketball_common import today_et
    days = sorted(days)
    past = [d for d in days if d <= today_et()]
    return past[-1] if past else days[-1]


WORLD_STATS = ('min', 'pts', 'reb', 'ast', 'fg3m', 'stl', 'blk', 'tov', 'fgm', 'fga', 'fg3a', 'fta')  # nightly.project_slate's order
AVG_STATS = ('min', 'pts', 'reb', 'ast', 'fg3m', 'stl', 'blk', 'tov')


def averages(P: dict, pids) -> dict:
    """Season and last-10 per-game averages (games played) as of the projection's cutoff (its stats.json)."""
    out = {}
    for pid in pids:
        x = P.get(pid)
        if not x or not x.get('gp'):
            continue
        played = [g for g in x.get('log', []) if not g.get('dnp')]
        last = played[-10:]
        out[pid] = {'gp': x['gp'], 'season': {k: round(x['totals'].get(k, 0) / x['gp'], 2) for k in AVG_STATS},
                    'last10': {k: round(sum(g.get(k, 0) or 0 for g in last) / len(last), 2) for k in AVG_STATS} if last else None,
                    'last10_n': len(last)}
    return out


def world_lines(path: Path, gid: str, sims: int) -> dict | None:
    """One game's stored per-world player lines and team points, packed for the app (base64 uint8, row-major worlds ×
    players × stats). The app only slices these worlds (conditional and joint outcomes); nothing is simulated here."""
    import base64
    import numpy as np
    pl, tm = path / 'engine_players.npz', path / 'engine_worlds.npz'
    if not pl.exists() or not tm.exists():
        return None
    with np.load(pl) as z, np.load(tm) as t:
        if f'{gid}__lines' not in z.files or gid not in t.files:
            return None
        lines, ids, side = z[f'{gid}__lines'], z[f'{gid}__ids'], z[f'{gid}__side']
        per = t[gid]  # (worlds, home/away, Q1–Q4 + OT)
    stats = list(WORLD_STATS)[:lines.shape[2]]
    return {'worlds': int(lines.shape[0]), 'stats': stats, 'players': [str(x) for x in ids], 'side': side.astype(int).tolist(),
            'lines': base64.b64encode(np.ascontiguousarray(lines).tobytes()).decode(),
            # team points per world and period: worlds × (home, away) × (Q1, Q2, Q3, Q4, OT), uint8
            'team_periods': base64.b64encode(np.clip(per, 0, 255).astype(np.uint8).tobytes()).decode(), 'periods': ['q1', 'q2', 'q3', 'q4', 'ot']}


def lab(serving: dict) -> dict:
    """Forecast Lab (PLAN phase 3): the engine's trust tests as logged — every M9 backtest run (player tiers first, D28;
    then strength loading, margins and game CRPS v the team-rating model), the minutes allocator check and the nightly
    record of projected v actual starters. Read from analysis/experiments and data/derived only (serving never computes)."""
    from scripts.evaluate import EXPERIMENTS
    runs = []
    for path in sorted(EXPERIMENTS.glob('*_backtest_*.json')):
        r = read_json(path)
        if r.get('experiment') != 'm9_engine_backtest' or 'summary' not in r:
            continue
        sm, t = r['summary'], r['summary'].get('team_rating_baseline', {})
        runs.append({'run': path.stem, 'stamp': r['run'], 'config': Path(r.get('config', '')).stem, 'fold': r.get('fold'),
                     'rotation': r.get('rotation', 'replay'), 'known_starters': bool(r.get('known_starters')), 'games': r.get('games'),
                     'worlds': r.get('worlds'),
                     'players': {tier: {k: {m: v[k][m] for m in ('actual', 'sim', 'rel_bias', 'coverage_10_90', 'crps')}
                                        for k in ('min', 'pts', 'reb', 'ast') if k in v} | {'n': v.get('player_games')}
                                 for tier, v in sm.get('players', {}).items()},
                     'strength': t.get('strength_loading'), 'margin': {k: sm['margin'].get(k) for k in ('slope_real_on_sim', 'corr', 'crps', 'bias', 'coverage_10_90')},
                     'total': {k: sm['total'].get(k) for k in ('bias', 'crps', 'coverage_10_90', 'sim_sd', 'actual_sd_around_sim')},
                     'win_log_loss': sm['win']['log_loss'], 'possessions_bias': sm['possessions_per_team']['bias_pct'],
                     'team_model': {'margin_crps': t.get('margin', {}).get('crps'), 'total_crps': t.get('total', {}).get('crps'),
                                    'win_log_loss': t.get('win', {}).get('log_loss')}})
    alloc = sorted(EXPERIMENTS.glob('*_minutes_alloc_*.json'))
    lineups = DERIVED / 'lineups' / 'accuracy.json'
    lin = read_json(lineups) if lineups.exists() else None
    return {'serving': {k: serving.get(k) for k in ('id', 'version', 'label')}, 'backtests': runs,
            'minutes_allocator': (lambda a: {'run': alloc[-1].stem, **{t: a[t] for t in ('star', 'starter', 'bench') if t in a}})(read_json(alloc[-1])) if alloc else None,
            'lineups': ({'overall': lin.get('overall'), 'slates': [{k: v for k, v in x.items() if k != 'misses'} for x in lin['slates'].values()]} if lin else None)}


def build(views_root: Path = VIEWS) -> dict:
    teams = read_json(DERIVED / 'teams.json')
    registry = read_json(DERIVED / 'players.json')['players']
    master = master_fixtures.load()
    by_id = {r['game_id']: r for r in master}
    team_rows = box_scores.load_csv('team_games.csv')
    player_rows = box_scores.load_csv('player_games.csv')
    snaps = load_snapshots()
    if not snaps:
        raise SystemExit('No snapshots yet: run scripts/nightly.py')
    latest_day = current_snapshot(snaps)
    latest = snaps[latest_day]
    L = read_json(latest['path'] / 'stats.json')
    season_latest = read_json(latest['path'] / 'season.json')
    team_model = {g['game_id']: g for g in season_latest['games']}

    # Records before each game: a running tally over results in tip order.
    record = defaultdict(lambda: [0, 0])
    before = {}
    for r in sorted(master, key=lambda r: (r['tip_utc'], r['game_id'])):
        before[r['game_id']] = {r['away_id']: list(record[r['away_id']]), r['home_id']: list(record[r['home_id']])}
        if r['status'] == 'final' and r['home_pts'] and r['away_pts']:
            hw = int(r['home_pts']) > int(r['away_pts'])
            record[r['home_id']][0 if hw else 1] += 1
            record[r['away_id']][1 if hw else 0] += 1
    current = {t: list(record[t]) for t in teams}

    box_by_game = defaultdict(lambda: defaultdict(list))
    for r in player_rows:
        box_by_game[r['game_id']][r['team_id']].append(r)
    team_box = defaultdict(dict)
    for r in team_rows:
        team_box[r['game_id']][r['team_id']] = r
    period_rows = pbp.load()
    pbp_by_game = defaultdict(lambda: defaultdict(list))
    for r in period_rows:
        pbp_by_game[r['game_id']][r['player_id']].append(r)

    out = views_root.with_name(views_root.name + '.partial')
    if out.exists():
        shutil.rmtree(out)
    api = out / 'api'

    def game_core(r):
        side = lambda s: {'id': r[s + '_id'], 'abbr': r[s + '_abbr'],
                          'score': int(r[s + '_pts']) if r[s + '_pts'] not in ('', None) and r['status'] in ('final', 'live') else None,
                          'record': before[r['game_id']][r[s + '_id']]}
        return {'id': r['game_id'], 'date': r['date_et'], 'tip_utc': r['tip_utc'], 'time_valid': bool(int(r['time_valid'])),
                'status': r['status'], 'detail': r['status_detail'], 'tv': [x for x in r['tv'].split('|') if x],
                'venue': r['venue'], 'city': r['city'], 'neutral': bool(int(r['neutral'])),
                'notes': [x for x in r['notes'].split('|') if x], 'periods': int(r['periods']) if r['periods'] else None,
                'away': side('away'), 'home': side('home')}

    # Snapshot projections, loaded once.
    projections = {}
    for day, snap in snaps.items():
        games = read_json(snap['path'] / 'games.json')
        for gid, sim in games.items():
            projections[gid] = {'day': day, 'meta': snap['meta'], 'sim': sim}

    def proj_summary(gid):
        p = projections.get(gid)
        if not p:
            return None
        fg = p['sim']['periods']['fg']
        return {'snapshot': p['day'], 'kind': p['meta']['kind'], 'pre_tip': p['meta']['pre_tip'].get(gid),
                'p_home': fg['home']['win'], 'p_away': fg['away']['win'],
                'mu_home': fg['home']['pts']['mean'], 'mu_away': fg['away']['pts']['mean'],
                'total': fg['total']['mean'], 'margin_mean': fg['margin']['mean'], 'margin_median': fg['margin']['q'][2],
                'ot': p['sim']['ot'],
                # projected top performers for the slate card: each side's top scorer (pts, reb, ast means over all worlds)
                'leaders': {side: [{'id': x['id'], 'name': x['name'], 'pts': x['periods']['fg']['mean']['pts'],
                                    'reb': x['periods']['fg']['mean']['oreb'] + x['periods']['fg']['mean']['dreb'],
                                    'ast': x['periods']['fg']['mean']['ast']}
                                   for x in sorted((y for y in p['sim'][side]['players'] if y.get('periods')),
                                                   key=lambda y: -y['periods']['fg']['mean']['pts'])[:1]] for side in ('away', 'home')}}

    slate_dates = sorted({r['date_et'] for r in master} | set(snaps))
    by_date = defaultdict(list)
    for r in master:
        by_date[r['date_et']].append(r)
    for day in slate_dates:
        snap = snaps.get(day)
        games = []
        for r in sorted(by_date.get(day, []), key=lambda r: (r['tip_utc'], r['game_id'])):
            g = game_core(r)
            g['proj'] = proj_summary(r['game_id'])
            tm = team_model.get(r['game_id'])
            g['team_model'] = ({'p_home': tm['p_home'], 'mu_home': tm.get('mu_home'), 'mu_away': tm.get('mu_away'),
                                'snapshot': latest_day} if tm and not g['proj'] else None)
            games.append(g)
        write_json(api / 'slate' / f'{day}.json', {
            'date': day, 'snapshot': day if snap else None,
            'kind': snap['meta']['kind'] if snap else None,
            'generated': snap['meta']['generated'] if snap else None,
            'model': snap['meta']['model'] if snap else None, 'games': games})

    stats_cache = {latest_day: L}
    for r in master:
        gid = r['game_id']
        core = game_core(r)
        p = projections.get(gid)
        as_of = p['day'] if p else latest_day
        if as_of not in stats_cache:
            stats_cache[as_of] = read_json(snaps[as_of]['path'] / 'stats.json')
        stats_source = stats_cache[as_of]
        comparison = {s: {**team_slice(stats_source['teams'], r[s + '_id']),
                          'league': rounded({k: stats_source['league'].get(k) for k in ('ortg', 'pace', 'efg', 'tov_pct', 'oreb_pct', 'ftr', 'fg3a_rate', 'pts')})}
                      for s in ('away', 'home')}
        actual = None
        if r['status'] == 'final' and gid in box_by_game:
            actual = {}
            for s in ('away', 'home'):
                tid = r[s + '_id']
                rows = box_by_game[gid][tid]
                tb = team_box[gid].get(tid, {})
                actual[s] = {
                    'linescores': [int(tb[q]) for q in ('q1', 'q2', 'q3', 'q4') if tb.get(q) not in (None, '')]
                                  + ([int(tb['ot'])] if tb.get('ot') not in (None, '', '0') else []),
                    'players': [{'id': x['player_id'], 'name': x['name'], 'pos': x['pos'], 'starter': bool(int(x['starter'])),
                                 'dnp': bool(int(x['dnp'])), 'reason': x['dnp_reason'],
                                 **({k: int(x[k]) for k in BOX_TOTALS if x[k] not in ('', None)} if not int(x['dnp']) else {}),
                                 **({'periods': period_lines(pbp_by_game[gid][x['player_id']])} if not int(x['dnp']) and pbp_by_game[gid].get(x['player_id']) else {})}
                                for x in rows],
                    'totals': {k: int(float(tb[k])) for k in ('pts', 'fgm', 'fga', 'fg3m', 'fg3a', 'ftm', 'fta', 'oreb', 'dreb', 'reb', 'ast', 'stl', 'blk', 'tov', 'pf') if tb.get(k) not in (None, '')},
                }
        tm = team_model.get(gid)
        avg = None
        if p:
            sim_ids = [x['id'] for side in ('home', 'away') for x in p['sim'][side]['players']]
            avg = averages(stats_source['players'], sim_ids)
            wl = world_lines(snaps[p['day']]['path'], gid, p['meta'].get('sims'))
            if wl is not None:
                write_json(api / 'game' / gid / 'worlds.json', wl)
        write_json(api / 'game' / f'{gid}.json', {
            'game': core,
            'projection': ({'snapshot': p['day'], 'kind': p['meta']['kind'], 'generated': p['meta']['generated'],
                            'pre_tip': p['meta']['pre_tip'].get(gid), 'model': p['meta']['model'], 'notes': p['meta']['notes'],
                            'cutoff': p['meta']['cutoff'], 'sim': p['sim']} if p else None),
            'team_model': ({'snapshot': latest_day, **tm} if tm and not p else None),
            'actual': actual, 'comparison': comparison, 'comparison_as_of': as_of, 'averages': avg,
            'worlds': bool(p and (api / 'game' / gid / 'worlds.json').exists())})

    for day, snap in snaps.items():
        stats = read_json(snap['path'] / 'stats.json')
        season = read_json(snap['path'] / 'season.json')
        rows = []
        for tid, info in teams.items():
            t = stats['teams'][tid]
            f = season['teams'][tid]
            rows.append({**info, **team_slice(stats['teams'], tid),
                         'pct': round(t['w'] / t['gp'], 4) if t['gp'] else None,
                         'forecast': {k: f[k] for k in ('remaining', 'scheduled', 'mean_w', 'mean_l', 'seed_mean', 'seeds', 'top6',
                                                        'playin', 'out', 'first', 'best_record', 'worst_record', 'wins')}})
        for conf in ('East', 'West'):
            group = [x for x in rows if x['conf'] == conf]
            lead = max(group, key=lambda x: (x['w'] - x['l']))
            for x in group:
                x['gb'] = ((lead['w'] - x['w']) + (x['l'] - lead['l'])) / 2
        write_json(api / 'standings' / f'{day}.json', {
            'date': day, 'kind': snap['meta']['kind'], 'generated': snap['meta']['generated'],
            'model': snap['meta']['model'], 'sims': season['sims'], 'notes': season['notes'],
            'season_model': ({'id': season['model'], 'kind': season['pathway'].get('kind'), 'label': season['pathway'].get('label'),
                              'as_of': season.get('as_of'), 'engine_games': len(season.get('engine_games', []))}
                             if season.get('pathway') else {'id': season['model'], 'kind': 'placeholder', 'label': snap['meta']['model'].get('label')}),
            'unresolved_before': len(season['unresolved_before']), 'teams': rows})

    P = L['players']
    Qall, _ = period_profiles(period_rows, player_rows, latest_day)
    roster_ids = defaultdict(list)
    for pid, reg in registry.items():
        if reg.get('on_roster'):
            roster_ids[reg['team']].append(pid)
    player_rows_out = []
    for pid, reg in registry.items():
        p = P.get(pid)
        if not p and not reg.get('on_roster'):
            continue
        player_rows_out.append({'id': pid, 'name': reg.get('name') or (p or {}).get('name'), 'team': reg.get('team') or (p or {}).get('team'),
                                'pos': reg.get('pos', ''), 'jersey': reg.get('jersey', ''), 'status': reg.get('status'),
                                'on_roster': bool(reg.get('on_roster')), 'gp': p['gp'] if p else 0, 'gs': p['gs'] if p else 0,
                                'tot': {k: p['totals'].get(k, 0) for k in BOX_TOTALS if k != 'pf' or True} if p else {}})
    player_rows_out.sort(key=lambda x: (-(x['tot'].get('pts', 0)), x['id']))
    write_json(api / 'players.json', {'date': latest_day, 'players': player_rows_out})

    upcoming = defaultdict(list)
    for r in sorted(master, key=lambda r: (r['tip_utc'], r['game_id'])):
        if r['date_et'] >= latest_day and r['status'] != 'final':
            for s in ('away', 'home'):
                upcoming[r[s + '_id']].append(r)

    for tid, info in teams.items():
        sched = []
        for r in sorted((r for r in master if tid in (r['home_id'], r['away_id'])), key=lambda r: (r['tip_utc'], r['game_id'])):
            home = r['home_id'] == tid
            opp = r['away_id'] if home else r['home_id']
            ps = proj_summary(r['game_id'])
            tm = team_model.get(r['game_id'])
            p_win = (ps['p_home'] if home else ps['p_away']) if ps else ((tm['p_home'] if home else 1 - tm['p_home']) if tm else None)
            mine, theirs = (r['home_pts'], r['away_pts']) if home else (r['away_pts'], r['home_pts'])
            sched.append({'game_id': r['game_id'], 'date': r['date_et'], 'tip_utc': r['tip_utc'], 'home': home, 'opp': opp,
                          'status': r['status'], 'pts': int(mine) if r['status'] == 'final' and mine else None,
                          'opp_pts': int(theirs) if r['status'] == 'final' and theirs else None,
                          'p_win': round(p_win, 4) if p_win is not None else None,
                          'p_source': 'game' if ps else ('team' if tm else None)})
        roster = []
        for pid in sorted(roster_ids.get(tid, []), key=lambda x: -(P.get(x, {}).get('totals', {}).get('min', 0))):
            reg, p = registry[pid], P.get(pid)
            roster.append({'id': pid, 'name': reg.get('name'), 'pos': reg.get('pos'), 'jersey': reg.get('jersey'),
                           'age': reg.get('age'), 'height': reg.get('height'), 'status': reg.get('status'), 'injury': reg.get('injury'),
                           'gp': p['gp'] if p else 0, 'gs': p['gs'] if p else 0,
                           'tot': {k: p['totals'].get(k, 0) for k in BOX_TOTALS} if p else {}})
        f = season_latest['teams'][tid]
        write_json(api / 'team' / f'{tid}.json', {
            'date': latest_day, 'team': info, 'record': current[tid], 'stats': team_slice(L['teams'], tid),
            'league': rounded({k: L['league'].get(k) for k in ('ortg', 'pace', 'efg', 'tov_pct', 'oreb_pct', 'ftr', 'fg3a_rate', 'pts')}),
            'forecast': {k: f[k] for k in ('remaining', 'scheduled', 'mean_w', 'mean_l', 'seed_mean', 'seeds', 'top6', 'playin',
                                           'out', 'first', 'best_record', 'wins')},
            'roster': roster, 'schedule': sched, 'model': season_latest['model']})

    latest_games = read_json(latest['path'] / 'games.json')
    for pid, reg in registry.items():
        p = P.get(pid)
        if not p and not reg.get('on_roster'):
            continue
        tid = reg.get('team') or (p or {}).get('team')
        nxt = upcoming.get(tid, [None])[0] if tid else None
        nxt_out = None
        if nxt:
            sim = latest_games.get(nxt['game_id'])
            stats = None
            if sim:
                side = 'home' if sim['home']['team_id'] == tid else 'away'
                me = next((x for x in sim[side]['players'] if x['id'] == pid), None)
                if me and me.get('periods'):
                    stats = {k: {'mean': v['mean'], 'q': v['q']} for k, v in me['periods']['fg']['stats'].items() if k in ('min', 'pts', 'reb', 'ast', 'fg3m', 'pra')}
                    stats['played'] = me['played']
            home = nxt['home_id'] == tid
            nxt_out = {'game_id': nxt['game_id'], 'date': nxt['date_et'], 'tip_utc': nxt['tip_utc'], 'home': home,
                       'opp': nxt['away_id'] if home else nxt['home_id'], 'projection': stats}
        write_json(api / 'player' / f'{pid}.json', {
            'date': latest_day, 'player': {k: reg.get(k) for k in ('id', 'name', 'short', 'pos', 'jersey', 'team', 'age', 'height',
                                                                    'weight', 'experience', 'status', 'injury', 'on_roster')},
            'season': ({'gp': p['gp'], 'gs': p['gs'], 'dnp': p['dnp'], 'teams': p['teams'], 'tot': p['totals'],
                        'min_ewma': p['min_ewma']} if p else None),
            'log': p['log'] if p else [], 'next': nxt_out,
            'quarters': ([{k: round(Qall[pid][k][q], 1) for k in PERIOD_BOX} | {'games': Qall[pid]['games']} for q in range(4)]
                         if pid in Qall else None)})

    write_json(api / 'lab.json', lab(latest['meta']['model']))

    snapshot_rows = [{'date': d, 'kind': s['meta']['kind'], 'cutoff': s['meta']['cutoff'], 'generated': s['meta']['generated'],
                      'model': s['meta']['model']['id'], 'games': len(s['meta']['games'])} for d, s in sorted(snaps.items())]
    finals = [r for r in master if r['status'] == 'final']
    write_json(api / 'meta.json', {
        'app': APP_NAME, 'season': SEASON_LABEL, 'built': utc_now(), 'latest': latest_day,
        'snapshots': snapshot_rows, 'first_date': slate_dates[0], 'last_date': slate_dates[-1],
        'dates': {d: len(by_date.get(d, [])) for d in slate_dates},
        'teams': teams, 'model': latest['meta']['model'],
        'data': {'finals': len(finals), 'last_final': max((r['date_et'] for r in finals), default=None),
                 'games': len(master), 'collected_run': registry and read_json(DERIVED / 'players.json')['run']}})

    if views_root.exists():
        shutil.rmtree(views_root)
    out.rename(views_root)
    count = sum(1 for _ in views_root.rglob('*.json'))
    print(f'views: {count} files -> {views_root}', flush=True)
    return {'files': count, 'latest': latest_day}


if __name__ == '__main__':
    build()
