#!/usr/bin/env python3
"""M6a — aggregation test with real rotations (ENGINE_PLAN §13; HANDOFF step 4).

Do per-decision probabilities add up to the right box scores? For held-out games (a fold's validation window) this
keeps every real segment — its lineups, clock, score, fouls and in-game counts so far (teacher forcing) — and samples
every decision of the chain from node models trained on the fold's training window only:

  event → who → what → location → shot result → assisted/assister, blocked/blocker → rebound/rebounder;
  turnover type → stealer; fouler; free throws (and their rebounds); penalty from the team-foul state.

Every reachable branch of every segment (each possible actor, zone, distance band, …) is scored once with the same
feature code as training (nodes.Chain.dataset on hypothetical rows), then 10,000 worlds are drawn from those tables.
Simulated player box scores are compared with what happened in the same segments: bias by role tier (stars = pre-game
usage ≥ 25%, other starters, bench), 10–90% coverage (randomised PIT) and CRPS against a recent-averages baseline
(the player's last 20 games, per minute, × his real minutes tonight).

Limits of v1, by design: minutes, possessions and segment count are real (fixed), so this tests the decisions given
the flow of the game, not the flow itself (duration, substitutions: M6–M7). Real end-of-period segments and heaves
are left out of both sides.

  .venv/bin/python scripts/aggregate.py --config models/v1.json [--fold F4] [--games 200] [--worlds 10000]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, write_json  # noqa: E402
from scripts import nodes, train  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS  # noqa: E402

SIM_NODES = ['event', 'who', 'what', 'location', 'shot_result', 'assisted', 'assister', 'blocked', 'blocker', 'rebound', 'rebounder',
             'turnover_type', 'stealer', 'fouler', 'free_throw']
STATS = ['pts', 'fga', 'fgm', 'fg3a', 'fg3m', 'fta', 'ftm', 'oreb', 'dreb', 'reb', 'ast', 'stl', 'blk', 'tov', 'pf']
REPORT = ['pts', 'reb', 'ast', 'fg3m', 'stl', 'blk', 'tov', 'fga', 'fta', 'pf']
EVENT_TYPES = ['shot', 'fouled', 'turnover', 'foul', 'violation', 'jump_ball']
ZONES = nodes.ZONES
NB = nodes.LOCATION_BANDS
BAND_ZONE = np.array([i for i, z in enumerate(ZONES) for _ in range(len(nodes.LOCATION_EDGES[z]) + 1)])
FT_COMBOS = [(1, 0), (2, 0), (2, 1), (3, 0), (3, 1), (3, 2)]  # (trip, attempt) → column of the free-throw table
FT_COL = {c: i for i, c in enumerate(FT_COMBOS)}


# ---------------------------------------------------------------------------------------------- hypothetical rows
class Branches(nodes.Chain):
    """A chain whose segments are copies of real segments with some upstream decisions overridden.

    The copies keep everything real (context, both lineups with their profiles and in-game counts); `dataset()` then
    builds features exactly as in training. Labels it returns are meaningless and ignored."""

    def __init__(self, base: nodes.Chain, src, **overrides):
        src = np.asarray(src)
        seg = base.seg.iloc[src].reset_index(drop=True)
        for col, value in overrides.items():
            seg[col] = value
        seg['seg_id'] = np.arange(len(seg))
        self.seg = seg
        self.off = _rekey(base.off, base._pos_off, src)
        self.dfn = _rekey(base.dfn, base._pos_def, src)


def _positions(table, n):
    ids = table['seg_id'].to_numpy()
    start = np.searchsorted(ids, np.arange(n), 'left')
    return start, np.searchsorted(ids, np.arange(n), 'right') - start


def _rekey(table, pos, src):
    start, count = pos[0][src], pos[1][src]
    total = int(count.sum())
    offsets = np.arange(total) - np.repeat(np.cumsum(count) - count, count)
    out = table.iloc[np.repeat(start, count) + offsets].copy()
    out['seg_id'] = np.repeat(np.arange(len(src)), count)
    return out.reset_index(drop=True)


class Scorer:
    """Scores branch tables with fitted node models."""

    def __init__(self, base, fitted):
        self.base, self.fitted = base, fitted

    def _X(self, node, d):
        return d['X'][self.fitted[node]['columns']]  # branch distances are already band means (band_table)

    def probs(self, node, src, **over):
        d = Branches(self.base, src, **over).dataset(node)
        f = self.fitted[node]
        if f.get('intercepts') is not None:  # level recalibration fitted on the latest training slice
            kind = 'binary' if f['model'].num_model_per_iteration() == 1 else 'multiclass'
            P = train.apply_intercepts(f['model'].predict(self._X(node, d), raw_score=True), np.asarray(f['intercepts']), kind)
        else:
            P = f['model'].predict(self._X(node, d))
        if d.get('class_mask') is not None:
            P = P * d['class_mask']
            P = P / P.sum(axis=1, keepdims=True)
        return P, d

    def scores(self, node, src, size, **over):
        """Raw candidate scores ÷ temperature, shape (branches, size); candidates in player-id order."""
        d = Branches(self.base, src, **over).dataset(node)
        z = self.fitted[node]['model'].predict(self._X(node, d), raw_score=True) / self.fitted[node]['temperature']
        if len(z) != len(src) * size or not np.array_equal(d['group'], np.repeat(np.arange(len(src)), size)):
            raise RuntimeError(f'{node}: candidate rows do not line up with branches')
        return z.reshape(len(src), size)


def softmax(z, axis=-1):
    z = z - z.max(axis=axis, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=axis, keepdims=True)


def exclude_self(z):
    """z (..., 5 candidates) → (..., 5 actors, 5 candidates): softmax over the four candidates other than the actor."""
    zz = np.repeat(z[..., None, :], 5, axis=-2)
    idx = np.arange(5)
    zz[..., idx, idx] = -np.inf
    return softmax(zz)


def tables(sc: Scorer, src, off, dfn, bands):
    """Every probability the sampler needs for segments `src` (S); off/dfn: (S, 5) players in id order."""
    S = len(src)
    T = {}
    r5, rB = np.repeat(src, 5), np.repeat(src, NB)
    a5 = off.ravel()
    T['event'], _ = sc.probs('event', src, end_type='shot', zone='rim', heave=False, actor=off[:, 0])
    T['who0'] = softmax(sc.scores('who', src, 5, end_type='shot', zone='rim', heave=False, actor=off[:, 0], fta=0))
    T['who1'] = softmax(sc.scores('who', src, 5, end_type='foul', fta=2, heave=False, actor=off[:, 0]))
    P, _ = sc.probs('what', r5, end_type='shot', zone='rim', heave=False, actor=a5)
    T['what'] = P.reshape(S, 5, -1)
    P, _ = sc.probs('location', np.repeat(src, 25), end_type='shot', heave=False, actor=np.repeat(a5, 5),
                    zone=np.array(ZONES, dtype=object)[np.tile(np.arange(5), S * 5)], distance=10.0, lateral=5.0)
    T['location'] = P.reshape(S, 5, 5, NB)                                  # (S, actor, zone, band)
    # shots by (segment, actor, band)
    r5B = np.repeat(src, 5 * NB)
    aB = np.repeat(a5, NB)
    kB = np.tile(np.arange(NB), S * 5)
    shot = dict(end_type='shot', heave=False, actor=aB, zone=np.array(ZONES, dtype=object)[BAND_ZONE[kB]],
                distance=bands['distance'][kB], lateral=bands['lateral'][kB], and_one=False, fta=0)
    P, _ = sc.probs('shot_result', r5B, made=0.0, **shot)
    T['shot_result'] = P.reshape(S, 5, NB, 3)
    P, _ = sc.probs('assisted', r5B, made=1.0, assister=np.repeat(off[:, 1], 5 * NB), **shot)
    T['assisted'] = P.reshape(S, 5, NB)
    P, _ = sc.probs('blocked', r5B, made=0.0, **shot)
    T['blocked'] = P.reshape(S, 5, NB)
    # by (segment, band): candidate choices that do not depend on the shooter's identity
    kS = np.tile(np.arange(NB), S)
    loc = dict(end_type='shot', heave=False, zone=np.array(ZONES, dtype=object)[BAND_ZONE[kS]], distance=bands['distance'][kS],
               lateral=bands['lateral'][kS], and_one=False)
    z = sc.scores('assister', rB, 5, made=1.0, actor='none', assister=np.repeat(off[:, 0], NB), fta=0, **loc)
    T['assister'] = exclude_self(z.reshape(S, NB, 5))                       # (S, NB, actor, candidate)
    T['blocker'] = softmax(sc.scores('blocker', rB, 5, made=0.0, actor=np.repeat(off[:, 0], NB), blocker=np.repeat(dfn[:, 0], NB),
                                     fta=0, **loc)).reshape(S, NB, 5)
    reb = {}
    for blk in (0, 1):
        P, _ = sc.probs('rebound', rB, made=0.0, fta=0, rebound='def', actor=np.repeat(off[:, 0], NB), value=np.where(BAND_ZONE[kS] >= 3, 3.0, 2.0),
                        blocker=np.repeat(dfn[:, 0], NB) if blk else None, **loc)
        reb[blk] = P.reshape(S, NB, 4)
    T['rebound_shot'] = np.stack([reb[0], reb[1]], axis=2)                 # (S, NB, blocked, side)
    P, _ = sc.probs('rebound', rB, made=1.0, fta=1, rebound='def', actor=np.repeat(off[:, 0], NB), value=np.where(BAND_ZONE[kS] >= 3, 3.0, 2.0),
                    blocker=None, **{**loc, 'and_one': True})
    T['rebound_and1'] = P.reshape(S, NB, 4)
    ft_cases = [('fouled', 2), ('fouled', 3), ('foul', 2)]
    T['rebound_ft'] = np.stack([sc.probs('rebound', src, end_type=e, fta=t, made=np.nan, zone=None, value=np.nan, distance=np.nan,
                                         lateral=np.nan, blocker=None, rebound='def', actor=off[:, 0], heave=False)[0] for e, t in ft_cases], axis=1)
    # rebounder: case = band (shot or and-one) or 21 = free throw; offensive candidates depend on who shot (is_shooter)
    cases = np.tile(np.arange(NB + 1), S)
    rc = np.repeat(src, NB + 1)
    casecol = dict(zone=np.array(list(ZONES) + [None], dtype=object)[np.r_[BAND_ZONE, 5][cases]],
                   distance=np.r_[bands['distance'], np.nan][cases], lateral=np.r_[bands['lateral'], np.nan][cases])
    zd = sc.scores('rebounder', rc, 5, end_type='shot', heave=False, made=0.0, rebound='def', rebounder=np.repeat(dfn[:, 0], NB + 1),
                   actor=np.repeat(off[:, 0], NB + 1), **casecol)
    T['rebounder_def'] = softmax(zd).reshape(S, NB + 1, 5)
    zo = np.empty((S, NB + 1, 5, 5))
    for j in range(5):  # actor slot j
        z = sc.scores('rebounder', rc, 5, end_type='shot', heave=False, made=0.0, rebound='off', rebounder=np.repeat(off[:, (j + 1) % 5], NB + 1),
                      actor=np.repeat(off[:, j], NB + 1), **casecol)
        zo[:, :, j, :] = z.reshape(S, NB + 1, 5)
    T['rebounder_off'] = softmax(zo)                                          # (S, case, actor, candidate)
    P, _ = sc.probs('turnover_type', r5, end_type='turnover', turnover='live', actor=a5, heave=False)
    T['turnover_type'] = P.reshape(S, 5, 3)
    T['stealer'] = softmax(sc.scores('stealer', src, 5, end_type='turnover', turnover='live', stealer=dfn[:, 0], actor=off[:, 0]))
    T['fouler'] = np.stack([softmax(sc.scores('fouler', src, 5, end_type=e, fouler=dfn[:, 0], and_one=False, actor=off[:, 0], fta=2))
                            for e in ('foul', 'fouled')], axis=1)              # (S, shooting, defender)
    ft = np.zeros((S, 5, len(FT_COMBOS)))
    for trip in (1, 2, 3):
        P, d = sc.probs('free_throw', r5, end_type='shot' if trip == 1 else 'fouled', fta=trip, ft_seq='0' * trip, actor=a5,
                        and_one=trip == 1, made=1.0 if trip == 1 else np.nan, heave=False)
        P = P.reshape(S, 5, trip)
        for att in range(trip):
            ft[:, :, FT_COL[(trip, att)]] = P[:, :, att]
    T['free_throw'] = ft
    return T


# ---------------------------------------------------------------------------------------------- sampling
def draw(P, rng):
    """One category per row of P (..., K)."""
    c = np.cumsum(P, axis=-1)
    u = rng.random(P.shape[:-1]) * c[..., -1]
    return np.minimum((u[..., None] > c).sum(axis=-1), P.shape[-1] - 1)


def simulate(T, penalty, worlds, rng):
    """Box-score increments per world for segments S: returns dict stat → (S, W) of (player slot, amount) arrays.

    Player slots: 0–4 offence (id order), 5–9 defence. Returns per stat a pair (slot (S, W), amount (S, W))."""
    S = T['event'].shape[0]
    W = worlds
    s = np.arange(S)[:, None]
    g = lambda table, *idx: table[(s,) + idx]
    ev = draw(np.repeat(T['event'][:, None, :], W, axis=1), rng)
    out = {k: [] for k in STATS}

    def add(stat, slot, amount, mask):
        out[stat].append((np.where(mask, slot, -1), np.where(mask, amount, 0).astype(np.int16)))

    action, dfoul = ev == 0, ev == 1
    a = draw(np.repeat(T['who0'][:, None, :], W, axis=1), rng)
    k = draw(g(T['what'], a), rng)
    shot = action & (k < 5)
    zone = np.minimum(k, 4)
    band = draw(g(T['location'], a, zone), rng)
    res = draw(g(T['shot_result'], a, band), rng)
    made, and1, miss = shot & (res >= 1), shot & (res == 2), shot & (res == 0)
    three = BAND_ZONE[band] >= 3
    add('fga', a, 1, shot)
    add('fgm', a, 1, made)
    add('fg3a', a, 1, shot & three)
    add('fg3m', a, 1, made & three)
    add('pts', a, np.where(three, 3, 2), made)
    assisted = made & (rng.random((S, W)) < g(T['assisted'], a, band))
    add('ast', draw(g(T['assister'], band, a), rng), 1, assisted)
    blocked = miss & (rng.random((S, W)) < g(T['blocked'], a, band))
    add('blk', 5 + draw(g(T['blocker'], band), rng), 1, blocked)
    side = draw(g(T['rebound_shot'], band, blocked.astype(int)), rng)
    rebound(T, s, side, band, a, miss, add, rng)
    # turnovers
    tov = action & (k == 5)
    add('tov', a, 1, tov)
    ttype = draw(g(T['turnover_type'], a), rng)
    add('stl', 5 + draw(np.repeat(T['stealer'][:, None, :], W, axis=1), rng), 1, tov & (ttype == 0))
    add('pf', a, 1, tov & (ttype == 1))
    # fouls and free throws
    shooting_foul = action & (k >= 6)
    add('pf', 5 + draw(np.repeat(T['fouler'][:, None, 1, :], W, axis=1), rng), 1, shooting_foul | and1)
    add('pf', 5 + draw(np.repeat(T['fouler'][:, None, 0, :], W, axis=1), rng), 1, dfoul)
    pen = dfoul & (rng.random((S, W)) < penalty[:, None])
    a_pen = draw(np.repeat(T['who1'][:, None, :], W, axis=1), rng)
    trip = np.select([and1, shooting_foul & (k == 6), shooting_foul & (k == 7), pen], [1, 2, 3, 2], 0)
    shooter = np.where(pen, a_pen, a)
    last_made = np.zeros((S, W), dtype=bool)
    for t in (1, 2, 3):
        for att in range(t):
            m = trip == t
            p = g(T['free_throw'], shooter, np.full((S, W), FT_COL[(t, att)]))
            hit = m & (rng.random((S, W)) < p)
            add('fta', shooter, 1, m)
            add('ftm', shooter, 1, hit)
            add('pts', shooter, 1, hit)
            if att == t - 1:
                last_made |= hit
    ft_miss = (trip > 0) & ~last_made
    case = np.select([and1, (trip == 2) & ~pen, trip == 3, pen], [-1, 0, 1, 2], 0)
    side_ft = np.where(and1, draw(g(T['rebound_and1'], band), rng),
                       draw(g(T['rebound_ft'], np.clip(case, 0, 2)), rng))
    rebound(T, s, side_ft, np.where(and1, band, NB), shooter, ft_miss, add, rng)
    return out


def rebound(T, s, side, case, shooter, mask, add, rng):
    """Credit a rebound: side 0 off (player), 1 team off, 2 def (player), 3 team def; case = band or NB (free throw)."""
    off_p = draw(T['rebounder_off'][s, case, shooter], rng)
    def_p = draw(T['rebounder_def'][s, case], rng)
    add('oreb', off_p, 1, mask & (side == 0))
    add('dreb', 5 + def_p, 1, mask & (side == 2))
    add('reb', off_p, 1, mask & (side == 0))
    add('reb', 5 + def_p, 1, mask & (side == 2))


def accumulate(out, slot_player, n_players, worlds):
    """Sum increments into (stat, world, player) using each segment's slot → game-player index map (S, 10)."""
    S = slot_player.shape[0]
    box = {}
    for stat, parts in out.items():
        total = np.zeros(worlds * n_players)
        for slot, amount in parts:
            ok = slot >= 0
            player = np.take_along_axis(slot_player, np.where(ok, slot, 0), axis=1)
            flat = (np.arange(worlds)[None, :] * n_players + player)[ok]
            total += np.bincount(flat, weights=amount[ok], minlength=worlds * n_players)
        box[stat] = total.reshape(worlds, n_players)
    return box


def expected_events(T, penalty):
    """Expected count of each event over the segments (exact, from the branch tables) — traces a box-score bias to its node."""
    ev = T['event']
    who = T['who0']                                                     # (S, actor)
    what = (who[:, :, None] * T['what']).sum(axis=1)                    # (S, 8)
    shot_zone = who[:, :, None, None] * T['what'][:, :, :5, None] * T['location']   # (S, actor, zone, band)
    shot_band = shot_zone.sum(axis=2)                                   # (S, actor, band)
    res = (shot_band[..., None] * T['shot_result']).sum(axis=(1, 2))    # (S, 3) miss / make / and-one per action
    tt = (who[:, :, None] * T['turnover_type']).sum(axis=1)             # (S, 3) given a turnover-what
    act = ev[:, 0]
    out = {'action': act, 'def_foul': ev[:, 1], 'violation': ev[:, 2], 'team_turnover': ev[:, 3],
           'penalty_trips': ev[:, 1] * penalty, 'fga': act * what[:, :5].sum(axis=1), 'fgm': act * res[:, 1:].sum(axis=1),
           'and_one': act * res[:, 2], 'fg3a': act * shot_band[:, :, BAND_ZONE >= 3].sum(axis=(1, 2)),
           'turnover': act * what[:, 5], 'live_turnover': act * what[:, 5] * tt[:, 0], 'offensive_foul': act * what[:, 5] * tt[:, 1],
           'shooting_foul_2': act * what[:, 6], 'shooting_foul_3': act * what[:, 7]}
    return {k: float(v.sum()) for k, v in out.items()}


def actual_events(gseg):
    e, f = gseg['end_type'], gseg['fta'] > 0
    shot = e == 'shot'
    return {'action': float(e.isin(['shot', 'fouled']).sum() + ((e == 'turnover') & gseg['actor'].notna()).sum()),
            'def_foul': float((e == 'foul').sum()), 'violation': float(e.isin(['violation', 'jump_ball']).sum()),
            'team_turnover': float(((e == 'turnover') & gseg['actor'].isna()).sum()), 'penalty_trips': float(((e == 'foul') & f).sum()),
            'fga': float(shot.sum()), 'fgm': float((shot & (gseg['made'] == 1)).sum()), 'and_one': float((shot & (gseg['and_one'] == True)).sum()),
            'fg3a': float((shot & (gseg['value'] == 3)).sum()), 'turnover': float(((e == 'turnover') & gseg['actor'].notna()).sum()),
            'live_turnover': float(((e == 'turnover') & gseg['actor'].notna() & (gseg['turnover'] == 'live')).sum()),
            'offensive_foul': float(((e == 'turnover') & gseg['actor'].notna() & (gseg['fouler'] == gseg['actor'])).sum()),
            'shooting_foul_2': float(((e == 'fouled') & (gseg['fta'] < 3)).sum()), 'shooting_foul_3': float(((e == 'fouled') & (gseg['fta'] >= 3)).sum())}


# ---------------------------------------------------------------------------------------------- actuals and scoring
def chunk_sizes(worlds, size=2000):
    """Worlds are simulated in chunks to bound memory (≈ segments × chunk × 21 bands floats)."""
    return [size] * (worlds // size) + ([worlds % size] if worlds % size else [])


def actual_stats(seg: pd.DataFrame) -> pd.DataFrame:
    """Per (game, player) box stats from real segments, with the sampler's definitions."""
    shots = seg[seg['end_type'] == 'shot']
    three = shots['value'] == 3
    made = shots['made'] == 1
    parts = [
        shots.assign(fga=1, fgm=made.astype(int), fg3a=three.astype(int), fg3m=(made & three).astype(int),
                     pts=np.where(made, shots['value'], 0)).groupby(['game_id', 'actor'])[['fga', 'fgm', 'fg3a', 'fg3m', 'pts']].sum(),
        seg[seg['fta'] > 0].groupby(['game_id', 'actor'])[['fta', 'ftm']].sum(),
        seg[seg['end_type'] == 'turnover'].groupby(['game_id', 'actor']).size().rename('tov'),
        seg[seg['rebound'] == 'off'].groupby(['game_id', 'rebounder']).size().rename('oreb'),
        seg[seg['rebound'] == 'def'].groupby(['game_id', 'rebounder']).size().rename('dreb'),
        seg[seg['assister'].notna()].groupby(['game_id', 'assister']).size().rename('ast'),
        seg[seg['stealer'].notna()].groupby(['game_id', 'stealer']).size().rename('stl'),
        seg[seg['blocker'].notna()].groupby(['game_id', 'blocker']).size().rename('blk'),
        seg[seg['fouler'].notna()].groupby(['game_id', 'fouler']).size().rename('pf'),
    ]
    for p in parts:
        p.index.names = ['game_id', 'player']
    df = pd.concat(parts, axis=1).fillna(0)
    df['pts'] = df['pts'] + df['ftm']
    df['reb'] = df['oreb'] + df['dreb']
    return df.reset_index()


def crps_samples(x, y):
    """CRPS of empirical samples x (n, m) for outcomes y (m)."""
    n = x.shape[0]
    xs = np.sort(x, axis=0)
    w = (2 * np.arange(1, n + 1) - n - 1)[:, None]
    return np.abs(x - y[None, :]).mean(axis=0) - (w * xs).sum(axis=0) / n ** 2


def pit(x, y, rng):
    below = (x < y[None, :]).mean(axis=0)
    at = (x <= y[None, :]).mean(axis=0)
    return below + rng.random(len(y)) * (at - below)


# ---------------------------------------------------------------------------------------------- driver
def fit_models(fold, spec_path, threads):
    """Node models trained on the fold's training window only; kept in data/models/folds/ and reused while the settings
    and the dataset cache signature are unchanged."""
    import lightgbm as lgb
    spec = json.loads(Path(spec_path).read_text()) if spec_path else {'version': 'default', 'default': {}, 'nodes': {}}
    base = {'half_life': None, 'playoff_weight': 1.0, 'drop': [], 'features': None, 'seed': 7, **spec.get('default', {}), 'threads': threads}
    pregame = Path(base['features']) if base.get('features') else None
    folder = train.MODELS / 'folds' / f"{spec.get('version', 'default')}_{fold}"
    key = json.dumps({'spec': spec, 'signature': nodes.signature(pregame), 'nodes': SIM_NODES}, sort_keys=True, default=str)
    meta_path = folder / 'meta.json'
    if meta_path.exists() and json.loads(meta_path.read_text())['key'] == key:
        meta = json.loads(meta_path.read_text())
        fitted = {n: {**m, 'model': lgb.Booster(model_file=str(folder / f'{n}.txt'))} for n, m in meta['fitted'].items()}
        print(f'fold models reused from {folder}', flush=True)
        return fitted, meta['metrics'], spec
    fitted, metrics = {}, {}
    for d in nodes.datasets(SIM_NODES, pregame=pregame):
        cfg = {**base, **spec.get('nodes', {}).get(d['name'], {})}
        r, _, f = train.run_node(d, fold, FOLDS[fold], cfg)
        fitted[d['name']], metrics[d['name']] = f, {k: r[k] for k in ('model', 'league', 'profile', 'gain_vs_best_baseline', 'ece_model')}
        print(f"fit {d['name']:14} {fold}  gain {r['gain_vs_best_baseline']:+.2%}  it {r['iterations']}", flush=True)
    folder.mkdir(parents=True, exist_ok=True)
    for n, f in fitted.items():
        f['model'].save_model(str(folder / f'{n}.txt'), num_iteration=f['model'].best_iteration)
    meta = {'key': key, 'metrics': metrics, 'fitted': {n: {k: v for k, v in f.items() if k != 'model'} for n, f in fitted.items()}}
    meta_path.write_text(json.dumps(meta, default=float))
    return fitted, metrics, spec


def band_table(base, train_to):
    s = base.seg
    shots = s[(s['end_type'] == 'shot') & ~s['heave'].fillna(False).astype(bool) & s['zone'].isin(ZONES) & s['distance'].notna()
              & (s['date_et'] <= train_to)]
    b = nodes.location_band(shots['zone'].to_numpy(), shots['distance'].to_numpy())
    g = pd.DataFrame({'b': b, 'd': shots['distance'].to_numpy(), 'l': shots['lateral'].to_numpy()}).groupby('b').mean().reindex(range(NB))
    return {'distance': g['d'].to_numpy(), 'lateral': g['l'].to_numpy()}


def penalty_table(base, train_to):
    """P(free throws | non-shooting defensive foul) by overtime, last two minutes and team fouls (0–4+): the bonus rule."""
    s = base.seg
    f = s[(s['end_type'] == 'foul') & (s['date_et'] <= train_to)]
    key = lambda x: ((x['period'] >= 5).astype(int) * 10 + (x['start_clock'] <= 120).astype(int) * 5 + x['fouls_def'].clip(upper=4)).to_numpy()
    rate = pd.Series(f['fta'].to_numpy() > 0).groupby(key(f)).mean()
    return lambda rows: pd.Series(key(rows)).map(rate).fillna(0.99).to_numpy()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--config', type=Path, default=None, help='model version settings (models/<version>.json)')
    ap.add_argument('--fold', default='F4')
    ap.add_argument('--games', type=int, default=0, help='random sample of held-out games (0 = all)')
    ap.add_argument('--worlds', type=int, default=10_000)
    ap.add_argument('--threads', type=int, default=12)
    ap.add_argument('--seed', type=int, default=20261119)
    args = ap.parse_args()
    start = time.time()
    train_to, val_from, val_to = FOLDS[args.fold]
    fitted, node_metrics, spec = fit_models(args.fold, args.config, args.threads)
    base = nodes.Chain(pregame=Path(spec['default']['features']) if spec.get('default', {}).get('features') else None)
    assert (base.seg['seg_id'].to_numpy() == np.arange(len(base.seg))).all()
    base._pos_off, base._pos_def = _positions(base.off, len(base.seg)), _positions(base.dfn, len(base.seg))
    bands = band_table(base, train_to)
    penalty_of = penalty_table(base, train_to)
    sc = Scorer(base, fitted)
    seg = base.seg
    held = seg[(seg['date_et'] >= val_from) & (seg['date_et'] <= val_to)]
    games = np.array(sorted(held['game_id'].unique()))
    rng = np.random.default_rng(args.seed)
    if args.games and args.games < len(games):
        games = np.sort(rng.choice(games, args.games, replace=False))
    pre = pd.read_parquet(DERIVED / 'features' / 'pregame.parquet', columns=['game_id', 'player', 'date_et', 'usage', 'starter'])
    minutes = pd.concat([pd.read_parquet(p, columns=['game_id', 'player', 'date_et', 'sec']) for p in sorted((DERIVED / 'history').glob('*/on_court.parquet'))])
    eligible_all = seg['end_type'].isin(EVENT_TYPES) & ~seg['heave'].fillna(False).astype(bool)
    hist = actual_stats(seg[eligible_all]).merge(minutes, on=['game_id', 'player'], how='right').fillna({s: 0 for s in STATS})
    hist = hist.sort_values(['player', 'date_et']).reset_index(drop=True)
    by_player = {p: g for p, g in hist.groupby('player')}
    rows, team_rows = [], []
    events = {k: [0.0, 0.0] for k in ('action', 'def_foul', 'violation', 'team_turnover', 'penalty_trips', 'fga', 'fgm', 'and_one', 'fg3a',
                                      'turnover', 'live_turnover', 'offensive_foul', 'shooting_foul_2', 'shooting_foul_3')}
    for gi, game in enumerate(games):
        gseg = seg[(seg['game_id'] == game) & eligible_all]
        src = gseg['seg_id'].to_numpy()
        pick = lambda table, pos: table['player'].to_numpy()[np.minimum(np.repeat(pos[0][src], 5) + np.tile(np.arange(5), len(src)),
                                                                        len(table) - 1)].reshape(-1, 5)
        off, dfn = pick(base.off, base._pos_off), pick(base.dfn, base._pos_def)
        five = (base._pos_off[1][src] == 5) & (base._pos_def[1][src] == 5)
        src, off, dfn, gseg = src[five], off[five], dfn[five], gseg[five]
        T = tables(sc, src, off, dfn, bands)
        exp_ev, act_ev = expected_events(T, penalty_of(gseg)), actual_events(gseg)
        for k in exp_ev:
            events[k][0] += exp_ev[k]
            events[k][1] += act_ev[k]
        players = np.unique(np.concatenate([off.ravel(), dfn.ravel()]))
        slot_player = np.searchsorted(players, np.concatenate([off, dfn], axis=1))
        game_rng = np.random.default_rng([args.seed, int(game)])
        pen = penalty_of(gseg)
        chunks = [accumulate(simulate(T, pen, n, game_rng), slot_player, len(players), n) for n in chunk_sizes(args.worlds)]
        box = {stat: np.concatenate([c[stat] for c in chunks]) for stat in STATS}
        act = actual_stats(gseg).set_index('player').reindex(players).fillna(0)
        date = gseg['date_et'].iloc[0]
        # team points: each player's team from the side he was on
        team_of = pd.Series(np.concatenate([np.repeat(gseg['offense'].to_numpy(), 5), np.repeat(gseg['defense'].to_numpy(), 5)]),
                            index=np.concatenate([off.ravel(), dfn.ravel()]))
        team_of = team_of[~team_of.index.duplicated()].reindex(players).to_numpy()
        home = gseg.loc[gseg['off_home'] == 1, 'offense'].iloc[0]
        sim_team = {t: box['pts'][:, team_of == t].sum(axis=1) for t in np.unique(team_of)}
        act_team = {t: float(act['pts'].to_numpy()[team_of == t].sum()) for t in sim_team}
        away = [t for t in sim_team if t != home][0]
        for label, x, y in (('home_pts', sim_team[home], act_team[home]), ('away_pts', sim_team[away], act_team[away]),
                            ('margin', sim_team[home] - sim_team[away], act_team[home] - act_team[away]),
                            ('total', sim_team[home] + sim_team[away], act_team[home] + act_team[away])):
            team_rows.append({'game_id': game, 'measure': label, 'actual': y, 'sim': float(x.mean()), 'sd': float(x.std()),
                              'crps': float(crps_samples(x[:, None], np.array([y]))[0]), 'pit': float(pit(x[:, None], np.array([y]), rng)[0])})
        for j, p in enumerate(players):
            row = {'game_id': game, 'player': p, 'date_et': date}
            past = by_player.get(p)
            past = past[(past['date_et'] < date) & (past['sec'] >= 300)].tail(20) if past is not None else None
            sec = minutes[(minutes['game_id'] == game) & (minutes['player'] == p)]['sec']
            row['sec'] = float(sec.iloc[0]) if len(sec) else np.nan
            for stat in STATS:  # means of every stat (accounting identities are checked by smoke.py)
                row[f'{stat}_actual'], row[f'{stat}_sim'] = float(act.loc[p, stat]), float(box[stat][:, j].mean())
            for stat in REPORT:
                x = box[stat][:, j]
                y = float(act.loc[p, stat])
                row[f'{stat}_crps'] = float(crps_samples(x[:, None], np.array([y]))[0])
                row[f'{stat}_pit'] = float(pit(x[:, None], np.array([y]), rng)[0])
                if past is not None and len(past) >= 5 and row['sec'] == row['sec']:
                    xb = (past[stat] / past['sec']).to_numpy() * row['sec']
                    row[f'{stat}_base_crps'] = float(crps_samples(xb[:, None], np.array([y]))[0])
            rows.append(row)
        if gi % 10 == 0:
            print(f'game {gi + 1}/{len(games)}  {game}  {len(src)} segments  {time.time() - start:.0f}s', flush=True)
    res = pd.DataFrame(rows).merge(pre[['game_id', 'player', 'usage', 'starter']], on=['game_id', 'player'], how='left')
    res['tier'] = np.where(res['usage'] >= 0.25, 'star', np.where(res['starter'] == True, 'starter', 'bench'))
    summary = summarise(res)
    summary['events'] = {k: {'expected': round(e, 1), 'actual': round(a, 1), 'rel_bias': round(e / a - 1, 4) if a else None} for k, (e, a) in events.items()}
    teams = pd.DataFrame(team_rows)
    summary['team'] = {m: {'games': len(g), 'actual': round(float(g['actual'].mean()), 2), 'sim': round(float(g['sim'].mean()), 2),
                           'bias': round(float((g['sim'] - g['actual']).mean()), 2), 'sim_sd': round(float(g['sd'].mean()), 2),
                           'actual_sd_around_sim': round(float((g['actual'] - g['sim']).std()), 2),
                           'coverage_10_90': round(float(g['pit'].between(0.1, 0.9).mean()), 3), 'crps': round(float(g['crps'].mean()), 3)}
                       for m, g in teams.groupby('measure')}
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    (DERIVED / 'experiments').mkdir(parents=True, exist_ok=True)
    res.to_parquet(DERIVED / 'experiments' / f'{stamp}_m6a.parquet', index=False)
    teams.to_parquet(DERIVED / 'experiments' / f'{stamp}_m6a_teams.parquet', index=False)
    write_json(EXPERIMENTS / f'{stamp}_m6a.json', {'experiment': 'm6a_aggregation', 'run': stamp, 'commit': train.git_commit(),
                                                   'config': str(args.config) if args.config else None, 'fold': args.fold,
                                                   'games': len(games), 'worlds': args.worlds, 'seconds': round(time.time() - start),
                                                   'node_fit': node_metrics, 'summary': summary}, pretty=True)
    print_summary(summary)
    print(f'\nrun {stamp}_m6a  ({len(games)} games, {time.time() - start:.0f}s)')


def summarise(res):
    out = {}
    for tier in ['star', 'starter', 'bench', 'all']:
        r = res if tier == 'all' else res[res['tier'] == tier]
        r = r[r['sec'] > 0]
        out[tier] = {'player_games': len(r)}
        for stat in REPORT:
            a, s = r[f'{stat}_actual'], r[f'{stat}_sim']
            base = r[f'{stat}_base_crps'] if f'{stat}_base_crps' in r else pd.Series(dtype=float)
            both = base.notna()
            out[tier][stat] = {'actual': round(float(a.mean()), 3), 'sim': round(float(s.mean()), 3),
                               'bias': round(float((s - a).mean()), 3), 'rel_bias': round(float(s.sum() / max(a.sum(), 1e-9) - 1), 4),
                               'coverage_10_90': round(float(r[f'{stat}_pit'].between(0.1, 0.9).mean()), 3),
                               'crps': round(float(r.loc[both, f'{stat}_crps'].mean()), 4) if both.any() else None,
                               'crps_baseline': round(float(base[both].mean()), 4) if both.any() else None}
    return out


def print_summary(summary):
    print(f"{'event':16} {'expected':>10} {'actual':>10} {'bias':>7}")
    for k, x in summary.get('events', {}).items():
        print(f"{k:16} {x['expected']:10.1f} {x['actual']:10.1f} {x['rel_bias'] if x['rel_bias'] is not None else float('nan'):+7.1%}")
    print(f"{'team':9} {'actual':>7} {'sim':>7} {'bias':>6} {'sim sd':>7} {'real sd':>8} {'cover':>6} {'CRPS':>6}")
    for m, x in summary.get('team', {}).items():
        print(f"{m:9} {x['actual']:7.2f} {x['sim']:7.2f} {x['bias']:+6.2f} {x['sim_sd']:7.2f} {x['actual_sd_around_sim']:8.2f} "
              f"{x['coverage_10_90']:6.1%} {x['crps']:6.2f}")
    print(f"\n{'tier':8} {'stat':5} {'actual':>7} {'sim':>7} {'bias':>7} {'rel':>7} {'cover':>6} {'CRPS':>7} {'base':>7} {'skill':>6}")
    for tier, t in summary.items():
        if tier in ('team', 'events'):
            continue
        for stat in REPORT:
            x = t[stat]
            skill = 1 - x['crps'] / x['crps_baseline'] if x['crps'] and x['crps_baseline'] else float('nan')
            print(f"{tier:8} {stat:5} {x['actual']:7.2f} {x['sim']:7.2f} {x['bias']:+7.2f} {x['rel_bias']:+7.1%} {x['coverage_10_90']:6.1%} "
                  f"{x['crps'] or float('nan'):7.3f} {x['crps_baseline'] or float('nan'):7.3f} {skill:+6.1%}")
        print(f"{'':8} ({t['player_games']} player-games)")


if __name__ == '__main__':
    main()
