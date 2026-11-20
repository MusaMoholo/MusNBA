#!/usr/bin/env python3
"""Team engine trust test (PLAN M12, first cut): walk-forward seasons on 2022-23 → 2025-26.

From several dates in each past season, the team pathway (`scripts/pathway.py`) starts from the ratings known that day
(games before it only) and plays the real remaining regular-season schedule in 10,000 universes; the real final wins
are then scored against the simulated distribution. Variants differ in the two sources of spread:

  start_scale   the start draw at the estimate's posterior SD (0 = every universe starts at today's estimate)
  scale         the update gain, × the estimator's own response 1 / (n + 1 + K) (0 = ratings never move)

Measures, pooled over teams × seasons × start dates:
  dispersion    SD of z = (real final wins − simulated mean) / simulated SD: 1.0 = right, < 1 too wide, > 1 too narrow
  coverage      share of real final wins inside the simulated 10–90% interval (target 80%)
  CRPS          of final wins (lower is better); bias of the mean
  persistence   correlation across teams of the surprise (wins − expected wins) in the first and second half of the
                remaining games: real seasons v the same quantity inside each universe (averaged) — strength that
                really drifts makes surprises persist, and the gain should reproduce that

Uses 2022-26 history only (the 2026-27 final test is untouched). Logs to analysis/experiments/<UTC>_season_backtest.json.

  .venv/bin/python scripts/season_backtest.py [--worlds 10000] [--dates 11-20 12-25 02-01 03-10]
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import write_json  # noqa: E402
from scripts import aggregate, nodes, pathway, train  # noqa: E402
from scripts.evaluate import EXPERIMENTS  # noqa: E402

SEASONS = (2023, 2024, 2025, 2026)  # hoopR labels: 2023 = 2022-23
VARIANTS = {  # name: (start_scale, scale, n_cap)
    'fixed': (0.0, 0.0, None), 'start_only': (1.0, 0.0, None), 'updates_only': (0.0, 1.0, None), 'v0': (1.0, 1.0, None),
    'start_half_upd_half': (0.5, 0.5, None), 'start_1_upd_half': (1.0, 0.5, None), 'start_half_upd_1': (0.5, 1.0, None),
    'start_1_upd_2': (1.0, 2.0, None),
}
GRID = {'start_scale': (0.4, 0.6, 0.8, 1.0), 'scale': (0.5, 1.0, 1.5), 'n_cap': (None, 20, 40)}  # --grid (M12 calibration)


def grid_variants() -> dict:
    out = {'fixed': VARIANTS['fixed'], 'v0': VARIANTS['v0']}
    for st in GRID['start_scale']:
        for sc in GRID['scale']:
            for cap in GRID['n_cap']:
                out[f's{st:g}_u{sc:g}_c{cap or "inf"}'] = (st, sc, cap)
    return out


def team_games(season: int) -> pd.DataFrame:
    """One row per team-game of the regular season (NBA teams only): date, team, opponent, home, points for and
    against, box possessions (FGA − OREB + TOV + 0.44 FTA; team turnovers are not in player boxes) and game minutes."""
    box = pd.read_parquet(ROOT / 'data' / 'raw' / 'hoopr' / f'player_box_{season}.parquet',
                          columns=['game_id', 'season_type', 'game_date', 'team_id', 'opponent_team_id', 'home_away', 'team_score',
                                   'opponent_team_score', 'minutes', 'field_goals_attempted', 'offensive_rebounds', 'turnovers',
                                   'free_throws_attempted'])
    box = box[(box['season_type'] == 2)].dropna(subset=['team_id'])
    box['team'] = box['team_id'].astype('int64').astype(str)
    box['opp'] = box['opponent_team_id'].astype('int64').astype(str)
    box = box[box['team'].isin(nodes.NBA_TEAM_IDS) & box['opp'].isin(nodes.NBA_TEAM_IDS)]
    for c in ('minutes', 'field_goals_attempted', 'offensive_rebounds', 'turnovers', 'free_throws_attempted'):
        box[c] = pd.to_numeric(box[c], errors='coerce').fillna(0)
    g = box.groupby(['game_id', 'team'], as_index=False).agg(
        date=('game_date', 'first'), opp=('opp', 'first'), home=('home_away', 'first'), pts=('team_score', 'first'),
        opp_pts=('opponent_team_score', 'first'), fga=('field_goals_attempted', 'sum'), oreb=('offensive_rebounds', 'sum'),
        tov=('turnovers', 'sum'), fta=('free_throws_attempted', 'sum'), player_min=('minutes', 'sum'))
    g['date'] = pd.to_datetime(g['date']).dt.strftime('%Y-%m-%d')
    g['poss'] = g['fga'] - g['oreb'] + g['tov'] + 0.44 * g['fta']
    g['minutes'] = 48 + 5 * np.maximum(0, np.round((g['player_min'] / 5 - 48) / 5))
    g = g.merge(g[['game_id', 'team', 'poss']].rename(columns={'team': 'opp', 'poss': 'opp_poss'}), on=['game_id', 'opp'])
    g['home'] = g['home'] == 'home'
    g['win'] = g['pts'] > g['opp_pts']
    return g.sort_values(['date', 'game_id', 'team']).reset_index(drop=True)


def state_before(g: pd.DataFrame, day: str):
    """T and league as projection.team_table would give them for `day` (games before it), in the pathway's fields."""
    past = g[g['date'] < day]
    T = {}
    for t, d in past.groupby('team'):
        T[t] = {'gp': len(d), 'w': int(d['win'].sum()), 'l': int((~d['win']).sum()),
                'ortg': 100 * d['pts'].sum() / d['poss'].sum(), 'drtg': 100 * d['opp_pts'].sum() / d['opp_poss'].sum(),
                'pace': 48 * (d['poss'].sum() + d['opp_poss'].sum()) / 2 / d['minutes'].sum()}
    lg = {'ortg': 100 * past['pts'].sum() / past['poss'].sum(),
          'pace': 48 * (past['poss'].sum() + past['opp_poss'].sum()) / 2 / past['minutes'].sum()}
    return T, lg


def run(g: pd.DataFrame, day: str, worlds: int, seed: int, start_scale: float, scale: float, n_cap=None) -> dict:
    T, lg = state_before(g, day)
    future = g[(g['date'] >= day) & g['home']]
    games = [{'game_id': r.game_id, 'home_id': r.team, 'away_id': r.opp, 'neutral': 0} for r in future.itertuples()]
    ids = sorted(T, key=int)
    idx = {t: i for i, t in enumerate(ids)}
    rng = np.random.default_rng(seed)
    out = pathway.play(T, lg, games, worlds, rng, None, {'start_scale': start_scale, 'scale': scale, 'n_cap': n_cap})
    hw = out['home_win']  # (W, G)
    H = np.zeros((len(games), len(ids)))
    A = np.zeros((len(games), len(ids)))
    for k, r in enumerate(games):
        H[k, idx[r['home_id']]], A[k, idx[r['away_id']]] = 1, 1
    real_hw = future['win'].to_numpy()
    half = len(games) // 2  # surprise halves by game order (the season's remaining games, split in time)
    first, second = np.arange(len(games)) < half, np.arange(len(games)) >= half
    p = hw.mean(0)  # each game's simulated home win share

    def wins(x, mask):  # x: (..., G) home wins → per-team wins over masked games
        x = np.asarray(x, float)
        return x[..., mask] @ H[mask] + (1 - x[..., mask]) @ A[mask]

    sim_w = wins(hw, np.ones(len(games), bool))  # (W, teams) remaining wins
    real_w = wins(real_hw, np.ones(len(games), bool))
    exp1, exp2 = wins(p, first), wins(p, second)
    real_s1, real_s2 = wins(real_hw, first) - exp1, wins(real_hw, second) - exp2
    sim_s1, sim_s2 = wins(hw, first) - exp1, wins(hw, second) - exp2
    sim_corr = np.mean([np.corrcoef(a, b)[0, 1] for a, b in zip(sim_s1[:2000], sim_s2[:2000])])
    mean, sd = sim_w.mean(0), sim_w.std(0)
    lo, hi = np.quantile(sim_w, 0.1, axis=0), np.quantile(sim_w, 0.9, axis=0)
    crps = aggregate.crps_samples(sim_w[:2000], real_w)  # per team (samples along axis 0)
    return {'day': day, 'games': len(games), 'teams': len(ids), 'z': ((real_w - mean) / sd).tolist(),
            'inside': ((real_w >= lo) & (real_w <= hi)).tolist(), 'crps': np.asarray(crps).tolist(),
            'bias': (mean - real_w).tolist(), 'sim_sd': sd.tolist(),
            'persistence_real': float(np.corrcoef(real_s1, real_s2)[0, 1]), 'persistence_sim': float(sim_corr)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--worlds', type=int, default=10000)
    ap.add_argument('--dates', nargs='+', default=['11-20', '12-25', '02-01', '03-10'], metavar='MM-DD')
    ap.add_argument('--variants', nargs='+', default=None)
    ap.add_argument('--grid', action='store_true', help='calibration grid (GRID) with leave-one-season-out selection')
    ap.add_argument('--name', default=None)
    args = ap.parse_args()
    started = time.time()
    table = grid_variants() if args.grid else VARIANTS
    args.variants = args.variants or list(table)
    args.name = args.name or ('season_calibration' if args.grid else 'season_backtest')
    data = {s: team_games(s) for s in SEASONS}
    results = {v: [] for v in args.variants}
    for s, g in data.items():
        for md in args.dates:
            day = f'{s - 1 if md >= "07" else s}-{md}'
            for v in args.variants:
                st, sc, cap = table[v]
                r = run(g, day, args.worlds, 20261120 + s, st, sc, cap)  # same seed per date: variants paired
                r['season'] = s
                results[v].append(r)
        print(f'season {s - 1}-{str(s)[2:]} done  {time.time() - started:.0f}s', flush=True)
    summary = {}
    for v, rs in results.items():
        z = np.concatenate([r['z'] for r in rs])
        by_date = {}
        for md in args.dates:
            sel = [r for r in rs if r['day'].endswith(md)]
            zz = np.concatenate([r['z'] for r in sel])
            by_date[md] = {'dispersion': round(float(zz.std()), 3), 'coverage_10_90': round(float(np.mean(np.concatenate([r['inside'] for r in sel]))), 3),
                           'crps': round(float(np.mean(np.concatenate([r['crps'] for r in sel]))), 3),
                           'sim_sd': round(float(np.mean(np.concatenate([r['sim_sd'] for r in sel]))), 2),
                           'persistence_real': round(float(np.mean([r['persistence_real'] for r in sel])), 3),
                           'persistence_sim': round(float(np.mean([r['persistence_sim'] for r in sel])), 3)}
        summary[v] = {'start_scale': table[v][0], 'scale': table[v][1], 'n_cap': table[v][2], 'team_starts': int(z.size),
                      'dispersion': round(float(z.std()), 3), 'mean_z': round(float(z.mean()), 3),
                      'coverage_10_90': round(float(np.mean(np.concatenate([r['inside'] for r in rs]))), 3),
                      'crps': round(float(np.mean(np.concatenate([r['crps'] for r in rs]))), 3),
                      'bias': round(float(np.mean(np.concatenate([r['bias'] for r in rs]))), 3),
                      'sim_sd': round(float(np.mean(np.concatenate([r['sim_sd'] for r in rs]))), 2),
                      'persistence_real': round(float(np.mean([r['persistence_real'] for r in rs])), 3),
                      'persistence_sim': round(float(np.mean([r['persistence_sim'] for r in rs])), 3),
                      'by_date': by_date}
    # Leave one season out: choose by mean CRPS on the other three seasons, score on the held-out one.
    loso = {}
    for held in SEASONS:
        def crps_of(v, keep):
            return float(np.mean(np.concatenate([r['crps'] for r in results[v] if keep(r['season'])])))
        pick = min(results, key=lambda v: crps_of(v, lambda s: s != held))
        loso[f'{held - 1}-{str(held)[2:]}'] = {'chosen': pick, **{v: {
            'crps': round(crps_of(v, lambda s: s == held), 3),
            'dispersion': round(float(np.concatenate([r['z'] for r in results[v] if r['season'] == held]).std()), 3)}
            for v in dict.fromkeys([pick, 'fixed', 'v0']) if v in results}}
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    write_json(EXPERIMENTS / f'{stamp}_{args.name}.json', {
        'experiment': 'm12_season_backtest', 'run': stamp, 'commit': train.git_commit(), 'worlds': args.worlds,
        'seasons': [f'{s - 1}-{str(s)[2:]}' for s in SEASONS], 'dates': args.dates, 'pathway': pathway.PATHWAY,
        'variants': {v: table[v] for v in args.variants}, 'seconds': round(time.time() - started), 'summary': summary,
        'leave_one_season_out': loso}, pretty=True)
    print(f"{'variant':22} {'disp':>6} {'cov':>6} {'crps':>7} {'bias':>6} {'simSD':>6} {'pers real':>9} {'pers sim':>8}")
    for v, m in summary.items():
        print(f"{v:22} {m['dispersion']:6.3f} {m['coverage_10_90']:6.3f} {m['crps']:7.3f} {m['bias']:6.2f} {m['sim_sd']:6.2f} "
              f"{m['persistence_real']:9.3f} {m['persistence_sim']:8.3f}")
    for held, m in loso.items():
        print(f"held out {held}: chosen {m['chosen']}  " + '  '.join(f"{v} crps {x['crps']:.3f} disp {x['dispersion']:.3f}" for v, x in m.items() if v != 'chosen'))
    print(f'\nrun {stamp}_{args.name}  ({time.time() - started:.0f}s)')


if __name__ == '__main__':
    main()
