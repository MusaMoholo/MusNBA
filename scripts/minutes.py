#!/usr/bin/env python3
"""Minutes (ENGINE_PLAN D29): healthy-role minutes, a priority, 240 per game allocated by priority, a return ramp
after absences, and per-world targets.

Recent minutes are contaminated by absences: a backup's minutes inflate while the starter is out, and a returning star's
recent minutes are zero. So, per player, in date order over every regular-season game (all teams, all seasons):

  1. **Healthy-role minutes** h: a decayed average (half-life 5 games, season carry) of *absence-corrected* regulation
     minutes — each game's minutes minus what the allocator gave him for the absences that night (step 3), so a backup's
     inflated nights count at his healthy level and a star's healthy level is not dragged by missed games.
  2. **Priority**: the coach's pecking order — healthy minutes plus a starter bonus (start share, decayed).
  3. **Allocation** of 240 regulation minutes among the available players: everyone starts at his healthy minutes (after
     the return ramp); a shortfall (absences) is shared down the rotation in proportion to healthy minutes^gamma, each
     player capped by his own observed maximum; a surplus (a full, deep roster) is taken from the lowest priority up.
     Rescale and cap until the sum is exactly 240 — a star's absence cascades and reverses when he returns.
  4. **Return ramp** after N games missed: minutes in the k-th game back relative to the allocation, learned from history
     before the cutoff (FINDINGS §3p).
  5. **Per-world targets**: each world draws its own minutes around the allocation (residual spread by role, learned from
     history) and re-solves to 240 with the caps (D7: honest ranges).

Overtime minutes are not allocated here (the engine keeps the closing five, 25 per overtime).

  .venv/bin/python scripts/minutes.py --evaluate [--season 2026 --from 2026-01-01]   allocator v actual (no engine)
"""
from __future__ import annotations

import argparse
import bisect
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, write_json  # noqa: E402

MINUTES = {'half_life': 5.0, 'carry': 0.5, 'start_half_life': 5.0, 'gamma': 0.0, 'start_bonus': 4.0, 'prior_min': 10.0,
           'cap_games': 30, 'cap_floor': 6.0, 'cap_ceiling': 46.0, 'total': 240.0, 'ramp_k': 6,
           'ramp_bins': (0, 1, 3, 6, 12, 25, 1000), 'ramp_shrink': 30.0, 'sd_floor': 1.5, 'correct': 0.5, 'room': 1.0}
SP = None


def group(pos) -> str:
    p = str(pos or '').upper()
    return 'C' if p.startswith('C') else 'G' if p.startswith('G') or p in ('PG', 'SG') else 'F'


def player_games(include_current: bool = True) -> pd.DataFrame:
    """Regular-season player-games (history + the live season): regulation minutes from the M3 on-court shares."""
    paths = sorted((DERIVED / 'history').glob('*/on_court.parquet'))
    if include_current and (DERIVED / 'rotations' / 'on_court.parquet').exists():
        paths.append(DERIVED / 'rotations' / 'on_court.parquet')
    cols = ['game_id', 'date_et', 'season', 'season_type', 'team', 'player', 'pos', 'starter', 'sec'] + [f'm{m:02d}' for m in range(1, 49)]
    frames = [pd.read_parquet(p, columns=cols) for p in paths]
    o = pd.concat(frames, ignore_index=True)
    o = o[o['season_type'] == 2].copy()
    o['reg'] = o[[f'm{m:02d}' for m in range(1, 49)]].sum(axis=1).clip(0, 48)
    o = o.drop(columns=[f'm{m:02d}' for m in range(1, 49)])
    o['game_id'], o['player'], o['team'] = o['game_id'].astype(str), o['player'].astype(str), o['team'].astype(str)
    o = o.drop_duplicates(['game_id', 'player'])
    return o.sort_values(['date_et', 'game_id', 'team', 'player'], kind='stable').reset_index(drop=True)


# ---------------------------------------------------------------- allocation

def allocate(h, cap, prio, total=240.0, gamma=1.0, iters=30, room=0.0) -> np.ndarray:
    """Exactly `total` minutes over the available players (vectors of equal length; nan-free).

    Shortfall: shared in proportion to h^gamma, never above a player's cap. Surplus: removed from the lowest priority
    first (a deep, full roster squeezes the end of the bench)."""
    h = np.maximum(np.asarray(h, float), 0.0)
    cap = np.maximum(np.asarray(cap, float), h * 0 + 0.5)
    m = np.minimum(h, cap)
    n = len(m)
    if n == 0:
        return m
    if n * 48 < total:  # fewer than five: everyone plays everything
        return np.full(n, 48.0)
    cap = np.where(cap * 1 < 48, cap, 48.0)
    s = m.sum()
    if s > total:
        excess = s - total
        for i in np.argsort(prio, kind='stable'):  # lowest priority first
            take = min(m[i], excess)
            m[i] -= take
            excess -= take
            if excess <= 1e-9:
                break
        return m
    w = np.power(np.maximum(h, 0.5), gamma) * np.power(np.maximum(cap - h, 0.5), room)
    for _ in range(iters):
        short = total - m.sum()
        if short <= 1e-6:
            break
        room = cap - m
        live = room > 1e-9
        if not live.any():  # every cap reached: lift the caps toward 48 in proportion
            cap = np.minimum(48.0, cap + short / n + 1e-6)
            continue
        add = short * w * live / (w * live).sum()
        m = np.minimum(cap, m + add)
    return m * (total / m.sum()) if m.sum() > 0 else m


def redraw(mu, cap, sd, W, rng, total=240.0) -> np.ndarray:
    """(W, n) per-world minutes: mean `mu`, noise `sd`, clipped to [0, cap], each row re-solved to `total`."""
    mu, cap, sd = (np.asarray(a, float) for a in (mu, cap, sd))
    X = mu[None, :] + sd[None, :] * rng.standard_normal((W, len(mu)))
    X = np.clip(X, 0.0, np.minimum(48.0, cap)[None, :] + 2.0)
    for _ in range(6):
        X *= total / np.maximum(X.sum(1, keepdims=True), 1e-9)
        X = np.minimum(X, 48.0)
    return X


# ---------------------------------------------------------------- state pass

def coach_dnps(include_current: bool = True) -> dict:
    """(game_id, team) → players listed DNP – coach's decision (available, not used): hoopR boxes for history, our box
    scores for the live season. Injury and other absences are not here."""
    out: dict = defaultdict(list)
    for path in sorted((ROOT / 'data' / 'raw' / 'hoopr').glob('player_box_*.parquet')):
        b = pd.read_parquet(path, columns=['game_id', 'team_id', 'athlete_id', 'did_not_play', 'reason', 'season_type'])
        b = b[(b['season_type'] == 2) & b['did_not_play'].fillna(False).astype(bool) & b['reason'].fillna('').str.upper().str.contains('COACH')]
        b = b.dropna(subset=['athlete_id', 'team_id'])
        for g, t, a in zip(b['game_id'].astype('int64').astype(str), b['team_id'].astype('int64').astype(str), b['athlete_id'].astype('int64').astype(str)):
            out[(g, t)].append(a)
    live = DERIVED / 'player_games.csv'
    if include_current and live.exists():
        b = pd.read_csv(live, usecols=['game_id', 'team_id', 'player_id', 'dnp', 'dnp_reason'], dtype=str)
        b = b[(b['dnp'] == '1') & b['dnp_reason'].fillna('').str.upper().str.contains('COACH')]
        for g, t, a in zip(b['game_id'], b['team_id'], b['player_id']):
            out[(g, t)].append(a)
    return out


class _Player:
    __slots__ = ('S', 'Wt', 'st_S', 'st_W', 'recent', 'last_date', 'season', 'spell_n', 'k', 'games', 'r_S', 'r_W')

    def __init__(self):
        self.r_S, self.r_W = 0.8, 1.0  # rotation share prior: plays in 80% of the games he is available for
        self.S = self.Wt = self.st_S = self.st_W = 0.0
        self.recent = []
        self.last_date, self.season, self.spell_n, self.k, self.games = None, None, 0, 0, 0


def ramp_ratio(table, n_missed, k):
    """Return-ramp multiplier for the k-th game back after n_missed team games (1 = no ramp)."""
    if table is None or n_missed <= 0 or k <= 0 or k > MINUTES['ramp_k']:
        return 1.0
    b = int(np.searchsorted(MINUTES['ramp_bins'], n_missed, side='left')) - 1
    b = max(0, min(b, len(MINUTES['ramp_bins']) - 2))
    return float(table.get((b, k), 1.0))


def state_pass(pg: pd.DataFrame, params: dict | None = None, ramp: dict | None = None, upto: str | None = None, cd: dict | None = None):
    """Sequential pre-game minutes state for every player-game in `pg` (date order), and the state after each player's
    last game. Cutoff-safe by construction: a game's row is computed before its own minutes are seen."""
    P = {**MINUTES, **(params or {})}
    d, ds = 0.5 ** (1 / P['half_life']), 0.5 ** (1 / P['start_half_life'])
    players: dict[str, _Player] = defaultdict(_Player)
    team_dates: dict[str, list] = defaultdict(list)
    out = []
    for (day, gid, team), part in pg.groupby(['date_et', 'game_id', 'team'], sort=False):
        if upto is not None and day >= upto:
            break
        ids = part['player'].tolist()
        season = int(part['season'].iloc[0])
        h, cap, prio, start, missed, kk, ratio = [], [], [], [], [], [], []
        dates = team_dates[team]
        for pid in ids:
            s = players[pid]
            if s.season is not None and s.season != season:  # new season: older games count less
                s.S *= P['carry']
                s.Wt *= P['carry']
                s.st_S *= P['carry']
                s.st_W *= P['carry']
                s.season = season
            if s.season is None:
                s.season = season
            hv = s.S / s.Wt if s.Wt > 0 else P['prior_min']
            n_miss = 0
            if s.last_date is not None:
                n_miss = len(dates) - bisect.bisect_right(dates, s.last_date)  # this team's games since his last game
            if n_miss > 0:
                s.spell_n, s.k = n_miss, 1
            elif s.k > 0:
                s.k += 1
            r = ramp_ratio(ramp, s.spell_n, s.k) if s.k > 0 else 1.0
            c = max(s.recent) if s.recent else hv + 8
            c = float(np.clip(max(c, hv + 2.0, P['cap_floor']), 0, P['cap_ceiling']))
            st = s.st_S / s.st_W if s.st_W > 0 else 0.0
            h.append(hv)
            cap.append(c)
            start.append(st)
            prio.append(hv + P['start_bonus'] * st)
            missed.append(s.spell_n if s.k > 0 else 0)
            kk.append(s.k)
            ratio.append(r)
        h, cap, prio, ratio = (np.array(v, float) for v in (h, cap, prio, ratio))
        alloc0 = allocate(h, cap, prio, P['total'], P['gamma'], room=P['room'])  # absences only (no ramp): the correction for h
        alloc = allocate(h * ratio, cap, prio, P['total'], P['gamma'], room=P['room'])
        m = part['reg'].to_numpy(float)
        st_flag = part['starter'].astype(bool).to_numpy()
        for j, pid in enumerate(ids):
            s = players[pid]
            out.append((gid, pid, team, day, season, h[j], cap[j], prio[j], start[j], missed[j], kk[j], ratio[j], alloc0[j], alloc[j]))
            obs = (h[j] + P['correct'] * (m[j] - alloc0[j]) + (1 - P['correct']) * (m[j] - h[j])) if s.Wt > 0 else m[j]
            if s.k == 0 or ratio[j] >= 0.97:  # ramp games teach the ramp, not the healthy level
                s.S, s.Wt = s.S * d + obs, s.Wt * d + 1.0
            s.st_S, s.st_W = s.st_S * ds + float(st_flag[j]), s.st_W * ds + 1.0
            s.recent = (s.recent + [m[j]])[-int(P['cap_games']):]
            s.last_date, s.games = day, s.games + 1
            if s.k >= P['ramp_k']:
                s.k, s.spell_n = 0, 0
        for pid in (cd or {}).get((str(gid), str(team)), ()):  # available but unused: rotation share falls
            s = players[pid]
            s.r_S, s.r_W = s.r_S * d + 0.0, s.r_W * d + 1.0
        for pid in ids:
            s = players[pid]
            s.r_S, s.r_W = s.r_S * d + 1.0, s.r_W * d + 1.0
        dates.append(day)
    cols = ['game_id', 'player', 'team', 'date_et', 'season', 'healthy', 'cap', 'priority', 'start_share', 'missed', 'k_back',
            'ramp', 'alloc_absence', 'alloc']
    rows = pd.DataFrame(out, columns=cols)
    latest = {pid: {'healthy': s.S / s.Wt if s.Wt > 0 else P['prior_min'], 'start_share': s.st_S / s.st_W if s.st_W > 0 else 0.0,
                    'cap': float(np.clip(max(max(s.recent) if s.recent else 0, (s.S / s.Wt if s.Wt > 0 else 0) + 2, P['cap_floor']), 0, P['cap_ceiling'])),
                    'last_date': s.last_date, 'season': s.season, 'spell_n': s.spell_n, 'k_back': s.k, 'games': s.games,
                    'rotation': s.r_S / s.r_W}
              for pid, s in players.items()}
    return rows, latest, dict(team_dates)


def learn_ramp(pg: pd.DataFrame, rows: pd.DataFrame, before: str) -> dict:
    """Ramp table {(bin, k): ratio} from games before `before`: real regulation minutes over the absence-only allocation
    in the k-th game back after N missed, for players with a healthy role of 15+ minutes; shrunk toward 1."""
    x = rows.merge(pg[['game_id', 'player', 'reg']], on=['game_id', 'player'])
    x = x[(x['date_et'] < before) & (x['k_back'] > 0) & (x['healthy'] >= 15) & (x['alloc_absence'] > 1)]
    x = x.assign(b=np.searchsorted(MINUTES['ramp_bins'], x['missed'].to_numpy(), side='left') - 1)
    g = x.groupby(['b', 'k_back']).apply(lambda t: pd.Series({'num': t['reg'].sum(), 'den': t['alloc_absence'].sum(), 'n': len(t)}),
                                         include_groups=False)
    k0 = MINUTES['ramp_shrink']
    table = {}
    for (b, k), r in g.iterrows():
        mean_den = r['den'] / r['n']
        table[(int(b), int(k))] = float((r['num'] + k0 * mean_den) / (r['den'] + k0 * mean_den))
    return table


def residual_sd(pg: pd.DataFrame, rows: pd.DataFrame, before: str) -> dict:
    """Spread of real regulation minutes around the allocation, by allocation band (for per-world draws)."""
    x = rows.merge(pg[['game_id', 'player', 'reg']], on=['game_id', 'player'])
    x = x[x['date_et'] < before]
    edges = np.arange(0, 50, 4.0)
    b = np.digitize(x['alloc'], edges)
    res = (x['reg'] - x['alloc']).groupby(b).agg(['std', 'mean', 'size'])
    return {'edges': edges.tolist(), 'sd': {int(k): float(v) for k, v in res['std'].items()},
            'mean': {int(k): float(v) for k, v in res['mean'].items()}, 'n': {int(k): int(v) for k, v in res['size'].items()}}


def sd_for(table: dict, alloc) -> np.ndarray:
    b = np.digitize(np.asarray(alloc, float), table['edges'])
    return np.array([max(MINUTES['sd_floor'], table['sd'].get(int(k), 4.0)) for k in b])


def build(before: str, params: dict | None = None, include_current: bool = True, upto: str | None = None):
    """Ramp and spread learned from games before `before`; per player-game pre-game states (cutoff-safe row by row) and
    the state after each player's last game. `upto` stops the pass at that date (live: today — nothing on or after it
    enters the latest states, even if a rotations file holds it)."""
    pg = player_games(include_current)
    rows0, _, _ = state_pass(pg, params, None, upto)
    ramp = learn_ramp(pg, rows0, before)
    rows, latest, team_dates = state_pass(pg, params, ramp, upto, coach_dnps(include_current))
    sd = residual_sd(pg, rows, before)
    return {'pg': pg, 'rows': rows, 'latest': latest, 'team_dates': team_dates, 'ramp': ramp, 'sd': sd, 'params': {**MINUTES, **(params or {})}}


def player_state(m: dict, team: str, pid: str, day: str, row=None) -> dict:
    """One player's pre-game minutes inputs for a game of `team` on `day`: from his state-pass row for that game when
    given (backtest), else from his state after his last game (live: games missed = the team's games since then)."""
    P = m['params']
    rot = 1.0  # known to play (backtest rows: the players who played)
    if row is not None:
        h, cap, st, n, k, r = (float(row.healthy), float(row.cap), float(row.start_share), int(row.missed), int(row.k_back), float(row.ramp))
    else:
        s = m['latest'].get(str(pid))
        if s is None:
            h, cap, st, n, k, r = P['prior_min'], P['prior_min'] + 8, 0.0, 0, 0, 1.0
            rot = 0.5
        else:
            dates = m['team_dates'].get(str(team), [])
            n_miss = len([d for d in dates if s['last_date'] < d < day]) if s['last_date'] else 0
            n, k = (n_miss, 1) if n_miss > 0 else ((s['spell_n'], s['k_back'] + 1) if 0 < s['k_back'] < P['ramp_k'] else (0, 0))
            h, cap, st = s['healthy'], s['cap'], s['start_share']
            r = ramp_ratio(m['ramp'], n, k) if k > 0 else 1.0
            rot = float(s.get('rotation', 1.0))
    sd_tab = m['sd']
    return {'healthy': h, 'cap': cap, 'start_share': st, 'priority': h * rot + P['start_bonus'] * st, 'missed': n, 'k_back': k, 'ramp': r,
            'rotation': rot, 'sd_table': sd_tab}


def game_targets(states: list[dict], P: dict | None = None) -> np.ndarray:
    """Mean regulation minutes for the available players of one side (240 by priority, after the ramp)."""
    P = {**MINUTES, **(P or {})}
    h = np.array([s['healthy'] * s['ramp'] * s.get('rotation', 1.0) for s in states])
    cap = np.array([s['cap'] for s in states])
    prio = np.array([s['priority'] for s in states])
    return allocate(h, cap, prio, P['total'], P['gamma'], room=P['room'])


def projected_starters(states: list[dict], groups: list[str]) -> list[int]:
    """Five starters when no lineup source says otherwise: highest start share (then priority), at most three guards,
    three forwards or two centres."""
    order = sorted(range(len(states)), key=lambda i: (-round(states[i]['start_share'], 3), -states[i]['priority'], i))
    limit = {'G': 3, 'F': 3, 'C': 2}
    out, used = [], defaultdict(int)
    for i in order:
        if len(out) == 5:
            break
        if used[groups[i]] < limit[groups[i]]:
            out.append(i)
            used[groups[i]] += 1
    for i in order:  # not enough within the limits
        if len(out) == 5:
            break
        if i not in out:
            out.append(i)
    return out


# ---------------------------------------------------------------- evaluation (no engine)

def evaluate(season: int = 2026, start: str = '2026-01-01', end: str = '2026-04-30', params: dict | None = None, W: int = 400) -> dict:
    """Allocator targets v real regulation minutes on held-out regular-season games (known availability: the players who
    played), with the per-world draws' 10–90% coverage; replay v0 (template mapping, M3) on the same player-games."""
    m = build(start, params, include_current=False)
    pg, rows = m['pg'], m['rows']
    x = rows.merge(pg[['game_id', 'player', 'reg', 'starter', 'pos']], on=['game_id', 'player'])
    x = x[(x['date_et'] >= start) & (x['date_et'] <= end) & (x['season'] == season)].copy()
    pre = pd.read_parquet(DERIVED / 'features' / 'pregame.parquet', columns=['game_id', 'player', 'usage', 'min_avg'])
    pre['game_id'], pre['player'] = pre['game_id'].astype(str), pre['player'].astype(str)
    x = x.merge(pre, on=['game_id', 'player'], how='left')
    x['tier'] = np.where(x['usage'] >= 0.25, 'star', np.where(x['starter'], 'starter', 'bench'))
    rng = np.random.default_rng(11)
    cov, crps = [], []
    for gid_team, part in x.groupby(['game_id', 'team']):
        sd = sd_for(m['sd'], part['alloc'])
        X = redraw(part['alloc'].to_numpy(), part['cap'].to_numpy(), sd, W, rng)
        y = part['reg'].to_numpy()
        lo, hi = np.quantile(X, 0.1, axis=0), np.quantile(X, 0.9, axis=0)
        cov.append(pd.Series((y >= lo) & (y <= hi), index=part.index))
        crps.append(pd.Series(np.abs(X - y).mean(0) - 0.5 * np.abs(X[:, None, :] - X[None, :, :]).mean((0, 1)) if W <= 400 else np.nan, index=part.index))
    x['covered'] = pd.concat(cov)
    x['crps'] = pd.concat(crps)
    out = {'player_games': len(x), 'params': {k: v for k, v in m['params'].items() if not isinstance(v, tuple)},
           'ramp': {f'{b}:{k}': round(v, 3) for (b, k), v in sorted(m['ramp'].items())}}
    for tier, t in x.groupby('tier'):
        out[tier] = {'n': len(t), 'actual': round(float(t['reg'].mean()), 2), 'alloc': round(float(t['alloc'].mean()), 2),
                     'rel_bias': round(float(t['alloc'].mean() / t['reg'].mean() - 1), 4),
                     'mae': round(float((t['alloc'] - t['reg']).abs().mean()), 2), 'coverage_10_90': round(float(t['covered'].mean()), 3),
                     'crps': round(float(t['crps'].mean()), 3), 'ewma_min_avg_mae': round(float((t['min_avg'] - t['reg']).abs().mean()), 2)}
    x['pre_tier'] = np.where(x['usage'] >= 0.25, 'star', np.where(x['start_share'] >= 0.5, 'starter', 'bench'))
    out['by_pregame_tier'] = {t: {'n': len(d), 'rel_bias': round(float(d['alloc'].mean() / d['reg'].mean() - 1), 4),
                                  'mae': round(float((d['alloc'] - d['reg']).abs().mean()), 2),
                                  'ewma_mae': round(float((d['min_avg'] - d['reg']).abs().mean()), 2),
                                  'ewma_bias': round(float(d['min_avg'].mean() / d['reg'].mean() - 1), 4)} for t, d in x.groupby('pre_tier')}
    out['all'] = {'mae': round(float((x['alloc'] - x['reg']).abs().mean()), 3), 'ewma_mae': round(float((x['min_avg'] - x['reg']).abs().mean()), 3),
                  'rmse': round(float(np.sqrt(((x['alloc'] - x['reg']) ** 2).mean())), 3), 'ewma_rmse': round(float(np.sqrt(((x['min_avg'] - x['reg']) ** 2).mean())), 3)}
    back = x[(x['k_back'] == 1) & (x['missed'] >= 5) & (x['healthy'] >= 25)]
    out['returning_25plus_after_5plus'] = {'n': len(back), 'actual': round(float(back['reg'].mean()), 2),
                                           'alloc': round(float(back['alloc'].mean()), 2), 'healthy': round(float(back['healthy'].mean()), 2),
                                           'min_avg': round(float(back['min_avg'].mean()), 2)}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--evaluate', action='store_true')
    ap.add_argument('--season', type=int, default=2026)
    ap.add_argument('--from', dest='start', default='2026-01-01')
    ap.add_argument('--to', dest='end', default='2026-04-30')
    ap.add_argument('--set', action='append', default=[], metavar='KEY=VALUE', help='override a MINUTES setting')
    ap.add_argument('--log', default=None, help='experiment name to log under analysis/experiments/')
    args = ap.parse_args()
    params = {k: float(v) for k, v in (s.split('=') for s in args.set)}
    if args.evaluate:
        r = evaluate(args.season, args.start, args.end, params)
        print(json.dumps(r, indent=1))
        if args.log:
            from datetime import datetime, timezone
            from scripts.evaluate import EXPERIMENTS
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
            write_json(EXPERIMENTS / f'{stamp}_{args.log}.json', {'experiment': 'minutes_allocator', 'run': stamp, **r}, pretty=True)


if __name__ == '__main__':
    main()
