#!/usr/bin/env python3
"""Possession engine v1 — preview (ENGINE_PLAN §2–§3; M6 brought forward as a labelled preview).

Plays a game forward, segment by segment on the game clock, in W worlds at once, with the persisted v1 node models
(data/models/v1/): duration → event → who → what → location → shot result → assisted/assister, blocked/blocker →
rebound/rebounder; turnover type → stealer; fouler; free throws; penalty from the team-foul state. Every world carries
its own score, team fouls, personal fouls (foul-outs), in-game counts and minutes. Rotations are replayed from the
team's last ten games (M3 replay v0: a template per world, mapped to tonight's available players; overtime keeps the
closing five). Output is the app's game contract (projection.package), so the app needs no change.

Preview limits, labelled in the app: not yet backtested (M9 gate); rotations are replay v0 (M7 will be target-aware);
end-of-period possessions shoot at the buzzer with the normal models (no heave rule); no timeouts or technical free
throws; live-data adapter skew (FINDINGS §3h′) not yet fixed.

  .venv/bin/python scripts/engine.py --game <game_id> [--worlds 2000]     one game from the master fixtures (today's inputs)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED  # noqa: E402
from scripts import nodes, projection, rotations  # noqa: E402

ENGINE = {'id': 'engine-v1-preview', 'kind': 'preview', 'version': 'v1', 'sims': 2000,
          'label': 'Possession engine v1 (preview) — possession-by-possession simulation from the v1 decision models; '
                   'rotations replayed from recent games; not yet backtested against the placeholder (M9)'}
MODELS = DERIVED.parent / 'models'
ZONES = nodes.ZONES
NB = nodes.LOCATION_BANDS
BAND_ZONE = np.array([i for i, z in enumerate(ZONES) for _ in range(len(nodes.LOCATION_EDGES[z]) + 1)])
S = {s: i for i, s in enumerate(nodes.START_TYPES)}  # start-type codes as in training
OFF_REL, DEF_REL = ('usage', 'ast_rate', 'oreb_pct', 'shot_share'), ('blk_rate', 'stl_rate', 'dreb_pct', 'pf_rate')
IN_GAME = nodes.IN_GAME
STATS = projection.BOX + ('pf',)


def draw(P, rng):
    c = np.cumsum(P, axis=-1)
    u = rng.random(P.shape[:-1]) * c[..., -1]
    return np.minimum((u[..., None] > c).sum(axis=-1), P.shape[-1] - 1)


def softmax(z):
    z = z - z.max(axis=-1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=-1, keepdims=True)


class Models:
    """The persisted node models with their input lists, plus the rules' tables (bands, penalty, fill medians)."""

    def __init__(self, version: str = 'v1'):
        folder = MODELS / version
        self.cfg = json.loads((folder / 'config.json').read_text())
        self.nodes = self.cfg['nodes']
        self.boosters = {n: lgb.Booster(model_file=str(folder / m['file'])) for n, m in self.nodes.items()}
        hist = pd.concat([pd.read_parquet(p, columns=['date_et', 'game_ok', 'end_type', 'heave', 'zone', 'x', 'y', 'fta', 'period',
                                                       'start_clock', 'fouls_def', 'made', 'duration', 'shot_time'])
                          for p in sorted((DERIVED / 'history').glob('*/segments.parquet'))])
        hist = hist[hist['game_ok'] & (hist['date_et'] <= self.cfg['train_through'])]
        # Clock between the action and the next segment (the duration node predicts time to the action only): a missed
        # shot runs ~2.4 s until the rebound, a shooting foul ~0.5 s; made shots, turnovers and other fouls ~0 (FINDINGS §3j).
        gap = (hist['duration'] - hist['shot_time'].clip(lower=0)).clip(lower=0)
        missed = (hist['end_type'] == 'shot') & (hist['made'] != 1) & ~hist['heave'].fillna(False).astype(bool)
        self.miss_gap = [gap[missed & (hist['zone'] == z)].to_numpy(np.float32) for z in ZONES]
        self.foul_gap = gap[hist['end_type'] == 'fouled'].to_numpy(np.float32)
        # Seconds within each duration bin, as recorded (clocks are mostly whole seconds: a 2–4 s bin holds 2 and 3, mean
        # 2.5, not 3 — uniform sampling added ~0.5 s per segment).
        timed = hist[(hist['start_clock'] > 24) & ~hist['end_type'].isin(['end_period', 'unknown'])]
        t = timed['shot_time'].clip(lower=0).to_numpy(np.float32)
        b = np.digitize(t, nodes.DURATION_EDGES)
        self.bin_secs = [t[b == k] for k in range(len(nodes.DURATION_EDGES) + 1)]
        # End of period (≤ 24 s left; the duration node was trained on longer clocks): time to the action, or no action
        # before the buzzer, drawn from real segments that started with the same whole seconds left.
        late = hist[hist['start_clock'] <= 24]
        bucket = np.floor(late['start_clock']).clip(0, 24).astype(int).to_numpy()
        lt = np.minimum(late['shot_time'].clip(lower=0).fillna(0).to_numpy(np.float32), late['start_clock'].to_numpy(np.float32))
        none = late['end_type'].isin(['end_period', 'unknown']).to_numpy()
        self.late = [(lt[bucket == k], none[bucket == k]) for k in range(25)]
        shots = hist[(hist['end_type'] == 'shot') & ~hist['heave'].fillna(False).astype(bool) & hist['zone'].isin(ZONES)]
        d = np.sqrt((shots['x'] - 25) ** 2 + shots['y'] ** 2).to_numpy()
        band = nodes.location_band(shots['zone'].to_numpy(), d)
        g = pd.DataFrame({'b': band, 'd': d, 'l': (shots['x'] - 25).abs().to_numpy()})
        g = g[g['b'] >= 0].groupby('b').mean().reindex(range(NB))
        self.band_d, self.band_l = g['d'].to_numpy(np.float32), g['l'].to_numpy(np.float32)
        f = hist[hist['end_type'] == 'foul']
        key = ((f['period'] >= 5).astype(int) * 10 + (f['start_clock'] <= 120).astype(int) * 5 + f['fouls_def'].clip(upper=4)).to_numpy()
        self.penalty = pd.Series(f['fta'].to_numpy() > 0).groupby(key).mean().reindex(range(20)).fillna(0.99).to_numpy()
        pre = pd.read_parquet(DERIVED / 'features' / 'pregame.parquet', columns=list(OFF_REL + DEF_REL))
        self.median = {c: float(pre[c].median()) for c in OFF_REL + DEF_REL}

    def predict(self, node, cols: dict, n: int):
        m = self.nodes[node]
        X = np.empty((n, len(m['columns'])), dtype=np.float32)
        for j, c in enumerate(m['columns']):
            X[:, j] = cols[c]
        return self.boosters[node].predict(X, raw_score=m['kind'] == 'candidate')


class Game:
    """One game's players (home then away in one index space), profiles, team style and rotation tables."""

    def __init__(self, game, players: dict, profiles: pd.DataFrame, team_latest: pd.DataFrame, stints: pd.DataFrame, day: str):
        self.game = game
        self.sides = ('home', 'away')
        self.players = players
        self.ids = [p['id'] for s in self.sides for p in players[s]]
        self.side = np.array([i for i, s in enumerate(self.sides) for _ in players[s]])
        n = len(self.ids)
        prof = profiles.set_index('player').reindex(self.ids)
        self.P = {c: prof[c].to_numpy(np.float32) for c in nodes.PROFILE}
        grp = prof['pos'].fillna(pd.Series([p['pos'] for s in self.sides for p in players[s]], index=prof.index)).map(nodes.group)
        self.P['grp_code'] = grp.map({'G': 0, 'F': 1, 'C': 2}).fillna(1).to_numpy(np.float32)
        self.P['is_big'] = (grp == 'C').to_numpy(np.float32)
        self.expected = np.array([p['base_min'] for s in self.sides for p in players[s]], dtype=float)
        self.avail = np.array([p['availability'] for s in self.sides for p in players[s]], dtype=float)
        tl = team_latest.set_index('team')
        self.style, self.rest = {}, {}
        for i, s in enumerate(self.sides):
            tid = game[f'{s}_id']
            row = tl.loc[tid] if tid in tl.index else None
            self.style[i] = {c: (float(row[c]) if row is not None else np.nan) for c in tl.columns if c.startswith(('off_', 'def_'))}
            self.rest[i] = min(7.0, (pd.Timestamp(day) - pd.Timestamp(row['last_game'])).days) if row is not None else 7.0
        start = tl['season_start'].dropna().min() if 'season_start' in tl else day
        self.season_day = float((pd.Timestamp(day) - pd.Timestamp(start)).days)
        self.templates = {i: rotations.templates_for(stints, game[f'{s}_id'], day) for i, s in enumerate(self.sides)}
        self.n = n

    def lineup_tables(self, avail_world: np.ndarray, rng):
        """Per world a combination (template per side, availability pattern) → table (2880 s, 5) of player indices."""
        W = avail_world.shape[0]
        combos, combo_of = {}, np.zeros((W, 2), dtype=np.int64)
        tables = []
        for i in range(2):
            idx = np.flatnonzero(self.side == i)
            temps = self.templates[i]
            choice = rng.choice(len(temps), size=W, p=(w := np.linspace(1, 2, len(temps))) / w.sum()) if temps else np.zeros(W, int)
            for w in range(W):
                key = (i, int(choice[w]), tuple(avail_world[w, idx]))
                if key not in combos:
                    combos[key] = len(tables)
                    tables.append(self._table(i, temps[choice[w]] if temps else None, avail_world[w, idx]))
                combo_of[w, i] = combos[key]
        return np.stack(tables), combo_of

    def _table(self, i, template, avail):
        idx = np.flatnonzero(self.side == i)
        exp = np.where(avail, self.expected[idx], -1e9)
        on = np.zeros((len(idx), 2880), dtype=bool)
        if template is not None:
            players = [{'id': k, 'pos': self.players[self.sides[i]][k]['pos'], 'expected': exp[k]} for k in range(len(idx)) if avail[k]]
            for slot, k in rotations.assign(template, players).items():
                for a, b in template['slots'][slot]['spans']:
                    on[k, int(a):int(np.ceil(b))] = True
        key = on * 1e6 + exp[:, None] + np.arange(len(idx))[:, None] * 1e-6
        key[~avail] = -1e12
        top = np.argsort(-key, axis=0)[:5].T  # (2880, 5) local indices, on court first, then by expected minutes
        return idx[top]


class Worlds:
    """State of W worlds of one game."""

    def __init__(self, g: Game, W: int, rng):
        self.W, n = W, g.n
        self.period = np.ones(W, int)
        self.clock = np.full(W, 720.0)
        self.first = (rng.random(W) < 0.5).astype(int)  # side that wins the opening tip
        self.off = self.first.copy()
        self.start = np.full(W, S['period_start'])
        self.score = np.zeros((W, 2))
        self.tfouls = np.zeros((W, 2))
        self.done = np.zeros(W, bool)
        self.ingame = {c: np.zeros((W, n), np.float32) for c in IN_GAME}
        self.box = {k: np.zeros((W, n, 5), np.int64) for k in STATS}
        self.minutes = np.zeros((W, n, 5))
        self.pts = np.zeros((W, 2, 5), np.int64)
        self.poss = np.zeros((W, 2))  # possessions per team (segments that start a new possession)


class Engine:
    def __init__(self, version: str = 'v1'):
        self.m = Models(version)
        self.diag = None  # set to [] to record (start type, seconds to action, clock) per segment

    # ----------------------------------------------------------------------------- inputs
    def _context(self, g, st, A, L_off, L_def):
        off, dfn = st.off[A], 1 - st.off[A]
        per, clock = st.period[A], st.clock[A]
        c = {'period': per.astype(np.float32), 'start_clock': clock.astype(np.float32),
             'sec_left_game': np.where(per <= 4, (4 - per) * 720 + clock, clock).astype(np.float32),
             'margin': (np.take_along_axis(st.score[A], off[:, None], 1) - np.take_along_axis(st.score[A], dfn[:, None], 1))[:, 0].astype(np.float32),
             'fouls_def': np.take_along_axis(st.tfouls[A], dfn[:, None], 1)[:, 0].astype(np.float32),
             'fouls_off': np.take_along_axis(st.tfouls[A], off[:, None], 1)[:, 0].astype(np.float32),
             'off_home': (off == 0).astype(np.float32), 'season_type': np.full(len(A), 2, np.float32),
             'season': np.full(len(A), float(g.season), np.float32), 'start_code': st.start[A].astype(np.float32),
             'off_rest': np.where(off == 0, g.rest[0], g.rest[1]).astype(np.float32),
             'def_rest': np.where(dfn == 0, g.rest[0], g.rest[1]).astype(np.float32),
             'season_day': np.full(len(A), g.season_day, np.float32)}
        c['clutch'] = ((per >= 4) & (c['sec_left_game'] <= 300) & (np.abs(c['margin']) <= 5)).astype(np.float32)
        for k in ('pace', 'three', 'rim', 'tov', 'foul', 'oreb'):
            c[f'team_o_{k}'] = np.where(off == 0, g.style[0][f'off_{k}'], g.style[1][f'off_{k}']).astype(np.float32)
            c[f'team_d_{k}'] = np.where(dfn == 0, g.style[0][f'def_{k}'], g.style[1][f'def_{k}']).astype(np.float32)
        P = g.P
        o = lambda col: P[col][L_off]
        d = lambda col: P[col][L_def]
        c.update({'off_usage_sum': np.nansum(o('usage'), 1), 'off_usage_max': np.nanmax(o('usage'), 1), 'off_ast_sum': np.nansum(o('ast_rate'), 1),
                  'off_three_sum': np.nansum(o('mix_corner3') + o('mix_above3'), 1), 'off_oreb_sum': np.nansum(o('oreb_pct'), 1),
                  'off_bigs': o('is_big').sum(1), 'off_min_mean': np.nanmean(o('min_avg'), 1),
                  'def_blk_sum': np.nansum(d('blk_rate'), 1), 'def_blk_max': np.nanmax(d('blk_rate'), 1), 'def_stl_sum': np.nansum(d('stl_rate'), 1),
                  'def_dreb_sum': np.nansum(d('dreb_pct'), 1), 'def_pf_sum': np.nansum(d('pf_rate'), 1), 'def_bigs': d('is_big').sum(1),
                  'def_min_mean': np.nanmean(d('min_avg'), 1)})
        return c

    def _five(self, g, st, A, L, rel):
        """Per-candidate columns for a five (|A|, 5): profile, in-game, group, quarter usage now, shares and ranks."""
        P = g.P
        c = {col: P[col][L] for col in nodes.PROFILE}
        for col in IN_GAME:
            c[col] = np.take_along_axis(st.ingame[col][A], L, 1)
        c['grp_code'] = P['grp_code'][L]
        q = np.clip(st.period[A], 1, 4)
        c['usage_mult_now'] = np.choose(q[:, None] - 1, [P[f'usage_mult_q{k}'][L] for k in (1, 2, 3, 4)])
        for col in rel:
            v = np.where(np.isnan(c[col]), self.m.median[col], c[col])
            tot = v.sum(1, keepdims=True)
            c[f'{col}_share'] = np.where(tot > 0, v / np.where(tot > 0, tot, 1), np.nan)
            order = np.argsort(-v, axis=1, kind='stable')
            rank = np.empty_like(order)
            np.put_along_axis(rank, order, np.arange(1, 6)[None, :].repeat(len(A), 0), 1)
            c[f'{col}_rank'] = rank.astype(np.float32)
        return c

    @staticmethod
    def _flat(world_cols, five_cols, keep=None):
        """Candidate rows: world-level columns repeated per candidate, five-level columns flattened; optional mask."""
        out = {k: np.repeat(v, 5) for k, v in world_cols.items()}
        out.update({k: v.reshape(-1) for k, v in five_cols.items()})
        if keep is not None:
            out = {k: v[keep] for k, v in out.items()}
        return out

    @staticmethod
    def _actor(five_cols, slot):
        cols = list(nodes.PROFILE) + list(IN_GAME) + ['grp_code', 'usage_share', 'usage_rank', 'usage_mult_now']
        r = np.arange(len(slot))
        return {f'actor_{c}': five_cols[c][r, slot] for c in cols}

    def _choose(self, node, rows, k, rng, n_groups):
        """Sample one candidate per group of k rows (softmax of raw scores ÷ temperature)."""
        z = self.m.predict(node, rows, n_groups * k).reshape(n_groups, k) / self.m.nodes[node]['temperature']
        return draw(softmax(z), rng)

    # ----------------------------------------------------------------------------- one game
    def simulate(self, g: Game, W: int, seed) -> dict:
        rng = np.random.default_rng(seed)
        st = Worlds(g, W, rng)
        avail_world = rng.random((W, g.n)) < g.avail[None, :]
        tables, combo = g.lineup_tables(avail_world, rng)
        fouled_out = np.zeros((W, g.n), bool)
        m = self.m
        steps = 0
        while not st.done.all() and steps < 2000:
            steps += 1
            A = np.flatnonzero(~st.done)
            n = len(A)
            reg = st.period[A] <= 4
            t = np.where(reg, (st.period[A] - 1) * 720 + np.clip(720 - st.clock[A], 0, 719), 2879).astype(int)
            L = np.stack([tables[combo[A, i], t] for i in range(2)], axis=1)  # (n, 2 sides, 5)
            for i in range(2):  # foul-outs: replace with the best available player not on court
                bad = fouled_out[A[:, None], L[:, i]]
                for r, k in zip(*np.nonzero(bad)):
                    w = A[r]
                    side_idx = np.flatnonzero((g.side == i) & avail_world[w] & ~fouled_out[w] & ~np.isin(np.arange(g.n), L[r, i]))
                    if side_idx.size:
                        L[r, i, k] = side_idx[np.argmax(g.expected[side_idx])]
            off = st.off[A]
            new_poss = ~np.isin(st.start[A], [S['oreb'], S['foul'], S['other']])
            np.add.at(st.poss, (A[new_poss], off[new_poss]), 1)
            L_off = L[np.arange(n), off]
            L_def = L[np.arange(n), 1 - off]
            ctx = self._context(g, st, A, L_off, L_def)
            # duration
            P = m.predict('duration', ctx, n)
            b = draw(P, rng)
            secs = np.zeros(n)
            for k in np.unique(b):
                sel = b == k
                secs[sel] = rng.choice(m.bin_secs[k], size=sel.sum())
            late = np.flatnonzero(st.clock[A] <= 24)
            quiet = np.zeros(n, bool)
            for k in np.unique(np.floor(st.clock[A[late]]).astype(int)):
                sel = late[np.floor(st.clock[A[late]]).astype(int) == k]
                vals, none = m.late[k]
                pick = rng.integers(0, len(vals), size=sel.size)
                secs[sel], quiet[sel] = vals[pick], none[pick]
            secs = np.where(quiet, st.clock[A], np.minimum(secs, st.clock[A]))  # no action: the period runs out
            ctx['shot_time'] = secs.astype(np.float32)
            if self.diag is not None:
                self.diag.append((st.start[A].copy(), secs.copy(), st.clock[A].copy() + 0))
            pidx = np.minimum(st.period[A] - 1, 4)
            for side_L in (L_off, L_def):
                np.add.at(st.minutes, (A[:, None], side_L, pidx[:, None]), secs[:, None] / 60)
                st.ingame['sec_so_far'][A[:, None], side_L] += secs[:, None]
            st.clock[A] -= secs
            # event
            ev = draw(m.predict('event', ctx, n), rng)
            ev = np.where(quiet, -1, ev)
            off_five = self._five(g, st, A, L_off, OFF_REL)
            def_five = self._five(g, st, A, L_def, DEF_REL)
            ctx_who = {**ctx, 'foul_event': np.zeros(n, np.float32)}
            nxt_off, nxt_start = 1 - off, np.full(n, S['made_fg'])
            act = np.flatnonzero(ev == 0)
            actor = np.zeros(n, int)
            if act.size:
                rows = self._flat({k: v[act] for k, v in ctx_who.items()}, {k: v[act] for k, v in off_five.items()})
                actor[act] = self._choose('who', rows, 5, rng, act.size)
            a_glob = L_off[np.arange(n), actor]
            actor_cols = self._actor(off_five, actor)
            wctx = lambda idx, extra=None: {**{k: v[idx] for k, v in ctx.items()}, **{k: v[idx] for k, v in actor_cols.items()}, **(extra or {})}
            what = np.full(n, -1)
            if act.size:
                what[act] = draw(m.predict('what', wctx(act), act.size), rng)
            shot = act[what[act] < 5]
            zone = np.where(what < 5, what, 0)
            band = np.zeros(n, int)
            res = np.zeros(n, int)
            if shot.size:
                Pl = m.predict('location', wctx(shot, {'zone': zone[shot].astype(np.float32)}), shot.size) * nodes.LOCATION_MASK[zone[shot]]
                band[shot] = draw(Pl / Pl.sum(1, keepdims=True), rng)
                loc = {'zone': zone[shot].astype(np.float32), 'distance': m.band_d[band[shot]], 'lateral': m.band_l[band[shot]]}
                res[shot] = draw(m.predict('shot_result', wctx(shot, loc), shot.size), rng)
            made = shot[res[shot] >= 1]
            and1 = shot[res[shot] == 2]
            miss = shot[res[shot] == 0]
            three = BAND_ZONE[band] >= 3
            self._add(st, 'fga', A[shot], a_glob[shot], pidx[shot])
            self._add(st, 'fg3a', A[shot[three[shot]]], a_glob[shot[three[shot]]], pidx[shot[three[shot]]])
            self._add(st, 'fgm', A[made], a_glob[made], pidx[made])
            self._add(st, 'fg3m', A[made[three[made]]], a_glob[made[three[made]]], pidx[made[three[made]]])
            pts_fg = np.where(three, 3, 2)
            self._points(g, st, A, made, a_glob, pidx, pts_fg[made])
            st.ingame['fga_so_far'][A[shot], a_glob[shot]] += 1
            st.ingame['made_so_far'][A[made], a_glob[made]] += 1
            st.ingame['uses_so_far'][A[act], a_glob[act]] += 1
            # assists
            if made.size:
                loc = {'zone': zone[made].astype(np.float32), 'distance': m.band_d[band[made]], 'lateral': m.band_l[band[made]]}
                asst = made[rng.random(made.size) < m.predict('assisted', wctx(made, loc), made.size)]
                if asst.size:
                    keep = (np.arange(5)[None, :] != actor[asst][:, None]).reshape(-1)
                    rows = self._flat({**{k: v[asst] for k, v in ctx.items()}, 'zone': zone[asst].astype(np.float32),
                                       'distance': m.band_d[band[asst]]}, {k: v[asst] for k, v in off_five.items()}, keep)
                    pick = self._choose('assister', rows, 4, rng, asst.size)
                    others = np.array([[j for j in range(5) if j != a] for a in actor[asst]])
                    who_ast = L_off[asst, others[np.arange(asst.size), pick]]
                    self._add(st, 'ast', A[asst], who_ast, pidx[asst])
                    st.ingame['ast_so_far'][A[asst], who_ast] += 1
            # misses: blocks and rebounds
            if miss.size:
                loc = {'zone': zone[miss].astype(np.float32), 'distance': m.band_d[band[miss]], 'lateral': m.band_l[band[miss]]}
                blocked = rng.random(miss.size) < m.predict('blocked', wctx(miss, loc), miss.size)
                bl = miss[blocked]
                if bl.size:
                    rows = self._flat({**{k: v[bl] for k, v in ctx.items()}, 'zone': zone[bl].astype(np.float32), 'distance': m.band_d[band[bl]]},
                                      {k: v[bl] for k, v in def_five.items()})
                    blocker = L_def[bl, self._choose('blocker', rows, 5, rng, bl.size)]
                    self._add(st, 'blk', A[bl], blocker, pidx[bl])
                reb_extra = {**loc, 'value': np.where(three[miss], 3.0, 2.0).astype(np.float32), 'fta': np.zeros(miss.size, np.float32),
                             'ft_miss': np.zeros(miss.size, np.float32), 'blocked': blocked.astype(np.float32)}
                self._rebound(g, st, A, miss, reb_extra, ctx, off_five, def_five, L_off, L_def, actor, pidx, nxt_off, nxt_start, off, rng)
            # turnovers
            tov = act[what[act] == 5]
            if tov.size:
                self._add(st, 'tov', A[tov], a_glob[tov], pidx[tov])
                tt = draw(m.predict('turnover_type', wctx(tov), tov.size), rng)
                live, offf = tov[tt == 0], tov[tt == 1]
                if live.size:
                    rows = self._flat({k: v[live] for k, v in ctx.items()}, {k: v[live] for k, v in def_five.items()})
                    stealer = L_def[live, self._choose('stealer', rows, 5, rng, live.size)]
                    self._add(st, 'stl', A[live], stealer, pidx[live])
                self._foul(st, A[offf], a_glob[offf], pidx[offf])
                nxt_start[tov] = np.where(tt == 0, S['steal'], S['dead_turnover'])
            # fouls: shooting (fouled on a 2 / 3), and-ones, non-shooting
            shooting = np.concatenate([act[what[act] >= 6], and1])
            if shooting.size:
                self._fouler(g, st, A, shooting, 1.0, ctx, def_five, L_def, pidx, rng)
            dfoul = np.flatnonzero(ev == 1)
            if dfoul.size:
                self._fouler(g, st, A, dfoul, 0.0, ctx, def_five, L_def, pidx, rng)
            # free throws: and-one 1, fouled on a 2 → 2, on a 3 → 3, penalty → 2
            trip = np.zeros(n, int)
            trip[and1] = 1
            trip[act[what[act] == 6]] = 2
            trip[act[what[act] == 7]] = 3
            shooter = a_glob.copy()
            ft_actor = actor.copy()
            if dfoul.size:
                key = (st.period[A[dfoul]] >= 5).astype(int) * 10 + (st.clock[A[dfoul]] + ctx['shot_time'][dfoul] <= 120).astype(int) * 5 \
                      + np.minimum(ctx['fouls_def'][dfoul], 4).astype(int)
                pen = dfoul[rng.random(dfoul.size) < m.penalty[key]]
                if pen.size:
                    rows = self._flat({**{k: v[pen] for k, v in ctx.items()}, 'foul_event': np.ones(pen.size, np.float32)},
                                      {k: v[pen] for k, v in off_five.items()})
                    slot = self._choose('who', rows, 5, rng, pen.size)
                    ft_actor[pen], shooter[pen] = slot, L_off[pen, slot]
                    trip[pen] = 2
                    st.ingame['uses_so_far'][A[pen], shooter[pen]] += 1
                nopen = np.setdiff1d(dfoul, pen)
                nxt_off[nopen], nxt_start[nopen] = off[nopen], S['foul']
            fts = np.flatnonzero(trip > 0)
            if fts.size:
                ft_cols = self._actor(off_five, ft_actor)
                last_made = np.zeros(n, bool)
                for att in range(3):
                    rows_i = fts[trip[fts] > att]
                    if not rows_i.size:
                        continue
                    extra = {'and_one': (trip[rows_i] == 1).astype(np.float32), 'attempt': np.full(rows_i.size, att, np.float32),
                             'trip': trip[rows_i].astype(np.float32), 'last_of_trip': (trip[rows_i] == att + 1).astype(np.float32)}
                    cols = {**{k: v[rows_i] for k, v in ctx.items()}, **{k: v[rows_i] for k, v in ft_cols.items()}, **extra}
                    hit = rng.random(rows_i.size) < m.predict('free_throw', cols, rows_i.size)
                    self._add(st, 'fta', A[rows_i], shooter[rows_i], pidx[rows_i])
                    self._add(st, 'ftm', A[rows_i[hit]], shooter[rows_i[hit]], pidx[rows_i[hit]])
                    self._points(g, st, A, rows_i[hit], shooter, pidx, np.ones(hit.sum(), int))
                    last = trip[rows_i] == att + 1
                    last_made[rows_i[last & hit]] = True
                nxt_off[fts], nxt_start[fts] = 1 - off[fts], S['made_ft']
                ftm_miss = fts[~last_made[fts]]
                if ftm_miss.size:
                    is_and1 = trip[ftm_miss] == 1
                    reb_extra = {'zone': np.where(is_and1, zone[ftm_miss], np.nan).astype(np.float32),
                                 'distance': np.where(is_and1, m.band_d[band[ftm_miss]], np.nan).astype(np.float32),
                                 'lateral': np.where(is_and1, m.band_l[band[ftm_miss]], np.nan).astype(np.float32),
                                 'value': np.where(is_and1, np.where(three[ftm_miss], 3.0, 2.0), np.nan).astype(np.float32),
                                 'fta': trip[ftm_miss].astype(np.float32), 'ft_miss': (~is_and1).astype(np.float32),
                                 'blocked': np.zeros(ftm_miss.size, np.float32)}
                    self._rebound(g, st, A, ftm_miss, reb_extra, ctx, off_five, def_five, L_off, L_def, ft_actor, pidx, nxt_off, nxt_start, off, rng)
            # game time after the action: rebound delay after a miss (by zone), the stop around a shooting foul
            gap = np.zeros(n)
            for zi in range(len(ZONES)):
                sel = miss[zone[miss] == zi]
                gap[sel] = rng.choice(m.miss_gap[zi], size=sel.size)
            fouled = act[what[act] >= 6]
            gap[fouled] = rng.choice(m.foul_gap, size=fouled.size)
            gap = np.minimum(gap, st.clock[A])
            if gap.any():
                for side_L in (L_off, L_def):
                    np.add.at(st.minutes, (A[:, None], side_L, pidx[:, None]), gap[:, None] / 60)
                    st.ingame['sec_so_far'][A[:, None], side_L] += gap[:, None]
                st.clock[A] -= gap
            # violations keep the ball; team turnovers give it away
            viol = np.flatnonzero(ev == 2)
            nxt_off[viol], nxt_start[viol] = off[viol], S['other']
            ttov = np.flatnonzero(ev == 3)
            nxt_start[ttov] = S['dead_turnover']
            # carry the possession and handle period ends
            st.off[A], st.start[A] = nxt_off, nxt_start
            ended = A[(st.clock[A] <= 0.0) | quiet]
            self._period_end(st, ended, rng)
        return self._package(g, st, W)

    # ----------------------------------------------------------------------------- state updates
    @staticmethod
    def _add(st, stat, worlds, players, pidx, amount=1):
        if len(worlds):
            np.add.at(st.box[stat], (worlds, players, pidx), amount)

    def _points(self, g, st, A, idx, who, pidx, pts):
        if len(idx):
            np.add.at(st.box['pts'], (A[idx], who[idx], pidx[idx]), pts)
            np.add.at(st.pts, (A[idx], g.side[who[idx]], pidx[idx]), pts)
            np.add.at(st.score, (A[idx], g.side[who[idx]]), pts)
            st.ingame['pts_so_far'][A[idx], who[idx]] += pts

    def _foul(self, st, worlds, players, pidx):
        if len(worlds):
            np.add.at(st.box['pf'], (worlds, players, pidx), 1)
            st.ingame['pf_so_far'][worlds, players] += 1

    def _fouler(self, g, st, A, idx, shooting, ctx, def_five, L_def, pidx, rng):
        rows = self._flat({**{k: v[idx] for k, v in ctx.items()}, 'shooting': np.full(idx.size, shooting, np.float32)},
                          {k: v[idx] for k, v in def_five.items()})
        fouler = L_def[idx, self._choose('fouler', rows, 5, rng, idx.size)]
        self._foul(st, A[idx], fouler, pidx[idx])
        np.add.at(st.tfouls, (A[idx], g.side[fouler]), 1)

    def _rebound(self, g, st, A, idx, extra, ctx, off_five, def_five, L_off, L_def, shooter_slot, pidx, nxt_off, nxt_start, off, rng):
        m = self.m
        cols = {**{k: v[idx] for k, v in ctx.items()}, **extra}
        side = draw(m.predict('rebound', cols, idx.size), rng)  # 0 off, 1 team off, 2 def, 3 team def
        offensive = side <= 1
        nxt_off[idx] = np.where(offensive, off[idx], 1 - off[idx])
        nxt_start[idx] = np.where(offensive, S['oreb'], S['dreb'])
        for flag, five, L, sel in ((1.0, off_five, L_off, idx[side == 0]), (0.0, def_five, L_def, idx[side == 2])):
            if not sel.size:
                continue
            pos = np.searchsorted(idx, sel)
            sub = {k: v[sel] for k, v in five.items()}
            pct = 'oreb_pct' if flag else 'dreb_pct'  # as in training: the side's rate, its share and rank in the five
            sub['reb_side_pct'], sub['reb_share'], sub['reb_rank'] = sub[pct], sub[f'{pct}_share'], sub[f'{pct}_rank']
            sub['offensive'] = np.full((sel.size, 5), flag, np.float32)
            sub['is_shooter'] = ((np.arange(5)[None, :] == shooter_slot[sel][:, None]) & (flag == 1.0)).astype(np.float32)
            wcols = {**{k: v[sel] for k, v in ctx.items()}, 'zone': extra['zone'][pos], 'distance': extra['distance'][pos]}
            who = L[sel, self._choose('rebounder', self._flat(wcols, sub), 5, rng, sel.size)]
            self._add(st, 'oreb' if flag else 'dreb', A[sel], who, np.minimum(st.period[A[sel]] - 1, 4))

    @staticmethod
    def _period_end(st, ended, rng):
        if not len(ended):
            return
        p = st.period[ended]
        tied = st.score[ended, 0] == st.score[ended, 1]
        over = (p >= 4) & ~tied
        st.done[ended[over]] = True
        go = ended[~over]
        st.period[go] += 1
        newp = st.period[go]
        st.clock[go] = np.where(newp <= 4, 720.0, 300.0)
        st.tfouls[go] = 0
        first = st.first[go]
        st.off[go] = np.where(newp == 4, first, np.where(newp <= 3, 1 - first, (rng.random(go.size) < 0.5).astype(int)))
        st.start[go] = S['period_start']

    def _package(self, g, st, W):
        teams = {}
        for i, s in enumerate(g.sides):
            idx = np.flatnonzero(g.side == i)
            teams[s] = {'tid': g.game[f'{s}_id'], 'players': g.players[s], 'minutes': st.minutes[:, idx, :],
                        'box': {k: st.box[k][:, idx, :] for k in projection.BOX}}
        pts = {s: st.pts[:, i, :] for i, s in enumerate(g.sides)}
        n_ot = np.maximum(st.period - 4, 0)
        exp = {'mu_home': float(pts['home'].sum(1).mean()), 'mu_away': float(pts['away'].sum(1).mean()),
               'pace': float(st.poss.mean())}
        out = projection.package(g.game, teams, pts, n_ot, W, exp, ENGINE['id'])
        out['engine'] = {'fouled_out': int((st.box['pf'].sum(2) >= 6).sum()), 'pf_mean': {s: round(float(st.box['pf'][:, np.flatnonzero(g.side == i)].sum((1, 2)).mean()), 2)
                                                                                         for i, s in enumerate(g.sides)}}
        return out


def inputs_for(game: dict, day: str, T, lg, P, registry, Q=None, priors=None):
    """Players (with injury availability and expected minutes) from the placeholder's inputs, profiles as of today."""
    players = {s: [p for p in projection.player_inputs(game[f'{s}_id'], P, registry, lg, T, True, Q, priors) if p['availability'] > 0]
               for s in ('home', 'away')}
    profiles = pd.read_parquet(DERIVED / 'features' / 'latest.parquet')
    team_latest = pd.read_parquet(DERIVED / 'features' / 'team_latest.parquet')
    if profiles['date_et'].max() >= day or team_latest['last_game'].max() >= day:  # cutoff safety: today's slate only
        raise ValueError(f'profiles include games on or after {day}: the engine projects only slates after the latest game')
    stints = pd.read_parquet(DERIVED / 'rotations' / 'stints.parquet')
    g = Game(game, players, profiles, team_latest, stints, day)
    g.season = int(profiles['season'].max())
    return g


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--game', required=True)
    ap.add_argument('--worlds', type=int, default=ENGINE['sims'])
    args = ap.parse_args()
    from scripts import master_fixtures, box_scores
    from scripts.season_stats import period_profiles, player_table, team_table
    from basketball_common import read_json
    master = master_fixtures.load()
    game = next(r for r in master if r['game_id'] == args.game)
    day = game['date_et']
    team_rows, player_rows = box_scores.load_csv('team_games.csv'), box_scores.load_csv('player_games.csv')
    period_rows = box_scores.load_csv('player_periods.csv')
    teams = json.loads((DERIVED / 'teams.json').read_text())
    registry = read_json(DERIVED / 'players.json')['players']
    T, lg = team_table(team_rows, day, teams)
    P = player_table(player_rows, day)
    Q, priors = period_profiles(period_rows, player_rows, day, team_rows, blowout=15)
    start = time.time()
    g = inputs_for(game, day, T, lg, P, registry, Q, priors)
    eng = Engine()
    print(f'inputs {time.time() - start:.1f}s')
    start = time.time()
    out = eng.simulate(g, args.worlds, projection.seed_for(ENGINE['id'], day, game['game_id']))
    fg = out['periods']['fg']
    print(f"{args.worlds} worlds in {time.time() - start:.1f}s  home {fg['home']['pts']['mean']:.1f}  away {fg['away']['pts']['mean']:.1f}  "
          f"home win {fg['home']['win']:.3f}  OT {out['ot']:.3f}  {out['engine']}")
    for s in ('home', 'away'):
        top = sorted(out[s]['players'], key=lambda p: -p.get('periods', {}).get('fg', {}).get('mean', {}).get('pts', 0))[:5]
        print(s, [(p['name'], round(p['periods']['fg']['sec'] / 60, 1), p['periods']['fg']['mean']['pts']) for p in top if 'periods' in p])


if __name__ == '__main__':
    main()
