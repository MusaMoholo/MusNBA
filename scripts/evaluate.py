#!/usr/bin/env python3
"""Evaluation harness and node baselines (TRAINING_PLAN.md §5; ENGINE_PLAN M4).

Scores each decision on the rolling-origin folds — never on the final test (this season). Two baselines
per node: league rates from the fold's training window, and shrunk player rates from the point-in-time
profiles (scripts/features.py). LightGBM (M5) must beat the better of the two on every node.

  .venv/bin/python scripts/evaluate.py          baselines on folds F1–F4, logged to analysis/experiments/
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, write_json  # noqa: E402

FOLDS = {  # name: (train through, validate from, validate through)  — TRAINING_PLAN §5
    'F1': ('2023-12-31', '2024-01-01', '2024-04-30'),
    'F2': ('2024-12-31', '2025-01-01', '2025-04-30'),
    'F3': ('2025-09-30', '2025-10-01', '2025-12-31'),
    'F4': ('2025-12-31', '2026-01-01', '2026-04-30'),
}
TEST_FROM = '2026-07-01'  # 2026-27: the untouched final test
ZONES = ('rim', 'paint', 'mid', 'corner3', 'above3')
EPS = 1e-12
EXPERIMENTS = ROOT / 'analysis' / 'experiments'


def load():
    seg = pd.concat([pd.read_parquet(p) for p in sorted((DERIVED / 'history').glob('*/segments.parquet'))], ignore_index=True)
    seg = seg[seg['game_ok'] & (seg['date_et'] < TEST_FROM)].reset_index(drop=True)
    seg['seg_id'] = np.arange(len(seg))
    pre = pd.read_parquet(DERIVED / 'features' / 'pregame.parquet')
    return seg, pre


def attach(seg, pre, side, columns):
    """Long table: one row per segment × on-court player of `side` with his pre-game features."""
    cols = [f'{side}_{i}' for i in range(1, 6)]
    long = seg[['seg_id', 'game_id'] + cols].melt(id_vars=['seg_id', 'game_id'], value_vars=cols, value_name='player').dropna(subset=['player'])
    return long.merge(pre[['game_id', 'player'] + columns], on=['game_id', 'player'], how='left')


def logloss(p):
    return float(-np.mean(np.log(np.clip(p, EPS, 1))))


def node_who(seg, pre, mask_val):
    """Which of the five ends the segment: uniform v usage-proportional."""
    use = seg[seg['actor'].notna() & seg['end_type'].isin(['shot', 'fouled', 'turnover', 'foul']) & ~seg['heave']]
    use = use[((use['end_type'] != 'foul') | (use['fta'] > 0)) & mask_val.loc[use.index]]
    long = attach(use, pre, 'off', ['usage'])
    long['usage'] = long['usage'].fillna(long['usage'].median())
    long['share'] = long['usage'] / long.groupby('seg_id')['usage'].transform('sum')
    picked = long.merge(use[['seg_id', 'actor']], on='seg_id')
    p = picked.loc[picked['player'] == picked['actor'], ['seg_id', 'share']].drop_duplicates('seg_id')
    n = use['seg_id'].isin(p['seg_id']).sum()
    return {'rows': int(n), 'league': float(np.log(5)), 'player': logloss(p['share'].to_numpy())}


def node_what(seg, pre, mask_train, mask_val):
    """Given the actor: shot by zone, turnover or foul drawn (7 classes)."""
    use = seg[seg['actor'].notna() & seg['end_type'].isin(['shot', 'fouled', 'turnover', 'foul']) & ~seg['heave']]
    use = use[(use['end_type'] != 'foul') | (use['fta'] > 0)]
    use = use[(use['end_type'] != 'shot') | use['zone'].isin(ZONES)]
    label = np.where(use['end_type'] == 'shot', use['zone'], np.where(use['end_type'] == 'turnover', 'tov', 'foul'))
    use = use.assign(label=label)
    classes = list(ZONES) + ['tov', 'foul']
    freq = use[mask_train.loc[use.index]]['label'].value_counts(normalize=True).reindex(classes).fillna(EPS)
    val = use[mask_val.loc[use.index]].merge(pre[['game_id', 'player', 'shot_share', 'tov_share', 'foul_drawn_share'] + [f'mix_{z}' for z in ZONES]],
                                             left_on=['game_id', 'actor'], right_on=['game_id', 'player'], how='left')
    probs = pd.DataFrame({z: val['shot_share'] * val[f'mix_{z}'] for z in ZONES})
    probs['tov'], probs['foul'] = val['tov_share'], val['foul_drawn_share']
    probs = probs.fillna(freq).div(probs.fillna(freq).sum(axis=1), axis=0)
    pick = probs.to_numpy()[np.arange(len(val)), [classes.index(c) for c in val['label']]]
    return {'rows': len(val), 'league': logloss(freq.reindex(val['label']).to_numpy()), 'player': logloss(pick)}


def node_shot_result(seg, pre, mask_train, mask_val):
    """Make or miss, by zone: league zone FG% v the shooter's shrunk zone FG%."""
    shots = seg[(seg['end_type'] == 'shot') & ~seg['heave'] & seg['zone'].isin(ZONES)]
    shots = shots.assign(made=shots['made'].astype(float))
    league = shots[mask_train.loc[shots.index]].groupby('zone')['made'].mean().astype(float)
    val = shots[mask_val.loc[shots.index]].merge(pre[['game_id', 'player'] + [f'fg_{z}' for z in ZONES]],
                                                left_on=['game_id', 'actor'], right_on=['game_id', 'player'], how='left')
    y = val['made'].to_numpy(dtype=float)
    p_league = val['zone'].map(league).to_numpy(dtype=float)
    zone_index = val['zone'].map({z: i for i, z in enumerate(ZONES)}).to_numpy()
    p_player = val[[f'fg_{z}' for z in ZONES]].to_numpy(dtype=float)[np.arange(len(val)), zone_index]
    p_player = np.where(np.isnan(p_player), p_league, p_player)
    bce = lambda p: float(-np.mean(y * np.log(np.clip(p, EPS, 1)) + (1 - y) * np.log(np.clip(1 - p, EPS, 1))))
    return {'rows': len(val), 'league': bce(p_league), 'player': bce(p_player)}


def node_rebound(seg, pre, mask_train, mask_val):
    """Offensive or defensive rebound: league rate v the ten players' rebound rates."""
    reb = seg[seg['rebound'].notna()]
    y_all = reb['rebound'].isin(['off', 'team_off'])
    league = float(y_all[mask_train.loc[reb.index]].mean())
    val = reb[mask_val.loc[reb.index]]
    off = attach(val, pre, 'off', ['oreb_pct']).groupby('seg_id')['oreb_pct'].sum()
    dfn = attach(val, pre, 'def', ['dreb_pct']).groupby('seg_id')['dreb_pct'].sum()
    share = (off / (off + dfn)).reindex(val['seg_id']).to_numpy()
    # Player rebound rates exclude team rebounds; rescale to the league offensive share including them.
    train_share = league
    raw_mean = np.nanmean(share)
    p_player = np.clip(share * (train_share / raw_mean), 0.01, 0.99)
    p_player = np.where(np.isnan(p_player), league, p_player)
    y = y_all.loc[val.index].astype(float).to_numpy()
    bce = lambda p: float(-np.mean(y * np.log(np.clip(p, EPS, 1)) + (1 - y) * np.log(np.clip(1 - p, EPS, 1))))
    return {'rows': len(val), 'league': bce(np.full(len(y), league)), 'player': bce(p_player)}


def run():
    seg, pre = load()
    results = {}
    for fold, (train_to, val_from, val_to) in FOLDS.items():
        mask_train = seg['date_et'] <= train_to
        mask_val = (seg['date_et'] >= val_from) & (seg['date_et'] <= val_to)
        results[fold] = {'who': node_who(seg, pre, mask_val), 'what': node_what(seg, pre, mask_train, mask_val),
                         'shot_result': node_shot_result(seg, pre, mask_train, mask_val),
                         'rebound_side': node_rebound(seg, pre, mask_train, mask_val)}
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    record = {'experiment': 'baselines', 'run': stamp, 'folds': FOLDS, 'final_test_untouched_from': TEST_FROM,
              'features': json.loads((DERIVED / 'features' / 'features_report.json').read_text())['families'], 'results': results}
    write_json(EXPERIMENTS / f'{stamp}_baselines.json', record, pretty=True)
    return record


def main():
    record = run()
    nodes = ['who', 'what', 'shot_result', 'rebound_side']
    print(f"{'node':14} " + ' '.join(f'{f:>22}' for f in FOLDS) + f"{'mean gain':>11}")
    for node in nodes:
        cells, gains = [], []
        for fold in FOLDS:
            r = record['results'][fold][node]
            cells.append(f"{r['league']:.4f} → {r['player']:.4f}")
            gains.append(1 - r['player'] / r['league'])
        print(f"{node:14} " + ' '.join(f'{c:>22}' for c in cells) + f"{np.mean(gains):>10.1%}")
    print('(log loss: league baseline → player-profile baseline; lower is better)')


if __name__ == '__main__':
    main()
