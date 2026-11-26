"""Joint-role forecasts through a shared legal rotation decoder and fixed event engine."""
from __future__ import annotations
import argparse,sys,time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from analysis import c05_data as data,c05_models as models,c05_screen as screen,c02_rollout as old,c01_contexts as context,c01_metrics as metrics
from analysis.c04_core import legal
from analysis.c01_workbench import read,create_json
from analysis.c01_core import ContractError
from basketball_common import sha256_file
from scripts.rotation_fit import independent
STATE={}

def signature():
    return {'sources':{f'analysis/c05_{n}.py':sha256_file(ROOT/f'analysis/c05_{n}.py') for n in ('core','data','models','screen','rollout','compare')},'data':sha256_file(models.data.WORK/'data.json'),'fits':sha256_file(data.WORK/'fit.json'),'minute_screen':sha256_file(data.WORK/'minute_screen.json'),'fixed_engine':old.signature()}

def init():
    old.init();STATE['rows']=pd.read_parquet(models.data.WORK/'rows.parquet');STATE['models']={f:models.Predictor(f) for f in 'ABC'}

def native(ref):
    if sha256_file(ROOT/ref['capture'])!=ref['capture_sha256']:raise ContractError('native reference changed')
    with np.load(ROOT/ref['capture'],allow_pickle=False) as z:
        a={'player_ids':z['player_ids'],'side':z['side'],'minutes':z['minutes'][:1000].sum(2),'team':z['team_points'][:1000].sum(2),'final_period':z['final_period'][:1000]}
        for stat,key in [('pts','player_points'),('ast','player_ast'),('fg3m','player_fg3m'),('fga','player_fga'),('fg3a','player_fg3a'),('fta','player_fta')]:a[stat]=z[key][:1000].sum(2)
        a['reb']=(z['player_oreb'][:1000]+z['player_dreb'][:1000]).sum(2)
    for s in (0,1):
        if not np.array_equal(a['pts'][:,a['side']==s].sum(1),a['team'][:,s]):raise ContractError('native player/team identity')
    return a

def decoder(g,tables,combo,targets):
    from analysis.c05_core import schedule
    W=len(targets);out=np.empty((2*W,2880,5),np.int16);errors=[]
    for side in (0,1):
        ids=np.flatnonzero(g.side==side)
        for w in range(W):
            original=tables[combo[w,side]];pref=np.stack([(original==pid).any(1) for pid in ids]).astype(float)
            tab=ids[schedule(targets[w,ids],pref)];out[2*w+side]=tab
            realised=np.array([(tab==pid).sum()/60 for pid in ids]);errors.extend(abs(realised-targets[w,ids]))
    err=np.array(errors)
    return out,np.column_stack([2*np.arange(W),2*np.arange(W)+1]),{'mean_absolute_minutes':float(err.mean()),'p95_absolute_minutes':float(np.quantile(err,.95)),'max_absolute_minutes':float(err.max())}

def generate(gid,arms=('bridge','A','B','C'),fresh=None):
    s=old.STATE;ref=s['refs'][gid];g=context.make_game(ref,s['pre'],s['teams']);tables,combo,source_error=context.stored_schedules(ROOT/ref['capture']);out={'native':native(ref)};times={};fits={}
    path=data.WORK/'minute_draws'/f'{gid}.npz';plan=read(data.WORK/'minute_screen.json')
    if sha256_file(path)!=plan['draw_hashes'][gid]:raise ContractError('joint-minute draw cache changed')
    with np.load(path,allow_pickle=False) as z:draws={k:z[k] for k in ('native','A','B','C')}
    for arm in arms:
        started=time.monotonic();target=draws['native' if arm=='bridge' else arm]
        if fresh is not None and arm!='bridge':
            part=STATE['rows'][STATE['rows'].game_id.eq(gid)].set_index('player').loc[g.ids].reset_index();target=np.zeros_like(target)
            for side in (0,1):
                take=np.flatnonzero(g.side==side);target[:,take]=fresh[arm].draw(part.iloc[take],1000,np.random.default_rng(screen.seed(gid,side)))
            if not np.array_equal(target,draws[arm]):raise ContractError('fresh joint-minute draws differ')
        tab,comb,error=decoder(g,tables,combo,target);g.expected=target.mean(0);g.lineup_tables=lambda available,rng,fit_offsets=None:(tab,comb)
        e=s['engine'];e.world_observer=context.ZoneObserver();e.simulate(g,1000,old.seed(gid));a=old.capture_arrays(g,e.last);a['target_minutes']=target;a['scheduled_minutes']=np.stack([(tab[comb[:,g.side[i]]]==i).sum((1,2))/60 for i in range(g.n)],axis=1);out[arm]=a;fits[arm]=error;times[arm]=time.monotonic()-started
    return out,times,fits,source_error

def score(gid,arrays):
    s=old.STATE;ref=s['refs'][gid];box=s['box'][gid].copy();box['player']=box.athlete_id.astype('int64').astype(str);box=box.set_index('player');on=s['on'][gid].set_index('player').sec;prior=s['causal'][s['causal'].game_id.eq(gid)].set_index('player');truth=np.array([ref['official_points'][ref[k]] for k in ('home','away')],float);rows=[];joint=[];common={'game_id':gid,'date_et':ref['date_et']}
    for arm,a in arrays.items():
        t=a['team'];joint.append({**common,'model':arm,**metrics.joint_record(t,truth)})
        for ent,stat,side,x,y in [('team','points','home',t[:,0],truth[0]),('team','points','away',t[:,1],truth[1]),('game','total','both',t.sum(1),truth.sum()),('game','margin','both',t[:,0]-t[:,1],truth[0]-truth[1])]:rows.append({**common,'model':arm,'entity':ent,'stat':stat,'player':'','side':side,'role':'all',**metrics.scalar_record(x,y)})
        for i,pid in enumerate(a['player_ids']):
            p=prior.loc[pid];role='unknown' if not np.isfinite([p.usage,p.start_share]).all() else 'star' if p.usage>=.25 else 'starter' if p.start_share>=.5 else 'bench'
            for stat,col in [('min',None),('pts','points'),('reb','rebounds'),('ast','assists'),('fg3m','three_point_field_goals_made')]:
                y=float(on[pid])/60 if col is None else float(box.loc[pid,col]);x=a['minutes' if stat=='min' else stat][:,i];rows.append({**common,'model':arm,'entity':'player','stat':stat,'player':pid,'side':str(a['side'][i]),'role':role,**metrics.scalar_record(x,y)})
    return pd.DataFrame(rows),pd.DataFrame(joint)

def job(gid,arms):
    folder=data.WORK/'games'/gid;folder.mkdir(parents=True,exist_ok=False);arrays,times,errors,source_error=generate(gid,arms);hashes={}
    for arm,a in arrays.items():
        with (folder/f'{arm}.npz').open('xb') as stream:np.savez_compressed(stream,**a)
        hashes[f'{arm}.npz']=sha256_file(folder/f'{arm}.npz')
    scores,joint=score(gid,arrays)
    for name,f in [('scores.parquet',scores),('joint.parquet',joint)]:f.to_parquet(folder/name,index=False);hashes[name]=sha256_file(folder/name)
    r={'game_id':gid,'arms':['native',*arms],'new_worlds':1000*len(arms),'worlds':1000,'seconds_by_arm':times,'decoder_fit_errors':errors,'stored_schedule_discretisation_minutes':source_error,'legal_event_boundaries_passed':True,'hashes':hashes};create_json(folder/'receipt.json',r);return r

def run(stage,jobs=10):
    from analysis.c05_compare import summarise
    data.verify();p=data.verify();minute=read(data.WORK/'minute_screen.json');sig=signature();out=data.WORK/f'{stage}.json';plan=data.WORK/f'{stage}_plan.json'
    if out.exists():raise FileExistsError(out)
    families=list('ABC') if stage=='wiring' else minute['shortlist'] if stage=='short' else read(data.WORK/'short.json')['shortlist'];ids=p['game_ids'][:2] if stage=='wiring' else p['game_ids'][:20] if stage=='short' else p['game_ids']
    if not families:raise ContractError('no eligible role model: expansion forbidden')
    if not plan.exists():create_json(plan,{'sources':sig,'game_ids':ids,'families':families})
    elif read(plan)['sources']!=sig:raise ContractError('role resume sources changed')
    pending=[];done=0;start=time.monotonic()
    for gid in ids:
        folder=data.WORK/'games'/gid
        if (folder/'receipt.json').exists():
            r=read(folder/'receipt.json')
            if any(sha256_file(folder/k)!=h for k,h in r['hashes'].items()):raise ContractError('completed role game changed')
            if set(families)-set(r['arms']):raise ContractError('stored role game lacks required family')
            done+=1
        elif folder.exists():raise ContractError('partial role game requires retained fault inspection')
        else:pending.append(gid)
    with ProcessPoolExecutor(max_workers=jobs,initializer=init) as pool:
        for future in as_completed([pool.submit(job,gid,('bridge',*families)) for gid in pending]):
            r=future.result();done+=1;print('C05 legal games',done,'/',len(ids),'elapsed',round(time.monotonic()-start,1),'seconds',r['seconds_by_arm'],'fit',r['decoder_fit_errors'],flush=True)
    result={'games':len(ids),'families':families,'sources':sig,'seconds':time.monotonic()-start,'known_development':True,'production_changed':False}
    if stage!='wiring':result.update(summarise(ids,families))
    create_json(out,result);create_json(ROOT/f'analysis/experiments/20261126_c05_{stage}_v1.json',result);return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['wiring','short','final']);p.add_argument('--jobs',type=int,default=10);a=p.parse_args()
    if not 1<=a.jobs<=10:raise ContractError('role worker budget')
    run(a.stage,a.jobs)
