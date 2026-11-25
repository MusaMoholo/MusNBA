"""Fresh C03 fitting, independent probability scores, accounting and worker replay."""
from __future__ import annotations
import argparse,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from analysis import c03_data as data,c03_model as model,c03_rollout as rollout,c03_audit as audit
from analysis.c01_workbench import read,create_json
from analysis.c01_core import ContractError
from analysis.c01_reproduce import compare_numeric
from basketball_common import sha256_file


def source():
    p=data.verify()
    for f in 'ABC':
        fit=model.Predictor(f).meta
        if fit['code_sha256']!=sha256_file(ROOT/'analysis/c03_model.py') or fit['data_sha256']!=sha256_file(data.WORK/'data.json'):raise ContractError('C03 algorithm/data signature changed')
    for stage in ('mvp','finalists'):
        if (data.WORK/f'{stage}_plan.json').exists() and read(data.WORK/f'{stage}_plan.json')['sources']!=rollout.signature():raise ContractError('C03 runtime sources changed')
    return {'source_checks_passed':True,'games':len(p['game_ids'])}

def reproduce(output):
    output=Path(output).resolve()
    if output.is_relative_to(ROOT) and not output.is_relative_to(ROOT/'data'):raise ContractError('C03 fits must stay private')
    source();output.mkdir(parents=True,exist_ok=False);start=time.monotonic();fresh={};fits={};diff={};a=data.load('panel');scores=pd.read_parquet(data.WORK/'events.parquet')
    for f in 'ABC':
        fits[f]=model.fit_family(f,output/'models');original=read(data.WORK/'models'/f/'fit.json')
        compare_numeric(fits[f]['heads'],original['heads']);fresh[f]=model.Predictor(f,output/'models');incumbent=model.Predictor(f);maxp=0.;maxs=0.
        for begin in range(0,len(a['y']),1000):
            q=data.subset(a,slice(begin,begin+1000));p=fresh[f].predict(*data.unpack(q));old=incumbent.predict(*data.unpack(q));maxp=max(maxp,float(np.abs(p-old).max()))
            # Independent explicit true-class likelihood and expanded squared-error Brier.
            truth=np.zeros_like(p);truth[np.arange(len(p)),q['y']]=1
            loss=-np.log(np.sum(p*truth,axis=1));brier=((p-truth)**2).sum(1)
            expected=scores[scores.model.eq(f)].set_index('seg_id').loc[q['seg_id']]
            maxs=max(maxs,float(np.abs(expected.loss.to_numpy()-loss).max()),float(np.abs(expected.brier.to_numpy()-brier).max()))
        if maxp>1e-12 or maxs>1e-10:raise ContractError('C03 fresh probability or independent score reproduction differs')
        diff[f]={'max_probability_difference':maxp,'max_independent_score_difference':maxs,'selected_rounds_identical':True,'model_hashes_identical':fits[f]['hashes']==original['hashes']}
        print('Fresh C03 fit and probability audit complete',f,diff[f],flush=True)
    # All fitting finished before sequential full-game replays; no nested heavy pools.
    rollout.init();rollout.STATE['predictors']=fresh;gid=read(data.WORK/'data.json')['game_ids'][0];replays={}
    for f in 'ABC':
        arrays,counts,times,_=rollout.generate(gid,(f,));expected_path=data.WORK/'rollout'/gid/f'{f}.npz'
        with np.load(expected_path,allow_pickle=False) as z:
            if set(z.files)!=set(arrays[f]) or any(not np.array_equal(z[k],arrays[f][k]) for k in z.files):raise ContractError('C03 fresh-fit single-worker full-game replay differs')
        data.save(output/f'{f}_replay.npz',arrays[f]);replays[f]={'game_id':gid,'worlds':1000,'exact_all_arrays':True,'head_calls':counts[f],'seconds':times[f]}
        print('Fresh full-game replay identical',f,flush=True)
    ids=read(data.WORK/'data.json')['game_ids'];stage='finalists' if (data.WORK/'finalists.json').exists() else 'mvp';used=ids if stage=='finalists' else ids[:20]
    checked=audit.check_saved(used);create_json(output/'accounting.json',checked)
    # Fresh summary from immutable per-game score rows; recompute the bounded decision.
    families=list('ABC') if stage=='mvp' else read(data.WORK/'mvp.json')['shortlist'];summary=rollout.summarise(used,families);stored=read(data.WORK/f'{stage}.json')
    for key in ('seconds','sources'):stored.pop(key,None)
    compare_numeric(summary,stored)
    # Independent mean/half/threshold arithmetic on rows, not via summarise.
    rows=pd.concat([pd.read_parquet(data.WORK/'rollout'/g/'scores.parquet') for g in used],ignore_index=True);q=rows[rows.entity.eq('player')&rows.stat.eq('pts')];means=q.groupby('model').crps.mean();independent={}
    for f in families:
        ratio=float((means[f]-means['control'])/means['control']);expected=summary['eligible'][f]
        if abs(ratio-expected['player_pts_relative_change'])>1e-10:raise ContractError('C03 independent primary change differs')
        independent[f]={'player_pts_relative_change':ratio,'primary_mean_promise':ratio<=(-.01 if stage=='finalists' else -.005),'eligible':expected['eligible'],'failed_checks':[k for k,v in expected['checks'].items() if not v]}
        if not independent[f]['primary_mean_promise'] and expected['eligible']:raise ContractError('C03 false positive shortlist')
    result={'kind':'C03 fresh fits/probabilities, independent event scores and saved world accounting, exact single-worker replay','fits':diff,'replays':replays,'accounting':checked,'decision_reproduced':True,'independent_primary_arithmetic':independent,'shortlist':summary['shortlist'],'feature_parity':read(data.WORK/'feature_parity.json'),'source_checks':source(),'seconds':time.monotonic()-start,'retained_inputs':'same immutable causal training caches, known panel, stored rotations, fixed conversion/rotation engine; all candidate fits/probabilities and replay worlds fresh','production_changed':False}
    create_json(output/'receipt.json',result);create_json(ROOT/'analysis/experiments/20261125_c03_reproduction_v1.json',result);print(result,flush=True);return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['source','run']);p.add_argument('--output',type=Path,default=ROOT/'data/derived/experiments/c03_reproduction_v1');a=p.parse_args()
    print(source()) if a.stage=='source' else reproduce(a.output)
