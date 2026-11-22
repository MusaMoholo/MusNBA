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
from basketball_common import DERIVED, sha256_file, write_json  # noqa: E402
from scripts import aggregate, nodes, projection, train  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS  # noqa: E402

PLAYER_STATS = ('pts', 'reb', 'ast', 'min', 'fg3m')
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
    matchup = train._matchup_of(dflt.get('features'))  # the variant's assignment θ (D32 real, else D30 soft)
    write_json(folder / 'config.json', {'version': f"{spec.get('version')}_{fold}", 'fold': True, 'train_through': FOLDS[fold][0],
                                        'segments': dflt.get('segments'), 'features': dflt.get('features'), 'matchup': matchup,
                                        'nodes': entry}, pretty=True)
    return str(folder.relative_to(train.MODELS))


def load_inputs(spec: dict, fold: str, flow_diagnostics: bool = False):
    dflt = spec.get('default', {})
    features = Path(dflt['features']).parent if dflt.get('features') else DERIVED / 'features'
    segments = Path(dflt['segments']) if dflt.get('segments') else DERIVED
    _, val_from, val_to = FOLDS[fold]
    season = int(val_to[:4]) if val_to[5:7] <= '06' else int(val_to[:4]) + 1
    pre = pd.read_parquet(features / 'pregame.parquet')
    pre = pre[(pre['date_et'] >= val_from) & (pre['date_et'] <= val_to)]
    teams = pd.read_parquet(features / 'team_pregame.parquet')
    teams = teams[(teams['date_et'] >= val_from) & (teams['date_et'] <= val_to)]
    seg_columns = ['game_id', 'date_et', 'season', 'season_type', 'game_ok', 'offense', 'defense',
                   'off_home', 'poss', 'points', 'period']
    if flow_diagnostics:
        seg_columns += ['duration', 'start_clock']
    seg = pd.read_parquet(segments / 'history' / str(season) / 'segments.parquet', columns=seg_columns)
    seg = seg[(seg['date_et'] >= val_from) & (seg['date_et'] <= val_to)]
    stints = pd.read_parquet(DERIVED / 'history' / str(season) / 'stints.parquet')
    on = pd.read_parquet(DERIVED / 'history' / str(season) / 'on_court.parquet', columns=['game_id', 'player', 'sec'])
    box = pd.read_parquet(ROOT / 'data' / 'raw' / 'hoopr' / f'player_box_{season}.parquet',
                          columns=['game_id', 'athlete_id', 'team_id', 'points', 'rebounds', 'assists', 'minutes'] + list(COMPONENT_BOX.values()))
    box = box.dropna(subset=['athlete_id', 'team_id'])
    box = box.assign(game_id=box['game_id'].astype('int64').astype(str), player=box['athlete_id'].astype('int64').astype(str),
                     team=box['team_id'].astype('int64').astype(str))
    return pre, teams, seg, stints, on, box


def eligible_games(seg: pd.DataFrame) -> np.ndarray:
    """Reconciled regular-season NBA games."""
    s = seg[(seg['season_type'] == 2) & seg['offense'].astype(str).isin(nodes.NBA_TEAM_IDS)]
    ok = s.groupby('game_id')['game_ok'].all()
    return np.array(sorted(ok[ok].index))


def select_games(eligible: np.ndarray, count: int, seed: int, ids_path: Path | None = None) -> np.ndarray:
    if ids_path is not None:
        ids = json.loads(ids_path.read_text())
        if not isinstance(ids, list) or not ids or any(not isinstance(x, str) or not x.isdigit() for x in ids):
            raise ValueError('game IDs must be a non-empty JSON list of digit strings')
        if len(set(ids)) != len(ids):
            raise ValueError('game IDs must be unique')
        missing = sorted(set(ids) - set(eligible))
        if missing:
            raise ValueError(f'game IDs outside the eligible fold population: {missing}')
        return np.array(sorted(ids))
    if count < 0:
        raise ValueError('game count must be non-negative')
    if count and count < len(eligible):
        return np.sort(np.random.default_rng(seed).choice(eligible, count, replace=False))
    return eligible


def simulation_seed(version: str, day: str, gid: str, stream: int | None = None, seed_key: str | None = None) -> int:
    parts: list[str | int] = ['backtest', seed_key if seed_key is not None else version, day, gid]
    if stream is not None:
        parts.extend(['stream', stream])
    return projection.seed_for(*parts)


def _init(version, spec_path, fold, worlds, rotation='replay', known_starters=False, pool=None, stream=None, seed_key=None,
          flow_diagnostics=False, minutes_history='control', strict_minute_targets=False, substitution_report=None,
          capture_substitution_worlds=False):
    from scripts import engine
    if pool is not None:  # D36: rotation-table pool (0 = one table per world)
        engine.ROTATION['pool'] = pool
    spec = json.loads(Path(spec_path).read_text())
    _, _, val_to = FOLDS[fold]
    season = int(val_to[:4]) if val_to[5:7] <= '06' else int(val_to[:4]) + 1
    columns = ['game_id', 'team_id', 'period', 'pts']
    if flow_diagnostics:
        columns += ['player_id', 'sec', 'fga', 'fta', 'tov']
    period_rows = pd.read_csv(DERIVED / 'history' / str(season) / 'player_periods.csv.gz', usecols=columns,
                              dtype={'game_id': str, 'team_id': str, 'player_id': str})
    periods = period_rows.groupby(['game_id', 'team_id', 'period'])['pts'].sum()
    player_periods = None
    if flow_diagnostics:
        keys = ['game_id', 'team_id', 'player_id', 'period']
        if period_rows.duplicated(keys).any():
            raise ValueError('duplicate player-period source records')
        player_periods = period_rows.set_index(keys)
    _W.update({'engine': engine.Engine(version), 'mod': engine, 'inputs': load_inputs(spec, fold, flow_diagnostics), 'worlds': worlds,
               'teams': json.loads((DERIVED / 'teams.json').read_text()), 'rotation': rotation, 'known_starters': known_starters,
               'periods': periods, 'player_periods': player_periods, 'flow_diagnostics': flow_diagnostics,
               'stream': stream, 'seed_key': seed_key, 'strict_minute_targets': strict_minute_targets,
               'capture_substitution_worlds': capture_substitution_worlds})
    if substitution_report is not None:
        from scripts import a1_substitution_engine
        outgoing, incoming, timing = a1_substitution_engine.load_candidate(Path(substitution_report), fold)
        features = a1_substitution_engine.load_features(fold)
        _W['engine'].rotation_policy = a1_substitution_engine.SelectedTimeoutPolicy(
            outgoing, incoming, timing, features, capture_trace=capture_substitution_worlds)
    if rotation == 'targets':  # D29 minutes: pre-game states for every history player-game; ramp and spread from before the window
        from scripts import minutes
        if minutes_history == 'control':
            m = minutes.build(FOLDS[fold][1], include_current=False)
        elif minutes_history == 'nba_only':
            from scripts import a1_minutes_candidate
            m = a1_minutes_candidate.build(FOLDS[fold][1], include_current=False)
        else:
            raise ValueError(f'unknown minute-history candidate: {minutes_history}')
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
    g = engine.Game(game, players, p.drop(columns=['game_id']), t.drop(columns=['game_id']), stints, day,
                    position_policy=eng.m.position_policy, strict_minute_targets=_W['strict_minute_targets'])
    g.season = season
    sim_seed = simulation_seed(eng.m.cfg['version'], day, gid, _W['stream'], _W['seed_key'])
    if _W.get('flow_diagnostics'):
        eng.diag, eng.rotation_diag = [], []
    eng.simulate(g, worlds, sim_seed)
    st = eng.last
    sim_pts = st.pts.sum(2)  # (W, 2): home, away
    real_pts = {side: int(s.loc[s['offense'] == tid, 'points'].sum()) for side, tid in (('home', home), ('away', away))}
    gb = box[box['game_id'] == gid]
    real_pts_box = {side: int(gb.loc[gb['team'] == tid, 'points'].sum()) for side, tid in (('home', home), ('away', away))}
    real_poss = {side: int(s.loc[s['offense'] == tid, 'poss'].nunique()) for side, tid in (('home', home), ('away', away))}
    rng = np.random.default_rng(projection.seed_for('pit', gid))
    out = {'game_id': gid, 'date_et': day, 'home': home, 'away': away, 'worlds': worlds, 'simulation_seed': str(sim_seed),
           'real_home': real_pts_box['home'], 'real_away': real_pts_box['away'], 'real_home_seg': real_pts['home'], 'real_away_seg': real_pts['away'],
           'real_poss_home': real_poss['home'], 'real_poss_away': real_poss['away'], 'real_ot': int(s['period'].max() > 4),
           'sim_poss_home': float(st.poss[:, 0].mean()), 'sim_poss_away': float(st.poss[:, 1].mean()),
           'sim_ot': float((st.period > 4).mean())}
    if eng.rotation_policy is not None:
        for key, value in eng.rotation_policy.counts.items():
            out[f's06_{key}'] = value
        if _W['capture_substitution_worlds']:
            from scripts import a1_substitution_world_capture
            out['_s06_world_capture'] = a1_substitution_world_capture.capture(g, st, eng.rotation_policy)
    if _W.get('flow_diagnostics'):
        from scripts import a1_flow_capture
        if eng.diag is None or eng.rotation_diag is None or len(eng.rotation_diag) != 1:
            raise ValueError('flow diagnostics were not captured for this game')
        tables, combo = eng.rotation_diag[0]
        for key, value in a1_flow_capture.clock_summary(eng.diag, s, worlds).items():
            out[f'flow_clock_{key}'] = value
        game_stints = stints[stints['game_id'] == gid]
        for side, index, team in (('home', 0, home), ('away', 1, away)):
            capture = a1_flow_capture.scheduled_overlap(tables, combo, g.ids, g.P, game_stints, team, index)
            for key, value in capture.items():
                out[f'flow_rotation_{side}_{key}'] = value
        eng.diag, eng.rotation_diag = None, None
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
    periods = _W['periods']
    actual_quarters = {}
    for side, tid in (('home', home), ('away', away)):
        if (gid, tid) not in periods.index.droplevel('period'):
            raise ValueError(f'{gid}: missing player-period scores for {side} team {tid}')
        score = periods.loc[(gid, tid)]
        if int(score.sum()) != real_pts_box[side] or any(q not in score.index for q in range(1, 5)):
            raise ValueError(f'{gid}: player-period scores do not reconcile for {side} team {tid}')
        actual_quarters[side] = score
    quarter_rng = np.random.default_rng(projection.seed_for('pit', gid, 'quarters'))
    for q in range(4):
        h, a = st.pts[:, 0, q], st.pts[:, 1, q]
        yh, ya = int(actual_quarters['home'][q + 1]), int(actual_quarters['away'][q + 1])
        for label, x, y in (('total', h + a, yh + ya), ('margin', h - a, yh - ya)):
            x = x.astype(float)
            key = f'q{q + 1}_{label}'
            out[f'{key}_actual'] = y
            out[f'{key}_sim'] = float(x.mean())
            out[f'{key}_crps'] = float(aggregate.crps_samples(x[:, None], np.array([float(y)]))[0])
            out[f'{key}_pit'] = float(aggregate.pit(x[:, None], np.array([float(y)]), quarter_rng)[0])
    # components per side (where the points come from): simulated means v the real box (player sums, team turnovers excluded
    # on both sides) — for the component loadings in summarise()
    for side, i, tid in (('home', 0, home), ('away', 1, away)):
        cols = np.flatnonzero(g.side == i)
        for k, col in COMPONENT_BOX.items():
            out[f'sim_{k}_{side}'] = float(st.box[k][:, cols].sum((1, 2)).mean())
            out[f'real_{k}_{side}'] = float(gb.loc[gb['team'] == tid, col].sum())
    # players: simulated full-game boxes v the real box score
    rows = []
    idx = {pid: i for i, pid in enumerate(g.ids)}
    on_g = on[on['game_id'] == gid].set_index('player')['sec']
    threes_rng = np.random.default_rng(projection.seed_for('pit', gid, 'fg3m'))
    for r in gb.itertuples():
        if r.player not in idx:
            continue
        i = idx[r.player]
        sim = {'pts': st.box['pts'][:, i].sum(1), 'reb': (st.box['oreb'][:, i] + st.box['dreb'][:, i]).sum(1),
               'ast': st.box['ast'][:, i].sum(1), 'min': st.minutes[:, i].sum(1), 'fg3m': st.box['fg3m'][:, i].sum(1)}
        real = {'pts': r.points, 'reb': r.rebounds, 'ast': r.assists, 'min': float(on_g.get(r.player, np.nan)) / 60,
                'fg3m': r.three_point_field_goals_made}
        row = {'game_id': gid, 'player': r.player}
        for k in PLAYER_STATS:
            if real[k] is None or pd.isna(real[k]):
                continue
            x = sim[k].astype(float)
            row[f'{k}_actual'], row[f'{k}_sim'] = float(real[k]), float(x.mean())
            row[f'{k}_crps'] = float(aggregate.crps_samples(x[:, None], np.array([float(real[k])]))[0])
            row[f'{k}_pit'] = float(aggregate.pit(x[:, None], np.array([float(real[k])]), threes_rng if k == 'fg3m' else rng)[0])
        if _W.get('flow_diagnostics'):
            for k in ('fga', 'fgm', 'fg3a', 'fta', 'tov', 'oreb'):
                actual = getattr(r, COMPONENT_BOX[k])
                row[f'{k}_actual'] = float(actual) if pd.notna(actual) else None
                row[f'{k}_sim'] = float(st.box[k][:, i].sum(1).mean())
            player_periods = _W['player_periods']
            for q in range(1, 5):
                key = (gid, r.team, r.player, q)
                period = player_periods.loc[key] if key in player_periods.index else None
                for k in ('pts', 'fga', 'fta', 'tov', 'min'):
                    actual_key = 'sec' if k == 'min' else k
                    actual = period[actual_key] if period is not None else None
                    row[f'q{q}_{k}_actual'] = (float(actual) / 60 if k == 'min' else float(actual)) if pd.notna(actual) else None
                    values = st.minutes[:, i, q - 1] if k == 'min' else st.box[k][:, i, q - 1]
                    row[f'q{q}_{k}_sim'] = float(values.mean())
        rows.append(row)
    out['players'] = rows
    return out


COMPONENT_BOX = {'fga': 'field_goals_attempted', 'fgm': 'field_goals_made', 'fg3a': 'three_point_field_goals_attempted',
                 'fg3m': 'three_point_field_goals_made', 'fta': 'free_throws_attempted', 'tov': 'turnovers', 'oreb': 'offensive_rebounds'}


def component_loadings(g: pd.DataFrame) -> dict | None:
    """Where the defence is (or is not) expressed: per team-game rates — FG%, 3P%, 3PA share, FTA, TOV and OREB per 100
    possessions — regressed on the side's offensive and the opponent's defensive rating (as strength_loading), sim v real."""
    if 'sim_fga_home' not in g.columns or 'off_h' not in g.columns:
        return None
    def side(prefix, s, o):
        poss = g[f'{prefix}_poss_{s}'] if prefix == 'real' else g[f'sim_poss_{s}']
        f = lambda k: g[f'{prefix}_{k}_{s}']
        return pd.DataFrame({'fg_pct': f('fgm') / f('fga'), 'fg3_pct': f('fg3m') / f('fg3a'), 'fg3a_share': f('fg3a') / f('fga'),
                             'fga_100': 100 * f('fga') / poss, 'fta_100': 100 * f('fta') / poss, 'tov_100': 100 * f('tov') / poss,
                             'oreb_100': 100 * f('oreb') / poss, 'off': g[f'off_{o}'], 'opp_def': g[f'def_{"a" if o == "h" else "h"}']})
    out = {}
    for prefix in ('sim', 'real'):
        d = pd.concat([side(prefix, 'home', 'h'), side(prefix, 'away', 'a')], ignore_index=True).replace([np.inf, -np.inf], np.nan).dropna()
        X = np.column_stack([np.ones(len(d)), d['off'], d['opp_def']])
        out[prefix] = {k: dict(zip(('offence', 'opp_defence'), (round(float(v), 5) for v in np.linalg.lstsq(X, d[k], rcond=None)[0][1:])))
                       for k in ('fg_pct', 'fg3_pct', 'fg3a_share', 'fga_100', 'fta_100', 'tov_100', 'oreb_100')}
        out[prefix]['means'] = {k: round(float(d[k].mean()), 4) for k in ('fg_pct', 'fg3_pct', 'fg3a_share', 'fga_100', 'fta_100', 'tov_100', 'oreb_100')}
    out['ratio_sim_over_real_opp_defence'] = {k: (round(out['sim'][k]['opp_defence'] / out['real'][k]['opp_defence'], 3)
                                                  if abs(out['real'][k]['opp_defence']) > 1e-9 else None) for k in out['sim'] if k != 'means'}
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


def rating_baseline_inputs(games: pd.DataFrame) -> pd.DataFrame:
    """Pre-date rating and score inputs used by the team engine's comparison."""
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
    return pd.DataFrame(out_rows)


def rating_baseline(games: pd.DataFrame) -> dict:
    """The team engine's game model on the same games (D26): each side's expected points from ratings before the date
    (`season_backtest.state_before`: box possessions, shrunk K = 8 — what the pathway starts from), scores normal with
    baseline-v1's SD 11.25 and rho 0.35. Same measures as the engine's, so the two engines compare on real outcomes."""
    from scripts import pathway
    p = pathway.PATHWAY
    b = rating_baseline_inputs(games)
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
    out['component_loadings'] = component_loadings(g)
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
    selection = ap.add_mutually_exclusive_group()
    selection.add_argument('--games', type=int, default=200, help='random sample of held-out regular-season games (0 = all)')
    selection.add_argument('--game-ids', type=Path, help='JSON list of unique eligible game ID strings, instead of random selection')
    ap.add_argument('--worlds', type=int, default=1000)
    ap.add_argument('--jobs', type=int, default=4)
    ap.add_argument('--threads', type=int, default=8, help='LightGBM threads for fitting fold models')
    ap.add_argument('--seed', type=int, default=20261119)
    ap.add_argument('--simulation-stream', type=int, default=None, help='independent simulation stream; default preserves historical seeds')
    ap.add_argument('--seed-key', default=None, help='explicit common seed key instead of the fitted model version')
    ap.add_argument('--name', default=None)
    ap.add_argument('--rotation', choices=('replay', 'targets'), default='replay',
                    help='replay = M3 v0 templates (v1.1); targets = D29 minutes (healthy roles, 240 by priority, ramp)')
    ap.add_argument('--models', default=None, help='reuse fitted fold models (e.g. folds/v1.1_F4_all) instead of fitting')
    ap.add_argument('--known-starters', action='store_true', help='targets only: open with the real starters (a perfect lineup source)')
    ap.add_argument('--pool', type=int, default=None, help='rotation tables per side shared by the worlds (default 400; 0 = one per world, D36)')
    ap.add_argument('--flow-diagnostics', action='store_true', help='save opt-in clock, scheduled-five and player-quarter diagnostics')
    ap.add_argument('--minutes-history', choices=('control', 'nba_only'), default='control',
                    help='isolated A1 minute-history candidate; default preserves D29')
    ap.add_argument('--strict-minute-targets', action='store_true',
                    help='use the isolated 240-minute, 48-per-player allocator in targets mode')
    ap.add_argument('--substitution-candidate', type=Path, default=None,
                    help='isolated earlier-fold selected-timeout model report; research only')
    ap.add_argument('--audit-substitution-worlds', action='store_true',
                    help='save raw player worlds and lineup traces for independent S06 accounting')
    ap.add_argument('--summarise', metavar='RUN', help='re-score a saved run (<stamp>_<name>) without simulating; updates its log')
    args = ap.parse_args()
    if args.rotation != 'targets' and (args.minutes_history != 'control' or args.strict_minute_targets):
        ap.error('minute candidates require --rotation targets')
    if args.substitution_candidate is not None and (args.rotation != 'targets' or args.known_starters
                                                     or args.minutes_history != 'control' or args.strict_minute_targets):
        ap.error('the S06 candidate requires the unmodified targets control and projected starters')
    if args.audit_substitution_worlds and (args.substitution_candidate is None or args.summarise):
        ap.error('world accounting requires a new S06 candidate simulation')
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
    games = select_games(eligible_games(seg), args.games, args.seed, args.game_ids)
    print(f'backtest {spec.get("version")} {args.fold}: {len(games)} games × {args.worlds} worlds, {args.jobs} jobs, models {version}', flush=True)
    os.environ['OMP_NUM_THREADS'] = str(max(1, (os.cpu_count() or 4) // max(1, args.jobs)))
    name = args.name or f"backtest_{spec.get('version')}_{args.fold}"
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') if args.audit_substitution_worlds else None
    world_dir = DERIVED / 'experiments' / f'{stamp}_{name}_worlds' if stamp else None
    if world_dir is not None:
        world_dir.mkdir(parents=True, exist_ok=False)
    world_files = []
    ctx = mp.get_context('spawn')
    results = []
    with ctx.Pool(args.jobs, initializer=_init, initargs=(version, str(args.config), args.fold, args.worlds, args.rotation,
                                                         args.known_starters, args.pool, args.simulation_stream, args.seed_key,
                                                         args.flow_diagnostics, args.minutes_history,
                                                         args.strict_minute_targets, args.substitution_candidate,
                                                         args.audit_substitution_worlds)) as pool:
        for i, r in enumerate(pool.imap(run_game, list(games), chunksize=1), 1):
            if world_dir is not None:
                path = world_dir / f"{r['game_id']}.npz"
                np.savez_compressed(path, **r.pop('_s06_world_capture'))
                world_files.append(path)
            results.append(r)
            if i % min(10, max(1, len(games) // 10)) == 0 or i == len(games):
                print(f'game {i}/{len(games)}  {time.time() - start:.0f}s', flush=True)
    players = pd.DataFrame([p for r in results for p in r.pop('players')])
    frame = pd.DataFrame(results)
    pre, *_ = load_inputs(spec, args.fold)
    summary = summarise(frame, players, pre)
    summary['team_rating_baseline'] = rating_baseline(frame)
    summary['m6a_same_games'] = m6a_same_games(frame)
    stamp = stamp or datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    (DERIVED / 'experiments').mkdir(parents=True, exist_ok=True)
    frame.to_parquet(DERIVED / 'experiments' / f'{stamp}_{name}.parquet', index=False)
    players.to_parquet(DERIVED / 'experiments' / f'{stamp}_{name}_players.parquet', index=False)
    record = {'experiment': 'm9_engine_backtest', 'run': stamp, 'commit': train.git_commit(),
              'config': str(args.config), 'fold': args.fold, 'models': version, 'games': len(games),
              'worlds': args.worlds, 'rotation': args.rotation, 'known_starters': args.known_starters, 'pool': args.pool,
              'game_ids': games.tolist(), 'game_selection_seed': args.seed,
              'game_ids_file': str(args.game_ids) if args.game_ids else None,
              'simulation_stream': args.simulation_stream, 'seed_key': args.seed_key,
              'seconds': round(time.time() - start), 'summary': summary}
    if args.flow_diagnostics:
        paths = (Path(__file__), ROOT / 'scripts' / 'engine.py', ROOT / 'scripts' / 'a1_flow_capture.py')
        record['flow_diagnostics'] = {'sha256': {str(p.resolve().relative_to(ROOT)): sha256_file(p) for p in paths},
                                      'note': 'scheduled lineups precede foul-outs; actual period values may be missing'}
    if args.minutes_history != 'control' or args.strict_minute_targets:
        paths = (Path(__file__), ROOT / 'scripts' / 'engine.py', ROOT / 'scripts' / 'minutes.py',
                 ROOT / 'scripts' / 'a1_minutes_candidate.py')
        record['minutes_candidate'] = {'history': args.minutes_history, 'strict_targets': args.strict_minute_targets,
                                       'sha256': {str(p.resolve().relative_to(ROOT)): sha256_file(p) for p in paths}}
    if args.substitution_candidate is not None:
        from scripts import a1_minutes_fold_eval
        paths = (Path(__file__), ROOT / 'scripts/engine.py', ROOT / 'scripts/a1_substitution_engine.py',
                 args.substitution_candidate, ROOT / f'data/derived/experiments/20261122_a1_s05_unconditional_{args.fold}_corrected.parquet',
                 a1_minutes_fold_eval.CAUSAL_PROFILES)
        record['substitution_candidate'] = {
            'report': str(args.substitution_candidate),
            'sha256': {str(p.resolve().relative_to(ROOT)): sha256_file(p) for p in paths},
            'limitations': 'Selected-timeout templates and actual-participant rosters are not pre-game availability forecasts.',
        }
    if world_dir is not None:
        record['substitution_world_audit'] = {
            'capture_sha256': sha256_file(ROOT / 'scripts/a1_substitution_world_capture.py'),
            'world_sha256': {str(p.relative_to(ROOT)): sha256_file(p) for p in world_files},
            'note': 'Per-world traces contain research-only simulated lineups, not availability forecasts.',
        }
    write_json(EXPERIMENTS / f'{stamp}_{name}.json', record, pretty=True)
    print(json.dumps(summary, indent=1))
    print(f'\nrun {stamp}_{name}  ({len(games)} games, {time.time() - start:.0f}s)')


if __name__ == '__main__':
    main()
