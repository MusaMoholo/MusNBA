#!/usr/bin/env python3
"""Team engine — every game after the play-by-play horizon, MusSim-style (ENGINE_PLAN D25, D26).

Each universe k carries its own offensive and defensive rating per team (points scored / allowed per 100 possessions)
and plays the remaining schedule in date order:

  start    the season estimate as of the cutoff — the shrunk ratings baseline-v1 uses (K = 8 games of league prior) —
           plus a draw at its posterior SD, SIGMA / sqrt(gp + K): a world's truth is not our best guess at it
  engine   a game inside the play-by-play horizon takes universe k's result from engine world k mod W_engine, so
           both engines share the same draws (D14) and a game's season win % equals the engine's
  later    games draw both scores from the universe's ratings *at that point of its own path*:
           mu_home = pace × off_home × def_away / league / 100 + home court / 2 (baseline-v1's form), scores bivariate
           normal (SD 11.25, rho 0.35; baseline-v1's calibration), rounded; a regulation tie goes to overtime, won
           with the five-minute share of the expected margin
  update   after every game — engine or drawn — both teams move by the rating estimator's own response to one more
           game, gain = SCALE / (n + 1 + K) with n the team's games so far, applied to the surprise against the
           universe's own expectation, s = 100 × (points − mu) / pace: the scorer's offence and the opponent's defence
           move by the same s. The surprise averages zero under the universe's own draw, so favourites do not drift up
           and the schedule does not leak into the ratings.

Pace stays at the cutoff's estimate. v1's settings come from the walk-forward season test (M12 first cut,
`scripts/season_backtest.py --grid`, 2022-23 → 2025-26 from 20 Nov, 25 Dec, 1 Feb, 10 Mar): start draw × 0.4, the
estimator's own gain (SCALE 1) and a 20-game memory (the gain stops shrinking after 20 games, n_cap) — dispersion of final
wins 1.00, 10–90% coverage 84%, CRPS 2.61 v 2.73 for fixed probabilities; chosen in 3 of 4 leave-one-season-out folds.
Still slightly wide in November (dispersion 0.84) and its surprises fade with the date where real ones persist (0.40). Everything is vectorised over universes, one game at a
time: ~1,000 games × 10,000 universes in about a second. Seeded by the caller; identical inputs give identical outputs.
"""
from __future__ import annotations

import math

import numpy as np

PATHWAY = {  # v1: spread calibrated walk-forward on 2022-26 (scripts/season_backtest.py --grid; FINDINGS §3n)
    'id': 'team-pathway-v1', 'kind': 'team-pathway',
    'label': 'Team pathway v1 — per-world offensive and defensive ratings, updated after every simulated game; spread '
             'calibrated walk-forward on 2022-26 (M12 first cut: slightly wide in November)',
    'K': 8, 'sigma': 11.0, 'scale': 1.0, 'start_scale': 0.4, 'n_cap': 20,
    'home_court': 2.0, 'team_sd': 11.25, 'team_rho': 0.35, 'ot_share': 5 / 48,
}


def _shrink(value, n, prior, k):
    if value is None or not n:
        return prior
    return (n * value + k * prior) / (n + k)


def start_ratings(T: dict, lg: dict, ids: list[str], k: float):
    """Per-team shrunk offence, defence and pace (the estimator) and the games behind them."""
    gp = np.array([float(T[t]['gp'] or 0) for t in ids])
    off = np.array([_shrink(T[t]['ortg'], T[t]['gp'], lg['ortg'], k) for t in ids])
    dfn = np.array([_shrink(T[t]['drtg'], T[t]['gp'], lg['ortg'], k) for t in ids])
    pace = np.array([_shrink(T[t]['pace'], T[t]['gp'], lg['pace'], k) for t in ids])
    return off, dfn, pace, gp


def play(T: dict, lg: dict, games: list[dict], W: int, rng: np.random.Generator, engine: dict | None = None,
         params: dict | None = None) -> dict:
    """Play `games` (dicts with game_id, home_id, away_id, neutral; in date order) in W universes.

    engine: game_id → int array (W_engine, 2, P) of per-period points (home, away) for games the play-by-play engine
    played; P ≥ 4 (regulation periods first, then overtime). Returns home_win (W, G) bool, points (W, G, 2) int and the
    final ratings (W, teams) for diagnostics."""
    p = {**PATHWAY, **(params or {})}
    ids = sorted(T, key=int)
    index = {t: i for i, t in enumerate(ids)}
    k, league = p['K'], lg['ortg']
    off0, dfn0, pace_t, gp = start_ratings(T, lg, ids, k)
    sd0 = p['sigma'] / np.sqrt(gp + k)
    off = off0[None, :] + p['start_scale'] * sd0[None, :] * rng.standard_normal((W, len(ids)))
    dfn = dfn0[None, :] + p['start_scale'] * sd0[None, :] * rng.standard_normal((W, len(ids)))
    n = gp.copy()  # every universe plays the same schedule, so games so far are shared
    G = len(games)
    home_win = np.zeros((W, G), bool)
    points = np.zeros((W, G, 2), np.int32)
    sd, rho = p['team_sd'], p['team_rho']
    sd_margin = sd * math.sqrt(2 * (1 - rho))
    ot = p['ot_share']
    for g, r in enumerate(games):
        h, a = index[r['home_id']], index[r['away_id']]
        pace = pace_t[h] * pace_t[a] / lg['pace']
        hca = 0.0 if int(r.get('neutral') or 0) else p['home_court']
        mu_h = pace * (off[:, h] * dfn[:, a] / league) / 100 + hca / 2
        mu_a = pace * (off[:, a] * dfn[:, h] / league) / 100 - hca / 2
        played = engine.get(r['game_id']) if engine else None
        if played is not None:
            e = np.asarray(played)[np.arange(W) % len(played)]
            reg_h, reg_a = e[:, 0, :4].sum(1), e[:, 1, :4].sum(1)
            pts_h, pts_a = e[:, 0].sum(1), e[:, 1].sum(1)
            win = pts_h > pts_a
        else:
            z1 = rng.standard_normal(W)
            z2 = rho * z1 + math.sqrt(1 - rho * rho) * rng.standard_normal(W)
            reg_h, reg_a = np.rint(mu_h + sd * z1), np.rint(mu_a + sd * z2)
            u = rng.random(W)
            tie = reg_h == reg_a
            p_ot = 0.5 * (1 + _erf((mu_h - mu_a) * ot / (sd_margin * math.sqrt(ot)) / math.sqrt(2)))
            win = np.where(tie, u < p_ot, reg_h > reg_a)
            pts_h, pts_a = reg_h, reg_a
        home_win[:, g] = win
        points[:, g, 0], points[:, g, 1] = pts_h, pts_a
        s_h = 100 * (reg_h - mu_h) / pace  # surprises against the universe's own expectation (per 100)
        s_a = 100 * (reg_a - mu_a) / pace
        cap = p.get('n_cap') or np.inf  # finite memory: the gain stops shrinking after n_cap games (None = the estimator's)
        g_h, g_a = p['scale'] / (min(n[h], cap) + 1 + k), p['scale'] / (min(n[a], cap) + 1 + k)
        off[:, h] += g_h * s_h
        dfn[:, a] += g_a * s_h
        off[:, a] += g_a * s_a
        dfn[:, h] += g_h * s_a
        n[h] += 1
        n[a] += 1
    return {'home_win': home_win, 'points': points, 'off': off, 'def': dfn, 'ids': ids,
            'start': {'off': off0, 'def': dfn0, 'pace': pace_t, 'sd': sd0}}


def _erf(x: np.ndarray) -> np.ndarray:
    """Vectorised error function (Abramowitz–Stegun 7.1.26, |error| < 1.5e-7) — NumPy has none."""
    s = np.sign(x)
    x = np.abs(x)
    t = 1 / (1 + 0.3275911 * x)
    y = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * np.exp(-x * x)
    return s * y
