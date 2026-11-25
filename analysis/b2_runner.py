#!/usr/bin/env python3
"""Canonical1k historical B2 queue; results stay private until prospective grading."""
from concurrent.futures import ProcessPoolExecutor,as_completed
from pathlib import Path
import argparse
import os
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import pyarrow as pa
from basketball_common import read_json,write_json,sha256_file
from analysis.b2_prepare import PLAN,WORK,VARIANTS,frame_for
from analysis.b2_paths import HistoricalPaths
MANIFEST=ROOT/'analysis/experiments/20261124_b2_runtime_v2.json'
RUNS=ROOT/'data/derived/experiments/d42_b2_runs_v2'
STATE={}


def sources():
    paths=[PLAN,WORK/'starts.json',ROOT/'analysis/experiments/20261124_b2_prior_fits_v1.json',
           ROOT/'analysis/experiments/20261124_b2_score_truth_v3.json',ROOT/'analysis/b2_score_truth.py',
           ROOT/'analysis/experiments/20261124_b2_calendar_audit_v1.json',ROOT/'data/derived/teams.json']
    paths+=[ROOT/p for p in ['analysis/b2_runner.py','analysis/b2_paths.py','analysis/b2_prepare.py','analysis/b2_calendar_audit.py',
                           'scripts/competitions.py','scripts/competition_rules.py','scripts/pathway.py','scripts/projection.py']]
    for y in range(2023,2027):
        paths.extend([ROOT/f'data/derived/experiments/d42_b2_calendar_audit_v1/{y}.parquet',
                      ROOT/f'data/derived/experiments/d42_b2_score_truth_v3/{y}.parquet'])
    return {str(p.relative_to(ROOT)):sha256_file(p) for p in paths}


def freeze():
    if MANIFEST.exists():raise FileExistsError(MANIFEST)
    plan=read_json(PLAN)
    write_json(MANIFEST,{'kind':'B2 fixed16-origin five-arm10k queue; held-out scoring unopened',
        'origins':plan['origins'],'arms':['reference','persistence',*VARIANTS],
        'worlds':10000,'chunk_worlds':1000,'source_sha256':sources(),
        'independent_origins':[d for d in plan['origins'] if d>='2025-07-01'],
        'development_origins':[d for d in plan['origins'] if d<'2025-07-01'],
        'setup_repair':'V1 reference-only wiring exposed derived period-source inconsistencies. V2 uses original clock-ordered scoreboards and six retained ESPN summaries; no candidate accuracy inspected or policy changed.'},pretty=True)


def init_worker():
    pa.set_cpu_count(1)
    STATE['starts']=read_json(WORK/'starts.json');STATE['teams']=read_json(ROOT/'data/derived/teams.json')
    STATE['calendar']=read_json(ROOT/'analysis/experiments/20261124_b2_calendar_audit_v1.json')['seasons']
    STATE['frames']={y:frame_for(y) for y in range(2023,2027)};STATE['periods']={};STATE['previous']={}
    for y in range(2023,2027):
        p=pd.read_parquet(ROOT/f'data/derived/experiments/d42_b2_score_truth_v3/{y}.parquet')
        STATE['periods'][y]=p.set_index('game_id')
        STATE['previous'][y]=STATE['frames'][y-1].groupby('team').win.sum().to_dict() if y>2023 else {t:0 for t in STATE['teams']}


def task(job):
    day,arm,chunk,worlds,phase=job;year=int(day[:4])+(day[5:7]>='07')
    folder=RUNS/phase/day/arm;folder.mkdir(parents=True,exist_ok=True)
    receipt=folder/f'{chunk:03d}.json';path=receipt.with_suffix('.npz')
    if receipt.exists():
        row=read_json(receipt)
        if sha256_file(path)!=row['sha256']:raise ValueError('retained chunk changed')
        return str(receipt.relative_to(ROOT))
    if path.exists():raise FileExistsError('partial chunk needs inspection; no overwrite')
    params=VARIANTS.get(arm,{'scale':0. if arm=='persistence' else 1.,'n_cap':20})
    model=HistoricalPaths(STATE['frames'][year],STATE['calendar'][str(year)],day,
        STATE['starts']['origins'][day][arm],STATE['teams'],STATE['periods'][year],STATE['previous'][year],
        worlds,chunk,params)
    began=time.monotonic();arrays,audit=model.capture()
    with path.with_suffix('.partial').open('xb') as stream:np.savez_compressed(stream,**arrays)
    path.with_suffix('.partial').rename(path)
    write_json(receipt,{'origin':day,'arm':arm,'chunk':chunk,'worlds':worlds,'path':str(path.relative_to(ROOT)),
        'sha256':sha256_file(path),'audit':audit,'seconds':time.monotonic()-began},pretty=False)
    return str(receipt.relative_to(ROOT))


def run(phase,jobs):
    manifest=read_json(MANIFEST)
    if sources()!=manifest['source_sha256']:raise ValueError('frozen B2 source/fit changed')
    output=ROOT/f'analysis/experiments/20261124_b2_{phase}_v2.json'
    if output.exists():raise FileExistsError(output)
    tasks=([(d,'reference',0,100,'wiring') for d in ['2022-11-20','2023-11-20','2024-11-20']] if phase=='wiring' else
           [(d,a,k,1000,'screen') for d in manifest['origins'] for a in manifest['arms'] for k in range(10)])
    if phase=='screen':read_json(ROOT/'analysis/experiments/20261124_b2_wiring_v2.json')
    directory=RUNS/phase;signature={'manifest_sha256':sha256_file(MANIFEST),'tasks':[list(t) for t in tasks]}
    if directory.exists():
        if read_json(directory/'plan.json')!=signature:raise ValueError('resume signature changed')
    else:directory.mkdir(parents=True);write_json(directory/'plan.json',signature,pretty=False)
    completed=[];pending=[]
    for job in tasks:
        d,a,k,worlds,ph=job;p=RUNS/ph/d/a/f'{k:03d}.json'
        if p.exists():
            row=read_json(p)
            if row['worlds']!=worlds or sha256_file(ROOT/row['path'])!=row['sha256']:raise ValueError('resume chunk differs')
            completed.append(p)
        else:pending.append(job)
    started=time.monotonic()
    with ProcessPoolExecutor(max_workers=jobs,initializer=init_worker) as pool:
        for f in as_completed([pool.submit(task,j) for j in pending]):
            completed.append(ROOT/f.result())
            if phase=='wiring' or len(completed)%max(1,len(tasks)//10)==0:
                print(f'{len(completed)}/{len(tasks)} canonical chunks accounted;{time.monotonic()-started:.1f}s',flush=True)
    if sources()!=manifest['source_sha256']:raise ValueError('source changed during queue')
    rows=[read_json(p) for p in completed]
    write_json(output,{'kind':'B2 historical paths completed; no candidate score selection performed',
        'phase':phase,'chunks':len(rows),'worlds':sum(r['worlds'] for r in rows),
        'origins':sorted({r['origin'] for r in rows}),'arms':sorted({r['arm'] for r in rows}),
        'receipts':[{'path':str(p.relative_to(ROOT)),'sha256':sha256_file(p)} for p in sorted(completed)],
        'seconds':time.monotonic()-started,'source_sha256':manifest['source_sha256'],
        'protected_scoring':False,'production_changed':False},pretty=True)
    print(f'{phase} completed; no held-out accuracy opened',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['freeze','wiring','screen'])
    p.add_argument('--jobs',type=int,default=10,choices=range(1,11));args=p.parse_args()
    if any(os.environ.get(k)!='1' for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS']):raise ValueError('one inner thread per worker')
    if args.action=='freeze':freeze()
    else:run(args.action,args.jobs)
