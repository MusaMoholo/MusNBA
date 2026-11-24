#!/usr/bin/env python3
"""Placeholder projections: box-score-rate Monte Carlo with play-by-play quarter profiles.

NOT the possession engine (PLAN.md phase 2). It fills the same output contract so the app is
ready for it: every period (Q1–Q4, H1, H2, FG) has team and player distributions.

Per simulated world:
* team regulation scores from a calibrated bivariate model (ratings × pace, home court, lineup
  strength), split into quarters by each team's (shrunk) quarter-scoring shares; overtime periods;
* player minutes per quarter from each player's own play-by-play quarter profile (shrunk toward
  starter/bench norms), fitted so each team-quarter holds 60 player-minutes; starters sit more of
  Q4 when the game is a blowout after three quarters; closers play overtime;
* every quarter's team points, misses, rebounds, assists, turnovers, steals and blocks are
  allocated to the players on the floor by their rates and quarter usage — player points always sum
  to the team's quarter score.

Seeded per (model, slate date, game): identical inputs reproduce identical outputs.
"""
from __future__ import annotations

import hashlib
import math
import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
import sys
import warnings
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MODEL = {
    'id': 'baseline-v1', 'kind': 'placeholder', 'sims': 10000,
    'label': 'Placeholder baseline v1 — box-score rates with play-by-play quarter profiles, not the possession engine',
    'home_court': 2.0, 'team_sd': 11.25, 'team_rho': 0.35, 'prior_games': 8, 'prior_minutes': 80,
    'quarter_prior_seconds': 3600, 'usage_prior_points': 15, 'usage_prior_assists': 8,
}
AVAILABILITY_POLICY = 'report-bands-v1'  # owner-defined assumptions, not calibrated probabilities
AVAILABILITY = {'active': 1.0, 'probable': 0.75, 'day-to-day': 0.5, 'questionable': 0.5,
                'doubtful': 0.25, 'out': 0.0, 'suspension': 0.0, 'suspended': 0.0, 'injured reserve': 0.0}
PERIODS = ('q1', 'q2', 'q3', 'q4', 'h1', 'h2', 'fg')
SLICES = {'q1': [0], 'q2': [1], 'q3': [2], 'q4': [3], 'h1': [0, 1], 'h2': [2, 3], 'fg': [0, 1, 2, 3, 4]}
FG_DIST = ('min', 'pts', 'reb', 'oreb', 'dreb', 'ast', 'fg3m', 'fgm', 'ftm', 'stl', 'blk', 'tov', 'pra', 'pr', 'pa', 'ra', 'stocks',
           'fga', 'fta', 'fg3a')
PERIOD_DIST = ('min', 'pts', 'reb', 'oreb', 'dreb', 'ast', 'fg3m', 'fgm', 'ftm', 'stl', 'blk', 'pra', 'fga', 'fg3a', 'fta')
SHOOTING_PAIRS = {'fgpct': ('fgm', 'fga'), 'fg3pct': ('fg3m', 'fg3a'), 'ftpct': ('ftm', 'fta')}
BOX = ('pts', 'fgm', 'fga', 'fg3m', 'fg3a', 'ftm', 'fta', 'oreb', 'dreb', 'ast', 'stl', 'blk', 'tov')


def seed_for(*parts) -> int:
    return int.from_bytes(hashlib.sha256('|'.join(map(str, parts)).encode()).digest()[:8], 'little')


def rng_for(*parts) -> np.random.Generator:
    return np.random.Generator(np.random.PCG64(seed_for(*parts)))


def normal_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def shrink(value, n, prior, k):
    if value is None or not n:
        return prior
    return (n * value + k * prior) / (n + k)


def summary(values: np.ndarray, offset: bool = False) -> dict:
    """Exact discrete summary of integer outcomes; histogram counts start at `min`."""
    values = np.asarray(values, dtype=np.int64)
    lo = int(values.min()) if offset else 0
    counts = np.bincount(values - lo)
    cum = np.cumsum(counts)
    total = int(cum[-1])
    quant = [int(np.searchsorted(cum, q * total, side='left')) + lo for q in (0.1, 0.25, 0.5, 0.75, 0.9)]
    return {'mean': round(float(values.mean()), 3), 'sd': round(float(values.std()), 3), 'q': quant,
            'min': lo, 'hist': counts.astype(int).tolist()}


def shooting_summaries(values: dict) -> dict:
    """Whole-percent distributions, conditional on at least one attempt in the selected period."""
    out = {}
    for key, (made, attempted) in SHOOTING_PAIRS.items():
        if made not in values or attempted not in values:
            continue
        m, a = np.asarray(values[made]), np.asarray(values[attempted])
        if np.any(m < 0) or np.any(a < 0) or np.any(m > a):
            raise ValueError(f'Invalid shooting counts for {key}')
        mask = a > 0
        if mask.any():
            pct = np.floor(100 * m[mask] / a[mask] + 0.5).astype(np.int64)
            out[key] = {**summary(pct), 'defined': int(mask.sum()), 'total': int(a.size)}
    return out


# ---------------------------------------------------------------------------- team model

def team_expectation(T: dict, lg: dict, home: str, away: str, neutral: bool = False) -> dict:
    k = MODEL['prior_games']
    def get(tid, key, prior):
        return shrink(T[tid][key], T[tid]['gp'], prior, k)
    pace = get(home, 'pace', lg['pace']) * get(away, 'pace', lg['pace']) / lg['pace']
    h_off, h_def = get(home, 'ortg', lg['ortg']), get(home, 'drtg', lg['ortg'])
    a_off, a_def = get(away, 'ortg', lg['ortg']), get(away, 'drtg', lg['ortg'])
    hca = 0 if neutral else MODEL['home_court']
    mu_h = pace * (h_off * a_def / lg['ortg']) / 100 + hca / 2
    mu_a = pace * (a_off * h_def / lg['ortg']) / 100 - hca / 2
    sd_margin = MODEL['team_sd'] * math.sqrt(2 * (1 - MODEL['team_rho']))
    return {'pace': pace, 'mu_home': mu_h, 'mu_away': mu_a, 'p_home': normal_cdf((mu_h - mu_a) / sd_margin)}


def team_rates(T: dict, lg: dict, tid: str) -> dict:
    k = MODEL['prior_games']
    s, gp = T[tid], T[tid]['gp']
    pg, lpg = s['per_game'], lg['per_game']
    def per(key, prior):
        return shrink(pg.get(key), gp, prior, k)
    pts = per('pts', lpg['pts'])
    quarters = s.get('quarters') or [None] * 4
    qsum = sum(q for q in quarters if q) if all(quarters) else None
    share = [shrink(q / qsum if qsum else None, gp, lg['quarter_share'][i], 10) for i, q in enumerate(quarters)]
    return {
        'share3': 3 * per('fg3m', lpg['fg3m']) / pts, 'shareft': per('ftm', lpg['ftm']) / pts,
        'oreb_pct': shrink(s['oreb_pct'], gp, lg['oreb_pct'], k), 'dreb_pct': shrink(s['dreb_pct'], gp, 1 - lg['oreb_pct'], k),
        'ast_rate': shrink(s['ast_rate'], gp, lg['ast_rate'], k),
        'tov_pct': shrink(s['tov_pct'], gp, lg['tov_pct'], k), 'opp_tov_pct': shrink(s['opp_tov_pct'], gp, lg['tov_pct'], k),
        'stl_share': (pg.get('stl') or lpg['stl']) / max(1e-9, (s['opp_per_game'].get('tov') or lpg['tov'])),
        'blk_per_miss': (pg.get('blk') or lpg['blk']) / max(1e-9, ((s['opp_per_game'].get('fga') or lpg['fga']) - (s['opp_per_game'].get('fgm') or lpg['fgm']))),
        'quarter_share': [x / sum(share) for x in share],
    }


# ---------------------------------------------------------------------------- players

def availability(status: str | None) -> float:
    return AVAILABILITY.get((status or '').strip().lower(), 0.5)


def report_availability(reg: dict, game_day: str | None) -> tuple[float, str]:
    """Conservative, auditable report-to-band conversion for the specified ET game date.

    Structured clear status wins. Generic DTD/unknown uses only a recent report explicitly
    naming this game day. Stale/ambiguous text cannot rule a player in or out.
    """
    status = (reg.get('status') or '').strip().lower()
    basis = 'not_listed_assumption' if status == 'active' and reg.get('status_source') == 'not_listed_assumption' else 'status'
    if status in AVAILABILITY and status != 'day-to-day':
        return availability(status), basis
    injury = reg.get('injury') or {}
    try:
        target = date.fromisoformat(game_day)
        published = datetime.fromisoformat(injury['date'].replace('Z', '+00:00')).astimezone(ZoneInfo('America/New_York')).date()
    except (TypeError, ValueError, KeyError):
        return .5, 'ambiguous_report'
    text = str(injury.get('comment') or '').lower().replace('’', "'")
    weekdays = re.findall(r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', text)
    named_day = set(weekdays) == {target.strftime('%A').lower()}
    same_day = published == target and bool(re.search(r'\b(today|tonight)\b', text)) and not weekdays
    if not (timedelta(0) <= target - published < timedelta(days=7) and (named_day or same_day)):
        return .5, 'ambiguous_report'
    # Contradictory historical wording is ambiguous; no optimistic keyword fallback.
    if re.search(r'not (?:yet )?cleared|unclear|not clear|whether .*will play', text):
        return .5, 'ambiguous_report'
    signals = set()
    for pattern, band in (
        (r"(?:won't|will not|not expected to) play|ruled out|will miss|unavailable for|(?:listed|designated) as out", 0),
        (r"(?:listed as |listed |is |to |deemed )doubtful", .25),
        (r"(?:listed as |listed |is |to |remains? )questionable|game.time decision", .5),
        (r"(?:listed as |listed |is |to |deemed )probable|expected to play", .75),
        (r"(?:will|cleared to) play|available (?:to play|for)", 1),
    ):
        if re.search(r'\b(?:' + pattern + r')\b', text):
            signals.add(band)
    # 'not expected to play' contains 'expected to play'; the explicit negative wins.
    if 'not expected to play' in text:
        signals.discard(.75)
    return (signals.pop(), 'game_report') if len(signals) == 1 else (.5, 'ambiguous_report')


def player_inputs(tid: str, P: dict, registry: dict, lg: dict, T: dict, prospective: bool,
                  Q: dict | None = None, priors: dict | None = None, game_day: str | None = None) -> list[dict]:
    if prospective:
        ids = [pid for pid, r in registry.items() if r.get('on_roster') and r.get('team') == tid]
    else:
        ids = [pid for pid, p in P.items() if p['team'] == tid]
    lpm = {k: v / 240 for k, v in lg['per_game'].items()}  # league per player-minute
    K = MODEL['prior_minutes']
    team_gp = max(1, T[tid]['gp'])
    out = []
    for pid in ids:
        p, reg = P.get(pid), registry.get(pid, {})
        t = p['totals'] if p else {}
        gp, mins = (p['gp'], t.get('min', 0)) if p else (0, 0)
        if prospective:
            status = (reg.get('status') or '').strip() or 'Unknown'
            a, basis = report_availability(reg, game_day)
            if p and a == 1.0 and basis == 'not_listed_assumption' and p['recent_window'] >= 3 and p['recent_played'] == 0:
                a = 0.75 if (p['min_ewma'] or 0) >= 20 else 0.5
                basis = 'recent_inactivity'
        else:
            status, basis = 'Unknown (retrospective)', None
            a = 1.0 if p and p['recent_played'] >= 1 else 0.2
        m0 = (0.6 * p['min_ewma'] + 0.4 * mins / gp) if p and gp else 0.0
        def rate(key, prior_key=None):
            return (t.get(key, 0) + K * lpm[prior_key or key]) / (mins + K)
        fg2m, fg2a = t.get('fgm', 0) - t.get('fg3m', 0), t.get('fga', 0) - t.get('fg3a', 0)
        p3 = (t.get('fg3m', 0) + 15 * lg['fg3_pct']) / (t.get('fg3a', 0) + 15)
        p2 = (fg2m + 25 * lg['fg2_pct']) / (fg2a + 25)
        pft = (t.get('ftm', 0) + 10 * lg['ft_pct']) / (t.get('fta', 0) + 10)
        r3 = rate('fg3m')
        r2 = (fg2m + K * (lpm['fgm'] - lpm['fg3m'])) / (mins + K)
        rft = rate('ftm')
        out.append({
            'id': pid, 'name': reg.get('name') or (p['name'] if p else pid), 'pos': reg.get('pos') or (p['pos'] if p else ''),
            'jersey': reg.get('jersey', ''),
            'status': status, 'availability_basis': basis, 'availability_policy': AVAILABILITY_POLICY if prospective else None,
            'injury': reg.get('injury') if prospective else None, 'availability': a, 'base_min': m0,
            'recent_started': p['recent_started'] if p else 0, 'gp': gp,
            'r3': r3, 'r2': r2, 'rft': rft, 'p3': p3, 'p2': p2, 'pft': pft,
            'miss3': r3 / p3 * (1 - p3), 'miss2': r2 / p2 * (1 - p2), 'missft': rft / pft * (1 - pft),
            'oreb': rate('oreb'), 'dreb': rate('dreb'), 'ast': rate('ast'), 'stl': rate('stl'), 'blk': rate('blk'), 'tov': rate('tov'),
            'value': (t.get('pts', 0) + 0.7 * t.get('ast', 0) + K * (lpm['pts'] + 0.7 * lpm['ast']) * 0.8) / (mins + K),
            'usual_min': mins / team_gp,
        })
    eligible = sorted([x for x in out if x['availability'] > 0 and x['base_min'] > 0],
                      key=lambda x: (-x['recent_started'], -x['base_min'], x['id']))
    starters = {x['id'] for x in eligible[:5]}
    tau, beta_p, beta_a = MODEL['quarter_prior_seconds'], MODEL['usage_prior_points'], MODEL['usage_prior_assists']
    for x in out:
        x['starter'] = x['id'] in starters
        prior = (priors or {}).get('starter' if x['starter'] else 'bench') or [0.25] * 4
        prof = (Q or {}).get(x['id'])
        sec = prof['sec'][:4] if prof else [0.0] * 4
        S = sum(sec)
        x['qshare'] = [(sec[k] + tau * prior[k]) / (S + tau) for k in range(4)]
        def usage(stat, beta):
            if not prof or not S:
                return [1.0] * 4
            total = sum(prof[stat][:4])
            return [(prof[stat][k] + beta) / (total * sec[k] / S + beta) for k in range(4)]
        x['u_pts'], x['u_ast'] = usage('pts', beta_p), usage('ast', beta_a)
    out.sort(key=lambda x: (not x['starter'], -x['base_min'] * max(x['availability'], 0.01), x['id']))
    return out


def multinomial_rows(rng, n, weights):
    totals = weights.sum(axis=1, keepdims=True)
    probs = np.where(totals > 0, weights / np.where(totals > 0, totals, 1), 1.0 / weights.shape[1])
    return rng.multinomial(n, probs)


def quarter_minutes(mins, share, starters, blowout, rng):
    """Per-world minutes by quarter: rows keep each player's game minutes, columns hold 60 player-minutes."""
    X = mins[:, :, None] * share[None, :, :] * np.exp(rng.normal(0, 0.08, mins.shape + (4,)))
    if starters.any() and (~starters).any():
        X[:, starters, 3] *= (1 - 0.6 * blowout)[:, None]
        X[:, ~starters, 3] *= (1 + blowout)[:, None]
    target = X.sum(axis=2)
    target *= 240 / np.maximum(target.sum(axis=1, keepdims=True), 1e-9)
    for _ in range(8):
        X *= 60 / np.maximum(X.sum(axis=1, keepdims=True), 1e-9)
        np.minimum(X, 12, out=X)
        X *= (target / np.maximum(X.sum(axis=2), 1e-9))[:, :, None]
    X *= 60 / np.maximum(X.sum(axis=1, keepdims=True), 1e-9)
    np.minimum(X, 12, out=X)
    return X


# ---------------------------------------------------------------------------- one game

def simulate_game(game: dict, T: dict, lg: dict, P: dict, registry: dict, day: str, prospective: bool,
                  sims: int | None = None, Q: dict | None = None, priors: dict | None = None) -> dict:
    W = sims or MODEL['sims']
    rng = rng_for(MODEL['id'], day, game['game_id'])
    h, a = game['home_id'], game['away_id']
    exp = team_expectation(T, lg, h, a, bool(int(game.get('neutral') or 0)))
    sides = {'home': h, 'away': a}
    other = {'home': 'away', 'away': 'home'}
    teams, fallbacks = {}, []
    for side, tid in sides.items():
        players = player_inputs(tid, P, registry, lg, T, prospective, Q, priors, game['date_et'])
        if prospective and sum(bool(p['starter']) for p in players) < 5:
            eligible = sorted((p for p in players if p['availability'] > 0),
                              key=lambda p: (-p.get('recent_started', 0), -p['base_min'], p['id']))
            starters = {p['id'] for p in eligible[:5]}
            for player in players:
                player['starter'] = player['id'] in starters
        n = len(players)
        arr = lambda key, players=players: np.array([x[key] for x in players], dtype=float)
        avail = rng.random((W, n)) < arr('availability')
        short = int((avail.sum(axis=1) < 5).sum()) if prospective else 0
        if short:
            raise ValueError(f"{side} in game {game['game_id']}: {short} worlds have fewer than five available players; "
                             'check the roster and availability report')
        raw = arr('base_min') * avail * np.exp(rng.normal(0, 0.10, (W, n)))
        tot = raw.sum(axis=1, keepdims=True)
        mins = np.minimum(raw * (240 / np.where(tot > 0, tot, 1)), 44.0)
        mins *= 240 / np.maximum(mins.sum(axis=1, keepdims=True), 1e-9)
        cold = (np.count_nonzero(raw > 0, axis=1) < 5) if prospective else np.zeros(W, dtype=bool)
        if cold.any():
            mins[cold] = avail[cold] * (240 / avail[cold].sum(axis=1))[:, None]
            count = int(cold.sum())
            fallbacks.append({'side': side, 'worlds': count, 'method': 'equal_share_available',
                              'reason': 'fewer_than_five_positive_minute_inputs'})
            warnings.warn(f"{side} in game {game['game_id']}: {count} worlds lack five positive minute inputs; "
                          'placeholder uses equal shares for available players', RuntimeWarning)
        value = arr('value')
        base = max(1e-9, float((value * arr('usual_min')).sum()))
        strength = np.clip((mins * value).sum(axis=1) / base, 0.8, 1.2) ** 0.35
        teams[side] = {'tid': tid, 'players': players, 'arr': arr, 'mins': mins, 'strength': strength,
                       'rates': team_rates(T, lg, tid), 'starters': np.array([x['starter'] for x in players], dtype=bool),
                       'qshare': np.array([x['qshare'] for x in players]).reshape(n, 4),
                       'u_pts': np.array([x['u_pts'] for x in players]).reshape(n, 4),
                       'u_ast': np.array([x['u_ast'] for x in players]).reshape(n, 4), 'cold': cold}
    sd, rho = MODEL['team_sd'], MODEL['team_rho']
    z1, z2 = rng.standard_normal(W), rng.standard_normal(W)
    zh, za = z1, rho * z1 + math.sqrt(1 - rho * rho) * z2
    mu = {'home': exp['mu_home'] * teams['home']['strength'], 'away': exp['mu_away'] * teams['away']['strength']}
    reg = {'home': np.maximum(60, np.rint(mu['home'] + sd * zh)).astype(np.int64),
           'away': np.maximum(60, np.rint(mu['away'] + sd * za)).astype(np.int64)}
    pts_by_period = {}
    for side in sides:
        shares = rng.dirichlet(400 * np.array(teams[side]['rates']['quarter_share']), size=W)
        pts_by_period[side] = np.zeros((W, 5), np.int64)
        pts_by_period[side][:, :4] = rng.multinomial(reg[side], shares)
    n_ot = np.zeros(W, np.int64)
    tied = reg['home'] == reg['away']
    for _ in range(8):
        idx = np.flatnonzero(tied)
        if not idx.size:
            break
        for side in sides:
            pts_by_period[side][idx, 4] += np.maximum(0, np.rint(rng.normal(mu[side][idx] * 5 / 48, 3.6))).astype(np.int64)
        n_ot[idx] += 1
        tied = pts_by_period['home'].sum(1) == pts_by_period['away'].sum(1)
    pts_by_period['home'][np.flatnonzero(tied), 4] += 1  # vanishingly rare after eight periods
    final = {s: pts_by_period[s].sum(1) for s in sides}
    m3 = pts_by_period['home'][:, :3].sum(1) - pts_by_period['away'][:, :3].sum(1)
    blowout = np.clip((np.abs(m3) - 12) / 15, 0, 1)

    for side, team in teams.items():
        X = quarter_minutes(team['mins'], team['qshare'], team['starters'], blowout, rng)
        if team['cold'].any():
            X[team['cold']] = team['mins'][team['cold'], :, None] / 4
        closers = X[:, :, 3] + 1e-9 * (team['mins'] > 0)
        otm = (25 * n_ot)[:, None] * closers / np.maximum(closers.sum(axis=1, keepdims=True), 1e-12)
        team['minutes'] = np.concatenate([X, np.minimum(otm, 5 * n_ot[:, None])[:, :, None]], axis=2)  # (W,P,5)
        team['hot'] = np.exp(rng.normal(0, 0.25, (W, len(team['players']))))
        team['hot_ast'] = np.exp(rng.normal(0, 0.25, (W, len(team['players']))))
        team['box'] = {k: np.zeros((W, len(team['players']), 5), np.int64) for k in BOX}
        team['missed'] = np.zeros((W, 5), np.int64)

    lengths = [12, 12, 12, 12, 5]
    for k in range(5):
        for side, team in teams.items():
            arr, r, box = team['arr'], team['rates'], team['box']
            m = team['minutes'][:, :, k]
            u = team['u_pts'][:, k] if k < 4 else 1.0
            hot = team['hot'] * np.exp(rng.normal(0, 0.15, m.shape))
            pts_k = pts_by_period[side][:, k]
            m3k = rng.binomial(pts_k // 3, np.clip(r['share3'], 0.05, 0.6))
            rest = pts_k - 3 * m3k
            ftk = rng.binomial(rest, np.clip(r['shareft'] / (1 - r['share3']), 0.02, 0.6))
            odd = ((rest - ftk) % 2) == 1
            ftk = np.where(odd & (ftk < rest), ftk + 1, np.where(odd, ftk - 1, ftk))
            m2k = (rest - ftk) // 2
            p3m = multinomial_rows(rng, m3k, arr('r3') * m * hot * u)
            p2m = multinomial_rows(rng, m2k, arr('r2') * m * hot * u)
            pftm = multinomial_rows(rng, ftk, arr('rft') * m * np.sqrt(hot) * u)
            miss3, miss2 = rng.poisson(arr('miss3') * m), rng.poisson(arr('miss2') * m)
            box['fg3m'][:, :, k], box['fg3a'][:, :, k] = p3m, p3m + miss3
            box['fgm'][:, :, k], box['fga'][:, :, k] = p3m + p2m, p3m + p2m + miss3 + miss2
            box['ftm'][:, :, k], box['fta'][:, :, k] = pftm, pftm + rng.poisson(arr('missft') * m)
            box['pts'][:, :, k] = 3 * p3m + 2 * p2m + pftm
            assert np.array_equal(box['pts'][:, :, k].sum(axis=1), pts_k), 'player points must equal team period points'
            team['missed'][:, k] = (miss3 + miss2).sum(axis=1)
            share = lengths[k] / 48 * (n_ot if k == 4 else 1)
            team['tov_k'] = rng.poisson((r['tov_pct'] + teams[other[side]]['rates']['opp_tov_pct']) / 2 * exp['pace'] * share)
        for side, team in teams.items():
            arr, r, box, opp = team['arr'], team['rates'], team['box'], teams[other[side]]
            o = opp['rates']
            m = team['minutes'][:, :, k]
            noise = lambda: np.exp(rng.normal(0, 0.2, m.shape))
            o_pct = np.clip((r['oreb_pct'] + (1 - o['dreb_pct'])) / 2, 0.1, 0.45)
            d_pct = np.clip((r['dreb_pct'] + (1 - o['oreb_pct'])) / 2, 0.55, 0.9)
            box['oreb'][:, :, k] = multinomial_rows(rng, rng.binomial(rng.binomial(team['missed'][:, k], 0.9), o_pct), arr('oreb') * m * noise())
            box['dreb'][:, :, k] = multinomial_rows(rng, rng.binomial(rng.binomial(opp['missed'][:, k], 0.9), d_pct), arr('dreb') * m * noise())
            ua = team['u_ast'][:, k] if k < 4 else 1.0
            box['ast'][:, :, k] = multinomial_rows(rng, rng.binomial(box['fgm'][:, :, k].sum(axis=1), np.clip(r['ast_rate'], 0.4, 0.8)),
                                                   arr('ast') * m * team['hot_ast'] * ua)
            box['tov'][:, :, k] = multinomial_rows(rng, team['tov_k'], arr('tov') * m * noise())
            box['stl'][:, :, k] = multinomial_rows(rng, rng.binomial(opp['tov_k'], np.clip(r['stl_share'], 0.3, 0.8)), arr('stl') * m * noise())
            box['blk'][:, :, k] = multinomial_rows(rng, rng.binomial(opp['missed'][:, k], np.clip(r['blk_per_miss'], 0.03, 0.2)), arr('blk') * m * noise())

    result = package(game, teams, pts_by_period, n_ot, W, exp, MODEL['id'])
    if fallbacks:
        result['fallbacks'] = fallbacks
    return result


def package(game: dict, teams: dict, pts_by_period: dict, n_ot: np.ndarray, W: int, exp: dict, model_id: str, weights=None) -> dict:
    from scripts.forecast_output import game as format_game
    return format_game(game, teams, pts_by_period, n_ot, W, exp, model_id, weights)


# ---------------------------------------------------------------------------- season

def simulate_season(T: dict, lg: dict, master: list[dict], day: str, teams: dict,
                    engine_pts: dict | None = None, sims: int | None = None, params: dict | None = None, weights=None) -> dict:
    """The season from `day` on (D25, D26): every remaining game, in date order, through the team pathway
    (`scripts/pathway.py`) — universe k carries its own offensive and defensive ratings, takes engine world k mod W for
    the play-by-play engine's games (`engine_pts`: game_id → per-world, per-period points) and updates both teams after
    every game. Win % for a game = share of universes in which the home side won it (D16)."""
    from scripts import pathway
    W = sims or MODEL['sims']
    rng = rng_for(pathway.PATHWAY['id'], day, 'season')
    ids = sorted(teams, key=int)
    index = {t: i for i, t in enumerate(ids)}
    remaining = sorted((r for r in master if r['date_et'] >= day), key=lambda r: (r['date_et'], r['tip_utc'], r['game_id']))
    unresolved = [r for r in master if r['date_et'] < day and r['status'] != 'final']
    G = len(remaining)
    if master and all(r.get('season') == '2026-27' for r in master) and (params is None or params.get('competition_schema')):
        from scripts import competitions
        played = competitions.play(T, lg, master, day, teams, engine_pts, W, params, weights)
    else:
        played = pathway.play(T, lg, remaining, W, rng, engine_pts, params)
    from scripts.forecast_output import season as format_season
    return format_season(T, master, day, teams, played, rng, engine_pts, params, weights)
