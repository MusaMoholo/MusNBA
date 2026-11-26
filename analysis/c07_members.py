"""Resumable coherent N/H/V/R/player-gated event members; immutable per-arm receipts."""
from __future__ import annotations
import argparse,sys,time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from analysis import c07_data as data,c05_rollout as old,c05_models as roles,c02_rollout as engine,c01_contexts as context
from analysis.c04_core import legal
from analysis.c05_core import schedule
from analysis.c07_core import seed
from analysis.c01_workbench import read,create_json
from analysis.c01_core import ContractError
from basketball_common import sha256_file
STATE={}


def signature(arm):
    r={'data':sha256_file(data.WORK/'data.json'),'generator':sha256_file(Path(__file__))}
    if arm=='C':r.update(gates=sha256_file(data.WORK/'fit.json'),model=sha256_file(ROOT/'analysis/c07_model.py'))
    return r


def path(gid,arm):return data.WORK/'members'/gid/arm

def load(gid,arm):
    folder=path(gid,arm);r=read(folder/'receipt.json')
    if r['sources']!=signature(arm) or sha256_file(folder/'worlds.npz')!=r['sha256']:raise ContractError('C07 member artifact/source changed')
    with np.load(folder/'worlds.npz',allow_pickle=False) as z:return {k:z[k] for k in z.files}


def init():
    old.init();STATE['refs']={r['game_id']:r for r in data.verify()['references']}
    if (data.WORK/'fit.json').exists():
        from analysis.c07_model import Predictor
        STATE['gates']=Predictor()


def native(ref):
    a=old.native(ref)
    with np.load(ROOT/ref['capture'],allow_pickle=False) as z:
        for stat,key in [('ftm','player_ftm'),('oreb','player_oreb'),('dreb','player_dreb'),('pf','player_fouls')]:a[stat]=z[key][:1000].sum(2)
    numerator=a['pts']-a['fg3m']-a['ftm']
    if (numerator<0).any() or (numerator%2).any():raise ContractError('native scoring identity derivation failed')
    a['fgm']=numerator//2
    return a


def draws(gid):
    source=roles.WORK/'minute_draws'/f'{gid}.npz';r=read(roles.WORK/'minute_screen.json')
    if sha256_file(source)!=r['draw_hashes'][gid]:raise ContractError('role minute law changed')
    with np.load(source,allow_pickle=False) as z:return z['native'],z['C']


def generate(gid,arm,fresh_gate=None):
    ref=STATE['refs'][gid];s=engine.STATE
    if arm=='N':return native(ref),0,{'retained_native':True}
    previous=roles.WORK/'games'/gid
    if arm=='R' and (previous/'C.npz').exists():
        r=read(previous/'receipt.json')
        if sha256_file(previous/'C.npz')!=r['hashes']['C.npz']:raise ContractError('retained C05 member changed')
        with np.load(previous/'C.npz',allow_pickle=False) as z:return {k:z[k] for k in z.files},0,{'retained_C05_R':True}
    g=context.make_game(ref,s['pre'],s['teams']);tables,combo,error=context.stored_schedules(ROOT/ref['capture']);n,r=draws(gid);target=r.copy();selected=(0,1) if arm in ('R','C') else (0,) if arm=='H' else (1,)
    if arm=='C':
        gate=(fresh_gate or STATE['gates']).player_prob(gid);pick=np.random.default_rng(seed(gid,'player-gates')).random(n.shape)<gate[None,:];target=np.where(pick,r,n)
        for side in (0,1):
            ids=np.flatnonzero(g.side==side);target[:,ids]=roles.quantise(legal(target[:,ids]))
    out=np.empty((2000,2880,5),np.int16);maximum=0.
    for side in (0,1):
        ids=np.flatnonzero(g.side==side)
        for w in range(1000):
            original=tables[combo[w,side]]
            if side in selected:
                pref=np.stack([(original==pid).any(1) for pid in ids]).astype(float);tab=ids[schedule(target[w,ids],pref)];maximum=max(maximum,max(abs(np.array([(tab==pid).sum()/60 for pid in ids])-target[w,ids])))
            else:tab=original
            out[2*w+side]=tab
        if side in selected:g.expected[ids]=target[:,ids].mean(0)
    comb=np.column_stack([2*np.arange(1000),2*np.arange(1000)+1]);g.lineup_tables=lambda available,rng,fit_offsets=None:(out,comb);e=s['engine'];e.world_observer=context.ZoneObserver();e.simulate(g,1000,engine.seed(gid));a=engine.capture_arrays(g,e.last)
    return a,1000,{'scheduled_target_error_max':float(maximum),'selected_role_sides':list(selected),'stored_schedule_error':error}


def job(gid,arms):
    receipts=[]
    for arm in arms:
        folder=path(gid,arm)
        if (folder/'receipt.json').exists():load(gid,arm);receipts.append(read(folder/'receipt.json'));continue
        if folder.exists():raise ContractError('retain/inspect partial expert member')
        folder.mkdir(parents=True);start=time.monotonic();a,new,info=generate(gid,arm)
        from analysis.c07_score import check_worlds
        check_worlds(a)
        with (folder/'worlds.npz').open('xb') as stream:np.savez_compressed(stream,**a)
        r={'game_id':gid,'arm':arm,'new_worlds':new,'seconds':time.monotonic()-start,'sources':signature(arm),'sha256':sha256_file(folder/'worlds.npz'),'accounting_passed':True,**info};create_json(folder/'receipt.json',r);receipts.append(r)
    return receipts


def run(stage,jobs):
    p=data.verify();ids=p['train_ids'] if stage=='train' else p['eval_ids'][:2] if stage=='wiring' else p['eval_ids'][:20] if stage=='short' else p['eval_ids'];arms=list('N H V R'.split()) if stage=='train' else ['N','H','V','R','C']
    if stage=='final':
        decision=read(data.WORK/'short_decision.json')
        if not decision['shortlist']:raise ContractError('no qualified expert: expansion forbidden')
        if 'C' not in decision['shortlist']:arms.remove('C')
    out=data.WORK/f'{stage}_members.json'
    if out.exists():raise FileExistsError(out)
    sig={a:signature(a) for a in arms};plan=data.WORK/f'{stage}_members_plan.json'
    if plan.exists():
        if read(plan)['sources']!=sig:raise ContractError('expert resume sources changed')
    else:create_json(plan,{'game_ids':ids,'arms':arms,'sources':sig})
    start=time.monotonic();done=0
    with ProcessPoolExecutor(max_workers=jobs,initializer=init) as pool:
        for future in as_completed([pool.submit(job,gid,arms) for gid in ids]):
            r=future.result();done+=1;print('C07',stage,'members',done,'/',len(ids),'seconds',round(time.monotonic()-start,1),'new_worlds',sum(x['new_worlds'] for x in r),flush=True)
    receipts=[read(path(g,a)/'receipt.json') for g in ids for a in arms];total=sum(read(f)['new_worlds'] for f in (data.WORK/'members').glob('*/*/receipt.json'))
    if total>802000:raise ContractError('expert world budget reserved replay limit exceeded')
    result={'games':len(ids),'arms':arms,'new_worlds_in_stage_members':sum(r['new_worlds'] for r in receipts),'total_unique_member_new_worlds':total,'seconds':time.monotonic()-start,'sources':sig};create_json(out,result);create_json(ROOT/f'analysis/experiments/20261126_c07_{stage}_members_v1.json',result);return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','train','wiring','short','final']);p.add_argument('--jobs',type=int,default=10);a=p.parse_args()
    if not 1<=a.jobs<=10:raise ContractError('expert thread budget')
    data.prepare() if a.stage=='prepare' else run(a.stage,a.jobs)
