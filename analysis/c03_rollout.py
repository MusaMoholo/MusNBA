"""Resumable C03 paired legal event worlds, with common control and frozen shortlist."""
from __future__ import annotations
import argparse,sys,time
from pathlib import Path
from contextlib import nullcontext
from concurrent.futures import ProcessPoolExecutor,as_completed
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from analysis import c03_data as data,c03_model as model,c03_evaluate as ev,c02_rollout as old,c01_contexts as context,c01_metrics as metrics
from analysis.c02_features import View
from analysis.c03_runtime import attached
from analysis.c01_workbench import read,create_json
from analysis.c01_core import ContractError
from basketball_common import sha256_file
STATE={}

def signature():
    paths=[ROOT/'analysis'/f'c03_{n}.py' for n in ('choices','data','model','runtime','rollout','evaluate')]+[data.CONTRACT,data.WORK/'data.json']+[data.WORK/'models'/f/'fit.json' for f in 'ABC']
    return {'c03_sources':{str(p.relative_to(ROOT)):sha256_file(p) for p in paths},'reused_c02_runtime':old.signature()}

def init():
    old.init();STATE['predictors']={f:model.Predictor(f) for f in 'ABC'}

def generate(gid,arms=('control','A','B','C'),worlds=1000):
    s=old.STATE;ref=s['refs'][gid]
    if sha256_file(ROOT/ref['capture'])!=ref['capture_sha256']:raise ContractError('stored rotation capture changed')
    g=context.make_game(ref,s['pre'],s['teams']);tables,combo,error=context.stored_schedules(ROOT/ref['capture']);g.lineup_tables=lambda available,rng,fit_offsets=None:(tables,combo[:worlds])
    view=View(g,s['causal'],s['causal_teams']);e=s['engine'];out={};counts={};times={}
    for arm in arms:
        e.world_observer=context.ZoneObserver();scope=nullcontext({}) if arm=='control' else attached(e,g,view,STATE['predictors'][arm]);start=time.monotonic()
        with scope as used:e.simulate(g,worlds,old.seed(gid));out[arm]=old.capture_arrays(g,e.last);counts[arm]=dict(used)
        times[arm]=time.monotonic()-start
        if arm!='control' and min(counts[arm].values())<=0:raise ContractError('unused C03 choice head')
    return out,counts,times,error

def job(gid,arms):
    folder=data.WORK/'rollout'/gid;folder.mkdir(parents=True,exist_ok=False)
    arrays,counts,times,error=generate(gid,arms);hashes={}
    for arm,a in arrays.items():
        path=folder/f'{arm}.npz';data.save(path,a);hashes[path.name]=sha256_file(path)
    # The frozen incumbent seed/path should reproduce the compatible retained control.
    previous=old.WORK/'rollout'/gid/'control.npz'
    if previous.exists():
        with np.load(previous,allow_pickle=False) as z:
            if any(not np.array_equal(z[k],arrays['control'][k]) for k in z.files):raise ContractError('common control differs from retained C02')
    scores,joints=old.score_arrays(gid,arrays)
    for name,f in [('scores.parquet',scores),('joint.parquet',joints)]:f.to_parquet(folder/name,index=False);hashes[name]=sha256_file(folder/name)
    r={'game_id':gid,'arms':list(arms),'worlds_per_arm':1000,'head_calls':counts,'seconds_by_arm':times,'hashes':hashes,'legal_event_accounting_passed':True,'schedule_discretisation_minutes':error}
    create_json(folder/'receipt.json',r);return r

def summarise(ids,families):
    scores=pd.concat([pd.read_parquet(data.WORK/'rollout'/g/'scores.parquet') for g in ids],ignore_index=True)
    joints=pd.concat([pd.read_parquet(data.WORK/'rollout'/g/'joint.parquet') for g in ids],ignore_index=True)
    result={'games':len(ids),'models':{},'changes':{},'joint':{},'contexts':{},'runtime':{},'eligible':{}}
    c=read(data.CONTRACT);limits=c['shortlist']['harms'];control=scores[scores.model.eq('control')]
    for family in ['control',*families]:
        f=scores[scores.model.eq(family)];result['models'][family]={f'{ent}/{stat}':{'rows':len(q),'crps':float(q.crps.mean()),'bias':float(q.bias.mean()),'mae':float(q.absolute_error.mean()),'coverage80':float(q.covered80.mean()),'width80':float(q.width80.mean()),'half1':float(q.crps_half1.mean()),'half2':float(q.crps_half2.mean())} for (ent,stat),q in f.groupby(['entity','stat'])}
    for family in families:
        f=scores[scores.model.eq(family)];changes={};checks={};contexts={}
        for (ent,stat),q in f.groupby(['entity','stat']):
            ref=control[control.entity.eq(ent)&control.stat.eq(stat)];key=f'{ent}/{stat}';changes[key]=ev.interval(metrics.paired_frame(ref,q))
            if ent=='player' and stat in ('pts','fg3m'):
                for field in ('role','minute_band','side'):
                    for label,ctx in q.groupby(field):
                        b=ev.interval(metrics.paired_frame(ref[ref[field].eq(label)],ctx));b['context_support']=b['games']>=30 and len(ctx)>=200;contexts[f'{stat}/{field}/{label}']=b
                cq=q[q.role.eq('star')];cr=ref[ref.role.eq('star')];b=ev.interval(metrics.paired_frame(cr,cq));base=cr.crps.mean();b['relative_change']=b['change']/base;b['relative_familywise_upper']=max(b['familywise_game'][1],b['familywise_week'][1])/base;b['context_support']=b['games']>=30 and len(cq)>=200;contexts[f'critical/{stat}']=b
        j=joints[joints.model.eq(family)].set_index('game_id').sort_index();jr=joints[joints.model.eq('control')].set_index('game_id').sort_index();joint={}
        for field in ('win_brier','energy','win_log_loss_smoothed'):
            joint[field]=ev.interval(j[['date_et']].assign(game_id=j.index,change=j[field]-jr[field]).reset_index(drop=True))
        # Point promise on20; familywise confidence requirements only on expanded200.
        full=len(ids)==200
        def upper(r):return max(r['familywise_game'][1],r['familywise_week'][1]) if full else r['change']
        primary=changes['player/pts'];base=result['models']['control']['player/pts'];cand=result['models'][family]['player/pts'];gain=primary['change']/base['crps']
        checks['primary']=gain<=(-.01 if full else -.005) and (not full or upper(primary)<0)
        checks['halves']=cand['half1']<base['half1'] and cand['half2']<base['half2']
        for key,lim in [('team/points',limits['team_points_crps']),('game/total',limits['game_total_crps']),('game/margin',limits['game_margin_crps']),*[(f'player/{s}',limits[f'player_{s}_crps']) for s in ('min','reb','ast','fg3m')]]:checks[key]=upper(changes[key])<=lim
        checks['win_brier']=upper(joint['win_brier'])<=limits['win_brier']
        for stat in ('pts','fg3m'):
            b=contexts[f'critical/{stat}'];checks[f'critical/{stat}']=(b['context_support'] and b['relative_familywise_upper']<=limits[f'critical_{stat}_relative_crps']) if full else b['relative_change']<=limits[f'critical_{stat}_relative_crps']
        checks['coverage80']=all(abs(result['models'][family][key]['coverage80']-result['models']['control'][key]['coverage80'])<=limits['coverage80_absolute_change'] for key in ('player/pts','team/points','game/total','game/margin'))
        timings=[read(data.WORK/'rollout'/g/'receipt.json')['seconds_by_arm'] for g in ids];ratio=float(np.median([t[family]/t['control'] for t in timings]));checks['runtime']=ratio<=8
        result['changes'][family]=changes;result['joint'][family]=joint;result['contexts'][family]=contexts;result['runtime'][family]={'median_control_ratio':ratio,'median_seconds':float(np.median([t[family] for t in timings]))};result['eligible'][family]={'eligible':bool(all(checks.values())),'checks':{k:bool(v) for k,v in checks.items()},'player_pts_relative_change':gain}
    result['shortlist']=sorted([f for f in families if result['eligible'][f]['eligible']],key=lambda f:result['eligible'][f]['player_pts_relative_change'])[:2]
    result['known_development_only']=True;result['production_changed']=False;return result

def run(stage,jobs=10):
    data.verify();sig=signature();p=read(data.WORK/'data.json');ids=p['game_ids'][:20] if stage=='mvp' else p['game_ids'][20:];families=list('ABC') if stage=='mvp' else read(data.WORK/'mvp.json')['shortlist']
    if not families:raise ContractError('no finalists: expansion forbidden')
    plan=data.WORK/f'{stage}_plan.json';out=data.WORK/f'{stage}.json'
    if out.exists():raise FileExistsError(out)
    if not plan.exists():create_json(plan,{'sources':sig,'game_ids':ids,'arms':['control',*families],'worlds':1000})
    elif read(plan)['sources']!=sig:raise ContractError('C03 resume source changed')
    pending=[];done=0;start=time.monotonic()
    for gid in ids:
        folder=data.WORK/'rollout'/gid
        if (folder/'receipt.json').exists():
            r=read(folder/'receipt.json')
            if any(sha256_file(folder/n)!=h for n,h in r['hashes'].items()):raise ContractError('C03 completed game changed')
            done+=1
        elif folder.exists():raise ContractError('inspect partial C03 game before technical rerun')
        else:pending.append(gid)
    with ProcessPoolExecutor(max_workers=jobs,initializer=init) as pool:
        for future in as_completed([pool.submit(job,gid,('control',*families)) for gid in pending]):
            r=future.result();done+=1;print('C03 legal games',done,'/',len(ids),'seconds',round(time.monotonic()-start,1),'arm_seconds',r['seconds_by_arm'],flush=True)
    allids=p['game_ids'][:20] if stage=='mvp' else p['game_ids'];result=summarise(allids,families);result['sources']=sig;result['seconds']=time.monotonic()-start;create_json(out,result);create_json(ROOT/f'analysis/experiments/20261125_c03_{stage}_v1.json',result)
    print('Shortlist',result['shortlist'],result['eligible'],flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['mvp','finalists']);p.add_argument('--jobs',type=int,default=10);a=p.parse_args()
    if not 1<=a.jobs<=10:raise ContractError('C03 worker budget')
    run(a.stage,a.jobs)
