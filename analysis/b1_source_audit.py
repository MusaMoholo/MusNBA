#!/usr/bin/env python3
"""Immutable B1 development-only score/pace/component audit of retained r3 worlds."""
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
import argparse
import os
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
import pyarrow as pa
from basketball_common import read_json, write_json, sha256_file
from analysis.rule3_confirmation import expected_coverage

PANEL = ROOT / 'analysis/experiments/20261124_c2_ready_panels_v1.json'
BASELINE = ROOT / 'analysis/experiments/20261124_c3_engine_development_v3.json'
WORK = ROOT / 'data/derived/experiments/d42_b1_source_audit_v2'
OUTPUT = ROOT / 'analysis/experiments/20261124_b1_source_audit_v2.json'


def extract(descriptor):
    pa.set_cpu_count(1)
    path = ROOT / descriptor['receipt']
    if sha256_file(path) != descriptor['sha256']:
        raise ValueError('retained receipt changed')
    entry = read_json(path)['entry']
    capture = ROOT / entry['capture']
    if sha256_file(capture) != entry['sha256']:
        raise ValueError('retained worlds changed')
    r = entry['result']
    with np.load(capture, allow_pickle=False) as z:
        sides, ids = z['side'], z['player_ids'].tolist()
        scores, pts, ftm = z['team_points'], z['player_points'], z['player_ftm']
        minutes, possessions = z['minutes'], z['possessions']
        fga, fg3a, fg3m = z['player_fga'], z['player_fg3a'], z['player_fg3m']
        fgm = (pts.astype(np.int64) - ftm - fg3m) / 2
        if (fgm != np.floor(fgm)).any() or (fgm < fg3m).any() or (fgm > fga).any():
            raise ValueError('shot identity failed')
        if not np.array_equal(scores.sum(2), z['final_score']):
            raise ValueError('period scores differ')
        team_rows = []
        for side, label in enumerate(('home', 'away')):
            keep = sides == side
            if not np.array_equal(pts[:, keep].sum(1), scores[:, side]):
                raise ValueError('player/team points differ')
            expected_minutes = 240 + 25 * (z['final_period'] - 4)
            error = float(np.max(np.abs(minutes[:, keep].sum((1, 2)) - expected_minutes)))
            if error > 1e-8:
                raise ValueError('team seconds differ')
            full, regulation = scores[:, side].sum(1), scores[:, side, :4].sum(1)
            row = {'game_id': r['game_id'], 'date_et': r['date_et'], 'team': r[label],
                   'side': label, 'actual': r['real_' + label], 'sim': float(full.mean()),
                   'crps': r[label + '_crps'], 'coverage80': expected_coverage(full, r['real_' + label]),
                   'actual_poss': r['real_poss_' + label], 'sim_poss': float(possessions[:, side].mean()),
                   'reg_sim': float(regulation.mean()), 'ot_sim': float(scores[:, side, 4].mean()),
                   'ot_probability': float((z['final_period'] > 4).mean()), 'actual_ot': r['real_ot'],
                   'max_minute_error': error,
                   'positive_minute_players_sim': float((minutes[:, keep].sum(2) > 0).sum(1).mean())}
            for stat in ('fga', 'fgm', 'fg3a', 'fg3m', 'fta', 'tov', 'oreb'):
                row['actual_' + stat] = r['real_' + stat + '_' + label]
                row['sim_' + stat] = r['sim_' + stat + '_' + label]
            for stat, values in [('ftm', ftm), ('pf', z['player_fouls'])]:
                row['sim_' + stat] = float(values[:, keep].sum((1, 2)).mean())
            row['sim_fg2a'] = float((fga[:, keep] - fg3a[:, keep]).sum((1, 2)).mean())
            row['sim_fg2m'] = float((fgm[:, keep] - fg3m[:, keep]).sum((1, 2)).mean())
            # A symmetric identity separates pace and efficiency without a fitted score adjustment.
            ps, po = row['sim_poss'], row['actual_poss']
            es, eo = row['sim'] / ps, row['actual'] / po
            row['pace_points'] = (ps - po) * (es + eo) / 2
            row['efficiency_points'] = (es - eo) * (ps + po) / 2
            if abs(row['pace_points'] + row['efficiency_points'] - (row['sim'] - row['actual'])) > 1e-10:
                raise ValueError('pace/efficiency decomposition failed')
            team_rows.append(row)
        usage, starts = z['prior_usage'], z['prior_start_share']
        players = []
        by_player = {p['player']: p for p in r['players']}
        for i, pid in enumerate(ids):
            if pid not in by_player:
                continue
            tier = ('unknown' if not np.isfinite([usage[i], starts[i]]).all() else
                    'star' if usage[i] >= .25 else 'starter' if starts[i] >= .5 else 'bench')
            players.append({**by_player[pid], 'tier': tier, 'team': r[('home', 'away')[sides[i]]],
                            'positive_minutes_probability': float((minutes[:, i].sum(1) > 0).mean())})
    return {'game_id': r['game_id'], 'teams': team_rows, 'players': players,
            'source': descriptor, 'capture': entry['capture'], 'capture_sha256': entry['sha256']}


def summary(frame, weights):
    """Bootstrap complete games; home and away always stay together."""
    f = frame.copy()
    f['error'] = f.sim - f.actual
    f['absolute_error'], f['squared_error'] = f.error.abs(), f.error ** 2
    metrics = {'bias': 'error', 'mae': 'absolute_error', 'mse': 'squared_error', 'crps': 'crps',
               'coverage80': 'coverage80', 'pace_points': 'pace_points', 'efficiency_points': 'efficiency_points'}
    ids = sorted(frame.game_id.unique())
    grouped = f.groupby('game_id')
    count = grouped.size().reindex(ids).to_numpy()
    report = {'games': len(ids), 'team_games': len(f)}
    for metric, column in metrics.items():
        sums = grouped[column].sum().reindex(ids).to_numpy()
        boot = (weights @ sums) / (weights @ count)
        value = float(sums.sum() / count.sum())
        if metric == 'mse':
            metric, value, boot = 'rmse', np.sqrt(value), np.sqrt(boot)
        report[metric] = {'mean': float(value), 'ci95': np.quantile(boot, [.025, .975]).tolist()}
    return report


def main(jobs):
    started = time.monotonic()
    if OUTPUT.exists():
        raise FileExistsError(OUTPUT)
    pa.set_cpu_count(1)
    panels, retained = read_json(PANEL), read_json(BASELINE)
    development, confirmation = panels['development_F4'], panels['reserved_confirmation_F4']
    if len(development) != 200 or len(confirmation) != 200 or set(development) & set(confirmation):
        raise ValueError('two disjoint 200-game panels required')
    tasks = [x for x in retained['receipts'] if x['arm'] == 'reference']
    if {x['game'] for x in tasks} != set(development) or len(tasks) != 200:
        raise ValueError('development references differ')
    paths = [Path(__file__), PANEL, BASELINE, ROOT / 'analysis/experiments/20261124_chunk_b_successor_v4.json',
             ROOT / 'data/derived/history/2026/segments.parquet', ROOT / 'data/raw/hoopr/player_box_2026.parquet',
             ROOT / 'data/derived/history/2026/player_periods.csv.gz']
    paths += [ROOT / f'scripts/{x}.py' for x in ('engine', 'backtest', 'nodes', 'features', 'matchups', 'foul_out', 'late_clock')]
    sources = {str(p.relative_to(ROOT)): sha256_file(p) for p in paths}
    signature = {'sources': sources, 'development': development, 'reserved_confirmation_ids': confirmation,
                 'confirmation_outcomes_opened': False, 'reference_descriptors': tasks}
    if WORK.exists():
        if read_json(WORK / 'plan.json') != signature:
            raise ValueError('resume inputs/source differ')
    else:
        WORK.mkdir(parents=True)
        write_json(WORK / 'plan.json', signature, pretty=True)
    done, pending = [], []
    for task in tasks:
        path = WORK / (task['game'] + '.json')
        if path.exists():
            result = read_json(path)
            if result['source'] != task or sha256_file(ROOT / result['capture']) != result['capture_sha256']:
                raise ValueError('resumed receipt differs')
            done.append(result)
        else:
            pending.append(task)
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        for future in as_completed([pool.submit(extract, task) for task in pending]):
            row = future.result()
            write_json(WORK / (row['game_id'] + '.json'), row, pretty=False)
            done.append(row)
            if len(done) % 20 == 0:
                print(f'{len(done)}/200 development references audited; {time.monotonic()-started:.1f}s', flush=True)
    frame = pd.DataFrame([row for result in done for row in result['teams']]).sort_values(['game_id', 'side'])
    players = pd.DataFrame([row for result in done for row in result['players']])
    # Read truth only after filtering by frozen development IDs.
    box = pd.read_parquet(paths[5], filters=[('game_id', 'in', list(map(int, development)))])
    box['game_id'] = box.game_id.astype('int64').astype(str)
    box['team'] = box.team_id.astype('int64').astype(str)
    box['positive_minutes'] = box.minutes.gt(0)
    truth = box.groupby(['game_id', 'team']).agg(actual_ftm=('free_throws_made', 'sum'),
               actual_pf=('fouls', 'sum'), positive_minute_players_actual=('positive_minutes', 'sum')).reset_index()
    frame = frame.merge(truth, on=['game_id', 'team'], validate='one_to_one')
    seg = pd.read_parquet(paths[4], filters=[('game_id', 'in', development)])
    periods = pd.read_csv(paths[6], dtype={'game_id': str, 'team_id': str})
    periods = periods[periods.game_id.isin(development)]
    reg = periods[periods.period <= 4].groupby(['game_id', 'team_id']).pts.sum()
    frame['reg_actual'] = [reg.loc[(r.game_id, r.team)] for r in frame.itertuples()]
    frame['ot_actual'] = frame.actual - frame.reg_actual
    frame['actual_fg2a'], frame['actual_fg2m'] = frame.actual_fga - frame.actual_fg3a, frame.actual_fgm - frame.actual_fg3m
    for prefix in ('actual', 'sim'):
        reconstructed = 2 * frame[prefix + '_fgm'] + frame[prefix + '_fg3m'] + frame[prefix + '_ftm']
        points = frame['actual' if prefix == 'actual' else 'sim']
        if np.max(np.abs(reconstructed - points)) > 1e-9:
            raise ValueError('box score points identity failed')
    ids = sorted(development)
    weights = np.random.default_rng(20261122).multinomial(200, np.full(200, 1/200), size=10000).astype(float)
    overall = summary(frame, weights)
    components = {stat: {'actual': float(frame['actual_' + stat].mean()),
                         'sim': float(frame['sim_' + stat].mean()),
                         'bias': float((frame['sim_' + stat] - frame['actual_' + stat]).mean())}
                  for stat in ('poss', 'fga', 'fgm', 'fg2a', 'fg2m', 'fg3a', 'fg3m', 'fta', 'ftm', 'tov', 'oreb', 'pf')}
    point_sources = {stat: multiplier * components[stat]['bias'] for stat, multiplier in [('fg2m', 2), ('fg3m', 3), ('ftm', 1)]}
    if abs(sum(point_sources.values()) - overall['bias']['mean']) > 1e-9:
        raise ValueError('scoring attribution failed')
    actual_seg = seg.groupby(['game_id', 'offense']).points.sum()
    frame['segment_points_residual'] = [r.actual - actual_seg.loc[(r.game_id, r.team)] for r in frame.itertuples()]
    frame['pace_stratum'] = pd.qcut(frame.groupby('game_id').actual_poss.transform('mean'), 3,
                                   labels=['low', 'middle', 'high'])
    strata = {}
    for column in ('side', 'team', 'pace_stratum'):
        strata[column] = {}
        for label, part in frame.groupby(column, observed=True):
            err = part.sim - part.actual
            strata[column][str(label)] = {'games': part.game_id.nunique(), 'team_games': len(part),
               'bias': float(err.mean()), 'mae': float(err.abs().mean()), 'rmse': float(np.sqrt((err**2).mean())),
               'crps': float(part.crps.mean()), 'coverage80': float(part.coverage80.mean())}
    tiers = {}
    for tier, part in players.groupby('tier'):
        tiers[tier] = {'player_games': len(part), 'games': part.game_id.nunique(), 'stats': {}}
        for stat in ('min', 'pts', 'reb', 'ast', 'fg3m'):
            valid = part.dropna(subset=[stat + '_actual', stat + '_sim'])
            tiers[tier]['stats'][stat] = {'n': len(valid), 'bias': float((valid[stat+'_sim']-valid[stat+'_actual']).mean()),
                'crps': float(valid[stat+'_crps'].mean()), 'coverage80': float(valid[stat+'_coverage_expected'].mean())}
    tables = {'teams.parquet': frame, 'players.parquet': players}
    for name, table in tables.items():
        path = WORK / name
        if path.exists():
            raise FileExistsError(path)
        table.to_parquet(path, index=False)
    if sources != {str(p.relative_to(ROOT)): sha256_file(p) for p in paths}:
        raise ValueError('source changed during audit')
    report = {'kind': 'B1 accepted r3 development baseline/source audit; no candidate or confirmation scores',
        'created_at': datetime.now(timezone.utc).isoformat(), 'development_games': 200, 'worlds_per_game': 1000,
        'supersedes': {'report': '20261124_b1_source_audit_v1.json',
            'reason': 'Correct private actual positive-minute player count: exclude DNP rows. Score, pace, tier and accounting results unchanged.',
            'original_source': 'data/derived/experiments/d42_b1_source_audit_v1/source.py'},
        'bootstrap': '10000 whole games, seed20261122; retain both team scores in each game',
        'overall': overall, 'player_tiers_first': tiers, 'components': components, 'bias_points_by_scoring_source': point_sources,
        'regulation': {'actual': float(frame.reg_actual.mean()), 'sim': float(frame.reg_sim.mean())},
        'overtime': {'actual_points': float(frame.ot_actual.mean()), 'sim_points': float(frame.ot_sim.mean()),
                     'actual_probability': float(frame.actual_ot.mean()), 'sim_probability': float(frame.ot_probability.mean())},
        'strata': strata, 'accounting': {'team_games': len(frame), 'player_games': len(players),
            'worlds': 200000, 'max_team_minute_error': float(frame.max_minute_error.max()),
            'box_identity_exact': True, 'pace_efficiency_identity_exact': True,
            'segment_residual_team_games': int(frame.segment_points_residual.ne(0).sum()),
            'segment_residual_points': float(frame.segment_points_residual.sum()),
            'positive_minute_players': {'actual': float(frame.positive_minute_players_actual.mean()),
                                       'sim': float(frame.positive_minute_players_sim.mean())}},
        'source_audit': {'existing_defence': 'features.matchup_counts already shares attempts and makes over all five likely defenders by role/size; ranks are not proximity.',
             'positions_at_shot': 'Unavailable; primary/help truth unsupported.',
             'shot_clock_state': 'Engine has game clock and start type, but no explicit24/14-second shot clock.',
             'fitted_cutoff': 'F4 nodes/clock through2025-12-31; prior-game features; historical assignment/body limitations remain, not newly certified by this audit.',
             'missingness': 'Unknown prior usage/start share stays unknown tier; actual-participant rosters do not validate availability.',
             'recorded_segments': len(seg), 'duration_missing': int(seg.duration.isna().sum()),
             'shot_coordinates_missing': int(seg.loc[seg.end_type.eq('shot'), ['x','y']].isna().any(axis=1).sum())},
        'confirmation': {'reserved_ids': confirmation, 'outcomes_opened': False},
        'production_changed': False, 'protected_scoring': False, 'sources': sources,
        'arrays': {str((WORK/name).relative_to(ROOT)): sha256_file(WORK/name) for name in tables},
        'workers': jobs, 'inner_threads': 1, 'seconds': time.monotonic()-started}
    write_json(OUTPUT, report, pretty=True)
    print({'overall': overall, 'components': components, 'seconds': report['seconds']}, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jobs', type=int, default=10, choices=range(1, 11))
    args = parser.parse_args()
    if any(os.environ.get(k) != '1' for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS')):
        raise ValueError('single-thread BLAS/OMP required')
    main(args.jobs)
