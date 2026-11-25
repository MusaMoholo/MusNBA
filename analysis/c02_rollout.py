"""Fresh paired research worlds: unchanged control versus C02 possession heads."""
from __future__ import annotations
import argparse
from concurrent.futures import ProcessPoolExecutor,as_completed
from contextlib import nullcontext
import hashlib
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import pyarrow as pa
from analysis import c02_data as data,c01_contexts as context,c01_benchmark as bench,c01_metrics as metrics
from analysis.c02_features import View
from analysis.c02_model import Predictor
from analysis.c02_runtime import attached,validate_worlds
from analysis.c01_core import ContractError
from analysis.c01_workbench import read,create_json,read_panel,FEATURES,TEAMS
from basketball_common import sha256_file

WORK=data.WORK;STATE={}

def seed(gid):return int.from_bytes(hashlib.sha256(f'c02-possession-v1|{gid}|0'.encode()).digest()[:8],'little')

def signature():
    p=read(WORK/'data.json')
    sources={**p['sources'],**read(bench.WORK/'plan.json')['sources']}
    for path in ('analysis/c02_rollout.py','analysis/c02_runtime.py','analysis/c02_features.py','analysis/c02_model.py',
                 'scripts/engine.py','scripts/foul_out.py','scripts/rotation_fit.py','scripts/late_clock.py',context.CLOCK,context.CLOCK_REPORT):
        sources[path]=sha256_file(ROOT/path)
    for path in (WORK/'models/fit.json',WORK/'screen.json',WORK/'feature_parity.json'):
        sources[str(path.relative_to(ROOT))]=sha256_file(path)
    return sources

def init():
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    p=read(WORK/'data.json');ids=p['game_ids'];e,_=context.load_engine(ids)
    STATE.update(engine=e,predictor=Predictor(),refs={r['game_id']:r for r in p['references']},
        pre=read_panel(ROOT/FEATURES,ids),teams=read_panel(ROOT/TEAMS,ids),
        causal=read_panel(data.PROFILE,ids),causal_teams=read_panel(data.PROFILE.parent/'team_pregame.parquet',ids),
        box={g:f for g,f in pd.read_parquet(bench.WORK/'box.parquet').groupby('game_id')},
        on={g:f for g,f in pd.read_parquet(bench.WORK/'on.parquet').groupby('game_id')})

def capture_arrays(g,st):
    validate_worlds(g,st)
    a={'player_ids':np.asarray(g.ids),'side':g.side.copy(),'team':st.pts.sum(2).copy(),'minutes':st.minutes.sum(2).copy(),
       'final_period':st.period.copy(),'possessions':st.poss.copy()}
    for stat in ('pts','fgm','fga','fg3m','fg3a','ftm','fta','oreb','dreb','ast','tov','pf'):a[stat]=st.box[stat].sum(2).copy()
    a['reb']=a['oreb']+a['dreb'];return a


def generate(gid,worlds=1000,arms=('control','candidate')):
    ref=STATE['refs'][gid]
    if sha256_file(ROOT/ref['capture'])!=ref['capture_sha256']:raise ContractError('retained schedule input changed')
    g=context.make_game(ref,STATE['pre'],STATE['teams'])
    tables,combo,error=context.stored_schedules(ROOT/ref['capture']);g.lineup_tables=lambda available,rng,fit_offsets=None:(tables,combo[:worlds])
    view=View(g,STATE['causal'],STATE['causal_teams']);e=STATE['engine'];out={};counts={}
    for arm in arms:
        observer=context.ZoneObserver();e.world_observer=observer
        scope=attached(e,g,view,STATE['predictor']) if arm=='candidate' else nullcontext({'who':0,'what':0})
        with scope as used:
            e.simulate(g,worlds,seed(gid));out[arm]=capture_arrays(g,e.last);counts[arm]=dict(used)
        if arm=='candidate' and min(counts[arm].values())<=0:raise ContractError('candidate heads not exercised')
    return out,counts,error


def score_arrays(gid,arrays):
    ref=STATE['refs'][gid];box=STATE['box'][gid].copy();box['player']=box.athlete_id.astype('int64').astype(str);box=box.set_index('player')
    on=STATE['on'][gid].set_index('player').sec
    prior=STATE['causal'][STATE['causal'].game_id.eq(gid)].set_index('player');rows=[];joints=[]
    truth=np.array([ref['official_points'][ref[s]] for s in ('home','away')],float)
    common={'game_id':gid,'date_et':ref['date_et'],'month':ref['date_et'][:7],'population':'actual_participant_stored_simulated_schedule'}
    columns={'pts':'points','reb':'rebounds','ast':'assists','fg3m':'three_point_field_goals_made','fga':'field_goals_attempted','fg3a':'three_point_field_goals_attempted','fta':'free_throws_attempted','tov':'turnovers'}
    for arm,a in arrays.items():
        ids=a['player_ids'].tolist();side=a['side'];values=a['team']
        for entity,stat,label,x,y in [('team','points','home',values[:,0],truth[0]),('team','points','away',values[:,1],truth[1]),
             ('game','total','both',values.sum(1),truth.sum()),('game','margin','both',values[:,0]-values[:,1],truth[0]-truth[1])]:
            rows.append({**common,'model':arm,'entity':entity,'stat':stat,'player':'','side':label,'role':'all','minute_band':'all',**metrics.scalar_record(x,y)})
        joints.append({**common,'model':arm,**metrics.joint_record(values,truth)})
        for i,pid in enumerate(ids):
            p=prior.loc[pid];b=box.loc[pid]
            role='unknown' if not np.isfinite([p.usage,p.start_share]).all() else 'star' if p.usage>=.25 else 'starter' if p.start_share>=.5 else 'bench'
            band='unknown' if not np.isfinite(p.min_avg) else '<12' if p.min_avg<12 else '12-24' if p.min_avg<24 else '24+'
            for stat in ('min',*columns):
                y=float(on[pid])/60 if stat=='min' else float(b[columns[stat]])
                x=a['minutes'][:,i] if stat=='min' else a[stat][:,i]
                rows.append({**common,'model':arm,'entity':'player','stat':stat,'player':pid,'side':('home','away')[side[i]],'role':role,'minute_band':band,**metrics.scalar_record(x,y)})
    return pd.DataFrame(rows),pd.DataFrame(joints)


def job(gid):
    folder=WORK/'rollout'/gid;folder.mkdir(parents=True,exist_ok=False);started=time.monotonic()
    arrays,counts,error=generate(gid);hashes={}
    for arm,a in arrays.items():
        path=folder/f'{arm}.npz'
        with path.open('xb') as stream:np.savez_compressed(stream,**a)
        hashes[path.name]=sha256_file(path)
    rows,joints=score_arrays(gid,arrays)
    for name,f in (('scores.parquet',rows),('joint.parquet',joints)):
        f.to_parquet(folder/name,index=False);hashes[name]=sha256_file(folder/name)
    result={'game_id':gid,'worlds_per_arm':1000,'head_calls':counts,'seconds':time.monotonic()-started,
       'all_legal_and_scoring_boundaries_passed':True,'schedule_discretisation_minutes':error,'hashes':hashes,
       'scope':'fresh paired event worlds on identical stored simulated schedule; not original incumbent worlds',
       'rotation_note':'schedule/policy fixed; legal foul replacements can change realised minutes between arms'}
    create_json(folder/'receipt.json',result);return result


def summarise(ids):
    scores=pd.concat([pd.read_parquet(WORK/'rollout'/g/'scores.parquet') for g in ids],ignore_index=True)
    joints=pd.concat([pd.read_parquet(WORK/'rollout'/g/'joint.parquet') for g in ids],ignore_index=True)
    report={'models':{},'paired_changes':{},'contexts':{},'joint_changes':{}}
    for arm,f in scores.groupby('model'):
        report['models'][arm]={f'{entity}/{stat}':{'rows':len(q),'games':q.game_id.nunique(),**{k:float(q[k].mean()) for k in ('crps','absolute_error','bias','covered80','width80','crps_half1','crps_half2')}} for (entity,stat),q in f.groupby(['entity','stat'])}
    for (entity,stat),cand in scores[scores.model.eq('candidate')].groupby(['entity','stat']):
        control=scores[scores.model.eq('control')&scores.entity.eq(entity)&scores.stat.eq(stat)]
        pair=metrics.paired_frame(control,cand);key=f'{entity}/{stat}'
        report['paired_changes'][key]={'pooled':metrics.bootstrap_change(pair),'equal_game':metrics.bootstrap_change(pair,False)}
        if entity=='player' and stat in ('pts','fg3m'):
            report['contexts'][key]={}
            for field in ('role','minute_band','side'):
                for label,q in cand.groupby(field):
                    r=control[control[field].eq(label)];b=metrics.bootstrap_change(metrics.paired_frame(r,q));b['context_support']=b['games']>=30 and len(q)>=200
                    report['contexts'][key][f'{field}/{label}']=b
    a=joints[joints.model.eq('control')].set_index('game_id').sort_index();b=joints[joints.model.eq('candidate')].set_index('game_id').sort_index()
    for field in ('win_brier','win_log_loss_smoothed','energy'):
        report['joint_changes'][field]=metrics.bootstrap_change(b[['date_et']].assign(game_id=b.index,change=b[field]-a[field]).reset_index(drop=True))
    report['joint_means']={arm:{k:float(f[k].mean()) for k in ('win_brier','energy','covariance','win_log_loss_smoothed')} for arm,f in joints.groupby('model')}
    report['monte_carlo_half_sensitivity']={arm:metrics.bootstrap_change(f.assign(change=f.crps_half2-f.crps_half1)) for arm,f in scores[scores.entity.eq('player')&scores.stat.eq('pts')].groupby('model')}
    return report


def run(jobs=10):
    data.verify();screen=read(WORK/'screen.json');p=read(WORK/'data.json');ids=p['game_ids'] if screen['screen_passed'] else p['wiring_ids']
    plan_path=WORK/'rollout_plan.json';sig=signature()
    if not plan_path.exists():create_json(plan_path,{'sources':sig,'game_ids':ids,'worlds':1000,'screen_passed':screen['screen_passed'],'no_full_game_target_interface':True})
    elif read(plan_path)['sources']!=sig:raise ContractError('rollout source signature changed')
    if (WORK/'rollout.json').exists():raise FileExistsError('immutable rollout complete')
    done=[];pending=[];started=time.monotonic()
    for gid in ids:
        folder=WORK/'rollout'/gid
        if (folder/'receipt.json').exists():
            r=read(folder/'receipt.json')
            if any(sha256_file(folder/n)!=h for n,h in r['hashes'].items()):raise ContractError('rollout cache changed')
            done.append(r)
        elif folder.exists():raise ContractError('partial rollout game requires inspection')
        else:pending.append(gid)
    with ProcessPoolExecutor(max_workers=jobs,initializer=init) as pool:
        for future in as_completed([pool.submit(job,gid) for gid in pending]):
            r=future.result();done.append(r);print(f'Paired legal possession games {len(done)}/{len(ids)}; {time.monotonic()-started:.1f}s',flush=True)
    summary=summarise(ids)
    result={'kind':'C02 paired pure possession integration','games':len(ids),'worlds_per_game_per_arm':1000,'new_worlds':len(pending)*2000,'jobs':jobs,'inner_threads':1,
        'seconds':time.monotonic()-started,'summary':summary,'receipts':{r['game_id']:sha256_file(WORK/'rollout'/r['game_id']/'receipt.json') for r in done},
        'screen_passed':screen['screen_passed'],'accuracy_qualification':'Wiring only; failed recorded-context screen blocks full200 and promotion' if not screen['screen_passed'] else 'Development only; separate qualification required',
        'source_signature':sig,'production_changed':False,'no_full_game_targets_or_score_repairs':True}
    create_json(WORK/'rollout.json',result);create_json(ROOT/'analysis/experiments/20261125_c02_rollout_v1.json',result)
    print('Paired possession integration complete',len(ids),flush=True);return result

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('stage',choices=['preflight','run']);a.add_argument('--jobs',type=int,default=10);args=a.parse_args()
    if not 1<=args.jobs<=10:raise ContractError('worker count exceeds budget')
    if args.stage=='preflight':
        init();gid=read(WORK/'data.json')['wiring_ids'][0];arrays,counts,error=generate(gid,16)
        create_json(WORK/'preflight.json',{'game_id':gid,'worlds_per_arm':16,'head_calls':counts,'legal_accounting_passed':True,'no_accuracy_evidence':True,'sources':signature()})
        print('Preflight passes',counts,flush=True)
    else:run(args.jobs)
