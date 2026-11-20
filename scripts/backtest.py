#!/usr/bin/env python3
"""Engine backtest (PLAN M9, first cut): play held-out fold games forward and compare with what happened.

Everything a game on date D sees is from before D: node models fitted on the fold's training window only (all 16,
`aggregate.fit_models`), each player's pre-game profile and each team's pre-game style for that game
(`pregame.parquet`, `team_pregame.parquet`), rotations replayed from the team's games before D (M3 v0). Known
availability: the players who actually played (the availability model is M11). The engine then plays the game with its
own clock — possessions, pace, minutes and the score all emerge, unlike M6a which replays the real clock.

Scores per game: team points, total and margin (CRPS, 10–90% coverage, bias), possessions and points per 100, win
probability (Brier, log loss, calibration), strength expression (slope of the real margin on the simulated mean
margin: 1 = right, > 1 = team quality under-expressed), overtime rate; players by role tier: points, rebounds, assists,
minutes (bias, coverage, CRPS).

  .venv/bin/python scripts/backtest.py --config models/v1.1.json [--fold F4] [--games 200] [--worlds 1000] [--jobs 4]
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, write_json  # noqa: E402
from scripts import aggregate, nodes, projection, train  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS  # noqa: E402

PLAYER_STATS = ('pts', 'reb', 'ast', 'min')
_W = {}  # per-worker state


def fold_engine_version(fold: str, spec_path: Path, threads: int) -> str:
    """Fit (or reuse) all 16 fold models and write the engine-readable config beside them; returns the Models version."""
    fitted, _, spec = aggregate.fit_models(fold, spec_path, threads, node_list=train.NODES)
    dflt = spec.get('default', {})
    folder = train.MODELS / 'folds' / f"{spec.get('version', 'default')}_{fold}_all"
    cache = nodes.cache_dir(Path(dflt['features']) if dflt.get('features') else None, Path(dflt['segments']) if dflt.get('segments') else None)
    entry = {}
    for n, f in fitted.items():
        z = np.load(cache / f'{n}.npz', allow_pickle=False)
        entry[n] = {'file': f'{n}.txt', 'kind': str(z['kind']), 'classes': int(z['classes']) or None, 'columns': f['columns'],
                    'categorical': f['categorical'], 'temperature': f['temperature'], 'intercepts': f.get('intercepts')}
    report = (Path(dflt['features']).parent if dflt.get('features') else DERIVED / 'features') / 'features_report.json'
    matchup = json.loads(report.read_text()).get('matchup') if report.exists() else None
    write_json(folder / 'config.json', {'version': f"{spec.get('version')}_{fold}", 'fold': True, 'train_through': FOLDS[fold][0],
                                        'segments': dflt.get('segments'), 'features': dflt.get('features'), 'matchup': matchup,
                                        'nodes': entry}, pretty=True)
    return str(folder.relative_to(train.MODELS))


def load_inputs(spec: dict, fold: str):
    dflt = spec.get('default', {})
    features = Path(dflt['features']).parent if dflt.get('features') else DERIVED / 'features'
    segments = Path(dflt['segments']) if dflt.get('segments') else DERIVED
    _, val_from, val_to = FOLDS[fold]
    season = int(val_to[:4]) if val_to[5:7] <= '06' else int(val_to[:4]) + 1
    pre = pd.read_parquet(features / 'pregame.parquet')
    pre = pre[(pre['date_et'] >= val_from) & (pre['date_et'] <= val_to)]
    teams = pd.read_parquet(features / 'team_pregame.parquet')
    teams = teams[(teams['date_et'] >= val_from) & (teams['date_et'] <= val_to)]
    seg = pd.read_parquet(segments / 'history' / str(season) / 'segments.parquet',
                          columns=['game_id', 'date_et', 'season', 'season_type', 'game_ok', 'offense', 'defense', 'off_home', 'poss', 'points', 'period'])
    seg = seg[(seg['date_et'] >= val_from) & (seg['date_et'] <= val_to)]
    stints = pd.read_parquet(DERIVED / 'history' / str(season) / 'stints.parquet')
    on = pd.read_parquet(DERIVED / 'history' / str(season) / 'on_court.parquet', columns=['game_id', 'player', 'sec'])
    box = pd.read_parquet(ROOT / 'data' / 'raw' / 'hoopr' / f'player_box_{season}.parquet',
                          columns=['game_id', 'athlete_id', 'team_id', 'points', 'rebounds', 'assists', 'minutes'])
    box = box.dropna(subset=['athlete_id', 'team_id'])
    box = box.assign(game_id=box['game_id'].astype('int64').astype(str), player=box['athlete_id'].astype('int64').astype(str),
                     team=box['team_id'].astype('int64').astype(str))
    return pre, teams, seg, stints, on, box


def eligible_games(seg: pd.DataFrame) -> np.ndarray:
    """Reconciled regular-season NBA games."""
    s = seg[(seg['season_type'] == 2) & seg['offense'].astype(str).isin(nodes.NBA_TEAM_IDS)]
    ok = s.groupby('game_id')['game_ok'].all()
    return np.array(sorted(ok[ok].index))


def _init(version, spec_path, fold, worlds, rotation='replay', known_starters=False):
    from scripts import engine
    spec = json.loads(Path(spec_path).read_text())
    _W.update({'engine': engine.Engine(version), 'mod': engine, 'inputs': load_inputs(spec, fold), 'worlds': worlds,
               'teams': json.loads((DERIVED / 'teams.json').read_text()), 'rotation': rotation, 'known_starters': known_starters})
    if rotation == 'targets':  # D29 minutes: pre-game states for every history player-game; ramp and spread from before the window
        from scripts import minutes
        m = minutes.build(FOLDS[fold][1], include_current=False)
        m['by_game'] = m['rows'].set_index(['game_id', 'player'])
        _W['minutes'] = m


def run_game(gid: str) -> dict:
    eng, engine, worlds = _W['engine'], _W['mod'], _W['worlds']
    pre, teams, seg, stints, on, box = _W['inputs']
    s = seg[seg['game_id'] == gid]
    day, season = str(s['date_et'].iloc[0]), int(s['season'].iloc[0])
    home = str(s.loc[s['off_home'], 'offense'].iloc[0])
    away = str(s.loc[~s['off_home'], 'offense'].iloc[0])
    p = pre[pre['game_id'] == gid]
    t = teams[teams['game_id'] == gid].copy()
    t['last_game'] = (pd.to_datetime(t['date_et']) - pd.to_timedelta(t['rest_days'], unit='D')).dt.strftime('%Y-%m-%d')
    t['season_start'] = (pd.to_datetime(t['date_et']) - pd.to_timedelta(t['season_day'], unit='D')).dt.strftime('%Y-%m-%d')
    players = {}
    for side, tid in (('home', home), ('away', away)):
        rows = p[p['team'] == tid]
        players[side] = [{'id': r.player, 'name': r.player, 'pos': r.pos or '', 'jersey': '', 'starter': bool(r.starter), 'status': 'Active',
                          'injury': None, 'availability': 1.0, 'base_min': float(r.min_avg) if pd.notna(r.min_avg) else 0.0}
                         for r in rows.itertuples()]
        if _W.get('rotation') == 'targets':
            from scripts import minutes
            m = _W['minutes']
            for pl in players[side]:
                key = (str(gid), str(pl['id']))
                row = m['by_game'].loc[key] if key in m['by_game'].index else None
                pl['minutes'] = minutes.player_state(m, tid, pl['id'], day, row) if row is not None else \
                    {**minutes.player_state({'params': m['params'], 'latest': {}, 'team_dates': {}, 'ramp': m['ramp'], 'sd': m['sd']}, tid, pl['id'], day)}
                pl['projected_starter'] = bool(pl['starter']) if _W.get('known_starters') else False
    game = {'game_id': gid, 'home_id': home, 'away_id': away}
    g = engine.Game(game, players, p.drop(columns=['game_id']), t.drop(columns=['game_id']), stints, day)
    g.season = season
    eng.simulate(g, worlds, projection.seed_for('backtest', eng.m.cfg['version'], day, gid))
    st = eng.last
    sim_pts = st.pts.sum(2)  # (W, 2): home, away
    real_pts = {side: int(s.loc[s['offense'] == tid, 'points'].sum()) for side, tid in (('home', home), ('away', away))}
    gb = box[box['game_id'] == gid]
    real_pts_box = {side: int(gb.loc[gb['team'] == tid, 'points'].sum()) for side, tid in (('home', home), ('away', away))}
    real_poss = {side: int(s.loc[s['offense'] == tid, 'poss'].nunique()) for side, tid in (('home', home), ('away', away))}
    rng = np.random.default_rng(projection.seed_for('pit', gid))
    out = {'game_id': gid, 'date_et': day, 'home': home, 'away': away, 'worlds': worlds,
           'real_home': real_pts_box['home'], 'real_away': real_pts_box['away'], 'real_home_seg': real_pts['home'], 'real_away_seg': real_pts['away'],
           'real_poss_home': real_poss['home'], 'real_poss_away': real_poss['away'], 'real_ot': int(s['period'].max() > 4),
           'sim_poss_home': float(st.poss[:, 0].mean()), 'sim_poss_away': float(st.poss[:, 1].mean()),
           'sim_ot': float((st.period > 4).mean())}
    measures = {'home': (sim_pts[:, 0], real_pts_box['home']), 'away': (sim_pts[:, 1], real_pts_box['away']),
                'total': (sim_pts.sum(1), real_pts_box['home'] + real_pts_box['away']),
                'margin': (sim_pts[:, 0] - sim_pts[:, 1], real_pts_box['home'] - real_pts_box['away'])}
    for m, (x, y) in measures.items():
        x = x.astype(float)
        out[f'{m}_sim'] = float(x.mean())
        out[f'{m}_sd'] = float(x.std())
        out[f'{m}_crps'] = float(aggregate.crps_samples(x[:, None], np.array([float(y)]))[0])
        out[f'{m}_pit'] = float(aggregate.pit(x[:, None], np.array([float(y)]), rng)[0])
    out['p_home'] = float((sim_pts[:, 0] > sim_pts[:, 1]).mean())
    # players: simulated full-game boxes v the real box score
    rows = []
    idx = {pid: i for i, pid in enumerate(g.ids)}
    on_g = on[on['game_id'] == gid].set_index('player')['sec']
    for r in gb.itertuples():
        if r.player not in idx:
            continue
        i = idx[r.player]
        sim = {'pts': st.box['pts'][:, i].sum(1), 'reb': (st.box['oreb'][:, i] + st.box['dreb'][:, i]).sum(1),
               'ast': st.box['ast'][:, i].sum(1), 'min': st.minutes[:, i].sum(1)}
        real = {'pts': r.points, 'reb': r.rebounds, 'ast': r.assists, 'min': float(on_g.get(r.player, np.nan)) / 60}
        row = {'game_id': gid, 'player': r.player}
        for k in PLAYER_STATS:
            if real[k] is None or pd.isna(real[k]):
                continue
            x = sim[k].astype(float)
            row[f'{k}_actual'], row[f'{k}_sim'] = float(real[k]), float(x.mean())
            row[f'{k}_crps'] = float(aggregate.crps_samples(x[:, None], np.array([float(real[k])]))[0])
            row[f'{k}_pit'] = float(aggregate.pit(x[:, None], np.array([float(real[k])]), rng)[0])
        rows.append(row)
    out['players'] = rows
    return out


def summarise(games: pd.DataFrame, players: pd.DataFrame, pre: pd.DataFrame) -> dict:
    g = games
    out = {'games': len(g)}
    for m in ('home', 'away', 'total', 'margin'):
        y = g[f'real_{m}'] if m in ('home', 'away') else (g['real_home'] + g['real_away'] if m == 'total' else g['real_home'] - g['real_away'])
        out[m] = {'actual': round(float(y.mean()), 2), 'sim': round(float(g[f'{m}_sim'].mean()), 2),
                  'bias': round(float((g[f'{m}_sim'] - y).mean()), 2), 'sim_sd': round(float(g[f'{m}_sd'].mean()), 2),
                  'actual_sd_around_sim': round(float((y - g[f'{m}_sim']).std()), 2),
                  'coverage_10_90': round(float(g[f'{m}_pit'].between(0.1, 0.9).mean()), 3), 'crps': round(float(g[f'{m}_crps'].mean()), 3)}
    real_margin = g['real_home'] - g['real_away']
    slope = float(np.polyfit(g['margin_sim'], real_margin, 1)[0])
    out['margin']['slope_real_on_sim'] = round(slope, 3)
    out['margin']['corr'] = round(float(np.corrcoef(g['margin_sim'], real_margin)[0, 1]), 3)
    poss_real = (g['real_poss_home'] + g['real_poss_away']) / 2
    poss_sim = (g['sim_poss_home'] + g['sim_poss_away']) / 2
    out['possessions_per_team'] = {'actual': round(float(poss_real.mean()), 2), 'sim': round(float(poss_sim.mean()), 2),
                                   'bias_pct': round(float(poss_sim.mean() / poss_real.mean() - 1), 4)}
    ortg_real = 100 * (g['real_home'] + g['real_away']) / (g['real_poss_home'] + g['real_poss_away'])
    ortg_sim = 100 * (g['home_sim'] + g['away_sim']) / (g['sim_poss_home'] + g['sim_poss_away'])
    out['points_per_100'] = {'actual': round(float(ortg_real.mean()), 2), 'sim': round(float(ortg_sim.mean()), 2)}
    # team offence expression: each side's simulated v real points per 100, regressed across team-games
    side_sim = np.concatenate([100 * g['home_sim'] / g['sim_poss_home'], 100 * g['away_sim'] / g['sim_poss_away']])
    side_real = np.concatenate([100 * g['real_home'] / g['real_poss_home'], 100 * g['real_away'] / g['real_poss_away']])
    out['points_per_100']['slope_real_on_sim'] = round(float(np.polyfit(side_sim, side_real, 1)[0]), 3)
    out['points_per_100']['sim_sd_across_team_games'] = round(float(side_sim.std()), 2)
    win = (real_margin > 0).astype(float)
    p = g['p_home'].clip(1e-4, 1 - 1e-4)
    bins = pd.cut(p, [0, 0.2, 0.4, 0.6, 0.8, 1.0], include_lowest=True)
    out['win'] = {'brier': round(float(((p - win) ** 2).mean()), 4), 'log_loss': round(float(-(win * np.log(p) + (1 - win) * np.log(1 - p)).mean()), 4),
                  'base_rate_home': round(float(win.mean()), 3), 'mean_p_home': round(float(p.mean()), 3),
                  'calibration': {str(k): {'n': int(v.size), 'p': round(float(p[v.index].mean()), 3), 'won': round(float(win[v.index].mean()), 3)}
                                  for k, v in p.groupby(bins, observed=True)}}
    out['overtime'] = {'actual': round(float(g['real_ot'].mean()), 4), 'sim': round(float(g['sim_ot'].mean()), 4)}
    pl = players.merge(pre[['game_id', 'player', 'usage', 'starter']], on=['game_id', 'player'], how='left')
    pl['tier'] = np.where(pl['usage'] >= 0.25, 'star', np.where(pl['starter'] == True, 'starter', 'bench'))  # noqa: E712
    out['players'] = {}
    for tier, d in pl.groupby('tier'):
        out['players'][tier] = {'player_games': len(d)}
        for k in PLAYER_STATS:
            if f'{k}_actual' not in d:
                continue
            e = d.dropna(subset=[f'{k}_actual'])
            out['players'][tier][k] = {'actual': round(float(e[f'{k}_actual'].mean()), 2), 'sim': round(float(e[f'{k}_sim'].mean()), 2),
                                       'rel_bias': round(float(e[f'{k}_sim'].mean() / max(e[f'{k}_actual'].mean(), 1e-9) - 1), 4),
                                       'coverage_10_90': round(float(e[f'{k}_pit'].between(0.1, 0.9).mean()), 3),
                                       'crps': round(float(e[f'{k}_crps'].mean()), 3)}
    return out


def _crps_normal(mu, sd, y):
    from math import erf, exp, pi, sqrt
    z = (y - mu) / sd
    cdf = 0.5 * (1 + np.vectorize(erf)(z / sqrt(2)))
    pdf = np.exp(-z * z / 2) / sqrt(2 * pi)
    return sd * (z * (2 * cdf - 1) + 2 * pdf - 1 / sqrt(pi))


def rating_baseline(games: pd.DataFrame) -> dict:
    """The team engine's game model on the same games (D26): each side's expected points from ratings before the date
    (`season_backtest.state_before`: box possessions, shrunk K = 8 — what the pathway starts from), scores normal with
    baseline-v1's SD 11.25 and rho 0.35. Same measures as the engine's, so the two engines compare on real outcomes."""
    from scripts import pathway, season_backtest
    p = pathway.PATHWAY
    out_rows = []
    cache = {}
    for r in games.itertuples():
        season = int(r.date_et[:4]) + (1 if r.date_et[5:7] >= '07' else 0)
        if season not in cache:
            cache[season] = season_backtest.team_games(season)
        T, lg = season_backtest.state_before(cache[season], r.date_et)
        off, dfn, pace, _ = pathway.start_ratings(T, lg, [r.home, r.away], p['K'])
        pace_g = pace[0] * pace[1] / lg['pace']
        mu_h = pace_g * off[0] * dfn[1] / lg['ortg'] / 100 + p['home_court'] / 2
        mu_a = pace_g * off[1] * dfn[0] / lg['ortg'] / 100 - p['home_court'] / 2
        out_rows.append({'game_id': r.game_id, 'mu_h': mu_h, 'mu_a': mu_a, 'pace': pace_g,
                         'off_h': off[0] - lg['ortg'], 'off_a': off[1] - lg['ortg'], 'def_h': dfn[0] - lg['ortg'], 'def_a': dfn[1] - lg['ortg']})
    b = pd.DataFrame(out_rows)
    g = games.merge(b, on='game_id')
    sd, rho = p['team_sd'], p['team_rho']
    sds = {'home': sd, 'away': sd, 'total': sd * np.sqrt(2 * (1 + rho)), 'margin': sd * np.sqrt(2 * (1 - rho))}
    mus = {'home': g['mu_h'], 'away': g['mu_a'], 'total': g['mu_h'] + g['mu_a'], 'margin': g['mu_h'] - g['mu_a']}
    ys = {'home': g['real_home'], 'away': g['real_away'], 'total': g['real_home'] + g['real_away'], 'margin': g['real_home'] - g['real_away']}
    out = {'games': len(g)}
    for m in mus:
        out[m] = {'sim': round(float(mus[m].mean()), 2), 'bias': round(float((mus[m] - ys[m]).mean()), 2),
                  'crps': round(float(_crps_normal(mus[m].to_numpy(), sds[m], ys[m].to_numpy()).mean()), 3),
                  'actual_sd_around_sim': round(float((ys[m] - mus[m]).std()), 2)}
    out['margin']['slope_real_on_sim'] = round(float(np.polyfit(mus['margin'], ys['margin'], 1)[0]), 3)
    out['margin']['corr'] = round(float(np.corrcoef(mus['margin'], ys['margin'])[0, 1]), 3)
    out['total']['slope_real_on_sim'] = round(float(np.polyfit(mus['total'], ys['total'], 1)[0]), 3)
    from math import erf, sqrt
    ph = np.clip(0.5 * (1 + np.vectorize(erf)(mus['margin'] / sds['margin'] / sqrt(2))), 1e-4, 1 - 1e-4)
    win = (ys['margin'] > 0).astype(float)
    out['win'] = {'brier': round(float(((ph - win) ** 2).mean()), 4),
                  'log_loss': round(float(-(win * np.log(ph) + (1 - win) * np.log(1 - ph)).mean()), 4)}
    # Strength expression: points per 100 per team-game on the side's offensive and the opponent's defensive rating
    # (deviations from the league, ratings before the date) — engine v real loadings; 1:1 with real = fully expressed.
    sides = pd.DataFrame({
        'off': np.concatenate([g['off_h'], g['off_a']]), 'opp_def': np.concatenate([g['def_a'], g['def_h']]),
        'sim': np.concatenate([100 * g['home_sim'] / g['sim_poss_home'], 100 * g['away_sim'] / g['sim_poss_away']]),
        'real': np.concatenate([100 * g['real_home'] / g['real_poss_home'], 100 * g['real_away'] / g['real_poss_away']])})
    X = np.column_stack([np.ones(len(sides)), sides['off'], sides['opp_def']])
    out['strength_loading'] = {y: dict(zip(('intercept', 'offence', 'opp_defence'),
                                           (round(float(v), 3) for v in np.linalg.lstsq(X, sides[y], rcond=None)[0])))
                               for y in ('sim', 'real')}
    out['engine_v_baseline_margin_corr'] = round(float(np.corrcoef(games.set_index('game_id').loc[g['game_id'], 'margin_sim'], mus['margin'])[0, 1]), 3)
    return out


def m6a_same_games(games: pd.DataFrame) -> dict | None:
    """M6a (real possessions, lineups and clock replayed; v1.1 settings) on the same games: separates per-possession error
    (shared with M6a) from what only the free-running engine adds (pace, rotations and minutes, end of game)."""
    files = sorted((DERIVED / 'experiments').glob('*_m6a_v1.1_teams.parquet'))
    if not files:
        return None
    m = pd.read_parquet(files[-1])
    m = m[m['game_id'].isin(set(games['game_id']))].pivot(index='game_id', columns='measure', values='sim')
    g = games.set_index('game_id').loc[m.index]
    real_margin, real_total = g['real_home'] - g['real_away'], g['real_home'] + g['real_away']
    return {'run': files[-1].stem, 'games': len(m),
            'total_bias': round(float((m['total'] - real_total).mean()), 2),
            'margin_bias': round(float((m['margin'] - real_margin).mean()), 2),
            'margin_slope_real_on_sim': round(float(np.polyfit(m['margin'], real_margin, 1)[0]), 3),
            'margin_corr': round(float(np.corrcoef(m['margin'], real_margin)[0, 1]), 3),
            'engine_v_m6a_margin_corr': round(float(np.corrcoef(m['margin'], g['margin_sim'])[0, 1]), 3)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--config', type=Path, required=True, help='model version settings (models/<version>.json)')
    ap.add_argument('--fold', default='F4')
    ap.add_argument('--games', type=int, default=200, help='random sample of held-out regular-season games (0 = all)')
    ap.add_argument('--worlds', type=int, default=1000)
    ap.add_argument('--jobs', type=int, default=4)
    ap.add_argument('--threads', type=int, default=8, help='LightGBM threads for fitting fold models')
    ap.add_argument('--seed', type=int, default=20261119)
    ap.add_argument('--name', default=None)
    ap.add_argument('--rotation', choices=('replay', 'targets'), default='replay',
                    help='replay = M3 v0 templates (v1.1); targets = D29 minutes (healthy roles, 240 by priority, ramp)')
    ap.add_argument('--models', default=None, help='reuse fitted fold models (e.g. folds/v1.1_F4_all) instead of fitting')
    ap.add_argument('--known-starters', action='store_true', help='targets only: open with the real starters (a perfect lineup source)')
    ap.add_argument('--summarise', metavar='RUN', help='re-score a saved run (<stamp>_<name>) without simulating; updates its log')
    args = ap.parse_args()
    start = time.time()
    spec = json.loads(args.config.read_text())
    if args.summarise:
        frame = pd.read_parquet(DERIVED / 'experiments' / f'{args.summarise}.parquet')
        players = pd.read_parquet(DERIVED / 'experiments' / f'{args.summarise}_players.parquet')
        pre, *_ = load_inputs(spec, args.fold)
        summary = summarise(frame, players, pre)
        summary['team_rating_baseline'] = rating_baseline(frame)
        summary['m6a_same_games'] = m6a_same_games(frame)
        log = EXPERIMENTS / f'{args.summarise}.json'
        record = json.loads(log.read_text())
        record['summary'] = summary
        write_json(log, record, pretty=True)
        print(json.dumps(summary, indent=1))
        return
    version = args.models or fold_engine_version(args.fold, args.config, args.threads)
    _, _, seg, _, _, _ = load_inputs(spec, args.fold)
    games = eligible_games(seg)
    rng = np.random.default_rng(args.seed)
    if args.games and args.games < len(games):
        games = np.sort(rng.choice(games, args.games, replace=False))
    print(f'backtest {spec.get("version")} {args.fold}: {len(games)} games × {args.worlds} worlds, {args.jobs} jobs, models {version}', flush=True)
    os.environ['OMP_NUM_THREADS'] = str(max(1, (os.cpu_count() or 4) // max(1, args.jobs)))
    ctx = mp.get_context('spawn')
    results = []
    with ctx.Pool(args.jobs, initializer=_init, initargs=(version, str(args.config), args.fold, args.worlds, args.rotation, args.known_starters)) as pool:
        for i, r in enumerate(pool.imap(run_game, list(games), chunksize=1), 1):
            results.append(r)
            if i % 10 == 0 or i == len(games):
                print(f'game {i}/{len(games)}  {time.time() - start:.0f}s', flush=True)
    players = pd.DataFrame([p for r in results for p in r.pop('players')])
    frame = pd.DataFrame(results)
    pre, *_ = load_inputs(spec, args.fold)
    summary = summarise(frame, players, pre)
    summary['team_rating_baseline'] = rating_baseline(frame)
    summary['m6a_same_games'] = m6a_same_games(frame)
    name = args.name or f"backtest_{spec.get('version')}_{args.fold}"
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    (DERIVED / 'experiments').mkdir(parents=True, exist_ok=True)
    frame.to_parquet(DERIVED / 'experiments' / f'{stamp}_{name}.parquet', index=False)
    players.to_parquet(DERIVED / 'experiments' / f'{stamp}_{name}_players.parquet', index=False)
    write_json(EXPERIMENTS / f'{stamp}_{name}.json', {'experiment': 'm9_engine_backtest', 'run': stamp, 'commit': train.git_commit(),
                                                      'config': str(args.config), 'fold': args.fold, 'models': version, 'games': len(games),
                                                      'worlds': args.worlds, 'rotation': args.rotation, 'known_starters': args.known_starters,
                                                      'seconds': round(time.time() - start), 'summary': summary}, pretty=True)
    print(json.dumps(summary, indent=1))
    print(f'\nrun {stamp}_{name}  ({len(games)} games, {time.time() - start:.0f}s)')


if __name__ == '__main__':
    main()
