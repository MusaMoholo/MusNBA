#!/usr/bin/env python3
"""A2 closure: prior recipe, wiring parity, then one protected comparison; never auto-publishes."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
import os
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pandas as pd
from basketball_common import read_json, write_json, sha256_file
from analysis import a2_late_clock, a2_clock_engine as clock, rule3_final as final
from scripts import backtest, engine, a1_compare, release_gate
from scripts.evaluate import TEST_FROM
from analysis.rule3_scores import distribution

EXP = ROOT / 'analysis/experiments'
RECIPE = EXP / '20261123_a2_clock_runtime_recipe_v1.json'
POOL = ROOT / 'data/models/v1.3-r3/clock.json'
F4_POOL = ROOT / 'data/derived/experiments/a2_clock_runtime_f4_recipe_20261123_v1.json'
PARITY = EXP / '20261123_a2_clock_runtime_parity_v1.json'
MANIFEST = EXP / '20261123_a2_clock_final_manifest_v1.json'
BASE_RUN = EXP / 'independent_rotation_final_20261123_v1.json'
BASE_MANIFEST = EXP / '20261123_independent_rotation_final_manifest_v1.json'
RUN = 'a2_clock_final_20261123_v1'
PROTOCOL = ROOT / 'docs/protocols/a2_clock_v3_development_20261123.md'
ORIGINAL_FINGERPRINTS, ORIGINAL_INIT, ENGINE_CLASS = final.fingerprints, final.init_worker, engine.Engine


def prepare():
    if any(p.exists() for p in (RECIPE, POOL, F4_POOL)):
        raise FileExistsError('candidate recipe already exists')
    stress = read_json(EXP / 'a2_clock_stress_20261123_v1_audit.json')
    resume = read_json(EXP / '20261123_a2_clock_stress_resume_accounting_v1.json')
    if (not stress['status'].startswith('pass') or stress['real_games'] != 3
            or stress['worlds_per_arm_game'] != 10000 or resume['unchanged_files'] != 41):
        raise ValueError('complete stress and clean-resume accounting required')
    base = read_json(BASE_MANIFEST)
    changed = [p for p, digest in base['fingerprints'].items()
               if p.startswith(('data/', 'models/')) and sha256_file(ROOT / p) != digest]
    if changed:
        raise ValueError(f'protected baseline inputs changed: {changed}')
    cfg = read_json(ROOT / 'data/models/v1.3/config.json')
    cutoff = cfg['train_through']
    if cutoff >= TEST_FROM:
        raise ValueError('clock fit must precede the protected season')
    paths = sorted((ROOT / 'data/derived/history').glob('*/segments.parquet'))
    columns = ['game_id', 'date_et', 'game_ok', 'start_clock', 'shot_time', 'end_type', 'period',
               'score_off', 'score_def', 'season_type', 'offense', 'defense']
    history = pd.concat([pd.read_parquet(p, columns=columns,
        filters=[('start_clock', '<=', 24), ('date_et', '<=', cutoff)]) for p in paths], ignore_index=True)
    table = a2_late_clock.fit(history, cutoff)
    pools = {kind: {str(k): {'x': p.x.tolist(), 'quiet': float(p.quiet)} for k, p in table[kind].items()}
             for kind in ('bridge', 'contextual')}
    payload = {'kind': 'contextual-clock-v1', 'train_through': cutoff,
               'training': table['info'], 'pools': pools}
    POOL.parent.mkdir(exist_ok=False)
    write_json(POOL, payload, pretty=False)
    from scripts.late_clock import load_recipe
    load_recipe(POOL, cutoff)
    oldpool, report = clock.pool_paths('F4')
    info = read_json(report)['folds']['F4']['training']
    write_json(F4_POOL, {'kind': 'contextual-clock-v1', 'train_through': info['cutoff'],
        'training': info, 'pools': read_json(oldpool)}, pretty=False)
    runtime = {**engine.ENGINE, 'id': 'engine-v1.3-r3', 'version': 'v1.3-r3',
        'clock_recipe': str(POOL.relative_to(ROOT)),
        'label': 'Possession engine: each world draws its own player minutes and rotations, with legal foul-out handling. '
                 'Prior-fitted timing responds to the score and clock late in Q4/overtime. '
                 'Lineup probabilities are assumptions; defender impact and late foul/shot choices still need improvement.'}
    write_json(RECIPE, {'status': 'fixed candidate; not promoted', 'runtime': runtime,
        'node_models': 'v1.3', 'clock_train_through': cutoff, 'training': table['info'],
        'pool_sha256': sha256_file(POOL), 'f4_parity_pool_sha256': sha256_file(F4_POOL),
        'fitted_with_unchanged_recipe': str(Path(a2_late_clock.__file__).relative_to(ROOT)),
        'fit_source_sha256': sha256_file(Path(a2_late_clock.__file__)),
        'history_sha256': {str(p.relative_to(ROOT)): sha256_file(p) for p in paths},
        'stress_sha256': sha256_file(EXP / 'a2_clock_stress_20261123_v1_audit.json'),
        'resume_sha256': sha256_file(EXP / '20261123_a2_clock_stress_resume_accounting_v1.json'),
        'protected_r2_controls': str(BASE_RUN.relative_to(ROOT)),
        'limits': 'Clock timing revision; no new shooting/form factor or universal player-accuracy claim.'}, pretty=True)
    print(f'Fixed clock pools through{cutoff}; production remains r2.', flush=True)


def parity_one(task):
    mode, gid = task
    clock.FOLD, clock.PHASE = 'F4', 'parity'
    clock.init_worker(1000, None)
    rt = {**engine.ENGINE, 'models': clock.metadata('F4')['models']}
    if mode == 'clock':
        rt.update(id='engine-v1.3-r3-candidate', clock_recipe=str(F4_POOL.relative_to(ROOT)))
        source_run = 'a2_clock_development_20261123_v1'
    else:
        source_run = 'independent_rotation_pilot_20261123_v1'
    backtest._W['engine'] = ENGINE_CLASS(rt['models'], runtime=rt)
    folder = ROOT / 'data/derived/experiments/a2_clock_runtime_parity_20261123_v1' / mode
    folder.mkdir(parents=True, exist_ok=True)
    source = ROOT / f'data/derived/experiments/{source_run}/{gid}.json'
    declared = next(r for r in read_json(EXP / f'{source_run}.json')['captures'] if r['game'] == gid)
    if sha256_file(source) != declared['meta_sha256']:
        raise ValueError('parity reference metadata changed')
    expected = read_json(source)['outputs']['candidate']
    if sha256_file(ROOT / expected['capture']) != expected['sha256']:
        raise ValueError('parity reference capture changed')
    result = clock.ORIGINAL_GAME((gid, str(folder)), labels=('candidate',), corrected=(True, True), persist=False)
    actual = result['outputs']['candidate']
    if actual['world_sha256'] != expected['world_sha256']:
        raise ValueError(f'{mode}/{gid}: raw wiring parity failed')
    return {'mode': mode, 'game': gid, 'raw_world_parity': True,
            'reference_meta_sha256': sha256_file(source), 'world_sha256': actual['world_sha256']}


def parity(jobs):
    if PARITY.exists():
        raise FileExistsError('wiring parity already recorded')
    read_json(RECIPE)
    panels = read_json(clock.MANIFEST)
    tasks = [('off', gid) for gid in panels['pilot']] + [('clock', gid) for gid in panels['development'][:3]]
    with ProcessPoolExecutor(max_workers=min(jobs, len(tasks))) as pool:
        rows = list(pool.map(parity_one, tasks))
    write_json(PARITY, {'status': 'pass; exact raw wiring parity, no new score', 'games': rows,
        'recipe_sha256': sha256_file(RECIPE), 'source_sha256': fingerprints()}, pretty=True)
    print('All three r2/off and three loaded-clock raw captures match retained references.', flush=True)


def fingerprints():
    paths = [Path(__file__), RECIPE, POOL, F4_POOL, ROOT / 'scripts/late_clock.py',
             ROOT / 'scripts/live_forecast.py', BASE_RUN, BASE_MANIFEST, PROTOCOL,
             EXP / 'a2_clock_stress_20261123_v1_audit.json',
             EXP / '20261123_a2_clock_stress_resume_accounting_v1.json']
    return {**ORIGINAL_FINGERPRINTS(), **{str(p.relative_to(ROOT)): sha256_file(p) for p in paths}}


def freeze():
    if MANIFEST.exists():
        raise FileExistsError('single protected recipe already frozen')
    parity = read_json(PARITY)
    if len(parity['games']) != 6 or not all(r['raw_world_parity'] for r in parity['games']):
        raise ValueError('both three-game wiring checks required')
    if parity['source_sha256'] != fingerprints():
        raise ValueError('wiring sources changed after parity')
    base = read_json(BASE_MANIFEST)
    write_json(MANIFEST, {**base, 'candidate': 'engine-v1.3-r3',
        'kind': 'single protected contextual-clock comparison; conditional actual participants',
        'frozen_at': datetime.now(timezone.utc).isoformat(), 'baseline': 'retained qualified r2 captures',
        'runtime': read_json(RECIPE)['runtime'], 'fingerprints': fingerprints(),
        'final_gate': 'explicit learned/v3,27 proper compatibility bounds; conditional-clock primary, unchanged margins',
        'parity_sha256': sha256_file(PARITY)}, pretty=True)
    print(f"Frozen {len(base['game_ids'])} protected IDs; no r3 protected outcomes generated.", flush=True)


def init_worker():
    rt = read_json(RECIPE)['runtime']
    with patch.object(final.engine, 'Engine', side_effect=lambda *a, **k: ENGINE_CLASS(*a, runtime=rt, **k)):
        ORIGINAL_INIT()


def one(task):
    gid, directory = task
    prior = ROOT / f'data/derived/experiments/independent_rotation_final_20261123_v1/{gid}.json'
    declared = next(r for r in read_json(BASE_RUN)['captures'] if r['game'] == gid)
    if sha256_file(prior) != declared['meta_sha256']:
        raise ValueError('retained protected control metadata changed')
    control = read_json(prior)['outputs']['candidate']
    source = ROOT / control['capture']
    if sha256_file(source) != control['sha256']:
        raise ValueError('retained protected control capture changed')
    target = Path(directory) / f'{gid}-control.npz'
    os.link(source, target)
    day = str(backtest._W['inputs'][0].loc[lambda x: x.game_id.eq(gid), 'date_et'].iloc[0])
    backtest._W['engine'].m.median = backtest._W['medians'][day]
    row = final.paired.paired_game(task, labels=('candidate',), corrected=(True, True), persist=False)
    row['outputs']['control'] = {**control, 'capture': str(target.relative_to(ROOT))}
    row.update(control_corrected=True, reused_control={'meta': str(prior.relative_to(ROOT)), 'sha256': sha256_file(prior)})
    meta = Path(directory) / f'{gid}.json'
    write_json(meta, row, pretty=False)
    cache = Path(directory).with_name(Path(directory).name + '_independent_audits')
    cache.mkdir(exist_ok=True)
    clock.auditor.audit_pair((str(meta), str(cache / f'{gid}.json')))
    return row


def score():
    output = EXP / f'{RUN}_compare.json'
    if output.exists() or output.with_name(output.stem + '_gate.json').exists():
        raise FileExistsError('single protected comparison already scored')
    audit = read_json(EXP / f'{RUN}_audit.json')
    if audit['pairs'] != 246 or not audit['status'].startswith('pass'):
        raise ValueError('complete independent protected accounting required')
    with patch.object(backtest, 'load_inputs', side_effect=final.load_inputs), patch.object(a1_compare, 'distribution', side_effect=distribution):
        report = a1_compare.compare(RUN + '_control', RUN + '_candidate')
    path = EXP / '20261123_a2_late_clock_confirmation_v1.json'
    node = read_json(path)['folds']['F4']
    report['clock_node_primary'] = {'source': str(path.relative_to(ROOT)), 'sha256': sha256_file(path),
        **{f'{k}_joint': node['comparisons'][k]['joint'] for k in ('legacy', 'bridge')}}
    report['method']['coverage'] = 'expected randomised PIT; no clipping'
    report['final_manifest_sha256'] = sha256_file(MANIFEST)
    write_json(output, report, pretty=True)
    gate = release_gate.assess(report, 'learned', 'clock_node_primary/legacy_joint', policy='v3')
    gate['primary']['also_beats_clean_bridge'] = node['comparisons']['bridge']['joint']['ci_95'][1] < 0
    gate['comparison_sha256'] = sha256_file(output)
    write_json(output.with_name(output.stem + '_gate.json'), gate, pretty=True)
    print(gate['decision'], gate['core']['established'], '/', gate['core']['checks'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'parity', 'freeze', 'run', 'score'))
    parser.add_argument('--jobs', type=int, default=10)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if not 1 <= args.jobs <= 10 or any(os.environ.get(k) != '1' for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS')):
        raise ValueError('1–10 single-thread workers; OMP/BLAS limits1 required')
    final.MANIFEST, final.PROTOCOL = MANIFEST, PROTOCOL
    final.fingerprints, final.init_worker, final.one = fingerprints, init_worker, one
    if args.action == 'prepare': prepare()
    elif args.action == 'parity': parity(args.jobs)
    elif args.action == 'freeze': freeze()
    elif args.action == 'run':
        final.run(RUN, args.jobs, args.resume)
        clock.finish_audit(RUN)
    else: score()
