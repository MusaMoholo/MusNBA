#!/usr/bin/env python3
"""Real matchups from NBA Stats (ENGINE_PLAN D32): who guarded whom, per game, in ESPN ids.

`data/derived/nbastats/matchups.parquet` (from `nbastats.py --matchups`) gives, per game, attacker and defender, the
partial possessions the defender spent on him and what the attacker did meanwhile (points, FGM/FGA, threes, free
throws, turnovers). Two uses, both cutoff-safe (a game on date D sees only games before D):

1. **Defender quality** — `shares()` gives each attacker's real per-game shares of who guarded him (all possessions;
   made and missed twos and threes separately), which `features.py --real-matchups` uses instead of the soft
   assignment to count what each defender allowed (the `m_*` family) — so a defender's FG% allowed is built from the
   shots he actually contested, by zone.
2. **Who will guard whom tonight** — the engine cannot see tonight's matchups, so the assignment over the five on
   court stays a pre-game model (no train/serve skew), now fitted on the real shares (soft labels) instead of ESPN's
   foul and block credits, with features the old one lacked: height and usage **ranks within each five** (the
   tallest guards the tallest; the stopper takes the star), a defender's **stopper tendency** (point-in-time usage of
   the attackers he usually takes) and the **pair's own history** (decayed share of the attacker's time this defender
   took when they met before).

  .venv/bin/python scripts/realmatch.py --fit [--through 2025-12-31] [--holdout-to 2026-04-30]
  .venv/bin/python scripts/realmatch.py --history          point-in-time pair history + stopper tables
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
from basketball_common import DERIVED, write_json  # noqa: E402

NB = DERIVED / 'nbastats'
PAIR_HALF_LIFE = 3.0     # meetings
PAIR_PRIOR = (0.1, 1.0)  # shrink a pair's history toward a 10% share with the weight of one meeting
STOP_HALF_LIFE = 15.0    # games
MATCH_REAL = ['abs_height', 'abs_weight', 'same_group', 'abs_role', 'big_on_small', 'small_on_big',
              'rank_height', 'rank_usage', 'stop_x_usage', 'pair_hist', 'pair_met']


def load(through: str | None = None) -> pd.DataFrame:
    M = pd.read_parquet(NB / 'matchups.parquet')
    g = pd.read_parquet(NB / 'games.parquet', columns=['espn_game', 'date'])
    M = M.merge(g, on='espn_game', how='left')
    M['espn_game'], M['off_player'], M['def_player'] = M['espn_game'].astype(str), M['off_player'].astype(str), M['def_player'].astype(str)
    if through:
        M = M[M['date'] <= through]
    return M


# ---------------------------------------------------------------- point-in-time history

def pair_history(M: pd.DataFrame) -> pd.DataFrame:
    """Per game, attacker and every defender who guarded anyone on his team that night: the pair's history before the
    game — `pair_hist` = log of the shrunk decayed share of the attacker's partial possessions this defender took in
    earlier meetings, `pair_met` = decayed number of earlier meetings. Rows of the current game are never used."""
    T = M.groupby(['espn_game', 'off_player'])['pposs'].transform('sum')
    M = M.assign(share=M['pposs'] / T.where(T > 0))
    att = M[['espn_game', 'date', 'off_tc', 'off_player']].drop_duplicates(['espn_game', 'off_player'])
    dfs = M[['espn_game', 'off_tc', 'def_player']].drop_duplicates(['espn_game', 'off_tc', 'def_player'])
    meet = att.merge(dfs, on=['espn_game', 'off_tc'])  # every attacker × every defender of the other side that night
    meet = meet.merge(M[['espn_game', 'off_player', 'def_player', 'share']], on=['espn_game', 'off_player', 'def_player'], how='left')
    meet['share'] = meet['share'].fillna(0.0)
    meet = meet.sort_values(['off_player', 'def_player', 'date', 'espn_game']).reset_index(drop=True)
    lam = 0.5 ** (1 / PAIR_HALF_LIFE)
    k = meet.groupby(['off_player', 'def_player']).cumcount().to_numpy()
    a = meet['share'].to_numpy() * lam ** (-k.astype(float))
    cum = pd.Series(a).groupby([meet['off_player'], meet['def_player']]).cumsum().to_numpy() - a
    ones = lam ** (-k.astype(float))
    cden = pd.Series(ones).groupby([meet['off_player'], meet['def_player']]).cumsum().to_numpy() - ones
    scale = lam ** (k - 1.0)
    num, den = cum * scale, cden * scale
    c, kappa = PAIR_PRIOR
    meet['pair_hist'] = np.log((num + c * kappa) / (den + kappa) / c)
    meet['pair_met'] = den
    return meet[['espn_game', 'date', 'off_player', 'def_player', 'pair_hist', 'pair_met', 'share']]


_CACHE: dict = {}


def build_history() -> dict:
    """Write data/derived/nbastats/pair_history.parquet (per game, pre-game pair history) for datasets and backtests."""
    M = load()
    h = pair_history(M)
    h.to_parquet(NB / 'pair_history.parquet', index=False)
    return {'rows': int(len(h)), 'games': int(h['espn_game'].nunique()), 'pairs_met_before': round(float((h['pair_met'] > 0).mean()), 4)}


def load_pair_history() -> pd.DataFrame:
    if 'hist' not in _CACHE:
        path = NB / 'pair_history.parquet'
        h = pd.read_parquet(path) if path.exists() else pd.DataFrame(columns=['espn_game', 'off_player', 'def_player', 'pair_hist', 'pair_met'])
        for c in ('espn_game', 'off_player', 'def_player'):
            h[c] = h[c].astype(str)
        _CACHE['hist'] = h
    return _CACHE['hist']


def pair_matrix(game_id: str, day: str, ids: list) -> tuple[np.ndarray, np.ndarray]:
    """(n, n) pair_hist and pair_met for one game's players (row attacker, column defender), before `day`: the stored
    per-game history for a past game, else the state from every matchup before `day` (games not yet played)."""
    ids = [str(x) for x in ids]
    n = len(ids)
    H, Mt = np.zeros((n, n), np.float32), np.zeros((n, n), np.float32)
    h = load_pair_history()
    rows = h[h['espn_game'] == str(game_id)]
    if rows.empty:
        if ('state', day) not in _CACHE:
            path = NB / 'matchups.parquet'
            _CACHE[('state', day)] = pair_state(load(), day) if path.exists() else pd.DataFrame(columns=['off_player', 'def_player', 'pair_hist', 'pair_met'])
        rows = _CACHE[('state', day)]
    pos = {p: i for i, p in enumerate(ids)}
    sel = rows[rows['off_player'].isin(pos) & rows['def_player'].isin(pos)]
    if len(sel):
        i = sel['off_player'].map(pos).to_numpy()
        j = sel['def_player'].map(pos).to_numpy()
        H[i, j] = sel['pair_hist'].to_numpy(np.float32)
        Mt[i, j] = sel['pair_met'].to_numpy(np.float32)
    return H, Mt


def pair_state(M: pd.DataFrame, before: str) -> pd.DataFrame:
    """The pair history as it stands before date `before` (for games the engine plays): one row per pair."""
    M = M[M['date'] < before]
    T = M.groupby(['espn_game', 'off_player'])['pposs'].transform('sum')
    M = M.assign(share=M['pposs'] / T.where(T > 0))
    att = M[['espn_game', 'date', 'off_tc', 'off_player']].drop_duplicates(['espn_game', 'off_player'])
    dfs = M[['espn_game', 'off_tc', 'def_player']].drop_duplicates(['espn_game', 'off_tc', 'def_player'])
    meet = att.merge(dfs, on=['espn_game', 'off_tc']).merge(M[['espn_game', 'off_player', 'def_player', 'share']],
                                                            on=['espn_game', 'off_player', 'def_player'], how='left')
    meet['share'] = meet['share'].fillna(0.0)
    meet = meet.sort_values(['off_player', 'def_player', 'date', 'espn_game'])
    lam = 0.5 ** (1 / PAIR_HALF_LIFE)
    n = meet.groupby(['off_player', 'def_player'])['share'].transform('size')
    k = meet.groupby(['off_player', 'def_player']).cumcount()
    w = lam ** (n - 1 - k)
    meet = meet.assign(ws=w * meet['share'], w=w)
    s = meet.groupby(['off_player', 'def_player'])[['ws', 'w']].sum().reset_index()
    c, kappa = PAIR_PRIOR
    s['pair_hist'] = np.log((s['ws'] + c * kappa) / (s['w'] + kappa) / c)
    s['pair_met'] = s['w']
    return s[['off_player', 'def_player', 'pair_hist', 'pair_met']]


def stopper(M: pd.DataFrame, usage: pd.DataFrame) -> pd.DataFrame:
    """Per defender-game, before the game: the decayed partial-possession-weighted pre-game usage of the attackers he
    guarded in earlier games (a stopper takes the stars). usage: game_id, player, usage (pre-game profiles)."""
    u = usage.rename(columns={'game_id': 'espn_game', 'player': 'off_player'})
    x = M.merge(u, on=['espn_game', 'off_player'], how='left')
    x = x[x['usage'].notna() & (x['pposs'] > 0)]
    g = x.assign(wu=x['pposs'] * x['usage']).groupby(['espn_game', 'date', 'def_player'], as_index=False)[['wu', 'pposs']].sum()
    g['u'] = g['wu'] / g['pposs']
    g = g.sort_values(['def_player', 'date', 'espn_game'])
    g['stop'] = g.groupby('def_player')['u'].transform(lambda s: s.shift().ewm(halflife=STOP_HALF_LIFE, ignore_na=True).mean())
    return g[['espn_game', 'date', 'def_player', 'stop', 'u', 'pposs']]


# ---------------------------------------------------------------- the assignment model

def rank5(v: np.ndarray) -> np.ndarray:
    """Rank within each row of five (0 = smallest); ties broken by position."""
    return np.argsort(np.argsort(v, axis=1, kind='stable'), axis=1, kind='stable').astype(float)


def real_pair_features(A: dict, D: dict, O: dict | None, rank_actor: np.ndarray | None = None) -> dict:
    """Pair features of the actor (n,) against five defenders (n, 5). O = the offensive five's columns (n, 5) for the
    rank features; A['slot'] = the actor's index within O. Missing inputs must be filled before."""
    from scripts.matchups import pair_features
    f = pair_features(A, D)
    if O is not None:
        slot = A['slot'].astype(int)
        rows = np.arange(len(slot))
        rh_o, rh_d = rank5(O['height_in']), rank5(D['height_in'])
        f['rank_height'] = np.abs(rh_o[rows, slot][:, None] - rh_d)
        ru_o, ru_d = rank5(O['usage']), rank5(D['stop'])
        f['rank_usage'] = np.abs(ru_o[rows, slot][:, None] - ru_d)
    zu = (A['usage'] - 0.19) / 0.06
    zs = (D["stop"] - 0.19) / 0.02
    f['stop_x_usage'] = zu[:, None] * zs
    f['pair_hist'] = D.get('pair_hist', np.zeros_like(D['height_in']))
    f['pair_met'] = np.minimum(D.get('pair_met', np.zeros_like(D['height_in'])), 5.0) / 5.0
    return f


WEAK_ZONES = ('rim', 'mid', 'three')


def weakness(D: dict, norm: dict) -> np.ndarray:
    """(n, 5) defender weakness: mean z-score of his FG% allowed at the rim, mid-range and from three (higher = weaker)."""
    zs = [(D[f'm_fg_{z}'] - norm[z][0]) / norm[z][1] for z in WEAK_ZONES if f'm_fg_{z}' in D]
    return np.nan_to_num(np.mean(zs, axis=0), nan=0.0) if zs else np.zeros_like(D['height_in'])


def real_assignment(theta: dict, A: dict, D: dict, O: dict | None) -> np.ndarray:
    f = real_pair_features(A, D, O)
    if 'hunt' in theta['match']:  # D35: the offence hunts weak defenders with its high-usage attackers
        f['hunt'] = ((A['usage'] - 0.19) / 0.06)[:, None] * weakness(D, theta['weak_norm'])
    z = sum(theta['match'][k] * f[k] for k in theta['match'])
    z = z - z.max(1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(1, keepdims=True)


def fit_soft(X, Y, w, iters=40, ridge=1e-3):
    """Conditional logit with soft labels Y (n, 5) summing to 1: max Σ w Σ_j Y_j log p_j (Newton)."""
    n, J, k = X.shape
    theta = np.zeros(k)
    for _ in range(iters):
        z = X @ theta
        z -= z.max(1, keepdims=True)
        p = np.exp(z)
        p /= p.sum(1, keepdims=True)
        xbar = (p[:, :, None] * X).sum(1)
        xy = (Y[:, :, None] * X).sum(1)
        grad = (w[:, None] * (xy - xbar)).sum(0) - ridge * theta
        xx = np.einsum('nj,njk,njl->kl', p * w[:, None], X, X)
        H = -(xx - np.einsum('n,nk,nl->kl', w, xbar, xbar)) - ridge * np.eye(k)
        step = np.linalg.solve(H, grad)
        theta -= step
        if np.abs(step).max() < 1e-7:
            break
    return theta


def soft_scores(P: np.ndarray, Y: np.ndarray, w: np.ndarray) -> dict:
    lp = np.log(np.clip(P, 1e-12, 1))
    ce = float(-(w * (Y * lp).sum(1)).sum() / w.sum())
    ent = float(-(w * (Y * np.log(np.clip(Y, 1e-12, 1))).sum(1)).sum() / w.sum())
    top1 = float((w * (P.argmax(1) == Y.argmax(1))).sum() / w.sum())
    mass = float((w * Y[np.arange(len(Y)), P.argmax(1)]).sum() / w.sum())  # real share held by the predicted top defender
    return {'cross_entropy': round(ce, 4), 'label_entropy': round(ent, 4), 'top1': round(top1, 4), 'top1_real_share': round(mass, 4)}


def design_real(seg: pd.DataFrame, M: pd.DataFrame, pre: pd.DataFrame, hist: pd.DataFrame, stop: pd.DataFrame, label: str = 'pposs'):
    """Per actor use with full fives: (A, D, O) columns, soft labels over the five from the real per-game shares."""
    use = seg[seg['actor'].notna() & seg['end_type'].isin(['shot', 'fouled', 'turnover'])]
    use = use[~((use['end_type'] == 'shot') & use['heave'])]
    defs = use[[f'def_{i}' for i in range(1, 6)]].astype(str).to_numpy()
    offs = use[[f'off_{i}' for i in range(1, 6)]].astype(str).to_numpy()
    act = use['actor'].astype(str).to_numpy()
    gid = use['game_id'].astype(str).to_numpy()
    slot = (offs == act[:, None])
    ok = (slot.sum(1) == 1) & (defs != 'None').all(1) & (defs != 'nan').all(1)
    use, defs, offs, act, gid, slot = use[ok], defs[ok], offs[ok], act[ok], gid[ok], slot[ok].argmax(1)
    # labels
    key = M.set_index(['espn_game', 'off_player', 'def_player'])
    lab_col = {'pposs': 'pposs', 'fga': 'fga'}[label]
    lab = np.zeros(defs.shape)
    for j in range(5):
        lab[:, j] = key[lab_col].reindex(pd.MultiIndex.from_arrays([gid, act, defs[:, j]])).fillna(0).to_numpy()
    tot = lab.sum(1)
    keep = tot > 0
    Y = lab[keep] / tot[keep][:, None]
    use, defs, offs, act, gid, slot = use[keep], defs[keep], offs[keep], act[keep], gid[keep], slot[keep]
    look = pre.set_index(['game_id', 'player'])
    cols = ['height_in', 'weight_lb', 'grp_code', 'min_avg', 'usage']
    def get(players):
        return look.reindex(pd.MultiIndex.from_arrays([gid, players]))[cols]
    fill = {c: float(np.nanmedian(pre[c])) for c in cols}
    A = {c: get(act)[c].to_numpy(float) for c in cols}
    D = {c: np.empty(defs.shape) for c in cols + ['stop', 'pair_hist', 'pair_met'] + [f'm_fg_{z}' for z in WEAK_ZONES]}
    O = {c: np.empty(offs.shape) for c in cols}
    st = stop.set_index(['espn_game', 'def_player'])['stop']
    hk = hist.set_index(['espn_game', 'off_player', 'def_player'])
    for j in range(5):
        g = get(defs[:, j])
        for c in cols:
            D[c][:, j] = g[c].to_numpy(float)
        go = get(offs[:, j])
        for c in cols:
            O[c][:, j] = go[c].to_numpy(float)
        D['stop'][:, j] = st.reindex(pd.MultiIndex.from_arrays([gid, defs[:, j]])).to_numpy(float)
        for z in WEAK_ZONES:
            D[f'm_fg_{z}'][:, j] = stop.set_index(['espn_game', 'def_player'])[f'm_fg_{z}'].reindex(pd.MultiIndex.from_arrays([gid, defs[:, j]])).to_numpy(float)
        idx = pd.MultiIndex.from_arrays([gid, act, defs[:, j]])
        D['pair_hist'][:, j] = hk['pair_hist'].reindex(idx).to_numpy(float)
        D['pair_met'][:, j] = hk['pair_met'].reindex(idx).to_numpy(float)
    fill['stop'] = float(np.nanmedian(stop['stop']))
    for c in cols:
        A[c] = np.where(np.isnan(A[c]), fill[c], A[c])
        D[c] = np.where(np.isnan(D[c]), fill[c], D[c])
        O[c] = np.where(np.isnan(O[c]), fill[c], O[c])
    D['stop'] = np.where(np.isnan(D['stop']), fill['stop'], D['stop'])
    D['pair_hist'] = np.nan_to_num(D['pair_hist'], nan=0.0)
    D['pair_met'] = np.nan_to_num(D['pair_met'], nan=0.0)
    A['slot'] = slot
    info = {'date': use['date_et'].astype(str).to_numpy(), 'end_type': use['end_type'].to_numpy(), 'zone': use['zone'].to_numpy()}
    return A, D, O, Y, fill, info


def _stack(f: dict, names: list[str]) -> np.ndarray:
    return np.stack([f[k] for k in names], axis=2)


def fit(through: str, holdout_to: str, features: Path) -> dict:
    """θ on actor uses through `through`, scored on (through, holdout_to]. The stopper input is the served profile
    column `m_stop` of `features` (features.py --real-matchups), so training and the engine see the same values."""
    from scripts import matchups, nodes
    M = load()
    seg = nodes.load_segments(False)
    seg = seg[seg['game_id'].astype(str).isin(set(M['espn_game']))]
    pre = matchups._players(None)
    usage = pd.read_parquet(DERIVED / 'features' / 'pregame.parquet', columns=['game_id', 'player', 'usage'])
    usage['game_id'], usage['player'] = usage['game_id'].astype(str), usage['player'].astype(str)
    pre = pre.merge(usage, on=['game_id', 'player'], how='left')
    hist = pair_history(M)
    fp = pd.read_parquet(features, columns=['game_id', 'player', 'date_et', 'm_stop'] + [f'm_fg_{z}' for z in WEAK_ZONES])
    stop = fp.rename(columns={'game_id': 'espn_game', 'player': 'def_player', 'm_stop': 'stop'})
    stop['espn_game'], stop['def_player'] = stop['espn_game'].astype(str), stop['def_player'].astype(str)
    trn = fp[fp['date_et'].astype(str) <= through]
    weak_norm = {z: [float(trn[f'm_fg_{z}'].mean()), float(trn[f'm_fg_{z}'].std())] for z in WEAK_ZONES}
    out = {'through': through, 'features': str(features), 'holdout_to': holdout_to, 'matchup_games': int(M['espn_game'].nunique()),
           'seasons_in_matchups': sorted(M['date'].str[:4].unique().tolist())}
    A, D, O, Y, fill, info = design_real(seg, M, pre, hist, stop)
    tr = info['date'] <= through
    f_hunt = ((A['usage'] - 0.19) / 0.06)[:, None] * weakness(D, weak_norm)
    te = (info['date'] > through) & (info['date'] <= holdout_to)
    w = np.ones(len(Y))
    f = real_pair_features(A, D, O)
    f['hunt'] = f_hunt
    old = json.loads((ROOT / 'models' / 'matchup_2025-12-31.json').read_text())
    P_old = matchups.assignment(old, {k: A[k] for k in ('height_in', 'weight_lb', 'grp_code', 'min_avg')},
                                {k: D[k] for k in ('height_in', 'weight_lb', 'grp_code', 'min_avg')})
    sets = {'old_pair_features': MATCH_REAL[:6], '+ranks': MATCH_REAL[:8], '+stopper': MATCH_REAL[:9], '+pair_history': MATCH_REAL,
            '+hunt': MATCH_REAL + ['hunt']}
    out['rows'] = {'train': int(tr.sum()), 'holdout': int(te.sum())}
    out['holdout'] = {'uniform': soft_scores(np.full_like(Y[te], 0.2), Y[te], w[te]),
                      'old_theta_espn_credits': soft_scores(P_old[te], Y[te], w[te])}
    thetas = {}
    for name, names in sets.items():
        X = _stack(f, names)
        th = fit_soft(X[tr], Y[tr], w[tr])
        thetas[name] = dict(zip(names, th.round(4).tolist()))
        z = X[te] @ th
        z -= z.max(1, keepdims=True)
        P = np.exp(z)
        P /= P.sum(1, keepdims=True)
        out['holdout'][name] = soft_scores(P, Y[te], w[te])
        if name in ('+pair_history', '+hunt'):
            shots = info['end_type'][te] == 'shot'
            out.setdefault('holdout_shots', {})[name] = soft_scores(P[shots], Y[te][shots], w[te][shots])
    out['theta'] = thetas
    out['weak_norm'] = weak_norm
    out['fill'] = fill
    out['settings'] = {'pair_half_life_meetings': PAIR_HALF_LIFE, 'pair_prior': PAIR_PRIOR, 'stop_half_life_games': STOP_HALF_LIFE}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--fit', action='store_true')
    ap.add_argument('--through', default='2025-12-31')
    ap.add_argument('--holdout-to', default='2026-04-30')
    ap.add_argument('--save', action='store_true', help='write models/realmatch_<through>.json from the chosen feature set')
    ap.add_argument('--set', default='+pair_history', help="feature set to save ('+pair_history' = v1.4c, '+hunt' = v1.4d)")
    ap.add_argument('--out', default=None, help='θ file name (default models/realmatch_<through>.json)')
    ap.add_argument('--history', action='store_true', help='write the per-game pair history table')
    ap.add_argument('--features', type=Path, default=DERIVED / 'variants' / 'realmatch' / 'features' / 'pregame.parquet')
    args = ap.parse_args()
    if args.history:
        print(json.dumps(build_history(), indent=1))
    if args.fit:
        r = fit(args.through, args.holdout_to, args.features)
        print(json.dumps({k: v for k, v in r.items() if k != 'fill'}, indent=1, default=float))
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        from scripts.evaluate import EXPERIMENTS
        write_json(EXPERIMENTS / f'{stamp}_realmatch_fit.json', {'experiment': 'real_matchup_assignment', 'run': stamp, **r}, pretty=True)
        if args.save:
            fill = {**r['fill'], 'pair_hist': 0.0, 'pair_met': 0.0}
            name = args.out or f'models/realmatch_{args.through}.json'
            write_json(ROOT / name, {'kind': 'real', 'through': args.through, 'set': args.set, 'match': r['theta'][args.set], 'fill': fill,
                                     'weak_norm': r['weak_norm'], 'settings': r['settings'], 'holdout': r['holdout'][args.set], 'run': stamp},
                       pretty=True)
            rep_path = Path(args.features).parent / 'features_report.json'
            if rep_path.exists():  # the variant's datasets and engine then use this θ for mu_* (nodes.Chain, train._matchup_of)
                rep = json.loads(rep_path.read_text())
                rep['assign'] = name
                write_json(rep_path, rep, pretty=True)


if __name__ == '__main__':
    main()
