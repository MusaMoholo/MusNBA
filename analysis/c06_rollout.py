"""Hash-resumable actor-only worlds with original native and compatible controls."""
from __future__ import annotations
import argparse,sys,time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from analysis import c06_data as data,c06_model as model,c02_rollout as old,c01_contexts as context
from analysis.c02_features import View
from analysis.c06_runtime import attached
from analysis.c04_rollout import native,score
from analysis.c01_workbench import read,create_json
from analysis.c01_core import ContractError
from basketball_common import sha256_file
STATE={}


def signature():
    paths=[ROOT/f'analysis/c06_{n}.py' for n in ('core','data','model','evaluate','runtime','rollout','compare')]+[data.CONTRACT,data.WORK/'data.json']+[data.WORK/'models'/f/'fit.json' for f in 'ABC']+[ROOT/'analysis/c04_rollout.py']
    return {'sources':{str(p.relative_to(ROOT)):sha256_file(p) for p in paths},'fixed_engine':old.signature()}


def init():
    old.init();STATE['models']={f:model.Predictor(f) for f in 'ABC'}


def retained_control(gid):
    folder=old.WORK/'rollout'/gid
    if not (folder/'receipt.json').exists():return None
    if read(old.WORK/'rollout_plan.json')['sources']!=old.signature():raise ContractError('retained compatible control provenance changed')
    r=read(folder/'receipt.json');path=folder/'control.npz'
    if sha256_file(path)!=r['hashes']['control.npz']:raise ContractError('retained compatible control artifact changed')
    with np.load(path,allow_pickle=False) as z:return {k:z[k] for k in z.files}


def generate(gid,families,benchmark=False,fresh=None):
    s=old.STATE;ref=s['refs'][gid];g=context.make_game(ref,s['pre'],s['teams']);tables,combo,error=context.stored_schedules(ROOT/ref['capture']);g.lineup_tables=lambda available,rng,fit_offsets=None:(tables,combo[:1000]);view=View(g,s['causal'],s['causal_teams']);e=s['engine'];control=retained_control(gid);arrays={'native':native(ref)};times={};calls={};new=0
    if control is None or benchmark:
        start=time.monotonic();e.world_observer=context.ZoneObserver();e.simulate(g,1000,old.seed(gid));generated=old.capture_arrays(g,e.last);times['control']=time.monotonic()-start;new+=1000
        if control is not None and any(not np.array_equal(control[k],generated[k]) for k in control):raise ContractError('fresh compatible control differs')
        control=generated
    else:times['control']=None
    arrays['control']=control
    for family in families:
        start=time.monotonic();e.world_observer=context.ZoneObserver()
        with attached(e,g,view,(fresh or STATE['models'])[family]) as used:e.simulate(g,1000,old.seed(gid));arrays[family]=old.capture_arrays(g,e.last)
        if used['who']<=0:raise ContractError('unused actor adapter')
        calls[family]=dict(used);times[family]=time.monotonic()-start;new+=1000
    return arrays,times,calls,error,new


def job(gid,families,benchmark,sig):
    folder=data.WORK/'games'/gid;folder.mkdir(parents=True,exist_ok=False);arrays,times,calls,error,new=generate(gid,families,benchmark);hashes={}
    for arm,a in arrays.items():
        with (folder/f'{arm}.npz').open('xb') as stream:np.savez_compressed(stream,**a)
        hashes[f'{arm}.npz']=sha256_file(folder/f'{arm}.npz')
    scores,joint=score(gid,arrays)
    for name,f in [('scores.parquet',scores),('joint.parquet',joint)]:f.to_parquet(folder/name,index=False);hashes[name]=sha256_file(folder/name)
    r={'game_id':gid,'arms':list(arrays),'new_worlds':new,'worlds':1000,'hashes':hashes,'seconds_by_arm':times,'head_calls':calls,'schedule_discretisation':error,'generation_signature':sig,'fixed_native_schedule':True};create_json(folder/'receipt.json',r);return r


def run(stage,jobs=10):
    from analysis.c06_compare import summarise
    p=data.verify();events=read(data.WORK/'events.json');families=list('ABC') if stage=='wiring' else events['shortlist'] if stage=='short' else read(data.WORK/'short.json')['shortlist']
    if not families:raise ContractError('no eligible actor: expansion forbidden')
    sig=signature();ids=p['game_ids'][:2] if stage=='wiring' else p['game_ids'][:20] if stage=='short' else p['game_ids'];plan=data.WORK/f'{stage}_plan.json';out=data.WORK/f'{stage}.json'
    if out.exists():raise FileExistsError(out)
    if plan.exists():
        if read(plan)['sources']!=sig:raise ContractError('actor resume sources changed')
    else:create_json(plan,{'sources':sig,'game_ids':ids,'families':families})
    pending=[];done=0;start=time.monotonic()
    for gid in ids:
        folder=data.WORK/'games'/gid
        if (folder/'receipt.json').exists():
            r=read(folder/'receipt.json')
            if r['generation_signature']!=sig or any(sha256_file(folder/n)!=h for n,h in r['hashes'].items()):raise ContractError('completed actor game/source changed')
            if set(families)-set(r['arms']):raise ContractError('missing actor family')
            done+=1
        elif folder.exists():raise ContractError('retain and inspect partial actor game')
        else:pending.append(gid)
    with ProcessPoolExecutor(max_workers=jobs,initializer=init) as pool:
        for future in as_completed([pool.submit(job,gid,families,gid in p['game_ids'][:2],sig) for gid in pending]):
            r=future.result();done+=1;print('C06 legal games',done,'/',len(ids),'elapsed',round(time.monotonic()-start,1),'seconds',r['seconds_by_arm'],flush=True)
    result={'games':len(ids),'families':families,'sources':sig,'seconds':time.monotonic()-start,'production_changed':False}
    if stage!='wiring':result.update(summarise(ids,families))
    create_json(out,result);create_json(ROOT/f'analysis/experiments/20261126_c06_{stage}_v1.json',result);return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['wiring','short','final']);p.add_argument('--jobs',type=int,default=10);a=p.parse_args()
    if not 1<=a.jobs<=10:raise ContractError('actor worker budget')
    run(a.stage,a.jobs)
