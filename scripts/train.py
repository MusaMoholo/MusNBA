#!/usr/bin/env python3
"""Train and score every decision of the chain on the rolling folds (ENGINE_PLAN M5; TRAINING_PLAN §5).

Per node and fold: LightGBM on games up to the fold's training cut-off (after a December 2022 burn-in),
early stopping on the latest 10% of that window, validation on the fold's held-out window — never on the
final test (this season). Candidate nodes (player choices) are binary models on one row per candidate,
normalised by softmax within each segment with a temperature fitted on the early-stopping slice.

Each node is compared with two baselines: league rates (training window) and player profiles. Every held-out
decision's log loss is stored (data/derived/experiments/<run>.npz) for paired comparisons (scripts/compare.py).

  .venv/bin/python scripts/train.py --name <label> [options]     every node, every fold (datasets cached by nodes.py)
  .venv/bin/python scripts/train.py --folds F4 --nodes who what
  options: --half-life S · --playoff-weight W · --drop f|@group … · --features DIR · --banded · --recalibrate · --seed
  .venv/bin/python scripts/train.py --config models/v1.json             the version's settings on the folds
  .venv/bin/python scripts/train.py --config models/v1.json --final     persist data/models/v1/ + score the final test once
  … --segments DIR --features DIR/features/pregame.parquet              a segments variant (possessions.py --out)
  … --train-segments DIR --train-features FILE   cross-data test: train each fold on that dataset's rows, validate on the
                                                 main dataset's held-out rows (e.g. old-convention models on 2026-27-style
                                                 inputs, paired with a run trained on the main dataset; FINDINGS §3k)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, write_json  # noqa: E402
from scripts import nodes  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS, TEST_FROM  # noqa: E402

BURN_IN = '2022-12-01'
FINAL_TRAIN_TO = '2026-06-30'  # --final: everything before the final test
MODELS = DERIVED.parent / 'models'  # data/models/<version>/ (fitted files stay out of git; settings in models/<version>.json)
NODES = ['duration', 'event', 'who', 'what', 'location', 'shot_result', 'assisted', 'assister', 'blocked', 'blocker', 'rebound',
         'rebounder', 'turnover_type', 'stealer', 'fouler', 'free_throw']
CATEGORICAL = ['start_code', 'zone', 'season_type', 'grp_code']
EPS = 1e-12
LOSSES = DERIVED / 'experiments'  # per-row held-out losses per run (paired comparisons: scripts/compare.py)


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
    if tag == 'location':  # league band shares within the shot's zone (training window)
        zones = X['zone'].to_numpy().astype(int)
        table = pd.crosstab(zones[tr], y[tr], normalize='index').reindex(index=range(len(nodes.ZONES)), columns=range(k), fill_value=0)
        P = table.to_numpy()[zones[va]] + EPS
        P = P * d['class_mask'][va]
        return P / P.sum(axis=1, keepdims=True)
    if tag == 'zone_rate':
        zones = X['zone'].to_numpy().astype(int)
        rate = pd.Series(y[tr]).groupby(zones[tr]).mean()
        return pd.Series(zones[va]).map(rate).to_numpy()
    if tag in ('actor_assisted_share', 'actor_ft_pct'):
        p = X[tag].to_numpy(dtype=float)[va]
        return np.where(np.isnan(p), y[tr].mean(), p)
    raise KeyError(tag)


def sample_weights(d, mask, train_to, cfg):
    """Training-row weights: exponential age decay (half-life in seasons) and a weight for playoff/play-in rows."""
    w = np.ones(int(mask.sum()))
    if cfg.get('half_life'):
        age = (pd.Timestamp(train_to) - pd.to_datetime(pd.Series(d['date'][mask]))).dt.days.to_numpy()
        w *= 0.5 ** (age / (365.25 * cfg['half_life']))
    if cfg.get('playoff_weight', 1.0) != 1.0:
        w[d['season_type'][mask] != 2] *= cfg['playoff_weight']
    return w


def intercepts(raw, y, kind, classes=None, steps=50):
    """Per-class log-odds offsets that make mean forecasts match class frequencies on (raw scores, labels) — the
    maximum-likelihood intercept refit, used to correct level drift on the latest slice of the training window."""
    if kind == 'binary':
        b, target = 0.0, y.mean()
        for _ in range(steps):
            p = 1 / (1 + np.exp(-(raw + b)))
            b += (target - p.mean()) / max(np.mean(p * (1 - p)), 1e-6)
        return np.array([b])
    freq = np.bincount(y, minlength=classes) / len(y)
    b = np.zeros(classes)
    for _ in range(steps):
        z = raw + b
        P = np.exp(z - z.max(axis=1, keepdims=True))
        P /= P.sum(axis=1, keepdims=True)
        b += np.log(np.maximum(freq, 1e-9) / np.maximum(P.mean(axis=0), 1e-9))
    return b


def apply_intercepts(raw, b, kind):
    if kind == 'binary':
        return 1 / (1 + np.exp(-(raw + b[0])))
    z = raw + b
    P = np.exp(z - z.max(axis=1, keepdims=True))
    return P / P.sum(axis=1, keepdims=True)


def band_distances(X, tr):
    """Replace shot distance (and lateral offset) by the mean of its location band over the training rows — the precision
    the engine can produce, since it samples a band (node "location"), not an exact spot."""
    if 'distance' not in X or 'zone' not in X:
        return X
    zone = np.array([nodes.ZONES[int(z)] if z == z else None for z in X['zone'].to_numpy()], dtype=object)
    band = nodes.location_band(zone, X['distance'].to_numpy())
    X = X.copy()
    for col in ('distance', 'lateral'):
        if col in X:
            means = pd.Series(X[col].to_numpy()[tr & (band >= 0)]).groupby(band[tr & (band >= 0)]).mean()
            X[col] = np.where(band >= 0, pd.Series(band).map(means).to_numpy(), X[col].to_numpy()).astype(np.float32)
    return X


def model_columns(X, drop):
    """Columns the model sees: `drop` removes a feature by name (also with the actor_ prefix) or a group (@team, …)."""
    drop = {c for item in (drop or ()) for c in (nodes.GROUPS[item[1:]] if item.startswith('@') else [item])}
    return [c for c in X.columns if c not in drop and c.removeprefix('actor_') not in drop]


def sample_labels(kind, P, group, rng):
    """Labels drawn from the model's own probabilities: the ECE a perfectly calibrated model would show on these rows."""
    if kind == 'multiclass':
        u = rng.random(len(P))
        return np.minimum((P.cumsum(axis=1) < u[:, None]).sum(axis=1), P.shape[1] - 1)
    if kind == 'binary':
        return (rng.random(len(P)) < P).astype(int)
    first = np.r_[True, group[1:] != group[:-1]]
    u = np.repeat(rng.random(first.sum()), np.diff(np.r_[np.flatnonzero(first), len(group)]))
    cs = pd.Series(P).groupby(group).cumsum().to_numpy()
    hit = (cs >= u) & (cs - P < u)
    hit &= pd.Series(hit).groupby(group).cumsum().to_numpy() == 1
    return hit.astype(int)


def calibration_error(kind, P, y, group=None):
    if kind == 'multiclass':
        return multiclass_ece(P, y)
    return ece(P, y.astype(float))


def class_bias(kind, P, y, group=None):
    """Largest gap between mean forecast and frequency over classes; for candidates, the favourite's forecast minus its hit rate."""
    if kind == 'multiclass':
        return float(np.max(np.abs(P.mean(axis=0) - np.bincount(y, minlength=P.shape[1]) / len(y))))
    if kind == 'binary':
        return float(P.mean() - y.mean())
    top = pd.Series(P).groupby(group).transform('max').to_numpy() == P
    top &= pd.Series(top).groupby(group).cumsum().to_numpy() == 1
    return float(P[top].mean() - y[top].mean())


def breakdown(kind, P, y, period, margin, group=None, seed=0):
    """ECE (and the ECE expected from noise alone) by period and by score-margin bucket of the offence."""
    rng = np.random.default_rng(seed)
    y_null = sample_labels(kind, P, group, rng)
    buckets = {f'Q{q}': period == q for q in (1, 2, 3, 4)}
    buckets['OT'] = period >= 5
    buckets.update({'m<=-15': margin <= -15, 'm-14..-6': (margin >= -14) & (margin <= -6), 'm-5..5': (margin >= -5) & (margin <= 5),
                    'm6..14': (margin >= 6) & (margin <= 14), 'm>=15': margin >= 15})
    out = {}
    for key, m in buckets.items():
        if m.sum() < 200:
            continue
        g = group[m] if group is not None else None
        out[key] = {'n': int(m.sum()), 'ece': round(calibration_error(kind, P[m], y[m]), 5),
                    'ece_null': round(calibration_error(kind, P[m], y_null[m]), 5), 'bias': round(class_bias(kind, P[m], y[m], g), 5)}
    return out


def params(kind, rows, cfg):
    big = rows > 2_000_000
    p = {'learning_rate': 0.1 if big or kind == 'multiclass' else 0.05, 'num_leaves': 63, 'min_data_in_leaf': 200,
         'feature_fraction': 0.8, 'bagging_fraction': 0.5 if big else 0.8, 'bagging_freq': 1, 'lambda_l2': 1.0,
         'max_bin': 63 if big else 255, 'num_threads': cfg.get('threads', 12), 'verbose': -1, 'seed': cfg.get('seed', 7),
         'deterministic': True, 'force_col_wise': True}
    p['objective'] = 'binary' if kind in ('binary', 'candidate') else 'multiclass'
    p.update(cfg.get('lgb', {}))
    return p


def data_root(value: str):
    """CLI value for a data location: 'default' = the canonical data in data/derived (None), else a path."""
    return None if value == 'default' else Path(value)


def hybrid(train_d: dict, val_d: dict, cut) -> dict:
    """Training rows (up to the fold's cut-off) from `train_d`, validation rows from `val_d`, in `val_d`'s order — so the
    held-out losses pair row by row with a run trained on `val_d` itself (scripts/compare.py)."""
    train_to, val_from, val_to = cut
    if list(train_d['X'].columns) != list(val_d['X'].columns):
        raise SystemExit(f"{val_d['name']}: the two datasets have different columns")
    a = train_d['date'] <= train_to
    b = (val_d['date'] >= val_from) & (val_d['date'] <= val_to)
    out = {k: val_d[k] for k in ('name', 'kind', 'classes', 'profile')}
    out['X'] = pd.concat([train_d['X'][a], val_d['X'][b]], ignore_index=True)
    for k in nodes.ARRAYS:
        if train_d.get(k) is None or val_d.get(k) is None:
            out[k] = None
            continue
        right = val_d[k][b]
        if k == 'group':  # candidate groups (one per decision) must stay distinct across the two sources
            right = right + (int(train_d[k][a].max()) + 1 if a.any() else 0)
        out[k] = np.concatenate([train_d[k][a], right])
    return out


def run_node(d, fold, cut, cfg=None):
    """Fit one node on one fold. Returns the logged metrics and per-row held-out losses (one per decision)."""
    cfg = cfg or {}
    train_to, val_from, val_to = cut
    date = d['date']
    tr_all = (date >= BURN_IN) & (date <= train_to)
    va = (date >= val_from) & (date <= val_to)
    es_from = np.quantile(pd.to_datetime(pd.Series(date[tr_all])).astype('int64'), 0.9)
    es = tr_all & (pd.to_datetime(pd.Series(date)).astype('int64').to_numpy() >= es_from)
    tr = tr_all & ~es
    X, y, kind = d['X'], d['y'], d['kind']
    cols = model_columns(X, cfg.get('drop'))
    Xm = band_distances(X[cols], tr) if cfg.get('banded') else X[cols]
    cats = [c for c in CATEGORICAL if c in cols]
    p = params(kind, int(tr.sum()), cfg)
    if kind == 'multiclass':
        p['num_class'] = d['classes']
    dtrain = lgb.Dataset(Xm[tr], label=y[tr], weight=sample_weights(d, tr, train_to, cfg), categorical_feature=cats, free_raw_data=True)
    dval = lgb.Dataset(Xm[es], label=y[es], categorical_feature=cats, reference=dtrain)
    start = time.time()
    model = lgb.train(p, dtrain, num_boost_round=3000, valid_sets=[dval], callbacks=[lgb.early_stopping(50, verbose=False)])
    out = {'rows_train': int(tr.sum()), 'rows_val': int(va.sum()), 'iterations': model.best_iteration, 'seconds': round(time.time() - start, 1),
           'features': len(cols)}
    gain = model.feature_importance('gain')
    out['top_features'] = [cols[i] for i in np.argsort(-gain)[:8]]
    group = None
    if kind == 'candidate':
        g = d['group']
        group = g[va]
        t = fit_temperature(model.predict(Xm[es], raw_score=True), y[es], g[es])
        P = softmax_groups(model.predict(Xm[va], raw_score=True), group, t)
        sizes = pd.Series(group).groupby(group).transform('size').to_numpy()
        prof = d['profile_score'][va]
        prof_p = prof / pd.Series(prof).groupby(group).transform('sum').to_numpy()
        chosen = y[va] == 1
        loss = -np.log(np.clip(P[chosen], EPS, 1))
        games = d['game'][va][chosen]
        out.update({'temperature': round(float(t), 3), 'model': float(loss.mean()),
                    'league': group_logloss(1 / sizes, y[va], group), 'profile': group_logloss(prof_p, y[va], group),
                    'ece_model': ece(P, y[va].astype(float)), 'ece_profile': ece(prof_p, y[va].astype(float))})
    elif kind == 'multiclass':
        P = model.predict(Xm[va], num_iteration=model.best_iteration)
        if cfg.get('recalibrate'):
            b = intercepts(model.predict(Xm[es], raw_score=True), y[es], kind, d['classes'])
            P = apply_intercepts(model.predict(Xm[va], raw_score=True), b, kind)
            out['intercepts'] = [round(float(v), 4) for v in b]
        freq = np.tile(np.bincount(y[tr_all], minlength=d['classes']) / tr_all.sum(), (va.sum(), 1))
        if d.get('class_mask') is not None:  # e.g. location: only the bands of the shot's zone are possible
            mask = d['class_mask'][va]
            P, freq = P * mask, (freq + EPS) * mask
            P, freq = P / P.sum(axis=1, keepdims=True), freq / freq.sum(axis=1, keepdims=True)
        prof = profile_baseline(d, tr_all, va)
        loss = -np.log(np.clip(P[np.arange(va.sum()), y[va]], EPS, 1))
        games = d['game'][va]
        out.update({'model': float(loss.mean()), 'league': logloss_multi(freq, y[va]),
                    'profile': logloss_multi(prof, y[va]), 'ece_model': multiclass_ece(P, y[va]), 'ece_profile': multiclass_ece(prof, y[va])})
    else:
        P = model.predict(Xm[va], num_iteration=model.best_iteration)
        if cfg.get('recalibrate'):
            b = intercepts(model.predict(Xm[es], raw_score=True), y[es], kind)
            P = apply_intercepts(model.predict(Xm[va], raw_score=True), b, kind)
            out['intercepts'] = [round(float(v), 4) for v in b]
        prof = profile_baseline(d, tr_all, va)
        yv = y[va]
        loss = -(yv * np.log(np.clip(P, EPS, 1)) + (1 - yv) * np.log(np.clip(1 - P, EPS, 1)))
        games = d['game'][va]
        out.update({'model': float(loss.mean()), 'league': logloss_binary(np.full(va.sum(), y[tr_all].mean()), y[va]),
                    'profile': logloss_binary(prof, y[va]), 'ece_model': ece(P, y[va].astype(float)), 'ece_profile': ece(prof, y[va].astype(float))})
    out['calibration'] = breakdown(kind, P, y[va], d['period'][va], d['margin'][va], group)
    if kind == 'multiclass':  # signed level bias per class on the held-out window (mean forecast − frequency)
        out['class_bias'] = [round(float(v), 5) for v in P.mean(axis=0) - np.bincount(y[va], minlength=P.shape[1]) / va.sum()]
    elif kind == 'binary':
        out['class_bias'] = [round(float(P.mean() - y[va].mean()), 5)]
    best = min(out['league'], out['profile'])
    out['gain_vs_best_baseline'] = round(1 - out['model'] / best, 5)
    fitted = {'model': model, 'columns': cols, 'categorical': cats, 'temperature': out.get('temperature', 1.0),
              'intercepts': out.get('intercepts')}
    return out, {'loss': loss.astype(np.float32), 'game': games.astype(str)}, fitted


def predict_ms(model, X, kind, rows):
    """Milliseconds to score `rows` rows (one engine step for 10,000 worlds; ×5 candidates for player choices)."""
    sample = X.sample(n=rows, replace=True, random_state=0)
    model.predict(sample.iloc[:100], raw_score=kind == 'candidate')
    start = time.perf_counter()
    model.predict(sample, raw_score=kind == 'candidate')
    return round((time.perf_counter() - start) * 1000, 1)


def save_model(folder: Path, name: str, d: dict, fitted: dict, result: dict, cfg: dict) -> dict:
    """Write the node's LightGBM model and return its config entry (inputs, temperature, timings, final-test score)."""
    folder.mkdir(parents=True, exist_ok=True)
    model = fitted['model']
    path = folder / f'{name}.txt'
    model.save_model(str(path), num_iteration=model.best_iteration)
    X = d['X'][fitted['columns']]
    rows = 50_000 if d['kind'] == 'candidate' else 10_000
    return {'file': path.name, 'kind': d['kind'], 'classes': d.get('classes'), 'columns': fitted['columns'],
            'categorical': fitted['categorical'], 'temperature': fitted['temperature'], 'intercepts': fitted['intercepts'],
            'iterations': model.best_iteration,
            'settings': {k: cfg.get(k) for k in ('half_life', 'playoff_weight', 'drop', 'banded', 'recalibrate', 'features', 'seed')},
            'rows_train': result['rows_train'], 'predict_ms_10k_worlds': predict_ms(model, X, d['kind'], rows),
            'final_test': {k: result[k] for k in ('rows_val', 'model', 'league', 'profile', 'gain_vs_best_baseline', 'ece_model', 'ece_profile')}}


def git_commit():
    try:
        return subprocess.run(['git', '-C', str(ROOT), 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--folds', nargs='*', default=list(FOLDS))
    ap.add_argument('--nodes', nargs='*', default=NODES)
    ap.add_argument('--name', default='control', help='experiment label (log file suffix)')
    ap.add_argument('--half-life', type=float, default=None, help='sample-weight half-life in seasons (default: no decay)')
    ap.add_argument('--playoff-weight', type=float, default=1.0, help='weight of playoff and play-in rows')
    ap.add_argument('--drop', nargs='*', default=[], help=f'features or @groups to leave out (ablation); groups: {", ".join(nodes.GROUPS)}')
    ap.add_argument('--features', type=Path, default=None, help='a pregame.parquet variant (scripts/features.py --out)')
    ap.add_argument('--segments', type=Path, default=None, help='a segments root variant (scripts/possessions.py --out)')
    ap.add_argument('--train-segments', type=data_root, default=False, help="cross-data test: segments root of the training rows ('default' = data/derived)")
    ap.add_argument('--train-features', type=data_root, default=False, help="cross-data test: pregame.parquet of the training rows ('default' = data/derived/features)")
    ap.add_argument('--banded', action='store_true', help='shot distance as its location band mean (what the engine can sample)')
    ap.add_argument('--recalibrate', action='store_true', help='refit class intercepts on the early-stopping slice (latest 10%%)')
    ap.add_argument('--seed', type=int, default=7)
    ap.add_argument('--threads', type=int, default=12)
    ap.add_argument('--config', type=Path, default=None,
                    help='model version settings (models/<version>.json): its default and per-node entries override the flags above')
    ap.add_argument('--final', action='store_true',
                    help='with --config: train every node on all games before the final test, save data/models/<version>/, '
                         'and score the final test (2026-27 to date) once — only at promotion')
    args = ap.parse_args()
    base = {'half_life': args.half_life, 'playoff_weight': args.playoff_weight, 'drop': args.drop, 'banded': args.banded,
            'recalibrate': args.recalibrate,
            'features': str(args.features) if args.features else None, 'segments': str(args.segments) if args.segments else None,
            'seed': args.seed, 'threads': args.threads}
    version = None
    if args.config:
        spec = json.loads(args.config.read_text())
        version = spec['version']
        base.update(spec.get('default', {}))
        per_node = spec.get('nodes', {})
    else:
        per_node = {}
    if args.final and not version:
        raise SystemExit('--final needs --config models/<version>.json')
    cfg_for = lambda node: {**base, **per_node.get(node, {}), 'name': args.name}
    features = Path(base['features']) if base['features'] else None
    segments = Path(base['segments']) if base.get('segments') else None
    cross = args.train_segments is not False or args.train_features is not False
    train_segments, train_features = (args.train_segments or None), (args.train_features or None)
    if cross and args.final:
        raise SystemExit('--train-segments/--train-features are a fold test; not with --final')
    if cross:
        base['train_segments'] = str(train_segments) if train_segments else 'default'
        base['train_features'] = str(train_features) if train_features else 'default'
    folds = {'final': (FINAL_TRAIN_TO, TEST_FROM, '2100-01-01')} if args.final else {f: FOLDS[f] for f in args.folds}
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    name_tag = f'final_{version}' if args.final else args.name
    results, losses, saved = {}, {}, {}
    model_dir = MODELS / version if args.final else None
    for d in nodes.datasets(args.nodes, pregame=features, include_current=args.final, segments=segments):
        name = d['name']
        cfg = cfg_for(name)
        results[name] = {}
        train_d = next(nodes.datasets([name], pregame=train_features, segments=train_segments)) if cross else None
        for fold, cut in folds.items():
            r, rows, fitted = run_node(hybrid(train_d, d, cut) if cross else d, fold, cut, cfg)
            results[name][fold] = r
            losses[f'{name}__{fold}__loss'], losses[f'{name}__{fold}__game'] = rows['loss'], rows['game']
            if args.final:
                saved[name] = save_model(model_dir, name, d, fitted, r, cfg)
            print(f"{name:14} {fold}  league {r['league']:.4f}  profile {r['profile']:.4f}  model {r['model']:.4f}  "
                  f"gain {r['gain_vs_best_baseline']:+.2%}  ECE {r['ece_model']:.4f} (profile {r['ece_profile']:.4f})  "
                  f"it {r['iterations']}  {r['seconds']}s  top {', '.join(r['top_features'][:4])}", flush=True)
        del d, train_d
    LOSSES.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(LOSSES / f'{stamp}_{name_tag}.npz', **losses)
    record = {'experiment': f'm5_{name_tag}', 'run': stamp, 'commit': git_commit(), 'version': version,
              'config': {'default': {**base, 'name': args.name}, 'nodes': per_node}, 'folds': folds, 'burn_in': BURN_IN,
              'losses': str((LOSSES / f'{stamp}_{name_tag}.npz').relative_to(ROOT)), 'results': results}
    write_json(EXPERIMENTS / f'{stamp}_{name_tag}.json', record, pretty=True)
    if args.final:
        write_json(model_dir / 'config.json', {'version': version, 'created': stamp, 'commit': git_commit(), 'burn_in': BURN_IN,
                                                'train_through': FINAL_TRAIN_TO, 'final_test_from': TEST_FROM,
                                                'segments': base.get('segments'), 'features': base.get('features'),
                                                'experiment': f'analysis/experiments/{stamp}_{name_tag}.json', 'nodes': saved}, pretty=True)
        print(f'models: {model_dir}')
    print(f'\nrun {stamp}_{name_tag}')
    print('node            mean gain v best baseline   worst fold   mean ECE')
    for name, by_fold in results.items():
        gains = [r['gain_vs_best_baseline'] for r in by_fold.values()]
        print(f"{name:15} {np.mean(gains):+10.2%} {min(gains):+18.2%} {np.mean([r['ece_model'] for r in by_fold.values()]):12.4f}")


if __name__ == '__main__':
    main()
