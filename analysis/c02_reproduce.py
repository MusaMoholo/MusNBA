"""One-command fresh C02 fit/prediction/feature/worker reproduction."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import gc
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import pyarrow as pa
from analysis import c02_data as data,c02_model as model,c02_rollout as rollout,c02_accounting as accounting,c02_parity as parity,c01_metrics as metrics
from analysis.c01_core import ContractError
from analysis.c01_workbench import read,create_json
from analysis.c01_reproduce import compare_numeric
from basketball_common import sha256_file

DEFAULT=ROOT/'data/derived/experiments/c02_reproduction_v1'


def source():
    p=data.verify();model.Predictor()
    if read(data.WORK/'rollout_plan.json')['sources']!=rollout.signature():raise ContractError('reproduction source/rollout signature differs')
    for path,h in read(data.WORK/'fit_lock.json')['sources'].items():
        if sha256_file(ROOT/path)!=h:raise ContractError('frozen training source changed')
    fit=read(data.WORK/'models/fit.json')
    if fit['source_sha256']!=sha256_file(ROOT/'analysis/c02_model.py'):raise ContractError('fitted algorithm changed')
    for path in ('analysis/c02_features.py','analysis/c02_parity.py'):
        key='view_sha256' if path.endswith('features.py') else 'parity_source_sha256'
        if read(data.WORK/'feature_parity.json')[key]!=sha256_file(ROOT/path):raise ContractError('feature provenance changed')
    return {'games':len(p['game_ids']),'source_signatures_passed':True,'scope':'pinned source and artifact checks; no fitting or generation'}


def compare_worlds(expected,actual):
    if set(expected)!=set(actual):raise ContractError('worker replay array keys differ')
    for key in expected:
        if not np.array_equal(expected[key],actual[key]):raise ContractError('worker replay differs: '+key)
    return True


def independent_rows(name,f,p,kind):
    if name=='who':
        truth=f.y.to_numpy().reshape(-1,5);chosen=np.sum(p*truth,1);keys=f.iloc[::5]
    else:chosen=p[np.arange(len(f)),f.y.to_numpy()];keys=f
    brier=np.square(p).sum(1)+1-2*chosen
    return pd.DataFrame({'seg_id':keys.seg_id.to_numpy(),'game_id':keys.game_id.to_numpy(),'date_et':keys.date_et.to_numpy(),
                         'node':name,'model':kind,'loss':-np.log(chosen),'brier':brier})


def reproduce(output=DEFAULT):
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    output=Path(output).resolve()
    if output.is_relative_to(ROOT) and not output.is_relative_to(ROOT/'data'):raise ContractError('private reproduction must stay ignored or outside repo')
    source();output.mkdir(parents=True,exist_ok=False);started=time.monotonic();folder=output/'models';folder.mkdir()
    train={n:pd.read_parquet(data.WORK/f'training_{n}.parquet') for n in ('who','what')}
    baseline=model.baseline_fit(train)
    if baseline!=read(data.WORK/'models/baseline.json'):raise ContractError('fresh baseline fit differs')
    create_json(folder/'baseline.json',baseline);heads={}
    for name in ('who','what'):
        print('Fresh independent fit',name,flush=True)
        _,heads[name]=model.train_head(train[name],name,folder)
        del train[name];gc.collect()
    original=read(data.WORK/'models/fit.json');compare_numeric(heads,original['heads'])
    meta={**original,'kind':'Independent fresh C02 fits','heads':heads,'created_at':datetime.now(timezone.utc).isoformat(),
          'hashes':{n:sha256_file(folder/n) for n in ('who.txt','what.txt','baseline.json')},'seconds':time.monotonic()-started}
    create_json(folder/'fit.json',meta)
    fresh=model.Predictor(folder);old=model.Predictor();parts=[];max_prediction=0.
    for name in ('who','what'):
        f=pd.read_parquet(data.WORK/f'panel_{name}.parquet')
        a,b=fresh.predict(name,f),old.predict(name,f)
        delta=float(np.max(np.abs(a-b)));max_prediction=max(max_prediction,delta)
        if delta>1e-12:raise ContractError('fresh per-possession probabilities differ')
        parts.append(independent_rows(name,f,a,'candidate'))
        parts.append(independent_rows(name,f,model.profile_predict(name,f,baseline),'profile'))
    new=pd.concat(parts,ignore_index=True);stored=pd.read_parquet(data.WORK/'event_scores.parquet')
    keys=['model','node','seg_id'];a=new.set_index(keys).sort_index();b=stored[stored.model.isin(['candidate','profile'])].set_index(keys).sort_index()
    if not a.index.equals(b.index):raise ContractError('fresh probability support differs')
    max_event=float(np.max(np.abs(a[['loss','brier']].to_numpy()-b[['loss','brier']].to_numpy())))
    if max_event>1e-10:raise ContractError('independent event arithmetic differs')
    new.to_parquet(output/'event_scores.parquet',index=False)
    incumbent=pd.read_parquet(data.WORK/'joint_event_scores.parquet');incumbent=incumbent[incumbent.model.eq('incumbent')].set_index('seg_id')
    original_screen=read(data.WORK/'screen.json');changes={}
    for kind in ('candidate','profile'):
        w=new[new.model.eq(kind)&new.node.eq('who')].set_index('seg_id').loc[incumbent.index]
        t=new[new.model.eq(kind)&new.node.eq('what')].set_index('seg_id').loc[incumbent.index]
        changes[kind]={}
        for field in ('loss','brier'):
            f=incumbent[['game_id','date_et']].assign(change=w[field]+t[field]-incumbent[field]).reset_index(drop=True)
            changes[kind][field]=metrics.bootstrap_change(f)
    max_summary=compare_numeric(changes,original_screen['changes_vs_incumbent'])
    create_json(output/'screen_changes.json',changes)
    print('Fresh fits and all200 probability/score conclusions match',flush=True)
    # Fitting work is finished before CPU-heavy source/history or worker work.
    feature=parity.run(output/'feature_parity.json')
    checked=accounting.run();create_json(output/'accounting.json',checked)
    rollout.init();rollout.STATE['predictor']=fresh
    gid=read(data.WORK/'data.json')['wiring_ids'][0]
    print('Fresh single-worker replay',gid,'1000 worlds using freshly fitted heads',flush=True)
    arrays,calls,_=rollout.generate(gid,1000,arms=('candidate',))
    with np.load(data.WORK/'rollout'/gid/'candidate.npz',allow_pickle=False) as z:expected={k:z[k] for k in z.files}
    compare_worlds(expected,arrays['candidate'])
    with (output/'candidate_replay.npz').open('xb') as stream:np.savez_compressed(stream,**arrays['candidate'])
    result={'kind':'C02 independent fresh-fit/event-score/feature/worker reproduction','games':200,
        'same_training_selected_rounds':True,'fresh_model_files_identical':all(meta['hashes'][n]==original['hashes'][n] for n in ('who.txt','what.txt','baseline.json')),
        'maximum_prediction_difference':max_prediction,'maximum_independent_event_score_difference':max_event,'maximum_screen_summary_difference':max_summary,
        'independent_feature_mismatches':feature['mismatches'],'saved_world_accounting':checked,'single_worker_fresh_fit_replay_identical':True,
        'replay_game_id':gid,'replay_worlds':1000,'replay_head_calls':calls,'seconds':time.monotonic()-started,
        'retained_inputs':'Immutable source-derived dataset caches, stored simulated rotations, and incumbent recorded-context probabilities; new candidate/profile fits and probabilities; one new full-game replay',
        'source_sha256':sha256_file(Path(__file__)),'production_changed':False}
    create_json(output/'receipt.json',result);print(result,flush=True);return result

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('stage',choices=['source','run']);a.add_argument('--output',type=Path,default=DEFAULT);args=a.parse_args()
    print(source()) if args.stage=='source' else reproduce(args.output)
