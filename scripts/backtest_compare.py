#!/usr/bin/env python3
"""Legacy engine comparison using actual-starter tiers; not the current promotion gate.

Use a1_compare.py and an explicit release_gate policy for new pre-game-tier qualification (MODEL.md).

For each run: player tiers (bias, 10–90% coverage, CRPS for minutes, points, rebounds, assists), then strength loading,
margin slope, total/margin CRPS and win log loss v the team-rating model. Each later run is paired with the first on
identical player-games and games: mean CRPS change with a standard error clustered by game.

  .venv/bin/python scripts/backtest_compare.py <run A> <run B> [<run C> …]     (run = <stamp>_<name>, as logged)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED  # noqa: E402
from scripts.evaluate import EXPERIMENTS  # noqa: E402

STATS = ('min', 'pts', 'reb', 'ast')


def clustered(diff: pd.Series, groups: pd.Series):
    g = diff.groupby(groups.to_numpy()).sum()
    n = len(diff)
    se = np.sqrt((g ** 2).sum()) / n if n else np.nan
    return float(diff.mean()), float(se)


def tiers(players: pd.DataFrame, pre: pd.DataFrame) -> pd.Series:
    pl = players.merge(pre, on=['game_id', 'player'], how='left')
    return pd.Series(np.where(pl['usage'] >= 0.25, 'star', np.where(pl['starter'] == True, 'starter', 'bench')), index=players.index)  # noqa: E712


def compare(runs: list[str]) -> dict:
    logs = {r: json.loads((EXPERIMENTS / f'{r}.json').read_text()) for r in runs}
    frames = {r: pd.read_parquet(DERIVED / 'experiments' / f'{r}.parquet') for r in runs}
    players = {r: pd.read_parquet(DERIVED / 'experiments' / f'{r}_players.parquet') for r in runs}
    pre = pd.read_parquet(DERIVED / 'features' / 'pregame.parquet', columns=['game_id', 'player', 'usage', 'starter'])
    pre['game_id'], pre['player'] = pre['game_id'].astype(str), pre['player'].astype(str)
    base = runs[0]
    out = {'runs': runs, 'per_run': {}, 'paired_v_first': {}}
    for r in runs:
        s = logs[r]['summary']
        t = s['team_rating_baseline']
        out['per_run'][r] = {
            'players': {tier: {k: {m: v[k][m] for m in ('rel_bias', 'coverage_10_90', 'crps')} for k in STATS if k in v}
                        for tier, v in s['players'].items()},
            'strength_loading_sim': t['strength_loading']['sim'], 'strength_loading_real': t['strength_loading']['real'],
            'margin_slope': s['margin']['slope_real_on_sim'], 'margin_corr': s['margin']['corr'],
            'total': {k: s['total'][k] for k in ('bias', 'crps', 'coverage_10_90', 'sim_sd', 'actual_sd_around_sim')},
            'margin': {k: s['margin'][k] for k in ('bias', 'crps', 'coverage_10_90', 'sim_sd', 'actual_sd_around_sim')},
            'win_log_loss': s['win']['log_loss'], 'team_model': {'total_crps': t['total']['crps'], 'margin_crps': t['margin']['crps'],
                                                                 'win_log_loss': t['win']['log_loss']},
            'possessions_bias': s['possessions_per_team']['bias_pct'], 'points_per_100': s['points_per_100']}
    for r in runs[1:]:
        a, b = frames[base].set_index('game_id'), frames[r].set_index('game_id')
        common = a.index.intersection(b.index)
        res = {'games': len(common)}
        for m in ('total', 'margin', 'home', 'away'):
            d = (b.loc[common, f'{m}_crps'] - a.loc[common, f'{m}_crps'])
            res[f'{m}_crps'] = {'change': round(float(d.mean()), 3), 'se': round(float(d.std() / np.sqrt(len(d))), 3)}
        pa, pb = players[base], players[r]
        key = ['game_id', 'player']
        m = pa.merge(pb, on=key, suffixes=('_a', '_b'))
        m['tier'] = tiers(m[key], pre).to_numpy()
        res['players'] = {}
        for tier, d in m.groupby('tier'):
            res['players'][tier] = {}
            for k in STATS:
                if f'{k}_crps_a' not in d:
                    continue
                e = d.dropna(subset=[f'{k}_crps_a', f'{k}_crps_b'])
                mean, se = clustered(e[f'{k}_crps_b'] - e[f'{k}_crps_a'], e['game_id'])
                res['players'][tier][k] = {'crps_change': round(mean, 4), 'se': round(se, 4), 'z': round(mean / se, 2) if se else None,
                                           'rel': round(mean / e[f'{k}_crps_a'].mean(), 4)}
        out['paired_v_first'][r] = res
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('runs', nargs='+')
    ap.add_argument('--log', default=None, help='write the comparison to analysis/experiments/<stamp>_<name>.json')
    args = ap.parse_args()
    r = compare(args.runs)
    print(json.dumps(r, indent=1))
    if args.log:
        from datetime import datetime, timezone
        from basketball_common import write_json
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        write_json(EXPERIMENTS / f'{stamp}_{args.log}.json', {'experiment': 'backtest_compare', 'run': stamp, **r}, pretty=True)


if __name__ == '__main__':
    main()
