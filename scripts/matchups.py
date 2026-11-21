#!/usr/bin/env python3
"""Implicit matchups (ENGINE_PLAN D30): who guards whom, from ESPN play-by-play only.

Position is only a guide, so each shooter gets a **soft assignment** — a probability over the five defenders on court —
from pair features (height gap, weight gap, same position group, role gap), recomputed for whoever is on the floor.
It is learned from the defender ESPN credits on a shot: the fouler on a shooting foul and the blocker (owner, 20 Nov:
the defender who affected the shot, close enough to count), weighting jump-shot fouls and blocks (mostly the on-ball
defender) above rim blocks and rim fouls (often a rotating help big), plus steals on the ball handler at a low weight.
A credit's chance is assignment × the defender's own propensity to be credited (his foul, block or steal rate), so the
fit carries per-event propensity terms that are *not* part of the assignment:

    P(credit d | shooter s, five on court) ∝ exp(θ_match · f(s, d) + θ_prop[event] · g(d))
    assignment a(s, d)                      ∝ exp(θ_match · f(s, d))

Also here: shot type from the play text (pull-up, step-back, isolation/post, driving, cutting/alley-oop, putback,
plain jump shot ≈ catch-and-shoot) for every shot segment — `shot_types()`.

  .venv/bin/python scripts/matchups.py --fit [--through 2025-12-31]     fit θ, log it, write models/matchup_<through>.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, NBA_TEAM_IDS, write_json  # noqa: E402

MATCH = ['abs_height', 'abs_weight', 'same_group', 'abs_role', 'big_on_small', 'small_on_big']
PROP = ['foul_pf', 'foul_big', 'block_blk', 'block_big', 'steal_stl', 'steal_big']
EVENT_WEIGHT = {'foul3': 1.0, 'foul2': 0.5, 'and1_jump': 1.0, 'and1_rim': 0.3, 'block_jump': 1.0, 'block_rim': 0.25, 'steal': 0.3}
SHOT_TYPES = ['catch', 'pullup', 'stepback', 'iso', 'drive', 'cut', 'putback', 'other']
JUMP_TYPES = {'catch', 'pullup', 'stepback', 'iso'}


def shot_type(type_text: str) -> str:
    t = (type_text or '').lower()
    if 'putback' in t or t.startswith('tip'):
        return 'putback'
    if 'alley oop' in t or 'cutting' in t:
        return 'cut'
    if 'step back' in t:
        return 'stepback'
    if 'pullup' in t:
        return 'pullup'
    if 'fade' in t or 'turnaround' in t or 'hook' in t:
        return 'iso'
    if 'driving' in t or 'running' in t or 'floating' in t:
        return 'drive'
    if t in ('jump shot', 'jump shot bank'):
        return 'catch'
    return 'other'


def _clock(text) -> float:
    from scripts.pbp import clock_seconds
    try:
        return round(float(clock_seconds(str(text))), 1)
    except ValueError:
        return np.nan


def shot_types(include_current: bool = True) -> pd.DataFrame:
    """(game_id, period, clock, actor) → shot type for every field-goal attempt: hoopR files for history, the retained
    ESPN finals for the live season (same canonical text)."""
    frames = []
    for path in sorted((ROOT / 'data' / 'raw' / 'hoopr').glob('play_by_play_*.parquet')):
        p = pd.read_parquet(path, columns=['game_id', 'period_number', 'clock_display_value', 'athlete_id_1', 'type_text', 'shooting_play'])
        p = p[p['shooting_play'].fillna(False).astype(bool) & ~p['type_text'].fillna('').str.contains('Free Throw', case=False)]
        p = p.dropna(subset=['athlete_id_1'])
        frames.append(pd.DataFrame({'game_id': p['game_id'].astype('int64').astype(str), 'period': p['period_number'].astype(int),
                                    'clock': p['clock_display_value'].map(_clock), 'actor': p['athlete_id_1'].astype('int64').astype(str),
                                    'type_text': p['type_text'].fillna('')}))
    if include_current:
        from scripts import possessions
        rows = []
        for g in possessions.current_games():
            for e in g['plays']:
                if e['shooting'] and e['points_attempted'] != 1 and 'free throw' not in e['type_text'].lower() and e['participants']:
                    rows.append((str(g['id']), int(e['period']), _clock(e['clock']), str(e['participants'][0]), e['type_text']))
        frames.append(pd.DataFrame(rows, columns=['game_id', 'period', 'clock', 'actor', 'type_text']))
    out = pd.concat(frames, ignore_index=True)
    out['shot_type'] = out['type_text'].map(shot_type)
    return out.drop_duplicates(['game_id', 'period', 'clock', 'actor'])[['game_id', 'period', 'clock', 'actor', 'shot_type']]


def attach_shot_types(seg: pd.DataFrame, types: pd.DataFrame) -> pd.Series:
    """Shot type per segment (NaN where the segment is not a shot or no play matched)."""
    key = seg[['game_id', 'period', 'action_clock', 'actor']].copy()
    key['game_id'], key['actor'] = key['game_id'].astype(str), key['actor'].astype(str)
    key['clock'] = key['action_clock'].astype(float).round(1)
    m = key.drop(columns='action_clock').reset_index().merge(types, on=['game_id', 'period', 'clock', 'actor'], how='left').set_index('index')
    return m['shot_type'].reindex(seg.index).where(seg['end_type'].eq('shot'))


# ---------------------------------------------------------------- pair features and the assignment

def pair_features(sh: dict, df: dict) -> dict:
    """Matchup features for shooter columns `sh` (arrays (n,)) against defender columns `df` (arrays (n, 5))."""
    hs, hd = sh['height_in'][:, None], df['height_in']
    ws, wd = sh['weight_lb'][:, None], df['weight_lb']
    gs, gd = sh['grp_code'][:, None], df['grp_code']
    rs, rd = sh['min_avg'][:, None], df['min_avg']
    return {'abs_height': np.abs(hs - hd) / 3.0, 'abs_weight': np.abs(ws - wd) / 20.0, 'same_group': (gs == gd).astype(float),
            'abs_role': np.abs(rs - rd) / 10.0, 'big_on_small': ((gd == 2) & (gs == 0)).astype(float),
            'small_on_big': ((gd == 0) & (gs == 2)).astype(float)}


def assignment(theta: dict, sh: dict, df: dict) -> np.ndarray:
    """(n, 5) probability that each of the five defenders guards the shooter (rows sum to 1; missing inputs → filled)."""
    f = pair_features(_fill(sh, theta), _fill(df, theta))
    z = sum(theta['match'][k] * f[k] for k in MATCH)
    z = z - z.max(1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(1, keepdims=True)


MU_SOURCES = ['m_fg_rim', 'm_fg_paint', 'm_fg_mid', 'm_fg_three', 'm_tov_rate', 'm_foul_rate',
              'd_fg_rim', 'd_fg_paint', 'd_fg_mid', 'd_fg_three', 'd_tov_rate', 'm_dx_three', 'm_dx_rim']


def mu_columns(theta: dict, A: dict, D: dict, O: dict | None = None) -> dict:
    """The actor's likely defenders, weighted by the soft assignment: their matchup FG% allowed by zone (on-court
    values where the matchup family is absent), turnovers forced and shooting fouls on their men, and the size gap.
    A: actor columns (n,) — grp_code, min_avg, height_in, weight_lb; D: the five defenders' columns (n, 5).
    Shared by the datasets (nodes.Chain) and the engine so training and simulation see the same inputs."""
    if theta.get('kind') == 'real':  # D32: fitted on real NBA matchup shares (scripts/realmatch.py)
        from scripts import realmatch
        a = realmatch.real_assignment(theta, _fill(A, theta), _fill(D, theta), _fill(O, theta))
    else:
        a = assignment(theta, A, D)
    def wavg(c):
        v = D[c]
        fill = np.nanmean(v, axis=1, keepdims=True)
        v = np.where(np.isnan(v), np.where(np.isnan(fill), np.nanmean(v), fill), v)
        return (a * v).sum(1)
    out = {}
    for z in ('rim', 'paint', 'mid', 'three'):
        src = f'm_fg_{z}' if f'm_fg_{z}' in D else f'd_fg_{z}'
        if src in D:
            out[f'mu_fg_{z}'] = wavg(src)
    if 'm_tov_rate' in D or 'd_tov_rate' in D:
        out['mu_tov'] = wavg('m_tov_rate' if 'm_tov_rate' in D else 'd_tov_rate')
    if 'm_foul_rate' in D:
        out['mu_foul'] = wavg('m_foul_rate')
    for k in ('three', 'rim'):  # D32 deterrence (v1.4e): attempt shares his likely defenders allow v expected
        if f'm_dx_{k}' in D:
            out[f'mu_dx_{k}'] = wavg(f'm_dx_{k}')
    hs = np.where(np.isnan(A['height_in']), theta['fill']['height_in'], A['height_in'])
    out['mu_height_gap'] = wavg('height_in') - hs
    if theta.get('top2'):  # v1.4f (owner, 20 Nov): the two most likely defenders' own numbers and the assignment's confidence
        order = np.argsort(-a, axis=1, kind='stable')
        r = np.arange(len(a))
        def filled(c):
            v = D[c]
            fill = np.nanmean(v, axis=1, keepdims=True)
            return np.where(np.isnan(v), np.where(np.isnan(fill), np.nanmean(v), fill), v)
        for k, pre in ((0, 'mu1'), (1, 'mu2')):
            j = order[:, k]
            out[f'{pre}_p'] = a[r, j]
            for z in ('rim', 'paint', 'mid', 'three'):
                src = f'm_fg_{z}' if f'm_fg_{z}' in D else f'd_fg_{z}'
                if src in D:
                    out[f'{pre}_fg_{z}'] = filled(src)[r, j]
            src = 'm_tov_rate' if 'm_tov_rate' in D else 'd_tov_rate'
            if src in D:
                out[f'{pre}_tov'] = filled(src)[r, j]
    return out


def _fill(cols: dict, theta: dict) -> dict:
    fill = theta.get('fill', {})
    return {k: np.where(np.isnan(v), fill.get(k, 0.0), v) if np.issubdtype(np.asarray(v).dtype, np.floating) else v for k, v in cols.items()}


# ---------------------------------------------------------------- fitting

def _players(through: str | None):
    pre = pd.read_parquet(DERIVED / 'features' / 'pregame.parquet', columns=['game_id', 'player', 'pos', 'min_avg', 'pf_rate', 'blk_rate', 'stl_rate'])
    pre['game_id'], pre['player'] = pre['game_id'].astype(str), pre['player'].astype(str)
    body = pd.read_parquet(DERIVED / 'athletes.parquet', columns=['player', 'height_in', 'weight_lb'])
    body['player'] = body['player'].astype(str)
    pre = pre.merge(body, on='player', how='left')
    p = pre['pos'].fillna('').str.upper()
    pre['grp_code'] = np.where(p.str.startswith('C'), 2, np.where(p.str.startswith('G') | p.isin(['PG', 'SG']), 0, 1)).astype(float)
    return pre


def events(seg: pd.DataFrame, types: pd.Series) -> pd.DataFrame:
    """Credited defender events with their weights: seg_id, shooter, credited defender, kind."""
    out = []
    f = seg[(seg['end_type'] == 'fouled') & seg['fouler'].notna() & seg['actor'].notna()]
    out.append(pd.DataFrame({'seg_id': f['seg_id'], 'shooter': f['actor'], 'credit': f['fouler'], 'kind': np.where(f['fta'] >= 3, 'foul3', 'foul2'), 'event': 'foul'}))
    st = types.reindex(seg.index)
    a = seg[(seg['end_type'] == 'shot') & seg['and_one'].fillna(False).astype(bool) & seg['fouler'].notna()]
    jump = st.loc[a.index].isin(JUMP_TYPES) | a['zone'].isin(['mid', 'corner3', 'above3'])
    out.append(pd.DataFrame({'seg_id': a['seg_id'], 'shooter': a['actor'], 'credit': a['fouler'], 'kind': np.where(jump, 'and1_jump', 'and1_rim'), 'event': 'foul'}))
    b = seg[(seg['end_type'] == 'shot') & seg['blocker'].notna()]
    jump = st.loc[b.index].isin(JUMP_TYPES) | b['zone'].isin(['mid', 'corner3', 'above3'])
    out.append(pd.DataFrame({'seg_id': b['seg_id'], 'shooter': b['actor'], 'credit': b['blocker'], 'kind': np.where(jump, 'block_jump', 'block_rim'), 'event': 'block'}))
    s = seg[(seg['end_type'] == 'turnover') & seg['stealer'].notna() & seg['actor'].notna()]
    out.append(pd.DataFrame({'seg_id': s['seg_id'], 'shooter': s['actor'], 'credit': s['stealer'], 'kind': 'steal', 'event': 'steal'}))
    ev = pd.concat(out, ignore_index=True)
    ev['w'] = ev['kind'].map(EVENT_WEIGHT)
    return ev


def design(seg: pd.DataFrame, ev: pd.DataFrame, pre: pd.DataFrame):
    """Per event: (n, 5, k) features over the five defenders, the credited index, weights."""
    s = seg.set_index('seg_id').loc[ev['seg_id']]
    defs = s[[f'def_{i}' for i in range(1, 6)]].astype(str).to_numpy()
    gid = s['game_id'].astype(str).to_numpy()
    look = pre.set_index(['game_id', 'player'])
    cols = ['height_in', 'weight_lb', 'grp_code', 'min_avg', 'pf_rate', 'blk_rate', 'stl_rate']

    def get(players, games):
        idx = pd.MultiIndex.from_arrays([games, players])
        return look.reindex(idx)[cols]
    sh = get(ev['shooter'].astype(str).to_numpy(), gid)
    dd = {c: np.empty(defs.shape) for c in cols}
    for j in range(5):
        g = get(defs[:, j], gid)
        for c in cols:
            dd[c][:, j] = g[c].to_numpy(float)
    shc = {c: sh[c].to_numpy(float) for c in cols}
    fill = {c: float(np.nanmedian(np.concatenate([shc[c], dd[c].ravel()]))) for c in cols}
    shc = {c: np.where(np.isnan(v), fill[c], v) for c, v in shc.items()}
    dd = {c: np.where(np.isnan(v), fill[c], v) for c, v in dd.items()}
    f = pair_features(shc, dd)
    ev_kind = ev['event'].to_numpy()
    z = lambda c: (dd[c] - np.nanmean(dd[c])) / (np.nanstd(dd[c]) + 1e-9)
    big = (dd['grp_code'] == 2).astype(float)
    g = {'foul_pf': z('pf_rate') * (ev_kind == 'foul')[:, None], 'foul_big': big * (ev_kind == 'foul')[:, None],
         'block_blk': z('blk_rate') * (ev_kind == 'block')[:, None], 'block_big': big * (ev_kind == 'block')[:, None],
         'steal_stl': z('stl_rate') * (ev_kind == 'steal')[:, None], 'steal_big': big * (ev_kind == 'steal')[:, None]}
    X = np.stack([f[k] for k in MATCH] + [g[k] for k in PROP], axis=2)
    y = (defs == ev['credit'].astype(str).to_numpy()[:, None])
    keep = (y.sum(1) == 1) & (defs != 'None').all(1) & (defs != 'nan').all(1)
    return X[keep], y[keep].argmax(1), ev['w'].to_numpy()[keep], ev['kind'].to_numpy()[keep], fill


def fit_clogit(X, y, w, iters=30, ridge=1e-3):
    n, J, k = X.shape
    theta = np.zeros(k)
    for _ in range(iters):
        z = X @ theta
        z -= z.max(1, keepdims=True)
        p = np.exp(z)
        p /= p.sum(1, keepdims=True)
        xbar = (p[:, :, None] * X).sum(1)
        xy = X[np.arange(n), y]
        grad = (w[:, None] * (xy - xbar)).sum(0) - ridge * theta
        xx = np.einsum('nj,njk,njl->kl', p * w[:, None], X, X)
        H = -(xx - np.einsum('n,nk,nl->kl', w, xbar, xbar)) - ridge * np.eye(k)
        step = np.linalg.solve(H, grad)
        theta -= step
        if np.abs(step).max() < 1e-7:
            break
    return theta


def loglik(X, y, w, theta, cols=None):
    z = X[:, :, cols] @ theta[cols] if cols is not None else X @ theta
    z -= z.max(1, keepdims=True)
    lp = z - np.log(np.exp(z).sum(1, keepdims=True))
    return float((w * lp[np.arange(len(y)), y]).sum() / w.sum())


def fit(through: str, holdout_to: str | None = None) -> dict:
    from scripts import nodes
    seg = nodes.load_segments(False)
    types = attach_shot_types(seg, shot_types(include_current=False))
    pre = _players(through)
    ev = events(seg, types)
    ev = ev.merge(seg[['seg_id', 'date_et']], on='seg_id')
    train = ev[ev['date_et'] <= through]
    X, y, w, kind, fill = design(seg, train, pre)
    theta = fit_clogit(X, y, w)
    out = {'through': through, 'events': int(len(y)), 'by_kind': pd.Series(kind).value_counts().to_dict(),
           'match': dict(zip(MATCH, theta[:len(MATCH)].round(4).tolist())), 'prop': dict(zip(PROP, theta[len(MATCH):].round(4).tolist())),
           'fill': fill, 'shot_type_coverage': round(float(types[seg['end_type'] == 'shot'].notna().mean()), 4),
           'shot_type_shares': types.value_counts(normalize=True).round(4).to_dict()}
    nk = len(MATCH)
    out['train_loglik'] = {'uniform': round(-np.log(5), 4), 'full': round(loglik(X, y, w, theta), 4),
                           'propensity_only': round(loglik(X, y, w, np.r_[np.zeros(nk), fit_clogit(X[:, :, nk:], y, w)]), 4)}
    if holdout_to:
        test = ev[(ev['date_et'] > through) & (ev['date_et'] <= holdout_to)]
        Xt, yt, wt, kt, _ = design(seg, test, pre)
        th_p = fit_clogit(X[:, :, nk:], y, w)
        out['holdout'] = {'events': int(len(yt)), 'uniform': round(-np.log(5), 4), 'full': round(loglik(Xt, yt, wt, theta), 4),
                          'propensity_only': round(loglik(Xt, yt, wt, np.r_[np.zeros(nk), th_p]), 4)}
        # top-1 accuracy of the pure assignment on fouls on threes and jump-shot blocks (the on-ball credits)
        on_ball = np.isin(kt, ['foul3', 'block_jump', 'and1_jump'])
        a = Xt[on_ball][:, :, :nk] @ theta[:nk]
        out['holdout']['on_ball_top1'] = round(float((a.argmax(1) == yt[on_ball]).mean()), 4)
        out['holdout']['on_ball_events'] = int(on_ball.sum())
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--fit', action='store_true')
    ap.add_argument('--through', default='2025-12-31', help='last training date (fold F4: 2025-12-31)')
    ap.add_argument('--holdout-to', default='2026-04-30')
    args = ap.parse_args()
    if args.fit:
        r = fit(args.through, args.holdout_to)
        print(json.dumps(r, indent=1, default=float))
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        from scripts.evaluate import EXPERIMENTS
        write_json(EXPERIMENTS / f'{stamp}_matchup_fit.json', {'experiment': 'matchup_assignment', 'run': stamp, **r}, pretty=True)
        write_json(ROOT / 'models' / f'matchup_{args.through}.json', {k: r[k] for k in ('through', 'match', 'prop', 'fill', 'events', 'by_kind')}, pretty=True)


if __name__ == '__main__':
    main()
