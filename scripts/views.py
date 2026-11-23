#!/usr/bin/env python3
"""Build API-ready presentation views in data/views/api from retained snapshots and data.

Views never fetch, fit or simulate. They join immutable dated snapshots
with the latest master fixtures and box scores (results). serve.py and the PWA bundle serve
exactly these files, so laptop and phone always show the same responses.
"""
from __future__ import annotations

import argparse
import math
import shutil
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import (APP_NAME, DERIVED, LINEUP_TIMING_POLICY, SEASON_LABEL, SNAPSHOTS, VIEWS, forecast_meta, read_json,  # noqa: E402
                               today_et, utc_now, verified_pre_tip, write_json)
from scripts import box_scores, master_fixtures, pbp, player_worlds  # noqa: E402
from scripts.season_stats import period_profiles  # noqa: E402
from scripts.player_icons import catalogue as player_icons

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
        interrupted = sorted(SNAPSHOTS.glob('.*.previous'))
        if interrupted:
            raise ValueError(f'interrupted snapshot publication requires recovery or review: {interrupted[0]}')
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


def current_snapshot(snapshots: dict) -> str:
    """Use a same-origin snapshot, never a previous day's preview of a future slate."""
    days = sorted(d for d, snap in snapshots.items() if snap['meta'].get('origin', d) == d)
    past = [d for d in days if d <= today_et()]
    if not past:
        raise ValueError('no same-origin snapshot dated today or earlier')
    return past[-1]


def discarded_preview(day: str, meta: dict) -> bool:
    # D50 took effect on 22 November 2026; older retained reviews remain available.
    return day > '2026-11-22' and meta.get('origin', day) < day


def load_projections(snaps: dict, latest_day: str) -> dict:
    """Keep older historical forecasts, but never reactivate a discarded D50 preview."""
    projections = {}
    for day, snap in snaps.items():
        if day > latest_day or discarded_preview(day, snap['meta']):
            continue
        for gid, sim in read_json(snap['path'] / 'games.json').items():
            projections[gid] = {'day': day, 'meta': forecast_meta(snap['meta'], gid), 'sim': sim}
    return projections


WORLD_STATS = ('min', 'pts', 'reb', 'ast', 'fg3m', 'stl', 'blk', 'tov', 'fgm', 'fga', 'fg3a', 'fta', 'oreb', 'dreb', 'ftm')  # nightly.project_slate's order (older snapshots: first 12)
AVG_STATS = ('min', 'pts', 'reb', 'ast', 'fg3m', 'stl', 'blk', 'tov', 'fgm', 'fga', 'fg3a', 'ftm', 'fta')  # makes/attempts → season %


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


DUEL_STATS = ('pposs', 'pts', 'fgm', 'fga', 'fg3m', 'fg3a', 'ftm', 'fta', 'tov')


def load_matchups():
    """Real NBA matchups in ESPN ids with game dates (D32; data/derived/nbastats), or None before the first ingest."""
    path = DERIVED / 'nbastats' / 'matchups.parquet'
    if not path.exists():
        return None
    import pandas as pd
    M = pd.read_parquet(path, columns=['espn_game', 'off_player', 'def_player'] + list(DUEL_STATS))
    g = pd.read_parquet(DERIVED / 'nbastats' / 'games.parquet', columns=['espn_game', 'date'])
    M = M.merge(g, on='espn_game', how='left')
    for c in ('espn_game', 'off_player', 'def_player'):
        M[c] = M[c].astype(str)
    return M


def duels(M, gid: str, day: str, sides: dict, final: bool) -> dict | None:
    """Who guards whom (D32): per attacker, his top defenders among tonight's opponents in earlier meetings (games before
    `day` only, the last 365 days) — share of his partial possessions against these players, points, FG, meetings; and
    for a final, that game's real matchups. sides: {'home'|'away': [(id, name, pts)]} ordered by importance."""
    if M is None:
        return None
    from datetime import date, timedelta
    since = (date.fromisoformat(day) - timedelta(days=365)).isoformat()
    names = {str(i): n for s in sides.values() for i, n, _ in s}
    out = {'since': since, 'sides': {}}
    def top(frame, attacker):
        x = frame[frame['off_player'] == attacker]
        if x.empty:
            return []
        agg = x.groupby('def_player').agg(**{k: (k, 'sum') for k in DUEL_STATS}, meetings=('espn_game', 'nunique')).reset_index()
        tot = float(agg['pposs'].sum())
        agg = agg.sort_values('pposs', ascending=False).head(3)
        return [{'id': r.def_player, 'name': names.get(r.def_player, r.def_player), 'share': round(r.pposs / tot, 3) if tot else None,
                 **{k: (round(float(getattr(r, k)), 1) if k == 'pposs' else int(getattr(r, k))) for k in DUEL_STATS},
                 'meetings': int(r.meetings)} for r in agg.itertuples(index=False)]
    for att, dfn in (('away', 'home'), ('home', 'away')):
        a_ids = [str(i) for i, _, _ in sides.get(att, [])]
        d_ids = {str(i) for i, _, _ in sides.get(dfn, [])}
        sub = M[M['off_player'].isin(a_ids)]
        past = sub[(sub['date'] < day) & (sub['date'] >= since) & sub['def_player'].isin(d_ids)]
        now = sub[sub['espn_game'] == str(gid)] if final else None
        rows = []
        for i, n, pts in sides.get(att, []):
            r = {'id': str(i), 'name': n, 'past': top(past, str(i))}
            if now is not None:
                r['tonight'] = top(now, str(i))
            if r['past'] or r.get('tonight'):
                rows.append(r)
        out['sides'][att] = rows
    return out if any(out['sides'].values()) else None


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
        players = player_worlds.read_player_worlds(z, gid)
        lines, ids, side = players['lines'], players['ids'], players['side']
        per = t[gid]  # (worlds, home/away, Q1–Q4 + OT)
    branch_file = path / 'lineups' / gid / 'worlds.json'
    if branch_file.exists():
        return read_json(branch_file)
    stats = list(WORLD_STATS)[:lines.shape[2]]
    result = {'worlds': int(lines.shape[0]), 'stats': stats, 'players': [str(x) for x in ids], 'side': side.astype(int).tolist(),
              'lines': base64.b64encode(np.ascontiguousarray(lines).tobytes()).decode(),
              # team points per world and period: worlds × (home, away) × (Q1, Q2, Q3, Q4, OT), uint8
              'team_periods': base64.b64encode(np.clip(per, 0, 255).astype(np.uint8).tobytes()).decode(), 'periods': ['q1', 'q2', 'q3', 'q4', 'ot']}
    if 'minutes' in players:
        result['minutes_schema'] = int(players['minutes_schema'])
        result['period_minutes_f64_le'] = base64.b64encode(
            np.ascontiguousarray(players['minutes'], dtype='<f8').tobytes()).decode()
    return result


def minute_marginals(path: Path, gid: str) -> dict | None:
    """Sorted independent period distributions for the Expected-only phone bundle."""
    import base64
    import numpy as np
    from scripts.projection import SLICES

    with np.load(path / 'engine_players.npz', allow_pickle=False) as archive:
        players = player_worlds.read_player_worlds(archive, gid)
    if 'minutes' not in players:
        return None
    minutes = players['minutes']
    values = np.stack([np.sort(minutes[:, :, cols].sum(axis=2), axis=0)
                       for cols in SLICES.values()], axis=2)
    return {'schema': 1, 'worlds': int(minutes.shape[0]), 'players': [str(x) for x in players['ids']],
            'periods': list(SLICES),
            'minutes_f64_le': base64.b64encode(np.ascontiguousarray(values, dtype='<f8').tobytes()).decode()}


def advanced_world_summaries(values: dict, opponent: dict | None = None, weights=None) -> dict:
    """Distributions of per-world box-derived rates, conditional on a positive denominator."""
    import numpy as np
    from scripts.projection import summary

    def ratio(required, numerator, denominator):
        if any(k not in values for k in required):
            return None
        n, d = numerator(values), denominator(values)
        out = np.full(np.shape(d), np.nan, dtype=float)
        return np.divide(n, d, out=out, where=d > 0)

    metrics = {
        'efg': (ratio(('fgm', 'fg3m', 'fga'), lambda x: x['fgm'] + 0.5 * x['fg3m'], lambda x: x['fga']), True),
        'ts': (ratio(('pts', 'fga', 'fta'), lambda x: x['pts'], lambda x: 2 * (x['fga'] + 0.44 * x['fta'])), True),
        'two': (ratio(('fgm', 'fg3m', 'fga', 'fg3a'), lambda x: x['fgm'] - x['fg3m'],
                      lambda x: x['fga'] - x['fg3a']), True),
        'threeShare': (ratio(('fg3a', 'fga'), lambda x: x['fg3a'], lambda x: x['fga']), True),
        'ftRate': (ratio(('fta', 'fga'), lambda x: x['fta'], lambda x: x['fga']), True),
        'astTov': (ratio(('ast', 'tov'), lambda x: x['ast'], lambda x: x['tov']), False),
    }
    if opponent is not None:
        def possessions(box):
            return (box['fga'] - box['oreb'] + box['tov'] + 0.44 * box['fta']
                    if all(k in box for k in ('fga', 'oreb', 'tov', 'fta')) else None)

        own, opp = possessions(values), possessions(opponent)
        def divide(n, d):
            if n is None or d is None:
                return None
            return np.divide(n, d, out=np.full(np.shape(d), np.nan, dtype=float), where=d > 0)

        ortg = divide(values.get('pts'), own)
        drtg = divide(opponent.get('pts'), opp)
        def rebound(key, other):
            a, b = values.get(key), opponent.get(other)
            return divide(a, a + b) if a is not None and b is not None else None
        metrics.update({
            'poss': (own, False), 'ortg': (100 * ortg if ortg is not None else None, False),
            'drtg': (100 * drtg if drtg is not None else None, False),
            'net': (100 * (ortg - drtg) if ortg is not None and drtg is not None else None, False),
            'oreb': (rebound('oreb', 'dreb'), True), 'dreb': (rebound('dreb', 'oreb'), True),
            'assist': (divide(values.get('ast'), values.get('fgm')), True),
            'turnover': (divide(values.get('tov'), own), True), 'steals': (divide(values.get('stl'), opp), True),
        })
    out = {}
    for key, (raw, percent) in metrics.items():
        if raw is None:
            continue
        raw = np.asarray(raw, dtype=float)
        if raw.ndim != 1 or np.isinf(raw).any():
            raise ValueError(f'invalid per-world values for {key}')
        from scripts.world_mass import WorldMass
        mass = WorldMass(len(raw), weights)
        mask = np.isfinite(raw)
        defined = raw[mask] * (100 if percent else 1)
        result = {'defined': int(mask.sum()) if weights is None else int(weights[mask].sum()), 'total': mass.total}
        if defined.size:
            selected = mass.subset(mask)
            scale = 1 if percent else 10
            bins = np.floor(defined * scale + 0.5).astype(np.int64)
            order = np.argsort(defined, kind='stable')
            ordered = defined[order]
            cumulative = np.cumsum(np.ones(len(order), np.int64) if weights is None else weights[mask][order])
            result.update(selected.summary(bins, offset=True))
            result.update({'scale': scale, 'exact_mean': round(float(selected.mean(defined)), 3),
                           'exact_q': [round(float(ordered[np.searchsorted(cumulative * d, n * selected.total, side='left')]), 3)
                                       for n, d in ((1,10),(1,4),(1,2),(3,4),(9,10))]})
        out[key] = result
    return out


def from_worlds(path: Path, gid: str, sim: dict) -> dict | None:
    """From the stored worlds (nothing simulated): each player's double/triple/quadruple/quintuple-double and 5×5 chances, and
    full-game distributions the snapshot lacks (FGM, FTM = PTS − 2·FGM − 3PM; OREB/DREB when the worlds carry them) — written
    into the view's copy of the projection so the player sheet shows them for snapshots built before they were packaged."""
    import numpy as np
    from scripts.projection import shooting_summaries, summary
    pl = path / 'engine_players.npz'
    if not pl.exists():
        return None
    with np.load(pl) as z:
        if f'{gid}__lines' not in z.files:
            return None
        lines, ids = z[f'{gid}__lines'].astype(np.int64), [str(x) for x in z[f'{gid}__ids']]
        sides = z[f'{gid}__side']
        weights = z[f'{gid}__weights'] if f'{gid}__weights' in z else None
    from scripts.world_mass import WorldMass
    from scripts.forecast_output import shooting_summaries
    mass = WorldMass(len(lines), weights)
    summary = mass.summary
    stats = list(WORLD_STATS)[:lines.shape[2]]
    col = {k: lines[:, :, j] for j, k in enumerate(stats)}
    if 'ftm' not in col:
        col['ftm'] = np.clip(col['pts'] - 2 * col['fgm'] - col['fg3m'], 0, None)
    tens = sum((col[k] >= 10).astype(int) for k in ('pts', 'reb', 'ast', 'stl', 'blk'))
    multi = {}
    for side in ('home', 'away'):
        for x in sim[side]['players']:
            if str(x['id']) not in ids or not x.get('periods'):
                continue
            i = ids.index(str(x['id']))
            multi[str(x['id'])] = {k: round(float(mass.mean(tens[:, i] >= n)), 5) for k, n in (('double', 2), ('triple', 3), ('quadruple', 4), ('quintuple', 5))}
            multi[str(x['id'])]['five_by_five'] = round(float(mass.mean(np.all([col[k][:, i] >= 5 for k in ('pts', 'reb', 'ast', 'stl', 'blk')], axis=0))), 5)
            fg = x['periods']['fg']
            fg['advanced'] = advanced_world_summaries({k: v[:, i] for k, v in col.items()}, weights=weights)
            for k in ('fgm', 'ftm', 'oreb', 'dreb', 'fga', 'fg3a', 'fta'):
                if k not in fg['stats'] and k in col:
                    fg['stats'][k] = summary(col[k][:, i])
            shooting = shooting_summaries({k: v[:, i] for k, v in col.items()}, None if weights is None else mass)
            for k, v in shooting.items():
                if k not in fg['stats']:
                    fg['stats'][k] = v
    tm = path / 'engine_worlds.npz'
    if tm.exists() and all(k in col for k in ('pts', 'fgm', 'fga', 'fg3m', 'fg3a', 'fta', 'oreb', 'dreb', 'ast', 'tov', 'stl')):
        with np.load(tm) as worlds:
            if gid in worlds.files:
                points = worlds[gid].astype(np.int64).sum(axis=2)
                if sides.shape != (len(ids),) or points.shape != (lines.shape[0], 2) or not np.isin(sides, (0, 1)).all():
                    raise ValueError(f'invalid team world dimensions for {gid}')
                team_boxes = [{k: v[:, sides == side].sum(axis=1) for k, v in col.items()} for side in (0, 1)]
                for side in (0, 1):
                    if not np.array_equal(team_boxes[side]['pts'], points[:, side]):
                        raise ValueError(f'player and team world points differ for {gid}, side {side}')
                    team_boxes[side]['pts'] = points[:, side]
                for side, name in enumerate(('home', 'away')):
                    sim[name]['advanced'] = advanced_world_summaries(team_boxes[side], team_boxes[1 - side], weights)
    return multi


SPOT_STATS = ('pts', 'reb', 'ast', 'fg3m', 'stl', 'blk')  # the six leader cards (owner, 20 Nov)
FANTASY = {'pts': 1.0, 'reb': 1.2, 'ast': 1.5, 'stl': 3.0, 'blk': 3.0, 'tov': -1.0}  # NBA's standard fantasy weights (headliner)


_LINES_CACHE: dict = {}


def _game_lines(path: Path, gid: str):
    """(lines worlds × players × stats, ids) of one game's stored worlds, cached per run (views only read them)."""
    import numpy as np
    key = (str(path), gid)
    if key not in _LINES_CACHE:
        pl = path / 'engine_players.npz'
        out = None
        if pl.exists():
            with np.load(pl) as z:
                if f'{gid}__lines' in z.files:
                    lines = z[f'{gid}__lines']
                    weights = None
                    coupled = path / 'season_player_indices.npz'
                    if coupled.exists():
                        with np.load(coupled, allow_pickle=False) as layout:
                            lines, weights = lines[layout[gid]], layout['weights']
                    out = (lines, [str(x) for x in z[f'{gid}__ids']], weights)
        _LINES_CACHE[key] = out
    return _LINES_CACHE[key]


def lead_chances(path: Path, gids: list, stat: str, pids: list) -> dict:
    """Chance each of `pids` leads all players of `gids` in `stat` (ties split), pairing world k across games — games are
    independent simulations, so world k of each game together is one simulated night. Read from stored worlds only."""
    import numpy as np
    cols, ids = [], []
    for gid in gids:
        got = _game_lines(path, gid)
        if got is None:
            return {}
        lines, gids_ids, weights = got
        j = list(WORLD_STATS).index(stat)
        cols.append(lines[:, :, j].astype(float))
        ids += gids_ids
    W = min(c.shape[0] for c in cols)
    M = np.concatenate([c[:W] for c in cols], axis=1)
    top = M.max(1, keepdims=True)
    lead = (M == top)
    from scripts.world_mass import WorldMass
    share = WorldMass(W, weights).mean(lead / lead.sum(1, keepdims=True))
    pos = {p: i for i, p in enumerate(ids)}
    return {p: round(float(share[pos[p]]), 4) for p in pids if p in pos}


def spotlight(entries: list, season_of, path: Path | None = None) -> dict | None:
    """Headliner, breakout watch and the six stat leaders (top three each) over projected players — a slate or one game
    (owner, 20 Nov). entries: dicts with id, name, team, opp, home, game_id, tip_utc and the projection's full-game entry `x`;
    season_of(pid) → season per-game averages or None. Read from stored projections; nothing simulated."""
    rows = []
    for e in entries:
        fg = (e['x'].get('periods') or {}).get('fg')
        if not fg:
            continue
        m = dict(fg['mean'])
        m['min'] = fg['sec'] / 60
        rows.append({**{k: e[k] for k in ('id', 'name', 'team', 'opp', 'home', 'game_id', 'tip_utc')}, 'mean': m, 'stats': fg['stats'],
                     'played': e['x'].get('played', 1.0), 'season': season_of(e['id'])})
    if not rows:
        return None
    fp = lambda v: sum(w * (v.get(k) or 0) for k, w in FANTASY.items())
    def card(r, extra=None):
        return {k: r[k] for k in ('id', 'name', 'team', 'opp', 'home', 'game_id', 'tip_utc', 'played')} | {
            'mean': {k: round(r['mean'].get(k, 0) or 0, 2) for k in SPOT_STATS + ('min', 'tov')},
            'fp': round(fp(r['mean']), 1), **(extra or {})}
    def at_least(d, x):  # share of worlds with stat ≥ x from a stored {min, hist} distribution
        tot = sum(d['hist']) or 1
        return round(sum(c for i, c in enumerate(d['hist']) if i + d['min'] >= x) / tot, 4)
    head = max(rows, key=lambda r: fp(r['mean']))
    hp = head['stats'].get('pts')
    hx = next(e['x'] for e in entries if e['id'] == head['id'])
    head_extra = {}
    if hp:
        tot = sum(hp['hist']) or 1
        cum, lo_i, hi_i = 0, 0, len(hp['hist']) - 1
        for i, c in enumerate(hp['hist']):  # trim to the 1st–99th percentile for the sparkline
            cum += c
            if cum / tot < 0.01:
                lo_i = i + 1
            if cum / tot <= 0.99:
                hi_i = i + 1
        head_extra = {'spark': {'min': hp['min'] + lo_i, 'hist': hp['hist'][lo_i:hi_i + 1]},
                      'chances': {'pts30': at_least(hp, 30), 'pts40': at_least(hp, 40), 'dd': hx.get('double_double'), 'td': hx.get('triple_double')}}
    cands = [r for r in rows if r['season'] and r['season'].get('gp', 0) >= 8 and r['played'] >= 0.9 and r['mean']['min'] >= 18
             and r['id'] != head['id']]  # two cards, two people
    brk = None
    if cands:
        b = max(cands, key=lambda r: fp(r['mean']) - fp(r['season']['season']))
        sa = b['season']['season']
        dmin = b['mean']['min'] - (sa.get('min') or 0)
        # the why: more minutes (a role change, often a teammate out) or the same minutes at higher rates
        why = (f"more minutes: {b['mean']['min']:.1f} projected v {sa.get('min', 0):.1f} this season" if dmin >= 3 else
               f"fewer minutes ({dmin:+.1f}) but higher rates per minute" if dmin <= -3 else
               f"similar minutes ({dmin:+.1f}), higher rates per minute — tonight's matchup and lineup")
        brk = card(b, {'season': {k: round(sa.get(k, 0) or 0, 2) for k in SPOT_STATS + ('min', 'tov')}, 'fp_season': round(fp(sa), 1),
                       'gp': b['season']['gp'], 'why': why})
    leaders = {k: [{**{f: r[f] for f in ('id', 'name', 'team', 'game_id')}, 'value': round(r['mean'].get(k, 0) or 0, 2)}
                   for r in sorted(rows, key=lambda r: -(r['mean'].get(k, 0) or 0))[:3]] for k in SPOT_STATS}
    if path is not None:  # chance each leader tops the slate (or the game) in that stat, over paired worlds
        gids = sorted({r['game_id'] for r in rows})
        for k, top3 in leaders.items():
            ch = lead_chances(path, gids, k, [x['id'] for x in top3])
            for x in top3:
                x['lead'] = ch.get(x['id'])
    return {'headliner': card(head, head_extra), 'breakout': brk, 'leaders': leaders}


def role_changes(entries: list, season_of, limit: int = 10) -> list:
    """U3: players projected ≥ 4 minutes above or below their season average tonight, with the reason from the minutes
    model's own basis (D29: return ramp, availability, a short-handed roster's extra minutes, healthy role)."""
    out = []
    for e in entries:
        x = e['x']
        fg = (x.get('periods') or {}).get('fg')
        sa = season_of(e['id'])
        if not fg or not sa or sa.get('gp', 0) < 5:
            continue
        proj, avg = fg['sec'] / 60, (sa['season'].get('min') or 0)
        d = proj - avg
        if abs(d) < 4:
            continue
        mb = x.get('minutes_basis') or {}
        if d < 0 and (x.get('availability') or 1) < 0.999:
            why = f"{(x.get('status') or 'questionable').lower()} — plays in {round(100 * (x.get('played') or 0))}% of sims"
        elif d < 0 and mb.get('rotation', 1) < 0.9:
            why = f"in and out of the rotation: plays {round(100 * mb['rotation'])}% of the games he is available for"
        elif d < 0 and mb.get('k_back', 0) > 0 and mb.get('ramp', 1) < 0.995:
            why = f"returning: game {mb['k_back']} back after {mb.get('missed', 0)} missed (×{mb['ramp']:.2f})"
        elif d > 0 and mb.get('target', 0) > mb.get('healthy', 0) + 1.5:
            why = f"extra minutes: short-handed roster (target {mb['target']:.0f} v healthy role {mb['healthy']:.0f})"
        elif mb.get('healthy'):
            why = f"healthy role {mb['healthy']:.0f} min v season {avg:.0f} (recent games weigh more)"
        else:
            why = 'role change'
        out.append({'id': e['id'], 'name': e['name'], 'team': e['team'], 'game_id': e['game_id'], 'proj': round(proj, 1),
                    'season': round(avg, 1), 'delta': round(d, 1), 'why': why})
    up = sorted([r for r in out if r['delta'] > 0], key=lambda r: -r['delta'])[:limit // 2]
    down = sorted([r for r in out if r['delta'] < 0], key=lambda r: r['delta'])[:limit // 2]
    return up + down  # risers first, then fallers


def slate_review(done: list, box_by_game) -> dict | None:
    """U4 "How we did": finished games with a pre-game projection — favourites' record, Brier and log loss of the home
    win chance, total and margin errors, and the players furthest from their own projected points distribution
    (percentile of the actual line in the simulated worlds)."""
    import math
    games, players = [], []
    for gid, r, sim in done:
        try:
            hp, ap = int(r['home_pts']), int(r['away_pts'])
        except (TypeError, ValueError):
            continue
        fg = sim['periods']['fg']
        ph = fg['home']['win']
        won = 1.0 if hp > ap else 0.0
        games.append({'game_id': gid, 'p_home': ph, 'won': won, 'fav_won': (ph >= 0.5) == (won == 1.0),
                      'total_err': (hp + ap) - fg['total']['mean'], 'margin_err': (hp - ap) - fg['margin']['mean']})
        for side, tid in (('home', r['home_id']), ('away', r['away_id'])):
            box = {b['player_id']: b for b in box_by_game[gid][tid]}
            for x in sim[side]['players']:
                b = box.get(str(x['id']))
                d = ((x.get('periods') or {}).get('fg') or {}).get('stats', {}).get('pts')
                if not b or not d or int(b.get('dnp') or 0) or b.get('pts') in ('', None):
                    continue
                a = int(b['pts'])
                tot = sum(d['hist']) or 1
                below = sum(c for i, c in enumerate(d['hist']) if i + d['min'] < a)
                at = d['hist'][a - d['min']] if 0 <= a - d['min'] < len(d['hist']) else 0
                players.append({'id': str(x['id']), 'name': x['name'], 'team': str(tid), 'game_id': gid, 'actual': a,
                                'proj': round(d['mean'], 1), 'pct': round((below + at / 2) / tot, 3)})
    if not games:
        return None
    n = len(games)
    brier = sum((g['p_home'] - g['won']) ** 2 for g in games) / n
    ll = -sum(math.log(max(1e-4, g['p_home'] if g['won'] else 1 - g['p_home'])) for g in games) / n
    rated = [p for p in players if p['proj'] >= 8]
    return {'games': n, 'fav_won': sum(g['fav_won'] for g in games), 'brier': round(brier, 3), 'log_loss': round(ll, 3),
            'total_mae': round(sum(abs(g['total_err']) for g in games) / n, 1), 'total_bias': round(sum(g['total_err'] for g in games) / n, 1),
            'margin_mae': round(sum(abs(g['margin_err']) for g in games) / n, 1),
            'in_range_share': round(sum(0.1 <= p['pct'] <= 0.9 for p in players) / max(len(players), 1), 3), 'players': len(players),
            'overs': sorted(rated, key=lambda p: (-p['pct'], -(p['actual'] - p['proj'])))[:4],
            'unders': sorted(rated, key=lambda p: (p['pct'], p['actual'] - p['proj']))[:4]}


def games_to_watch(day_games: list) -> dict | None:
    """Today strip: the closest finish (chance the final margin is within 5), the highest projected total and the likeliest
    overtime, over a slate's projected games (stored distributions only)."""
    rows = []
    for gid, r, sim in day_games:
        fg = sim['periods']['fg']
        m = fg['margin']
        tot = sum(m['hist']) or 1
        close = sum(c for i, c in enumerate(m['hist']) if abs(i + m['min']) <= 5) / tot
        rows.append({'game_id': gid, 'away': str(r['away_id']), 'home': str(r['home_id']), 'close': round(close, 4),
                     'total': round(fg['total']['mean'], 1), 'ot': round(float(sim.get('ot') or 0), 4)})
    if not rows:
        return None
    out, used = {}, set()
    for name, key in (('closest', 'close'), ('shootout', 'total'), ('overtime', 'ot')):  # three different games when possible
        pool = [x for x in rows if x['game_id'] not in used] or rows
        out[name] = max(pool, key=lambda x: x[key])
        used.add(out[name]['game_id'])
    return out


def spotlight_entries(gid: str, r: dict, sim: dict) -> list:
    out = []
    for side in ('home', 'away'):
        tid, opp = (r['home_id'], r['away_id']) if side == 'home' else (r['away_id'], r['home_id'])
        for x in sim[side]['players']:
            out.append({'id': str(x['id']), 'name': x['name'], 'team': str(tid), 'opp': str(opp), 'home': side == 'home',
                        'game_id': gid, 'tip_utc': r['tip_utc'], 'x': x})
    return out


def availability(sim: dict, season_of) -> dict:
    """U7: the saved report as used by the forecast, never the latest registry as a substitute for its origin."""
    report = sim.get('availability_report')
    if report is not None and (not isinstance(report, dict) or
                               any(not isinstance(report.get(side), list) for side in ('away', 'home'))):
        raise ValueError('invalid saved availability report')
    out: dict[str, str | list[dict]] = {'source': 'snapshot' if report is not None else 'partial-legacy'}
    for side in ('away', 'home'):
        simp = {str(x['id']): x for x in sim[side]['players']}
        rows = []
        entries = report[side] if report is not None else sim[side]['players']
        for entry in entries:
            pid = str(entry['id'])
            x = simp.get(pid)
            st = (entry.get('status') or '').strip() or 'Unknown'
            assumed = x.get('availability') if x else entry.get('availability')
            if st.lower() == 'active' and (assumed is None or assumed >= 1):
                continue
            sa = season_of(pid)
            inj = entry.get('injury') or {}
            rows.append({'id': pid, 'name': entry.get('name'), 'status': st, 'status_source': entry.get('status_source'),
                         'comment': inj.get('comment'), 'return': inj.get('return'),
                         'assumed_availability': assumed, 'basis': x.get('availability_basis') if x else None,
                         'simulated': x is not None,
                         'plays': round(float(x.get('played') or 0), 3) if x else 0.0,
                         'min_if_plays': round((x.get('if_plays') or {}).get('min') or (((x.get('periods') or {}).get('fg') or {}).get('sec', 0) / 60), 1) if x else None,
                         'season_min': round(sa['season'].get('min') or 0, 1) if sa else None, 'gp': sa['gp'] if sa else 0})
        out[side] = sorted(rows, key=lambda q: (-(q['season_min'] or 0)))
    return out


SHOT_ZONES = ('rim', 'paint', 'mid', 'corner3', 'above3')


def shot_profile_table() -> dict:
    """U10: each player's pre-game shot profile from the latest profiles (data/derived/features/latest.parquet): share of his
    shots and FG% by zone, the league's shot-weighted averages beside them, assisted share, free-throw rate, sample size."""
    path = DERIVED / 'features' / 'latest.parquet'
    if not path.exists():
        return {}
    import pandas as pd
    L = pd.read_parquet(path)
    w = L['shots_eff'].fillna(0)
    lg = {z: {'mix': float((L[f'mix_{z}'] * w).sum() / w.sum()), 'fg': float((L[f'fg_{z}'] * L[f'mix_{z}'] * w).sum() / (L[f'mix_{z}'] * w).sum())}
          for z in SHOT_ZONES}
    out = {}
    for r in L.itertuples(index=False):
        if not (r.shots_eff or 0) > 5:
            continue
        out[str(r.player)] = {'zones': [{'zone': z, 'mix': round(float(getattr(r, f'mix_{z}')), 4), 'fg': round(float(getattr(r, f'fg_{z}')), 4),
                                         'lg_mix': round(lg[z]['mix'], 4), 'lg_fg': round(lg[z]['fg'], 4)} for z in SHOT_ZONES],
                              'assisted': round(float(r.assisted_share), 3), 'ft_pct': round(float(r.ft_pct), 3),
                              'fta_per_use': round(float(r.fta_per_use or 0), 3), 'shots_eff': round(float(r.shots_eff), 1), 'as_of': str(r.date_et)}
    return out


def usage_profile_table(day: str) -> dict:
    """The latest prior-only, decayed and shrunk offensive-segment usage input."""
    path = DERIVED / 'features' / 'latest.parquet'
    if not path.exists():
        return {}
    import pandas as pd
    data = pd.read_parquet(path, columns=['player', 'date_et', 'usage', 'off_segs_eff'])
    out = {}
    for row in data.itertuples(index=False):
        if pd.isna(row.date_et) or str(row.date_et) >= day:
            raise ValueError(f'usage profile for {row.player} is not before {day}')
        if pd.isna(row.usage) or pd.isna(row.off_segs_eff):
            continue
        usage, exposure = float(row.usage), float(row.off_segs_eff)
        if not math.isfinite(usage) or not math.isfinite(exposure) or not 0 <= usage <= 1 or exposure < 0:
            raise ValueError(f'invalid usage profile for {row.player}')
        if exposure > 0:
            out[str(row.player)] = {'rate': round(usage, 4), 'off_segments_eff': round(exposure, 1),
                                    'through': str(row.date_et)}
    return out


def defence_profiles(M, day: str, registry: dict) -> dict:
    """U11: each defender's real-matchup profile over the last 365 days before `day` (D32): partial possessions guarded,
    points his man scored per 100 partial possessions v those attackers' own rate elsewhere (leave-one-out), three-point
    attempt share allowed v their normal share (deterrence), FG% allowed, and whom he guarded most."""
    if M is None:
        return {}
    from datetime import date, timedelta
    since = (date.fromisoformat(day) - timedelta(days=365)).isoformat()
    X = M[(M['date'] < day) & (M['date'] >= since)]
    if X.empty:
        return {}
    pair = X.groupby(['def_player', 'off_player'], as_index=False)[['pposs', 'pts', 'fga', 'fgm', 'fg3a']].sum()
    att = X.groupby('off_player')[['pposs', 'pts', 'fga', 'fg3a']].sum()
    pair = pair.join(att, on='off_player', rsuffix='_att')
    rest_pp = (pair['pposs_att'] - pair['pposs']).where(lambda v: v > 20)
    pair['exp_pts'] = pair['pposs'] * (pair['pts_att'] - pair['pts']) / rest_pp
    rest_fga = (pair['fga_att'] - pair['fga']).where(lambda v: v > 10)
    pair['exp_fg3a'] = pair['fga'] * (pair['fg3a_att'] - pair['fg3a']) / rest_fga
    out = {}
    for d, g in pair.groupby('def_player'):
        pp = float(g['pposs'].sum())
        if pp < 150:
            continue
        ok = g.dropna(subset=['exp_pts'])
        ok3 = g.dropna(subset=['exp_fg3a'])
        top = g.sort_values('pposs', ascending=False).head(5)
        out[str(d)] = {'since': since, 'pposs': round(pp), 'games_note': None,
                       'pts_100': round(100 * float(g['pts'].sum()) / pp, 1),
                       'exp_100': round(100 * float(ok['exp_pts'].sum()) / float(ok['pposs'].sum()), 1) if len(ok) and ok['pposs'].sum() > 0 else None,
                       'fg_allowed': round(float(g['fgm'].sum()) / float(g['fga'].sum()), 3) if g['fga'].sum() > 0 else None,
                       'fg3a_share': round(float(g['fg3a'].sum()) / float(g['fga'].sum()), 3) if g['fga'].sum() > 0 else None,
                       'exp_fg3a_share': round(float(ok3['exp_fg3a'].sum()) / float(ok3['fga'].sum()), 3) if len(ok3) and ok3['fga'].sum() > 0 else None,
                       'top': [{'id': str(r.off_player), 'name': (registry.get(str(r.off_player)) or {}).get('name', str(r.off_player)),
                                'pposs': round(float(r.pposs)), 'pts': int(r.pts), 'fgm': int(r.fgm), 'fga': int(r.fga)} for r in top.itertuples(index=False)]}
    return out


def opponent_history(registry: dict, teams: dict, M, day: str) -> dict:
    """U12: per player, his past games against each team (ESPN boxes 2022-23 → before `day`) and, from real matchups, which of
    that team's current players guarded him most. Returns {pid: {opp_team_id: {...}}} lazily filled for next opponents."""
    from scripts import nbastats
    E = nbastats.espn_tables()
    abbr_to_id = {v['abbr']: k for k, v in teams.items()}
    E = E[(E['date'] < day) & ~E['did_not_play'].fillna(False).astype(bool) & (E['min'].fillna(0) > 0)].copy()
    E['opp_id'] = E['opp_abbr'].map(abbr_to_id)
    by_player = {pid: g.sort_values('date') for pid, g in E.groupby('player')}
    on_team = {}
    for pid, reg in registry.items():
        if reg.get('on_roster'):
            on_team.setdefault(str(reg.get('team')), set()).add(str(pid))
    def lookup(pid: str, opp: str):
        g = by_player.get(str(pid))
        if g is None:
            return None
        v = g[g['opp_id'] == str(opp)]
        if v.empty:
            return None
        cols = ['pts', 'reb', 'ast', 'min']
        games = [{'date': r.date, 'min': int(r.min or 0), 'pts': int(r.pts or 0), 'reb': int(r.reb or 0), 'ast': int(r.ast or 0)}
                 for r in v.tail(8).itertuples(index=False)][::-1]
        out = {'n': int(len(v)), 'avg': {c: round(float(v[c].mean()), 1) for c in cols}, 'overall': {c: round(float(g[c].mean()), 1) for c in cols},
               'games': games, 'guards': []}
        if M is not None:
            mm = M[(M['off_player'] == str(pid)) & M['def_player'].isin(on_team.get(str(opp), set())) & (M['date'] < day)]
            if not mm.empty:
                gg = mm.groupby('def_player')[['pposs', 'pts', 'fgm', 'fga']].sum().sort_values('pposs', ascending=False).head(3)
                out['guards'] = [{'id': d, 'name': (registry.get(d) or {}).get('name', d), 'pposs': round(float(r.pposs)), 'pts': int(r.pts),
                                  'fgm': int(r.fgm), 'fga': int(r.fga)} for d, r in gg.iterrows()]
        return out
    return lookup


def season_movers(snaps, latest_day, season, master):
    """Compare distinct season cutoffs, not tomorrow's duplicate of today's season."""
    cutoff = season.get('as_of', latest_day)
    previous = None
    for day in sorted((d for d in snaps if d <= latest_day), reverse=True):
        old = read_json(snaps[day]['path'] / 'season.json')
        if old.get('as_of', day) < cutoff and old.get('model') == season.get('model'):
            previous = (day, old)
            break
    if previous is None:
        return {'from': None, 'to': cutoff, 'teams': [], 'results': []}
    day, old = previous
    since = old.get('as_of', day)
    changes = []
    for tid, f in season['teams'].items():
        before = old['teams'].get(tid)
        if not before:
            continue
        keys = ('mean_w', 'top6', 'playin', 'first')
        changes.append({'id': tid, 'before': {k: before[k] for k in keys}, 'now': {k: f[k] for k in keys},
                        'delta': {k: round(f[k] - before[k], 4) for k in keys}})
    results = [{'id': r['game_id'], 'date': r['date_et'], 'home': r['home_id'], 'away': r['away_id'],
                'home_pts': int(r['home_pts']), 'away_pts': int(r['away_pts'])}
               for r in master if r['status'] == 'final' and since <= r['date_et'] < cutoff]
    return {'from': since, 'from_snapshot': day, 'from_kind': snaps[day]['meta']['kind'],
            'to': cutoff, 'model': season['model'], 'teams': changes, 'results': results}


def trend_fields(p: dict | None) -> dict:
    """U13: last-10 per-game averages and the last 10 points totals (games played) for the Players tab's trend column."""
    if not p:
        return {}
    played = [g for g in p.get('log', []) if not g.get('dnp')][-10:]
    if not played:
        return {}
    n = len(played)
    return {'l10': {k: round(sum((g.get(k) or 0) for g in played) / n, 2) for k in ('pts', 'reb', 'ast', 'min')}, 'l10_n': n,
            'spark': [int(g.get('pts') or 0) for g in played]}


def lead_fan(path: Path, gid: str) -> dict | None:
    """U5: the home lead after Q1, at half-time, after Q3 and at the final whistle (overtime included) in every stored world:
    10/25/50/75/90th percentiles per break, and the chance the home side leads at each."""
    import numpy as np
    f = path / 'engine_worlds.npz'
    if not f.exists():
        return None
    with np.load(f) as z:
        if gid not in z.files:
            return None
        per = z[gid].astype(int)  # (worlds, home/away, Q1–Q4 + OT)
    weights = None
    with np.load(path / 'engine_players.npz', allow_pickle=False) as players:
        if f'{gid}__weights' in players:
            weights = players[f'{gid}__weights']
    if weights is not None:
        from scripts.lineup_forecast import lead_fan as weighted_fan
        return weighted_fan({'team_points': per}, weights)
    lead = np.cumsum(per[:, 0, :] - per[:, 1, :], axis=1)
    out = {'breaks': ['Q1', 'Half', 'Q3', 'Final'], 'q': [], 'p_lead': []}
    for k in (0, 1, 2, 4):
        v = lead[:, k]
        out['q'].append([int(x) for x in np.percentile(v, [10, 25, 50, 75, 90])])
        out['p_lead'].append(round(float((v > 0).mean()), 3))
    return out


def scorer_duel(path: Path, gid: str, a_id: str, b_id: str) -> dict | None:
    """Duel of the night (Today card): the chance the away side's projected top scorer outscores the home side's, read
    from the stored worlds (same worlds as the Game Centre; nothing simulated)."""
    import numpy as np
    pl = path / 'engine_players.npz'
    if not pl.exists():
        return None
    with np.load(pl) as z:
        if f'{gid}__lines' not in z.files:
            return None
        lines, ids = z[f'{gid}__lines'], [str(x) for x in z[f'{gid}__ids']]
        weights = z[f'{gid}__weights'] if f'{gid}__weights' in z else None
    from scripts.world_mass import WorldMass
    mass = WorldMass(len(lines), weights)
    if a_id not in ids or b_id not in ids:
        return None
    k = list(WORLD_STATS).index('pts')
    d = lines[:, ids.index(a_id), k].astype(int) - lines[:, ids.index(b_id), k].astype(int)
    return {'a': a_id, 'b': b_id, 'p_a': round(float(mass.mean(d > 0)), 4), 'p_level': round(float(mass.mean(d == 0)), 4),
            'p_b': round(float(mass.mean(d < 0)), 4), 'worlds': int(len(d))}


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
            'lineups': ({'timing_policy': lin.get('timing_policy'),
                         'overall': lin.get('overall') if lin.get('timing_policy') == LINEUP_TIMING_POLICY else None,
                         'slates': ([{k: v for k, v in x.items() if k != 'misses'} for x in lin['slates'].values()]
                                    if lin.get('timing_policy') == LINEUP_TIMING_POLICY else []),
                         'legacy_unverified_slates': len(lin.get('legacy_unverified_slates', {}))
                         + (len(lin['slates']) if lin.get('timing_policy') != LINEUP_TIMING_POLICY else 0)}
                        if lin else None)}


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
    snaps = {day: snap for day, snap in snaps.items() if not discarded_preview(day, snap['meta'])}
    latest_day = current_snapshot(snaps)
    latest = snaps[latest_day]
    usage_profiles = usage_profile_table(latest_day)
    L = read_json(latest['path'] / 'stats.json')
    season_latest = read_json(latest['path'] / 'season.json')
    team_model = {g['game_id']: g for g in season_latest['games'] if g.get('source') != 'engine'}

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
    projections = load_projections(snaps, latest_day)

    def proj_summary(gid):
        p = projections.get(gid)
        if not p:
            return None
        fg = p['sim']['periods']['fg']
        return {'snapshot': p['day'], 'kind': p['meta']['kind'], 'completed_at': p['meta'].get('completed_at'),
                'saved_worlds': p['sim']['sims'], 'lineup_branches': 2 ** len(p['sim']['lineups']['selected_players']) if p['sim'].get('lineups') else 1,
                'pre_tip': verified_pre_tip(p['meta'], gid),
                'p_home': fg['home']['win'], 'p_away': fg['away']['win'],
                'mu_home': fg['home']['pts']['mean'], 'mu_away': fg['away']['pts']['mean'],
                'total': fg['total']['mean'], 'margin_mean': fg['margin']['mean'], 'margin_median': fg['margin']['q'][2],
                'ot': p['sim']['ot'],
                # projected top performers for the slate card: each side's top scorer (pts, reb, ast means over all worlds)
                'leaders': {side: [{'id': x['id'], 'name': x['name'], 'pts': x['periods']['fg']['mean']['pts'],
                                    'reb': x['periods']['fg']['mean']['oreb'] + x['periods']['fg']['mean']['dreb'],
                                    'ast': x['periods']['fg']['mean']['ast']}
                                   for x in sorted((y for y in p['sim'][side]['players'] if y.get('periods')),
                                                   key=lambda y: -y['periods']['fg']['mean']['pts'])[:1]] for side in ('away', 'home')},
                'duel': None,
                # U2: the injury report as the engine used it — out (never plays) and maybes (0 < availability < 1)
                'report': {side: {'out': [x['name'] for x in p['sim'][side]['players'] if (x.get('availability') or 0) <= 0 or not x.get('periods')],
                                  'maybe': [x['name'] for x in p['sim'][side]['players'] if 0 < (x.get('availability') or 0) < 1 and x.get('periods')]}
                           for side in ('away', 'home')}}

    def with_duel(gid, summary):
        if summary and summary['leaders'].get('away') and summary['leaders'].get('home'):
            summary['duel'] = scorer_duel(snaps[projections[gid]['day']]['path'], gid, str(summary['leaders']['away'][0]['id']),
                                          str(summary['leaders']['home'][0]['id']))
        return summary

    slate_dates = sorted({r['date_et'] for r in master} | set(snaps))
    by_date = defaultdict(list)
    for r in master:
        by_date[r['date_et']].append(r)
    spot_stats = {}
    def season_lookup(day_):  # season averages as of a projection's snapshot (its stats.json)
        if day_ not in spot_stats:
            P_ = read_json(snaps[day_]['path'] / 'stats.json')['players']
            spot_stats[day_] = lambda pid: averages(P_, [pid]).get(pid)
        return spot_stats[day_]
    for day in slate_dates:
        snap = snaps.get(day) if day <= latest_day else None
        games = []
        entries, watch, done = [], [], []
        for r in sorted(by_date.get(day, []), key=lambda r: (r['tip_utc'], r['game_id'])):
            pj = projections.get(r['game_id'])
            if (pj and r['status'] == 'final' and pj['meta'].get('kind') == 'prospective'
                    and verified_pre_tip(pj['meta'], r['game_id']) is True):
                done.append((r['game_id'], r, pj['sim']))
            if pj and r['status'] != 'final':  # spotlight: projected, not yet played
                entries += spotlight_entries(r['game_id'], r, pj['sim'])
                watch.append((r['game_id'], r, pj['sim']))
            g = game_core(r)
            g['proj'] = with_duel(r['game_id'], proj_summary(r['game_id']))
            tm = team_model.get(r['game_id'])
            g['team_model'] = ({'p_home': tm['p_home'], 'mu_home': tm.get('mu_home'), 'mu_away': tm.get('mu_away'),
                                'source': tm.get('source'), 'snapshot': latest_day} if tm and not g['proj'] else None)
            games.append(g)
        write_json(api / 'slate' / f'{day}.json', {
            'date': day, 'snapshot': day if snap else None,
            'kind': snap['meta']['kind'] if snap else None,
            'generated': snap['meta']['generated'] if snap else None,
            'completed_at': snap['meta'].get('completed_at') if snap else None,
            'model': snap['meta']['model'] if snap else None, 'games': games,
            'spotlight': (spotlight(entries, season_lookup(projections[entries[0]['game_id']]['day']),
                                    snaps[projections[entries[0]['game_id']]['day']]['path']) if entries else None),
            'watch': games_to_watch(watch) if len(watch) > 1 else None,
            'roles': role_changes(entries, season_lookup(projections[entries[0]['game_id']]['day'])) if entries else [],
            'review': slate_review(done, box_by_game) if done else None})

    stats_cache = {latest_day: L}
    M_real = load_matchups()
    for r in master:
        gid = r['game_id']
        core = game_core(r)
        p = projections.get(gid)
        stats_day = p['day'] if p else latest_day
        if stats_day not in stats_cache:
            stats_cache[stats_day] = read_json(snaps[stats_day]['path'] / 'stats.json')
        stats_source = stats_cache[stats_day]
        as_of = p['meta'].get('origin', stats_day) if p else latest_day
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
        marginals = None
        if p:
            import numpy as np
            sim_ids = [x['id'] for side in ('home', 'away') for x in p['sim'][side]['players']]
            avg = averages(stats_source['players'], sim_ids)
            multi = from_worlds(snaps[p['day']]['path'], gid, p['sim'])
            wl = world_lines(snaps[p['day']]['path'], gid, p['meta'].get('sims'))
            if wl is not None:
                write_json(api / 'game' / gid / 'worlds.json', wl)
                if (wl.get('minutes_schema') or wl.get('branches')) and p['meta'].get('origin') == latest_day and p['day'] == latest_day:
                    with np.load(snaps[p['day']]['path'] / 'engine_players.npz', allow_pickle=False) as archive:
                        precise = player_worlds.read_player_worlds(archive, gid)
                    provenance = snaps[p['day']]['path'] / 'lineups' / gid / 'provenance.json'
                    if provenance.exists():
                        from scripts.lineup_minutes import encode_players
                        source_id = read_json(provenance)['source_id']
                        if p['sim'].get('lineups', {}).get('source_id', source_id) != source_id:
                            raise ValueError('Lineup and precise-minute sources differ')
                        marginals = encode_players(precise['minutes'], list(map(str, precise['ids'])), precise.get('weights'), api / 'game' / gid / 'minute-marginals', source_id)
                    else:
                        marginals = minute_marginals(snaps[p['day']]['path'], gid)
                        if marginals is None:
                            raise ValueError(f'{gid}: precise minute marginals are missing')
                        write_json(api / 'game' / gid / 'minute-marginals.json', marginals)
        duel = None
        if M_real is not None and (p or actual):
            sides = {}
            for s_ in ('home', 'away'):
                if p:
                    sides[s_] = sorted(((x['id'], x['name'], ((x.get('periods') or {}).get('fg') or {}).get('mean', {}).get('pts', 0))
                                        for x in p['sim'][s_]['players'] if x.get('availability', 1) > 0), key=lambda t: -(t[2] or 0))
                else:
                    sides[s_] = sorted(((x['id'], x['name'], x.get('pts', 0)) for x in actual[s_]['players'] if not x['dnp']), key=lambda t: -(t[2] or 0))
            duel_day = p['meta'].get('origin', r['date_et']) if p else r['date_et']
            duel = duels(M_real, gid, duel_day, sides, final=bool(actual))
        write_json(api / 'game' / f'{gid}.json', {
            'game': core, 'duels': duel, 'multi': multi if p else None, 'lead_fan': lead_fan(snaps[p['day']]['path'], gid) if p else None,
            'usage_profiles': ({str(pid): usage_profiles[str(pid)] for pid in sim_ids if str(pid) in usage_profiles}
                               if p and p['meta'].get('origin') == latest_day else None),
            'availability': availability(p['sim'], season_lookup(p['day'])) if p and r['status'] != 'final' else None,
            'spotlight': (spotlight(spotlight_entries(gid, r, p['sim']), season_lookup(p['day']), snaps[p['day']]['path'])
                          if p and r['status'] != 'final' else None),
            'projection': ({'snapshot': p['day'], 'origin': p['meta'].get('origin'), 'kind': p['meta']['kind'], 'generated': p['meta']['generated'],
                            'completed_at': p['meta'].get('completed_at'), 'pre_tip': verified_pre_tip(p['meta'], gid),
                            'model': p['meta']['model'], 'notes': p['meta']['notes'],
                            'cutoff': p['meta']['cutoff'], 'sim': p['sim']} if p else None),
            'team_model': ({'snapshot': latest_day, 'sims': season_latest['sims'], **tm} if tm and not p else None),
            'actual': actual, 'comparison': comparison, 'comparison_as_of': as_of, 'averages': avg,
            'worlds': bool(p and (api / 'game' / gid / 'worlds.json').exists()),
            'worlds_minutes_schema': (1 if wl.get('branches') else wl.get('minutes_schema')) if p and wl is not None else None,
            'minute_marginals': marginals if isinstance(marginals, dict) and marginals.get('schema') == 2 else marginals is not None})

    for day, snap in snaps.items():
        if day > latest_day:
            continue
        stats = read_json(snap['path'] / 'stats.json')
        season = read_json(snap['path'] / 'season.json')
        rows = []
        for tid, info in teams.items():
            t = stats['teams'][tid]
            f = season['teams'][tid]
            rows.append({**info, **team_slice(stats['teams'], tid),
                         'pct': round(t['w'] / t['gp'], 4) if t['gp'] else None,
                         'forecast': {k: f[k] for k in ('remaining', 'scheduled', 'mean_w', 'mean_l', 'seed_mean', 'seeds', 'top6',
                                                        'playin', 'out', 'first', 'best_record', 'worst_record', 'wins')} | {'bottom3': f.get('bottom3')}})
        for conf in ('East', 'West'):
            group = [x for x in rows if x['conf'] == conf]
            lead = max(group, key=lambda x: (x['w'] - x['l']))
            for x in group:
                x['gb'] = ((lead['w'] - x['w']) + (x['l'] - lead['l'])) / 2
        write_json(api / 'standings' / f'{day}.json', {
            'date': day, 'kind': snap['meta']['kind'], 'generated': snap['meta']['generated'],
            'model': snap['meta']['model'], 'sims': season['sims'], 'notes': season['notes'],
            **({'probability_mass': season['probability_mass']} if 'probability_mass' in season else {}),
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
                                'tot': {k: p['totals'].get(k, 0) for k in BOX_TOTALS if k != 'pf' or True} if p else {},
                                **trend_fields(p)})
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
        # U15: tonight's projected minutes and starters from the team's next projected game (stored worlds, nothing simulated)
        tonight = None
        nxt = upcoming.get(tid, [None])[0]
        pj = projections.get(nxt['game_id']) if nxt else None
        if pj:
            side = 'home' if pj['sim']['home']['team_id'] == tid else 'away'
            home = nxt['home_id'] == tid
            tonight = {'game_id': nxt['game_id'], 'date': nxt['date_et'], 'tip_utc': nxt['tip_utc'], 'home': home,
                       'opp': nxt['away_id'] if home else nxt['home_id'], 'sims': pj['sim'].get('sims'),
                       'players': {str(x['id']): {'min': round(x['periods']['fg']['stats']['min']['mean'], 1) if x.get('periods') else None,
                                                  'q': x['periods']['fg']['stats']['min']['q'] if x.get('periods') else None,
                                                  'starter': bool(x.get('starter')), 'played': x.get('played'), 'status': x.get('status')}
                                   for x in pj['sim'][side]['players']}}
        write_json(api / 'team' / f'{tid}.json', {
            'date': latest_day, 'team': info, 'record': current[tid], 'stats': team_slice(L['teams'], tid),
            'league': rounded({k: L['league'].get(k) for k in ('ortg', 'pace', 'efg', 'tov_pct', 'oreb_pct', 'ftr', 'fg3a_rate', 'pts')}),
            'forecast': {k: f[k] for k in ('remaining', 'scheduled', 'mean_w', 'mean_l', 'seed_mean', 'seeds', 'top6', 'playin',
                                           'out', 'first', 'best_record', 'wins')},
            'roster': roster, 'schedule': sched, 'tonight': tonight, 'model': season_latest['model']})

    latest_games = read_json(latest['path'] / 'games.json')
    shot_profiles = shot_profile_table()
    dprof = defence_profiles(M_real, latest_day, registry)
    vs_opp = opponent_history(registry, teams, M_real, latest_day)
    for pid, reg in registry.items():
        p = P.get(pid)
        if not p and not reg.get('on_roster'):
            continue
        tid = reg.get('team') or (p or {}).get('team')
        nxt = upcoming.get(tid, [None])[0] if tid else None
        nxt_out = None
        if nxt:  # the next game's projection from whichever snapshot holds it (today's or tomorrow's slate, D24)
            pj = projections.get(nxt['game_id'])
            sim = pj['sim'] if pj else latest_games.get(nxt['game_id'])
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
            nxt_out['history'] = vs_opp(str(pid), str(nxt_out['opp']))
        write_json(api / 'player' / f'{pid}.json', {
            'date': latest_day, 'player': {k: reg.get(k) for k in ('id', 'name', 'short', 'pos', 'jersey', 'team', 'age', 'height',
                                                                    'weight', 'experience', 'status', 'injury', 'on_roster')},
            'season': ({'gp': p['gp'], 'gs': p['gs'], 'dnp': p['dnp'], 'teams': p['teams'], 'tot': p['totals'],
                        'min_ewma': p['min_ewma']} if p else None),
            'log': p['log'] if p else [], 'next': nxt_out, 'shots': shot_profiles.get(str(pid)),
            'usage_profile': usage_profiles.get(str(pid)), 'defence': dprof.get(str(pid)),
            'quarters': ([{k: round(Qall[pid][k][q], 1) for k in PERIOD_BOX} | {'games': Qall[pid]['games']} for q in range(4)]
                         if pid in Qall else None)})

    write_json(api / 'season_movers.json', season_movers(snaps, latest_day, season_latest, master))

    write_json(api / 'lab.json', lab(latest['meta']['model']))

    snapshot_rows = [{'date': d, 'kind': s['meta']['kind'], 'cutoff': s['meta']['cutoff'], 'generated': s['meta']['generated'],
                      'model': s['meta']['model']['id'], 'games': len(s['meta']['games'])}
                     for d, s in sorted(snaps.items()) if d <= latest_day]
    finals = [r for r in master if r['status'] == 'final']
    write_json(api / 'meta.json', {
        'app': APP_NAME, 'season': SEASON_LABEL, 'built': utc_now(), 'latest': latest_day,
        'snapshots': snapshot_rows, 'first_date': slate_dates[0], 'last_date': slate_dates[-1],
        'dates': {d: len(by_date.get(d, [])) for d in slate_dates},
        'teams': teams, 'model': latest['meta']['model'],
        'player_icons': player_icons(),
        'required_capabilities': ['player-icons-v1'] + (['minute-cdf-player-v2', 'lineup-forecast-v1'] if any(p['sim'].get('lineups') for p in projections.values()) else []),
        'data': {'finals': len(finals), 'last_final': max((r['date_et'] for r in finals), default=None),
                 'games': len(master), 'collected_run': registry and read_json(DERIVED / 'players.json')['run']}})

    if views_root.exists():
        shutil.rmtree(views_root)
    out.rename(views_root)
    count = sum(1 for _ in views_root.rglob('*.json'))
    print(f'views: {count} files -> {views_root}', flush=True)
    return {'files': count, 'latest': latest_day}


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    build()
