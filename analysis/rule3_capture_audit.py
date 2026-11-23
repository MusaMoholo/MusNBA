#!/usr/bin/env python3
"""Audit saved paired Rule 3 worlds without trusting the runner's scores or counters."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from basketball_common import read_json, sha256_file, write_json
from scripts.a1_substitution_world_audit import audit_worlds
from analysis.a1_parallel_world_probe import capture_digest


def scores(samples, outcome):
    x = np.sort(np.asarray(samples, float))
    if not len(x) or not np.isfinite(x).all() or not np.isfinite(outcome):
        raise ValueError('unknown outcome or invalid worlds')
    n = len(x)
    crps = np.abs(x - outcome).mean() - np.dot(2 * np.arange(1, n + 1) - n - 1, x) / n**2
    a, b = np.searchsorted(x, outcome, side='left') / n, np.searchsorted(x, outcome, side='right') / n
    coverage = (min(b, .9) - max(a, .1)) / (b - a) if a < b and b > .1 and a < .9 else float(.1 <= a <= .9) if a == b else 0.
    return float(x.mean()), float(crps), float(coverage)


def team_fouls(data, corrected):
    order = np.argsort(data['trace_world'], kind='stable')
    w, p, off, pf, tf, fives = (data['trace_' + key][order].astype(np.int64) for key in
                               ('world', 'period', 'off', 'all_fouls', 'tfouls', 'lineups'))
    first = np.r_[True, (w[1:] != w[:-1]) | (p[1:] != p[:-1])]
    if (tf[first] != 0).any():
        raise ValueError('a period starts with nonzero team fouls')
    idx = np.flatnonzero(~first)
    delta = pf[idx] - pf[idx - 1]
    if ((delta < 0) | (delta > 1)).any():
        raise ValueError('personal-foul increments are invalid')
    expected = np.zeros((len(idx), 2), dtype=int)
    retained_offensive = 0
    for row, player in np.argwhere(delta):
        side = int(data['side'][player])
        defensive = side != off[idx[row]]
        retained = pf[idx[row], player] >= 6 and player in fives[idx[row], side]
        expected[row, side] += int(defensive or (corrected and retained))
        retained_offensive += int(not defensive and retained)
    if not np.array_equal(tf[idx] - tf[idx - 1], expected):
        raise ValueError('team fouls differ from independently classified personal fouls')
    return {'retained_offensive_fouls': retained_offensive}


def accounting(data):
    minutes, side, period = data['minutes'], data['side'], data['final_period']
    n = len(period)
    target = np.column_stack([np.full(n, 60.)] * 4 + [25. * (period - 4)])
    max_error = 0.
    for team in (0, 1):
        err = float(np.max(np.abs(minutes[:, side == team].sum(1) - target)))
        max_error = max(max_error, err)
        if err > 1e-8 or not np.array_equal(data['player_points'][:, side == team].sum(1), data['team_points'][:, team]):
            raise ValueError('period minutes or player/team points do not reconcile')
    if not np.array_equal(data['team_points'].sum(2), data['final_score']):
        raise ValueError('period/final scores do not reconcile')
    if (data['final_score'][:, 0] == data['final_score'][:, 1]).any():
        raise ValueError('unresolved final tie')
    # The control deliberately retains its known foul-out defect; report that rather than sanitising it.
    return {'max_team_period_minute_error': max_error,
            'known_disqualified_control_fives': int((data['trace_fouls'] >= 6).any(2).sum())}


def audit_metrics(data, result):
    def check(values, outcome, record, key):
        mean, crps, coverage = scores(values, outcome)
        for suffix, value in (('sim', mean), ('crps', crps), ('coverage_expected', coverage)):
            if not np.isclose(value, record[key + '_' + suffix], atol=1e-10, rtol=0):
                raise ValueError(f'{key}_{suffix}: independent world score differs')
    pts = data['team_points']
    yh, ya = result['real_home'], result['real_away']
    for key, values, y in (('home', pts[:, 0].sum(1), yh), ('away', pts[:, 1].sum(1), ya),
                           ('total', pts.sum((1, 2)), yh + ya), ('margin', pts[:, 0].sum(1) - pts[:, 1].sum(1), yh - ya)):
        check(values, y, result, key)
    for q in range(4):
        for label, values in (('total', pts[:, :, q].sum(1)), ('margin', pts[:, 0, q] - pts[:, 1, q])):
            key = f'q{q + 1}_{label}'
            check(values, result[key + '_actual'], result, key)
    ids = data['player_ids'].tolist()
    for row in result['players']:
        i = ids.index(row['player'])
        for key, values in (('min', data['minutes'][:, i].sum(1)), ('pts', data['player_points'][:, i].sum(1)),
                            ('reb', (data['player_oreb'][:, i] + data['player_dreb'][:, i]).sum(1)),
                            ('ast', data['player_ast'][:, i].sum(1)), ('fg3m', data['player_fg3m'][:, i].sum(1))):
            if key + '_actual' in row and np.isfinite(row[key + '_actual']):
                check(values, row[key + '_actual'], row, key)
    before, after = data['late_clock'], data['late_clock_after']
    if ((before <= 0) | (before > 120) | (after < 0) | (after > before)).any():
        raise ValueError('invalid late-state clock progression')
    fga = data['late_fga_after'] - data['late_fga_before']
    three = data['late_fg3a_after'] - data['late_fg3a_before']
    if ((fga < 0) | (three < 0) | (three > fga)).any() or (data['late_pf_after'] < data['late_pf_before']).any():
        raise ValueError('invalid late-state foul/attempt increment')


def legacy_parity(entries, legacy):
    games = pd.read_parquet(ROOT / f'data/derived/experiments/{legacy}.parquet').set_index('game_id')
    players = pd.read_parquet(ROOT / f'data/derived/experiments/{legacy}_players.parquet').set_index(['game_id', 'player'])
    count = 0
    for entry in entries:
        actual = entry['outputs']['control']['result']
        expected = games.loc[entry['game']]
        for key, value in expected.items():
            if key not in actual:
                raise ValueError(f'legacy control field missing: {key}')
            other = actual[key]
            if isinstance(value, (float, int, np.number)):
                if not np.isclose(float(value), float(other), atol=1e-12, rtol=0, equal_nan=True):
                    raise ValueError(f'legacy control mismatch {entry["game"]}:{key}: {value} != {other}')
            elif str(value) != str(other):
                raise ValueError(f'legacy control identity mismatch {key}')
            count += 1
        for row in actual['players']:
            for key, value in players.loc[(entry['game'], row['player'])].items():
                if key not in row or not np.isclose(float(value), float(row[key]), atol=1e-12, rtol=0, equal_nan=True):
                    raise ValueError(f'legacy player control mismatch: {entry["game"]}:{row["player"]}:{key}')
                count += 1
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run')
    parser.add_argument('--legacy')
    parser.add_argument('--same-worlds-as')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    path = ROOT / f'analysis/experiments/{args.run}.json'
    run = read_json(path)
    entries, reports = [], []
    other = read_json(ROOT / f'analysis/experiments/{args.same_worlds_as}.json') if args.same_worlds_as else None
    for game in run['captures']:
        meta = ROOT / game['meta']
        if sha256_file(meta) != game['meta_sha256']:
            raise ValueError('changed game metadata')
        entry = read_json(meta)
        entries.append(entry)
        other_entry = read_json(ROOT / other['directory'] / f'{entry["game"]}.json') if other else None
        for label, output in entry['outputs'].items():
            capture = ROOT / output['capture']
            if sha256_file(capture) != output['sha256']:
                raise ValueError('changed capture')
            with np.load(capture, allow_pickle=False) as packed:
                data = {key: packed[key] for key in packed.files}
                digest = capture_digest(data)
                if digest != output['world_sha256'] or (other_entry and digest != other_entry['outputs'][label]['world_sha256']):
                    raise ValueError('canonical captured worlds differ')
                # The existing replay auditor uses a -1 phase sentinel; preserve compact capture bytes.
                compatible = {**data, 'trace_phase': data['trace_phase'].astype(np.int16)}
                report = audit_worlds(compatible, foul_penalty=True) if label == 'candidate' else accounting(data)
                report.update(team_fouls(data, label == 'candidate'))
                audit_metrics(data, output['result'])
            reports.append({'game': entry['game'], 'label': label, **report})
        print(f'audited {len(entries)}/{len(run["captures"])} pairs', flush=True)
    parity = legacy_parity(entries, args.legacy) if args.legacy else None
    write_json(args.output, {'run': args.run, 'pairs': len(entries), 'worlds_per_branch_game': run['worlds'],
               'source_sha256': sha256_file(Path(__file__)), 'run_sha256': sha256_file(path),
               'legacy_fields_equal_1e_12': parity, 'same_worlds_as': args.same_worlds_as,
               'audits': reports, 'status': 'pass; accounting only, no accuracy claim'}, pretty=True)


if __name__ == '__main__':
    main()
