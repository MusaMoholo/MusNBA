#!/usr/bin/env python3
"""Train and score every decision of the chain on the rolling folds (ENGINE_PLAN M5; TRAINING_PLAN §5).

Per node and fold: LightGBM on games up to the fold's training cut-off (after a December 2022 burn-in),
early stopping on the latest 10% of that window, validation on the fold's held-out window — never on the
final test (this season). Candidate nodes (player choices) are binary models on one row per candidate,
normalised by softmax within each segment with a temperature fitted on the early-stopping slice.

Each node is compared with two baselines: league rates (training window) and player profiles.

  .venv/bin/python scripts/train.py                 every node, every fold
  .venv/bin/python scripts/train.py --folds F4 --nodes who what
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import write_json  # noqa: E402
from scripts import nodes  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS  # noqa: E402

BURN_IN = '2022-12-01'
NODES = ['duration', 'event', 'who', 'what', 'shot_result', 'assisted', 'assister', 'blocked', 'blocker', 'rebound', 'rebounder',
         'turnover_type', 'stealer', 'fouler', 'free_throw']
CATEGORICAL = ['start_code', 'zone', 'season_type', 'grp_code']
EPS = 1e-12


def params(kind, rows):
    big = rows > 2_000_000
    p = {'learning_rate': 0.1 if big or kind == 'multiclass' else 0.05, 'num_leaves': 63, 'min_data_in_leaf': 200,
         'feature_fraction': 0.8, 'bagging_fraction': 0.5 if big else 0.8, 'bagging_freq': 1, 'lambda_l2': 1.0,
         'max_bin': 63 if big else 255, 'num_threads': 12, 'verbose': -1, 'seed': 7}
    p['objective'] = 'binary' if kind in ('binary', 'candidate') else 'multiclass'
    return p


def softmax_groups(scores, groups, temperature=1.0):
    z = scores / temperature
    s = pd.Series(z)
    z = z - s.groupby(groups).transform('max').to_numpy()
    e = np.exp(z)
    return e / pd.Series(e).groupby(groups).transform('sum').to_numpy()


def group_logloss(p, y, groups):
    chosen = p[y == 1]
    return float(-np.mean(np.log(np.clip(chosen, EPS, 1))))


def fit_temperature(scores, y, groups):
    best = (np.inf, 1.0)
    for t in np.exp(np.linspace(np.log(0.5), np.log(2.0), 25)):
        ll = group_logloss(softmax_groups(scores, groups, t), y, groups)
        best = min(best, (ll, t))
    return best[1]


def ece(p, y, bins=10):
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(p, edges) - 1, 0, bins - 1)
    total = 0.0
    for b in range(bins):
        m = idx == b
        if m.any():
            total += abs(p[m].mean() - y[m].mean()) * m.sum()
    return total / len(p)


def multiclass_ece(P, y):
    out = 0.0
    for k in range(P.shape[1]):
        yk = (y == k).astype(float)
        out += ece(P[:, k], yk) * yk.mean()
    return out


def logloss_multi(P, y):
    return float(-np.mean(np.log(np.clip(P[np.arange(len(y)), y], EPS, 1))))


def logloss_binary(p, y):
    return float(-np.mean(y * np.log(np.clip(p, EPS, 1)) + (1 - y) * np.log(np.clip(1 - p, EPS, 1))))


def profile_baseline(d, tr, va):
    """Player-profile (or context) baseline probabilities for the validation rows."""
    X, y, name = d['X'], d['y'], d['name']
    if d['kind'] == 'candidate':
        return d['profile_score']
    tag = d['profile'][0] if d['profile'] else None
    k = d['classes'] or 2
    if tag == 'start_code':
        sc = d['start_code']
        table = pd.crosstab(sc[tr], y[tr], normalize='index').reindex(columns=range(k), fill_value=EPS)
        overall = np.bincount(y[tr], minlength=k) / tr.sum()
        P = np.array([table.loc[c].to_numpy() if c in table.index else overall for c in sc[va]])
        return P / P.sum(axis=1, keepdims=True)
    if tag == 'what':
        Xv = X[va]
        three = Xv['actor_mix_corner3'] + Xv['actor_mix_above3']
        fouled = Xv['actor_foul_drawn_share']
        cols = [Xv['actor_shot_share'] * Xv[f'actor_mix_{z}'] for z in nodes.ZONES]
        cols += [Xv['actor_tov_share'], fouled * (1 - 0.1 * three), fouled * 0.1 * three]
        P = np.column_stack(cols).astype(float)
        P = np.where(np.isnan(P), np.nanmean(P, axis=0), P)
        return P / P.sum(axis=1, keepdims=True)
    if tag == 'shot_result':
        zones = X['zone'].to_numpy().astype(int)
        fg = np.column_stack([X[f'actor_fg_{z}'] for z in nodes.ZONES])[np.arange(len(X)), zones]
        and1 = pd.Series((y[tr] == 2)).groupby(zones[tr]).mean()
        made = pd.Series((y[tr] >= 1)).groupby(zones[tr]).mean()
        fg = np.where(np.isnan(fg), pd.Series(zones).map(made).to_numpy(), fg)
        r = pd.Series(zones).map(and1 / made).to_numpy()
        Pm = fg[va]
        rv = r[va]
        return np.column_stack([1 - Pm, Pm * (1 - rv), Pm * rv])
    if tag == 'rebound':
        key = (X['ft_miss'].astype(int).astype(str) + '_' + X['zone'].fillna(-1).astype(int).astype(str)).to_numpy()
        table = pd.crosstab(key[tr], y[tr], normalize='index').reindex(columns=range(k), fill_value=EPS)
        overall = np.bincount(y[tr], minlength=k) / tr.sum()
        P = np.array([table.loc[c].to_numpy() if c in table.index else overall for c in key[va]])
        return P / P.sum(axis=1, keepdims=True)
    if tag == 'turnover_type':
        live = X['actor_live_tov_share'].to_numpy()[va]
        live = np.where(np.isnan(live), (y[tr] == 0).mean(), live)
        rest = np.bincount(y[tr], minlength=3)[1:] / max(1, (y[tr] > 0).sum())
        return np.column_stack([live, (1 - live) * rest[0], (1 - live) * rest[1]])
    if tag == 'zone_rate':
        zones = X['zone'].to_numpy().astype(int)
        rate = pd.Series(y[tr]).groupby(zones[tr]).mean()
        return pd.Series(zones[va]).map(rate).to_numpy()
    if tag in ('actor_assisted_share', 'actor_ft_pct'):
        p = X[tag].to_numpy(dtype=float)[va]
        return np.where(np.isnan(p), y[tr].mean(), p)
    raise KeyError(tag)


def run_node(d, fold, cut):
    train_to, val_from, val_to = cut
    date = d['date']
    tr_all = (date >= BURN_IN) & (date <= train_to)
    va = (date >= val_from) & (date <= val_to)
    es_from = np.quantile(pd.to_datetime(pd.Series(date[tr_all])).astype('int64'), 0.9)
    es = tr_all & (pd.to_datetime(pd.Series(date)).astype('int64').to_numpy() >= es_from)
    tr = tr_all & ~es
    X, y, kind = d['X'], d['y'], d['kind']
    cats = [c for c in CATEGORICAL if c in X.columns]
    p = params(kind, int(tr.sum()))
    if kind == 'multiclass':
        p['num_class'] = d['classes']
    dtrain = lgb.Dataset(X[tr], label=y[tr], categorical_feature=cats, free_raw_data=True)
    dval = lgb.Dataset(X[es], label=y[es], categorical_feature=cats, reference=dtrain)
    start = time.time()
    model = lgb.train(p, dtrain, num_boost_round=3000, valid_sets=[dval], callbacks=[lgb.early_stopping(50, verbose=False)])
    out = {'rows_train': int(tr.sum()), 'rows_val': int(va.sum()), 'iterations': model.best_iteration, 'seconds': round(time.time() - start, 1)}
    gain = model.feature_importance('gain')
    out['top_features'] = [X.columns[i] for i in np.argsort(-gain)[:8]]
    if kind == 'candidate':
        g = d['group']
        t = fit_temperature(model.predict(X[es], raw_score=True), y[es], g[es])
        P = softmax_groups(model.predict(X[va], raw_score=True), g[va], t)
        sizes = pd.Series(g[va]).groupby(g[va]).transform('size').to_numpy()
        prof = d['profile_score'][va]
        prof_p = prof / pd.Series(prof).groupby(g[va]).transform('sum').to_numpy()
        out.update({'temperature': round(float(t), 3), 'model': group_logloss(P, y[va], g[va]),
                    'league': group_logloss(1 / sizes, y[va], g[va]), 'profile': group_logloss(prof_p, y[va], g[va]),
                    'ece_model': ece(P, y[va].astype(float)), 'ece_profile': ece(prof_p, y[va].astype(float))})
    elif kind == 'multiclass':
        P = model.predict(X[va], num_iteration=model.best_iteration)
        freq = np.bincount(y[tr_all], minlength=d['classes']) / tr_all.sum()
        prof = profile_baseline(d, tr_all, va)
        out.update({'model': logloss_multi(P, y[va]), 'league': logloss_multi(np.tile(freq, (va.sum(), 1)), y[va]),
                    'profile': logloss_multi(prof, y[va]), 'ece_model': multiclass_ece(P, y[va]), 'ece_profile': multiclass_ece(prof, y[va])})
    else:
        P = model.predict(X[va], num_iteration=model.best_iteration)
        prof = profile_baseline(d, tr_all, va)
        out.update({'model': logloss_binary(P, y[va]), 'league': logloss_binary(np.full(va.sum(), y[tr_all].mean()), y[va]),
                    'profile': logloss_binary(prof, y[va]), 'ece_model': ece(P, y[va].astype(float)), 'ece_profile': ece(prof, y[va].astype(float))})
    best = min(out['league'], out['profile'])
    out['gain_vs_best_baseline'] = round(1 - out['model'] / best, 5)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--folds', nargs='*', default=list(FOLDS))
    ap.add_argument('--nodes', nargs='*', default=NODES)
    args = ap.parse_args()
    chain = nodes.Chain()
    results = {}
    for name in args.nodes:
        d = chain.dataset(name)
        results[name] = {}
        for fold in args.folds:
            r = run_node(d, fold, FOLDS[fold])
            results[name][fold] = r
            print(f"{name:14} {fold}  league {r['league']:.4f}  profile {r['profile']:.4f}  model {r['model']:.4f}  "
                  f"gain {r['gain_vs_best_baseline']:+.2%}  ECE {r['ece_model']:.4f} (profile {r['ece_profile']:.4f})  "
                  f"it {r['iterations']}  {r['seconds']}s  top {', '.join(r['top_features'][:4])}", flush=True)
        del d
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    write_json(EXPERIMENTS / f'{stamp}_m5_lightgbm.json', {'experiment': 'm5_lightgbm_v1', 'run': stamp, 'folds': {f: FOLDS[f] for f in args.folds},
                                                          'burn_in': BURN_IN, 'results': results}, pretty=True)
    print('\nnode            mean gain v best baseline   worst fold   mean ECE')
    for name, by_fold in results.items():
        gains = [r['gain_vs_best_baseline'] for r in by_fold.values()]
        print(f"{name:15} {np.mean(gains):+10.2%} {min(gains):+18.2%} {np.mean([r['ece_model'] for r in by_fold.values()]):12.4f}")


if __name__ == '__main__':
    main()
