#!/usr/bin/env python3
"""Frozen rule-level final adapter; unchanged nodes and shared paired runner/scorer."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import os
import sys
import time
from unittest.mock import patch

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, NBA_TEAM_IDS, read_json, sha256_file, write_json
from scripts import a1_compare, backtest, engine, minutes, release_gate
from scripts.evaluate import TEST_FROM
from analysis import rule3_confirmation as paired
from analysis.rule3_scores import distribution

MANIFEST = ROOT / 'analysis/experiments/20261123_rule3_final_manifest_v1.json'
PROTOCOL = ROOT / 'docs/protocols/rule3_final_20261123.md'
MODEL = 'v1.3'
ORIGIN = '2026-11-23'


def load_inputs(spec=None, fold=None, flow_diagnostics=False):
    feature = DERIVED / 'variants/matchup/features'
    pre = pd.read_parquet(feature / 'pregame.parquet')
    teams = pd.read_parquet(feature / 'team_pregame.parquet')
    pre = pre[pre['date_et'].ge(TEST_FROM) & pre['date_et'].lt(ORIGIN)]
    teams = teams[teams['date_et'].ge(TEST_FROM) & teams['date_et'].lt(ORIGIN)]
    seg = pd.read_parquet(DERIVED / 'segments.parquet')
    seg = seg[seg['date_et'].ge(TEST_FROM) & seg['date_et'].lt(ORIGIN)]
    stints = pd.concat([pd.read_parquet(p) for p in [*sorted((DERIVED / 'history').glob('*/stints.parquet')),
                                                   DERIVED / 'rotations/stints.parquet']], ignore_index=True)
    on = pd.read_parquet(DERIVED / 'rotations/on_court.parquet')
    box = pd.read_csv(DERIVED / 'player_games.csv', dtype={'game_id': str, 'player_id': str, 'team_id': str})
    rename = {'player_id': 'player', 'team_id': 'team', 'pts': 'points', 'reb': 'rebounds', 'ast': 'assists',
              'min': 'minutes', **{k: v for k, v in backtest.COMPONENT_BOX.items()}}
    box = box[box['dnp'].eq(0)].rename(columns=rename)
    return pre, teams, seg, stints, on, box


def fingerprints():
    paths = [Path(__file__), PROTOCOL, ROOT / 'models/v1.3.json', ROOT / 'models/matchup_2025-12-31.json',
             ROOT / 'basketball_common.py', DERIVED / 'athletes.parquet', DERIVED / 'teams.json']
    paths += list((ROOT / 'data/models/v1.3').glob('*'))
    paths += [ROOT / f'analysis/{p}.py' for p in ('rule3_confirmation', 'rule3_capture_audit', 'rule3_scores')]
    paths += [ROOT / f'scripts/{p}.py' for p in ('engine', 'backtest', 'minutes', 'foul_out', 'a1_compare', 'release_gate',
                                               'a1_minutes_gate', 'a1_substitution_world_audit', 'nodes', 'projection', 'rotations', 'matchups')]
    paths += [DERIVED / p for p in ('segments.parquet', 'player_games.csv', 'player_periods.csv', 'rotations/on_court.parquet',
                                  'rotations/stints.parquet', 'variants/matchup/features/pregame.parquet',
                                  'variants/matchup/features/team_pregame.parquet', 'variants/matchup/features/features_report.json')]
    for name in ('segments.parquet', 'on_court.parquet', 'stints.parquet'):
        paths += sorted((DERIVED / 'history').glob('*/' + name))
    paths += sorted((ROOT / 'data/raw/hoopr').glob('player_box_*.parquet'))
    return {str(p.relative_to(ROOT)): sha256_file(p) for p in sorted(set(paths))}


def prior_medians(pre, days):
    result = {day: {c: float(pre.loc[pre['date_et'].lt(day), c].median()) for c in engine.OFF_REL + engine.DEF_REL}
              for day in sorted(set(days))}
    if any(not np.isfinite(list(row.values())).all() for row in result.values()):
        raise ValueError('missing required prior-date fill medians')
    return result


def init_worker():
    engine.ROTATION['pool'] = 0
    inputs = load_inputs()
    e = engine.Engine(MODEL)
    if e.m.cfg['train_through'] >= TEST_FROM:
        raise ValueError('protected-season node fit')
    pre = pd.read_parquet(e.m.features / 'pregame.parquet', columns=['date_et'] + list(engine.OFF_REL + engine.DEF_REL))
    # Snapshot deterministic prior-date medians once/worker; neither final results nor future rows enter them.
    medians = prior_medians(pre, inputs[2]['date_et'].unique())
    m = minutes.build(TEST_FROM, include_current=True, upto=ORIGIN)
    m['by_game'] = m['rows'].set_index(['game_id', 'player'])
    period_rows = pd.read_csv(DERIVED / 'player_periods.csv', usecols=['game_id', 'team_id', 'period', 'pts'],
                              dtype={'game_id': str, 'team_id': str})
    backtest._W.clear()
    backtest._W.update({'engine': e, 'mod': engine, 'inputs': inputs, 'worlds': 1000, 'teams': read_json(DERIVED / 'teams.json'),
                       'rotation': 'targets', 'known_starters': False, 'periods': period_rows.groupby(['game_id', 'team_id', 'period'])['pts'].sum(),
                       'player_periods': None, 'flow_diagnostics': False, 'stream': None, 'seed_key': None,
                       'strict_minute_targets': False, 'capture_substitution_worlds': False, 'minutes': m, 'medians': medians})


def one(task):
    gid, _ = task
    pre = backtest._W['inputs'][0]
    day = str(pre.loc[pre['game_id'].eq(gid), 'date_et'].iloc[0])
    backtest._W['engine'].m.median = backtest._W['medians'][day]
    return paired.paired_game(task)


def freeze():
    if MANIFEST.exists():
        raise FileExistsError(MANIFEST)
    gate = read_json(ROOT / 'analysis/experiments/rule3_confirmation_20261123_v1_compare_gate.json')
    if gate['decision'] != 'development_scores_compatible' or gate['core']['established'] != 44:
        raise ValueError('development confirmation not qualified')
    for run in ('pilot', 'stream', 'stress'):
        report = read_json(ROOT / f'analysis/experiments/rule3_{run}_20261123_v1_audit.json')
        if not report['status'].startswith('pass'):
            raise ValueError('missing successful independent audit')
    pre, teams, seg, _, on, box = load_inputs()
    eligible = sorted(backtest.eligible_games(seg))
    if len(eligible) != 246 or not seg.loc[seg['game_id'].isin(eligible), 'defense'].astype(str).isin(NBA_TEAM_IDS).all():
        raise ValueError('population differs from declared final cohort')
    for frame, keys in ((pre, ['game_id', 'player']), (teams, ['game_id', 'team']), (on, ['game_id', 'player']), (box, ['game_id', 'player'])):
        if frame.duplicated(keys).any() or not set(eligible) <= set(frame['game_id']):
            raise ValueError('missing/duplicate source identities')
    sizes = pre[pre['game_id'].isin(eligible)].groupby(['game_id', 'team']).size()
    if len(sizes) != 2 * len(eligible) or sizes.min() < 5:
        raise ValueError('invalid conditional roster')
    write_json(MANIFEST, {'candidate': 'engine-v1.3-r1', 'kind': 'single rule-level protected final evaluation; conditional actual participants',
                         'game_ids': eligible, 'worlds': 1000, 'origin_before': ORIGIN, 'frozen_before_any_scores': True,
                         'model': MODEL, 'node_train_through': read_json(ROOT / 'data/models/v1.3/config.json')['train_through'],
                         'fingerprints': fingerprints(), 'final_gate': 'promotion-v2 mechanics; unchanged 44 core/25 diagnostic margins',
                         'prior_date_medians_both_arms': True, 'minute_aux_fit_before': TEST_FROM}, pretty=True)
    print(f'frozen {len(eligible)} final IDs, no outcome metrics read', flush=True)


def run(name, jobs, resume):
    declared = read_json(MANIFEST)
    if declared['fingerprints'] != fingerprints():
        raise ValueError('frozen final source/input identity differs')
    ids = declared['game_ids']
    folder = DERIVED / 'experiments' / name
    output = ROOT / f'analysis/experiments/{name}.json'
    if output.exists() or (folder.exists() and not resume):
        raise FileExistsError('fresh namespace required; completed final is never rerun')
    if not resume:
        folder.mkdir(parents=True)
        write_json(folder / 'plan.json', declared, pretty=True)
    elif read_json(folder / 'plan.json') != declared:
        raise ValueError('resume plan differs')
    done, allowed = {}, {folder / 'plan.json'}
    for gid in ids:
        path = folder / f'{gid}.json'
        if path.exists():
            record = read_json(path)
            if record['game'] != gid or set(record['outputs']) != {'control', 'candidate'}:
                raise ValueError('incomplete saved pair')
            for side, item in record['outputs'].items():
                target = folder / f'{gid}-{side}.npz'
                if ROOT / item['capture'] != target or sha256_file(target) != item['sha256']:
                    raise ValueError('changed saved final capture')
                allowed.add(target)
            done[gid] = record
            allowed.add(path)
    if set(folder.iterdir()) - allowed:
        raise ValueError('unverified partial/orphan outputs need inspection')
    started = time.monotonic()
    pending = [g for g in ids if g not in done]
    with ProcessPoolExecutor(max_workers=jobs, initializer=init_worker) as pool:
        for future in as_completed([pool.submit(one, (g, str(folder))) for g in pending]):
            row = future.result()
            done[row['game']] = row
            if len(done) % 24 == 0 or len(done) == len(ids):
                print(f'{len(done)}/{len(ids)} final paired games in {time.monotonic() - started:.1f}s', flush=True)
    if declared['fingerprints'] != fingerprints():
        raise ValueError('frozen inputs changed during final evaluation')
    for side in ('control', 'candidate'):
        label = name + '_' + side
        games = [dict(done[g]['outputs'][side]['result']) for g in ids]
        players = [p for g in games for p in g.pop('players')]
        pd.DataFrame(games).to_parquet(DERIVED / f'experiments/{label}.parquet', index=False)
        pd.DataFrame(players).to_parquet(DERIVED / f'experiments/{label}_players.parquet', index=False)
        write_json(ROOT / f'analysis/experiments/{label}.json', {'run': label, 'fold': 'final-rule3', 'config': 'models/v1.3.json',
                   'models': MODEL, 'games': len(ids), 'worlds': 1000, 'game_ids': ids, 'final_manifest_sha256': sha256_file(MANIFEST)}, pretty=True)
    write_json(output, {'run': name, 'game_ids': ids, 'worlds': 1000, 'directory': str(folder.relative_to(ROOT)),
               'manifest_sha256': sha256_file(MANIFEST), 'workers': jobs, 'elapsed_this_invocation': time.monotonic() - started,
               'captures': [{'game': g, 'meta': str((folder / f'{g}.json').relative_to(ROOT)),
                             'meta_sha256': sha256_file(folder / f'{g}.json')} for g in ids]}, pretty=True)


def score(name):
    output = ROOT / f'analysis/experiments/{name}_compare.json'
    if output.exists():
        raise FileExistsError('single final score already exists')
    with patch.object(backtest, 'load_inputs', side_effect=load_inputs), patch.object(a1_compare, 'distribution', side_effect=distribution):
        report = a1_compare.compare(name + '_control', name + '_candidate')
    report['method']['coverage'] = 'expected randomised PIT integrated over auxiliary uniform; legacy retained separately'
    report['final_manifest_sha256'] = sha256_file(MANIFEST)
    write_json(output, report, pretty=True)
    gate = release_gate.assess(report, 'mechanics', policy='v2')
    gate['comparison_sha256'] = sha256_file(output)
    write_json(output.with_name(output.stem + '_gate.json'), gate, pretty=True)
    print(gate['decision'], gate['core']['established'], '/', gate['core']['checks'], flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('freeze', 'run', 'score'))
    parser.add_argument('--name', default='rule3_final_20261123_v1')
    parser.add_argument('--jobs', type=int, default=8)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if not args.name.isidentifier() or not args.name.isascii() or not 1 <= args.jobs <= 10:
        raise ValueError('ASCII name, 1–10 single-thread workers required')
    if any(os.environ.get(n) != '1' for n in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS')):
        raise ValueError('set OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1')
    if args.action == 'freeze':
        freeze()
    elif args.action == 'run':
        run(args.name, args.jobs, args.resume)
    else:
        score(args.name)


if __name__ == '__main__':
    main()
