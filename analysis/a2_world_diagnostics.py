#!/usr/bin/env python3
"""Frozen accepted-control dependence and late-state diagnostics from shared paired captures."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
from unittest.mock import patch

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from basketball_common import read_json, sha256_file, write_json
from scripts import a2_residual_dependence as residual

CLOCKS = ('0–24', '24–60', '60–120')
MARGINS = ('≤−9', '−8…−4', '−3…−1', '0', '1…3', '4…8', '≥9')


def cells(clock, margin):
    return np.searchsorted([24, 60], clock, side='left') * 7 + np.searchsorted([-8, -3, 0, 1, 4, 9], margin, side='right')


def late_terms(clock, margin, seconds, dfoul, fga, three):
    if not (np.isfinite(clock).all() and np.isfinite(margin).all() and np.isfinite(seconds).all()):
        raise ValueError('non-finite late-state input')
    if ((clock <= 0) | (clock > 120) | (seconds < 0) | (seconds > clock) | (fga < 0) | (three < 0) | (three > fga)).any():
        raise ValueError('invalid late-state input')
    index = cells(clock, margin)
    return np.column_stack([np.bincount(index, weights=x, minlength=21) for x in
                            (np.ones(len(clock)), seconds, dfoul, fga, three)])


def joint(rows, worlds, gids, weights, stars_only):
    subset = rows[rows['tier'].isin(('star', 'starter'))] if stars_only else rows
    # Reuse the retained role-centering/game-bootstrap algebra with explicit metric names.
    with patch.object(residual, 'METRICS', ('minutes', 'points')):
        terms, counts = residual.build_terms(subset, gids)
        point = residual.evaluate(terms, np.ones((1, len(gids))))
        boot = residual.evaluate(terms, weights)
    sim = {relation: np.zeros((len(gids), 2)) for relation in ('teammate', 'opponent')}
    for k, gid in enumerate(gids):
        game = subset[subset['game_id'].eq(gid)]
        source = worlds[gid]
        ids = source['ids']
        teams = [g for _, g in game.groupby('team', sort=True)]
        for metric, name in enumerate(('minutes', 'points')):
            values = source[name]
            centred = values - values.mean(0)
            cov = centred.T @ centred / len(values)
            for team in teams:
                i = [ids.index(x) for x in team['player']]
                if len(i) >= 2:
                    matrix = cov[np.ix_(i, i)]
                    sim['teammate'][k, metric] += (matrix.sum() - np.trace(matrix)) / (len(i) * (len(i) - 1))
            if len(teams) == 2:
                a, b = ([ids.index(x) for x in team['player']] for team in teams)
                sim['opponent'][k, metric] = cov[np.ix_(a, b)].mean()
    result = {'counts': counts, 'metrics': {}}
    for relation in ('teammate', 'opponent'):
        units = terms[relation + '_units']
        sp = sim[relation].sum(0) / units.sum()
        sb = weights @ sim[relation] / (weights @ units)[:, None]
        for j, stat in enumerate(('MIN', 'PTS')):
            result['metrics'][relation + '_' + stat] = {
                'observed_role_centred_error_product': float(point[relation][0, j]),
                'observed_ci_95': np.quantile(boot[relation][:, j], [.025, .975]).tolist(),
                'within_world_covariance': float(sp[j]),
                'within_world_ci_95': np.quantile(sb[:, j], [.025, .975]).tolist(),
                'observed_minus_world': float(point[relation][0, j] - sp[j]),
                'difference_ci_95': np.quantile(boot[relation][:, j] - sb[:, j], [.025, .975]).tolist()}
    return result


def late_summary(actual, simulated, weights):
    output = []
    for index in range(21):
        a, b = actual[:, index], simulated[:, index]
        row = {'clock_seconds': CLOCKS[index // 7], 'offensive_margin': MARGINS[index % 7],
               'actual_games': int((a[:, 0] > 0).sum()), 'actual_opportunities': int(a[:, 0].sum()),
               'simulated_expected_opportunities_per_slate': float(b[:, 0].sum())}
        row['status'] = 'supported' if row['actual_games'] >= 30 and row['actual_opportunities'] >= 100 else 'insufficient'
        if row['status'] == 'supported':
            aa, bb = weights @ a, weights @ b
            row['metrics'] = {}
            for name, num, den in (('seconds_to_action', 1, 0), ('defensive_personal_foul_share', 2, 0), ('three_share_of_fga', 4, 3)):
                if a[:, den].sum() == 0 or b[:, den].sum() == 0 or (aa[:, den] == 0).any() or (bb[:, den] == 0).any():
                    row['metrics'][name] = {'status': 'no supported denominator'}
                    continue
                av, bv = a[:, num].sum() / a[:, den].sum(), b[:, num].sum() / b[:, den].sum()
                delta = bb[:, num] / bb[:, den] - aa[:, num] / aa[:, den]
                row['metrics'][name] = {'actual': float(av), 'simulated': float(bv), 'change': float(bv - av),
                                         'ci_95': np.quantile(delta, [.025, .975]).tolist()}
        output.append(row)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    run = read_json(ROOT / f'analysis/experiments/{args.run}.json')
    declared = read_json(ROOT / 'analysis/experiments/20261123_rule3_confirmation_manifest_v1.json')
    gids = sorted(run['game_ids'])
    if gids != sorted(declared['game_ids']) or run['worlds'] != 1000 or run['stream'] is not None:
        raise ValueError('requires the complete frozen 200-game original-stream control')
    rows, worlds, late, pace, ot = [], {}, [], [], []
    for item in run['captures']:
        path = ROOT / item['meta']
        if sha256_file(path) != item['meta_sha256']:
            raise ValueError('changed paired game metadata')
        entry = read_json(path)['outputs']['control']
        game = entry['result']
        capture = ROOT / entry['capture']
        if sha256_file(capture) != entry['sha256']:
            raise ValueError('changed control capture')
        with np.load(capture, allow_pickle=False) as z:
            ids = z['player_ids'].tolist()
            usage, starts = z['prior_usage'], z['prior_start_share']
            for rates in (usage, starts):
                if np.isinf(rates).any() or ((rates[np.isfinite(rates)] < 0) | (rates[np.isfinite(rates)] > 1)).any():
                    raise ValueError('invalid prior role rate')
            tier = np.select([~np.isfinite(usage) | ~np.isfinite(starts), usage >= .25, starts >= .5],
                             ['unknown', 'star', 'starter'], default='bench')
            for p in game['players']:
                i = ids.index(p['player'])
                rows.append({**p, 'team': str(z['side'][i]), 'tier': tier[i]})
            worlds[game['game_id']] = {'ids': ids, 'minutes': z['minutes'].sum(2), 'points': z['player_points'].sum(2)}
            poss = z['possessions']
            pace.append([game['real_poss_home'], game['real_poss_away'], *poss.mean(0),
                         *poss.var(0), float(np.mean((poss[:, 0] - poss[:, 0].mean()) * (poss[:, 1] - poss[:, 1].mean())))])
            w, off = z['late_world'].astype(int), z['late_off'].astype(int)
            dfoul = (z['late_pf_after'] - z['late_pf_before'])[np.arange(len(w)), 1 - off] > 0
            late.append(late_terms(z['late_clock'], z['late_margin'], z['late_clock'] - z['late_clock_after'], dfoul,
                                   z['late_fga_after'] - z['late_fga_before'], z['late_fg3a_after'] - z['late_fg3a_before']) / run['worlds'])
            ot.append((game['real_ot'], float((z['final_period'] > 4).mean())))
    frame = pd.DataFrame(rows)
    known_values = np.isfinite(frame[['min_actual', 'min_sim', 'pts_actual', 'pts_sim']].to_numpy(float)).all(1)
    supported = frame['tier'].ne('unknown') & known_values & frame['min_actual'].ge(8) & frame['min_sim'].ge(8)
    counts = {'player_games': len(frame), 'unknown_role': int(frame['tier'].eq('unknown').sum()),
              'missing_outcome_or_prediction': int((~known_values).sum()),
              'known_role_below_minutes_threshold': int((frame['tier'].ne('unknown') & known_values & ~supported).sum()), 'supported': int(supported.sum())}
    frame = frame[supported].copy()
    frame['minutes'], frame['points'] = frame['min_actual'] - frame['min_sim'], frame['pts_actual'] - frame['pts_sim']
    rng = np.random.default_rng(20261122)
    weights = rng.multinomial(len(gids), np.full(len(gids), 1 / len(gids)), size=10000).astype(float)
    dependence = {name: joint(frame, worlds, gids, weights, stars) for name, stars in (('all', False), ('stars_starters', True))}
    for values in dependence.values():
        counts_joint = values['counts']
        values['status'] = 'supported' if counts_joint['games'] >= 50 and counts_joint['teammate_team_games'] >= 100 else 'insufficient'
        if values['status'] != 'supported':
            values.pop('metrics')
    raw_path = ROOT / 'data/derived/history/2026/segments.parquet'
    actual = pd.read_parquet(raw_path)
    actual = actual[actual['game_id'].isin(gids) & (actual['period'] >= 4) & actual['start_clock'].between(0, 120, inclusive='right')]
    valid = actual['shot_time'].notna() & actual['shot_time'].between(0, actual['start_clock']) & actual['end_type'].ne('unknown')
    counts['actual_late_opportunities'], counts['actual_invalid_time_or_unknown_event'] = len(actual), int((~valid).sum())
    actual = actual[valid]
    real_late = []
    for gid in gids:
        g = actual[actual['game_id'].eq(gid)]
        fga = g['end_type'].eq('shot')
        foul = g['end_type'].isin(('fouled', 'foul')) | g['and_one'].fillna(False)
        real_late.append(late_terms(g['start_clock'].to_numpy(), (g['score_off'] - g['score_def']).to_numpy(),
                                   g['shot_time'].to_numpy(), foul.to_numpy(), fga.to_numpy(), (fga & g['value'].eq(3)).to_numpy()))
    pace = np.asarray(pace)
    errors = pace[:, :2] - pace[:, 2:4]
    means = weights @ errors / len(gids)
    variance = weights @ (errors**2) / len(gids) - means**2
    cross = weights @ (errors[:, 0] * errors[:, 1]) / len(gids) - means[:, 0] * means[:, 1]
    pv = weights @ pace[:, 4:6] / len(gids)
    pc = weights @ pace[:, 6] / len(gids)
    ot = np.asarray(ot)
    report = {'kind': 'A2 conditional accepted-engine diagnostics; no fitted or promoted factor',
              'run': args.run, 'games': len(gids), 'selection': counts, 'dependence': dependence,
              'late_states': late_summary(np.asarray(real_late), np.asarray(late), weights),
              'overtime': {'actual': float(ot[:, 0].mean()), 'simulated': float(ot[:, 1].mean()),
                           'difference_ci_95': np.quantile(weights @ (ot[:, 1] - ot[:, 0]) / len(gids), [.025, .975]).tolist()},
              'pace': {'observed_error_variance': errors.var(0).tolist(), 'within_world_variance': pace[:, 4:6].mean(0).tolist(),
                       'observed_minus_world_variance_ci_95': np.quantile(variance - pv, [.025, .975], axis=0).T.tolist(),
                       'observed_error_opponent_covariance': float(np.cov(errors.T, bias=True)[0, 1]),
                       'within_world_opponent_covariance': float(pace[:, 6].mean()),
                       'difference_opponent_covariance_ci_95': np.quantile(cross - pc, [.025, .975]).tolist()},
              'source_sha256': {str(p.relative_to(ROOT)): sha256_file(p) for p in (Path(__file__), Path(residual.__file__), raw_path,
                   ROOT / f'analysis/experiments/{args.run}.json', ROOT / 'docs/protocols/a2_joint_late_20261123.md')},
              'bootstrap': {'unit': 'game', 'replicates': 10000, 'seed': 20261122, 'refit': 'observed role means'},
              'limitations': ['actual-participant roster and minutes selection; fixed F4 panel',
                             'state visitation differs; descriptive rather than causal or intentional-foul classification',
                             'forecast errors also contain input/mean misspecification; excess is not an identified latent variance']}
    write_json(args.output, report, pretty=True)
    print(f'saved {len(gids)}-game joint/late-state diagnostic', flush=True)


if __name__ == '__main__':
    main()
