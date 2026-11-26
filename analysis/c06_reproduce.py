"""Fresh full-history fits, exact probabilities/worker replay and independent decision."""
from __future__ import annotations
import argparse,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from analysis import c06_data as data,c06_model as model,c06_rollout as rollout,c06_audit as audit
from analysis.c03_data import unpack,subset
from analysis.c06_core import check,PLAYER,CONTEXT
from analysis.c01_workbench import read,create_json
from analysis.c01_core import ContractError
from basketball_common import sha256_file


def independent_decision():
    a=data.load('panel');rows=pd.read_parquet(data.WORK/'events.parquet');report=read(data.WORK/'events.json');_,players=unpack(a);star=players['usage']>=.25;known=np.isfinite(players['usage']).all(1);truth=star[np.arange(len(a['y'])),a['y']];close=abs(a['context'][:,CONTEXT.index('margin')])<=5;nonstar=known&~star.any(1);out={};scores={}
    if sha256_file(data.WORK/'probabilities.npz')!=report['probabilities_sha256'] or sha256_file(data.WORK/'events.parquet')!=report['scores_sha256']:raise ContractError('actor score artifacts changed')
    with np.load(data.WORK/'probabilities.npz',allow_pickle=False) as z:
        for family in ('native','usage','uniform','A','B','C'):
            p=check(z[family]);loss=-np.log(p[np.arange(len(p)),a['y']]);brier=np.square(p).sum(1)+1-2*p[np.arange(len(p)),a['y']];sp=np.sum(np.where(star,p,0),axis=1);sb=(sp[known]-truth[known])**2;bias=sp[known]-truth[known];saved=rows[rows.model.eq(family)]
            if not np.array_equal(saved.seg_id,a['seg_id']) or not np.allclose(saved.loss,loss,atol=1e-12,rtol=0) or not np.allclose(saved.brier,brier,atol=1e-12,rtol=0):raise ContractError('independent actor probability scores differ')
            scores[family]={'loss':loss,'star_brier':float(sb.mean()),'star_bias':float(bias.mean())}
    for family in 'ABC':
        q=scores[family];r=scores['native'];checks={'native/benefit':float((q['loss']-r['loss']).mean())<=-.005,'usage/benefit':float((q['loss']-scores['usage']['loss']).mean())<=-.005,'population':len(np.unique(a['game_id']))>=100 and len(a['y'])>=20000,'critical_brier':q['star_brier']-r['star_brier']<=.005,'critical_calibration':abs(q['star_bias'])<=.03,'nonstar_context':float((q['loss']-r['loss'])[nonstar].mean())<=.01,'close':float((q['loss']-r['loss'])[close].mean())<=.01,'training_convergence':read(data.WORK/'models'/family/'fit.json')['converged']}
        for k,v in checks.items():
            if bool(v)!=report['eligible'][family]['checks'][k]:raise ContractError('independent actor acceptance differs:'+k)
        # Bootstrap support is checked from the independently reconstructed loss differences.
        from analysis.c04_compare import interval
        for reference in ('native','usage'):
            z=interval(pd.DataFrame({'game_id':a['game_id'],'date_et':a['date_et'],'change':q['loss']-scores[reference]['loss']}),6);support=max(z['familywise_game'][1],z['familywise_week'][1])<0
            if support!=report['eligible'][family]['checks'][reference+'/support']:raise ContractError('independent actor interval decision differs')
            checks[reference+'/support']=support
        out[family]={'all_checks_independently_matched':True,'eligible':bool(all(checks.values())),'nll':float(q['loss'].mean()),'native_change':float((q['loss']-r['loss']).mean()),'failed_checks':[k for k,v in checks.items() if not v]}
    return {'games':len(np.unique(a['game_id'])),'actions':len(a['y']),'six_laws_independently_scored':True,'decisions':out}


def fresh_final_fit(family,root):
    """Repeat the frozen final recipe; retain audited training-only selection decisions."""
    import gc
    original=read(data.WORK/'models'/family/'fit.json')
    folder=Path(root)/family;folder.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    full=data.load('final');model.dates_before(full['date_et'].tolist(),'2025-12-31');x=model.pack(*unpack(full));y=full['y'];del full;gc.collect()
    if family=='B':
        fitted,final=model.linear(x,y);path=folder/'model.json';create_json(path,fitted)
    else:
        fitted,final=model.tree(x,y,None,None,family,original['selection']['rounds']);path=folder/'model.txt';fitted.save_model(str(path))
    meta={**original,'hashes':{path.name:sha256_file(path)},'final':final,'seconds':time.monotonic()-start,'selection_reused_as_frozen_recipe':True,'fresh_final_fit':True,'final_fit_driver_sha256':sha256_file(Path(__file__))}
    if family=='B':meta['converged']=bool(original['selection']['converged'] and final['converged'])
    create_json(folder/'fit.json',meta);return meta


def run(output,resume=False):
    data.verify();output=Path(output).resolve()
    if not output.is_relative_to(ROOT/'data'):raise ContractError('fresh actor evidence must stay ignored under data')
    if output.exists() and not resume:raise FileExistsError(output)
    output.mkdir(parents=True,exist_ok=resume);start=time.monotonic();fresh={};fits={}
    for family in 'ABC':
        fitpath=output/'models'/family/'fit.json'
        if resume and fitpath.exists():meta=read(fitpath)
        else:meta=fresh_final_fit(family,output/'models')
        old=read(data.WORK/'models'/family/'fit.json')
        if meta['hashes']!=old['hashes']:raise ContractError('fresh actor fit differs')
        fresh[family]=model.Predictor(family,output/'models');fits[family]={'model_files_exact':True,'converged':meta['converged']};print('C06 fresh fit identical',family,flush=True)
    a=data.load('panel');count=0
    with np.load(data.WORK/'probabilities.npz',allow_pickle=False) as z:
        for family in 'ABC':
            for start in range(0,len(a['y']),2000):
                p=fresh[family].predict(*unpack(subset(a,slice(start,start+2000))))
                if not np.array_equal(p,z[family][start:start+len(p)]):raise ContractError('fresh actor probabilities differ')
                count+=p.size
            print('C06 fresh probabilities exact',family,flush=True)
    rollout.init();gid=data.verify()['game_ids'][0];replays={}
    for family in 'ABC':
        path=output/f'{family}_replay.npz'
        if resume and path.exists():
            with np.load(path,allow_pickle=False) as z:arrays={k:z[k] for k in z.files}
        else:
            arms,times,calls,error,new=rollout.generate(gid,(family,),fresh=fresh);arrays=arms[family]
            with path.open('xb') as stream:np.savez_compressed(stream,**arrays)
        with np.load(data.WORK/'games'/gid/f'{family}.npz',allow_pickle=False) as z:
            if set(z.files)!=set(arrays) or any(not np.array_equal(arrays[k],z[k]) for k in z.files):raise ContractError('fresh actor worker replay differs')
        from analysis.c02_accounting import check_arrays
        check_arrays(arrays);replays[family]={'all_arrays_exact':True,'new_worlds':1000};print('C06 fresh worker replay exact',family,flush=True)
    n=200 if (data.WORK/'final.json').exists() else 20 if (data.WORK/'short.json').exists() else 2
    result={'kind':'C06 fresh uncapped fits/probabilities/worker worlds and independent decision','fits':fits,'actor_probability_values_exact':count,'single_worker_replays':replays,'independent_decision':independent_decision(),'world_accounting':audit.world_audit(data.verify()['game_ids'][:n]),'retained_inputs':'Source-derived actor arrays, audited training-only selection decisions/frozen final recipes, native worlds and compatible controls; all final challenger fits, probabilities and replay worlds fresh. Selection optimisation itself is not repeated.','seconds':time.monotonic()-start,'production_changed':False};create_json(output/'reproduction.json',result);create_json(ROOT/'analysis/experiments/20261126_c06_reproduction_v1.json',result)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ROOT/'data/derived/experiments/c06_reproduction_v1');p.add_argument('--resume',action='store_true');a=p.parse_args();run(a.output,a.resume)
