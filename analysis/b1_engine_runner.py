#!/usr/bin/env python3
"""One frozen B1 long-shot screen with exact retained controls and resumable receipts."""
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import argparse
import copy
import os
import sys
import time
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
import pyarrow as pa
from basketball_common import read_json, write_json, sha256_file
from scripts import backtest, engine
from scripts.buzzer_shots import BuzzerShots
from scripts.late_clock import ContextClock
from analysis import rule3_confirmation as paired, rule3_capture_audit as audit
from analysis.c2_engine_runner import CLOCK, CLOCK_REPORT, REFERENCE

RECIPE = ROOT / 'analysis/experiments/20261124_b1_frozen_recipe_v2.json'
MANIFEST = ROOT / 'analysis/experiments/20261124_b1_runtime_v2.json'
WORK = ROOT / 'data/derived/experiments/d42_b1_buzzer_v2'


def references():
    rows = read_json(ROOT / 'analysis/experiments/20261124_c3_engine_development_v3.json')['receipts']
    return {x['game']: x for x in rows if x['arm'] == 'reference'}


def sources():
    recipe = read_json(RECIPE)
    prior = read_json(ROOT / 'analysis/experiments/20261124_c2_engine_runtime_v2.json')['source_sha256']
    # Fingerprint the current accepted reference's complete retained model/input graph.
    paths = {ROOT / p for p in prior if '/c2_' not in p and 'c2_' not in Path(p).name
             and 'a1_s02_f4_causal' not in p and 'c2_court' not in p}
    paths.update([Path(__file__), RECIPE, ROOT / recipe['auxiliary'], ROOT / CLOCK, ROOT / CLOCK_REPORT,
                  ROOT / 'analysis/experiments/20261124_c3_engine_development_v3.json',
                  ROOT / 'analysis/experiments/20261124_b1_source_audit_v2.json'])
    paths.update(ROOT / f'scripts/{name}.py' for name in
                 ['engine','buzzer_shots','backtest','foul_out','nodes','minutes','rotations','matchups','late_clock','projection'])
    paths.update(ROOT / p for p in ['basketball_common.py','analysis/rule3_confirmation.py','analysis/rule3_capture_audit.py',
                                    'scripts/a1_compare.py','scripts/release_gate.py','docs/protocols/promotion_v3_20261123.md'])
    return {str(p.relative_to(ROOT)): sha256_file(p) for p in sorted(paths)}


def freeze():
    if MANIFEST.exists():
        raise FileExistsError(MANIFEST)
    recipe = read_json(RECIPE)
    if sha256_file(ROOT / recipe['auxiliary']) != recipe['auxiliary_sha256']:
        raise ValueError('frozen auxiliary changed')
    BuzzerShots(read_json(ROOT / recipe['auxiliary']))
    refs = references()
    if set(refs) != set(recipe['panels']['development']):
        raise ValueError('fixed development reference IDs differ')
    write_json(MANIFEST, {'recipe_sha256': sha256_file(RECIPE), 'source_sha256': sources(),
                         'reference_descriptors': refs, 'wiring': recipe['panels']['development'][:3],
                         'worlds': recipe['worlds'], 'seed_key': recipe['seed_key'],
                         'confirmation_outcomes_opened': False}, pretty=True)
    print('Frozen runtime, auxiliary, development controls and3 wiring games', flush=True)


def init_worker():
    pa.set_cpu_count(1)
    backtest._W.clear()
    backtest._init(REFERENCE, str(ROOT/'models/v1.2d.json'), 'F4', 1000,
                   rotation='targets', pool=0, seed_key='v1.2d_F4')
    eng = backtest._W['engine']
    eng.runtime = {**engine.ENGINE, 'models': REFERENCE, 'clock_recipe': CLOCK}
    training = read_json(ROOT/CLOCK_REPORT)['folds']['F4']['training']
    if training['latest_training_date'] > '2025-12-31':
        raise ValueError('future clock auxiliary')
    eng.clock_policy = ContextClock(read_json(ROOT/CLOCK), training['cells'])
    eng.clock_policy.train_through = '2025-12-31'


def task(job):
    gid, arm, directory = job
    folder = Path(directory) / gid / arm
    folder.mkdir(parents=True, exist_ok=True)
    receipt = folder/'receipt.json'
    if receipt.exists() or any(folder.iterdir()):
        raise FileExistsError('partial arm requires inspection; no overwrite')
    eng = backtest._W['engine']
    recipe = read_json(RECIPE)
    eng.buzzer_policy = BuzzerShots(read_json(ROOT/recipe['auxiliary'])) if arm == 'candidate' else None
    started = time.monotonic()
    r = paired.paired_game((gid,str(folder)), labels=('candidate',), corrected=(True,True), persist=False)
    entry = r['outputs']['candidate']
    with np.load(ROOT / entry['capture'], allow_pickle=False) as z:
        raw = {k: z[k] for k in z.files}
    if audit.capture_digest(raw) != entry['world_sha256']:
        raise ValueError('canonical digest differs')
    checked = audit.audit_worlds({**raw, 'trace_phase': raw['trace_phase'].astype(np.int16)}, foul_penalty=True)
    checked.update(audit.team_fouls(raw, True))
    audit.audit_metrics(raw, entry['result'])
    row = {'game':gid, 'arm':arm, 'entry':entry, 'audit':checked,
           'mechanism':dict(eng.buzzer_policy.counts) if eng.buzzer_policy is not None else None,
           'segments_per_world': float((raw['trace_phase']==0).sum()/1000),
           'seconds':time.monotonic()-started}
    write_json(receipt,row,pretty=False)
    return str(receipt.relative_to(ROOT))


def verified(path, descriptor=None):
    if descriptor and sha256_file(path) != descriptor['sha256']:
        raise ValueError('reference metadata changed')
    row=read_json(path)
    if sha256_file(ROOT/row['entry']['capture']) != row['entry']['sha256']:
        raise ValueError('retained capture changed')
    return row


def run(phase,jobs):
    manifest, recipe = read_json(MANIFEST), read_json(RECIPE)
    if manifest['recipe_sha256'] != sha256_file(RECIPE) or sources() != manifest['source_sha256']:
        raise ValueError('frozen runtime/source differs')
    if phase=='confirmation':
        decision = read_json(ROOT/'analysis/experiments/20261124_b1_development_decision_v2.json')
        if not decision['qualified']:
            raise ValueError('no qualified development survivor')
    ids=manifest['wiring'] if phase=='wiring' else recipe['panels'][phase]
    output=ROOT/f'analysis/experiments/20261124_b1_{phase}_v2.json'
    if output.exists():
        raise FileExistsError(output)
    directory=WORK/phase
    signature={'manifest_sha256':sha256_file(MANIFEST),'phase':phase,'game_ids':ids}
    if directory.exists():
        if read_json(directory/'plan.json')!=signature:
            raise ValueError('resume signature differs')
    else:
        directory.mkdir(parents=True)
        write_json(directory/'plan.json',signature,pretty=True)
    refs=manifest['reference_descriptors']
    done, pending={},[]
    for gid in ids:
        for arm in ('reference','candidate'):
            path=directory/gid/arm/'receipt.json'
            if path.exists():
                done[gid,arm]=(verified(path),path)
            elif phase=='development' and arm=='reference':
                source=ROOT/refs[gid]['receipt']
                done[gid,arm]=(verified(source,refs[gid]),source)
            elif phase=='development' and gid in manifest['wiring']:
                source=WORK/'wiring'/gid/arm/'receipt.json'
                done[gid,arm]=(verified(source),source)
            else:
                pending.append((gid,arm,str(directory)))
    if phase=='development':
        wiring=read_json(ROOT/'analysis/experiments/20261124_b1_wiring_v2.json')
        if wiring['reference_raw_parity']!=manifest['wiring']:
            raise ValueError('three default-off raw replays required')
    # Fail in parent on init/cutoff errors, then release arrays before workers start.
    init_worker();backtest._W.clear()
    started=time.monotonic()
    with ProcessPoolExecutor(max_workers=jobs,initializer=init_worker) as pool:
        for future in as_completed([pool.submit(task,job) for job in pending]):
            path=ROOT/future.result();row=verified(path);done[row['game'],row['arm']]=(row,path)
            if phase=='wiring' or len(done)%20==0:
                print(f'{len(done)}/{2*len(ids)} arms complete; {time.monotonic()-started:.1f}s',flush=True)
    parity=[]
    if phase=='wiring':
        for gid in ids:
            retained=verified(ROOT/refs[gid]['receipt'],refs[gid])
            if done[gid,'reference'][0]['entry']['world_sha256'] != retained['entry']['world_sha256']:
                raise ValueError('disabled policy changes accepted raw worlds')
            parity.append(gid)
    if sources()!=manifest['source_sha256']:
        raise ValueError('source changed during run')
    derived={}
    for arm in ('reference','candidate'):
        rows=[copy.deepcopy(done[gid,arm][0]['entry']['result']) for gid in ids]
        players=[p for row in rows for p in row.pop('players')]
        name=f'b1_{phase}_v2_{arm}'
        for suffix,table in [('',pd.DataFrame(rows)),('_players',pd.DataFrame(players))]:
            path=ROOT/f'data/derived/experiments/{name}{suffix}.parquet'
            if path.exists():raise FileExistsError(path)
            table.to_parquet(path,index=False);derived[str(path.relative_to(ROOT))]=sha256_file(path)
        path=ROOT/f'analysis/experiments/{name}.json'
        if path.exists():raise FileExistsError(path)
        write_json(path,{'run':name,'fold':'F4','games':len(ids),'game_ids':ids,'worlds':1000,'models':REFERENCE,
              'config':'models/v1.2d.json','rotation':'targets','pool':0,'known_starters':False,
              'simulation_stream':None,'seed_key':'v1.2d_F4','kind':'B1 research; actual-participant rosters'},pretty=True)
    receipts=[{'game':gid,'arm':arm,'receipt':str(done[gid,arm][1].relative_to(ROOT)),
               'sha256':sha256_file(done[gid,arm][1])} for gid in ids for arm in ('reference','candidate')]
    counts={}
    for gid in ids:
        for key,value in (done[gid,'candidate'][0]['mechanism'] or {}).items():
            counts[key]=counts.get(key,0)+value
    write_json(output,{'kind':'B1 frozen end-of-period long-shot screen; no promotion','phase':phase,
        'game_ids':ids,'worlds':1000,'manifest_sha256':sha256_file(MANIFEST),
        'reference_raw_parity':parity,'receipts':receipts,'derived_outputs':derived,
        'mechanism_counts':counts,'fresh_jobs':len(pending),'seconds':time.monotonic()-started,
        'production_changed':False,'protected_scoring':False},pretty=True)
    print(f'{phase} complete; {counts}; no promotion',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['freeze','wiring','development','confirmation'])
    parser.add_argument('--jobs',type=int,default=10,choices=range(1,11))
    args=parser.parse_args()
    if any(os.environ.get(k)!='1' for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS']):
        raise ValueError('single-thread OMP/BLAS required')
    if args.action=='freeze':freeze()
    else:run(args.action,args.jobs)
