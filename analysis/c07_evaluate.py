"""Returned1000world expert laws and frozen native/pool selection decisions."""
from __future__ import annotations
import argparse,sys,time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from analysis import c07_data as data,c07_members as members,c07_model as model,c07_score as score,c01_metrics as metrics
from analysis.c07_core import pool
from analysis.c05_compare import interval
from analysis.c01_workbench import read,create_json
from analysis.c01_core import ContractError
from basketball_common import sha256_file


def signature():return {p:sha256_file(ROOT/p) for p in ('analysis/c07_evaluate.py','analysis/c07_model.py','analysis/c07_score.py','analysis/c07_core.py')}|{'fit':sha256_file(data.WORK/'fit.json')}


def forecasts(gid,families,predictor=None):
    pred=predictor or members.STATE['gates'];a={k:members.load(gid,k) for k in ('N','H','V','R') if (members.path(gid,k)/'receipt.json').exists()};out={'native':{**a['N'],'weight':np.full(1000,.001)}}
    for f in ['pool',*families]:
        if f=='C':out[f]={**members.load(gid,'C'),'weight':np.full(1000,.001)}
        else:
            if f=='B' and set(a)!=set(('N','H','V','R')):raise ContractError('team expert members missing')
            mass=pred.masses(gid,f);out[f]=pool({k:a[k] for k in ('N','H','V','R') if k in a},mass if len(a)==4 else mass[[0,3]],gid)
    return out


def evaluate_game(gid,families):
    folder=data.WORK/'forecasts'/gid;sig=signature()
    if (folder/'receipt.json').exists():
        r=read(folder/'receipt.json')
        if r['sources']!=sig or any(sha256_file(folder/k)!=v for k,v in r['hashes'].items()):raise ContractError('returned expert artifact/source changed')
        if set(families)-set(r['families']):raise ContractError('missing returned expert family')
        return
    if folder.exists():raise ContractError('retain partial returned expert stage')
    folder.mkdir(parents=True);a=forecasts(gid,families);hashes={}
    for f,x in a.items():
        with (folder/f'{f}.npz').open('xb') as stream:np.savez_compressed(stream,**x)
        hashes[f'{f}.npz']=sha256_file(folder/f'{f}.npz')
    rows,joint=score.score_game(gid,a)
    for name,frame in [('scores.parquet',rows),('joint.parquet',joint)]:frame.to_parquet(folder/name,index=False);hashes[name]=sha256_file(folder/name)
    r={'game_id':gid,'families':list(a),'sources':sig,'hashes':hashes,'worlds_per_model':1000,'mass_and_conservation_checked':True,'member_names':[k for k in ('N','H','V','R') if (members.path(gid,k)/'receipt.json').exists()],'mixture_masses':{f:members.STATE['gates'].masses(gid,f).tolist() for f in a if f in ('A','B','pool')}};create_json(folder/'receipt.json',r)


def coverage(ref,cand,count=7):
    keys=['game_id','entity','stat','player','side'];r=ref.set_index(keys).sort_index();c=cand.set_index(keys).sort_index()
    if not r.index.equals(c.index):raise ContractError('coverage support differs')
    x=r.reset_index()[['game_id','date_et']];x['r']=r.covered80.to_numpy();x['c']=c.covered80.to_numpy();g=x.groupby('game_id',sort=True).agg(r=('r','sum'),c=('c','sum'),n=('r','size'),date=('date_et','first'))
    def boot(ra,ca,den):
        n=len(den);w=np.random.default_rng(20261125).multinomial(n,[1/n]*n,size=10000);z=abs(w@ca/(w@den)-.8)-abs(w@ra/(w@den)-.8);return np.quantile(z,[.05/(2*count),1-.05/(2*count)]).tolist()
    _,code=np.unique(pd.to_datetime(g.date).map(lambda d:d.date().toordinal()//7),return_inverse=True)
    return {'change':float(abs(c.covered80.mean()-.8)-abs(r.covered80.mean()-.8)),'familywise_game':boot(g.r.to_numpy(),g.c.to_numpy(),g.n.to_numpy()),'familywise_week':boot(np.bincount(code,weights=g.r),np.bincount(code,weights=g.c),np.bincount(code,weights=g.n))}


def summarise(ids,families,full):
    rows=pd.concat([pd.read_parquet(data.WORK/'forecasts'/g/'scores.parquet') for g in ids]);joint=pd.concat([pd.read_parquet(data.WORK/'forecasts'/g/'joint.parquet') for g in ids]);contract=read(data.CONTRACT);limits=contract['harm_limits'];report={'games':len(ids),'models':{},'comparisons':{},'eligible':{}}
    for f,q in rows.groupby('model'):report['models'][f]={f'{ent}/{stat}':{'rows':len(v),'crps':float(v.crps.mean()),'mae':float(v.absolute_error.mean()),'bias':float(v.bias.mean()),'half1':float(v.crps_half1.mean()),'half2':float(v.crps_half2.mean()),**{f'coverage{k}':float(v[f'covered{k}'].mean()) for k in (50,80,95)}} for (ent,stat),v in q.groupby(['entity','stat'])}
    for f in [*families,'pool']:
        q=rows[rows.model.eq(f)];comparisons={};checks={}
        def upper(z):return max(z['familywise_game'][1],z['familywise_week'][1]) if full else z['change']
        for baseline in (['native'] if f=='pool' else ['native','pool']):
            r=rows[rows.model.eq(baseline)];changes={};critical={};cov={}
            for (ent,stat),c in q.groupby(['entity','stat']):
                ref=r[r.entity.eq(ent)&r.stat.eq(stat)];key=f'{ent}/{stat}';pair=metrics.paired_frame(ref,c);z=interval(pair,7);z['equal_game_change']=float(pair.groupby('game_id').change.mean().mean());changes[key]=z
                if ent=='player' and stat in ('pts','fg3m'):
                    cr=ref[ref.role.eq('star')];cc=c[c.role.eq('star')];cz=interval(metrics.paired_frame(cr,cc),7);cz.update(relative_change=cz['change']/cr.crps.mean(),relative_upper=max(cz['familywise_game'][1],cz['familywise_week'][1])/cr.crps.mean(),context_support=cz['games']>=30 and len(cr)>=200);critical[stat]=cz
                if key in ('player/min','player/pts','team/points','game/total','game/margin'):cov[key]=coverage(ref,c)
            base=report['models'][baseline]['player/pts'];cand=report['models'][f]['player/pts'];relative=changes['player/pts']['change']/base['crps'];j=joint[joint.model.eq(f)].set_index('game_id').sort_index();jr=joint[joint.model.eq(baseline)].set_index('game_id').sort_index();jc={field:interval(j[['date_et']].assign(game_id=j.index,change=j[field]-jr[field]).reset_index(drop=True),7) for field in ('win_brier','energy','win_log_loss_smoothed')}
            if baseline=='native':
                checks['primary']=relative<=(-.01 if full else -.005) and (not full or upper(changes['player/pts'])<0);checks['halves']=all(cand[f'half{k}']<base[f'half{k}'] for k in (1,2))
                for key in ('team/points','game/total','game/margin','player/min','player/reb','player/ast','player/fg3m'):checks[key]=upper(changes[key])<=limits[key]
                for stat,z in critical.items():checks[f'critical/{stat}']=(z['context_support'] and z['relative_upper']<=.02) if full else z['relative_change']<=.02
                checks['coverage80']=all(upper(z)<=.03 for z in cov.values());checks['win_brier']=upper(jc['win_brier'])<=.01;checks['energy']=jc['energy']['change']<=.15;checks['population']=len(ids)>=100 if full else True
            elif full:
                checks['learned_pool_gain']=relative<=-.0025 and upper(changes['player/pts'])<0
            comparisons[baseline]={'changes':changes,'critical':critical,'coverage80':cov,'joint':jc,'player_pts_relative_change':relative}
        if full and f=='pool':checks['shortlist']='pool' in read(data.WORK/'short_decision.json')['shortlist']
        if f!='pool':checks['converged']=read(data.WORK/'fit.json')['training'][f]['converged']
        report['comparisons'][f]=comparisons;report['eligible'][f]={'eligible':bool(all(checks.values())),'checks':{k:bool(v) for k,v in checks.items()}}
    learned=sorted([f for f in families if report['eligible'][f]['eligible']],key=lambda f:report['comparisons'][f]['native']['player_pts_relative_change'])[:2];report['shortlist']=learned+(['pool'] if report['eligible']['pool']['eligible'] else []);return report


def run(stage,jobs=10):
    p=data.verify();fit=read(data.WORK/'fit.json');families=[f for f in 'ABC' if fit['training'][f]['converged']]
    if stage=='final':
        selected=read(data.WORK/'short_decision.json')['shortlist']
        if not selected:raise ContractError('no qualified expert: expansion forbidden')
        families=[f for f in selected if f!='pool']
    ids=p['eval_ids'][:2] if stage=='wiring' else p['eval_ids'][:20] if stage=='short' else p['eval_ids'];out=data.WORK/f'{stage}_decision.json'
    if out.exists():raise FileExistsError(out)
    if stage=='wiring':members.run('wiring',jobs)
    else:
        arms=['N','R']+(['H','V'] if 'B' in families else [])+(['C'] if 'C' in families else []);plan=data.WORK/f'{stage}_generation_plan.json';sig={a:members.signature(a) for a in arms}
        if plan.exists():
            if read(plan)['sources']!=sig:raise ContractError('expert stage source changed')
        else:create_json(plan,{'game_ids':ids,'arms':arms,'sources':sig})
        used=sum(read(f)['new_worlds'] for f in (data.WORK/'members').glob('*/*/receipt.json'));upper=used+1000*sum(not (members.path(g,a)/'receipt.json').exists() for g in ids for a in arms if a!='N')
        if upper>802000:raise ContractError('expert generation budget would exceed replay reserve')
        start=time.monotonic()
        with ProcessPoolExecutor(max_workers=jobs,initializer=members.init) as executor:
            for k,done in enumerate(as_completed([executor.submit(members.job,gid,arms) for gid in ids]),1):done.result();print('C07',stage,k,'/',len(ids),'seconds',round(time.monotonic()-start,1),flush=True)
    members.init()
    for i,gid in enumerate(ids):
        evaluate_game(gid,list('ABC') if stage=='wiring' else families)
        if (i+1)%20==0:print('C07 returned laws scored',i+1,'/',len(ids),flush=True)
    r={'games':len(ids),'training_converged_slate':families,'sources':signature(),'production_changed':False}
    if stage!='wiring':r.update(summarise(ids,families,stage=='final'))
    create_json(out,r);create_json(ROOT/f'analysis/experiments/20261126_c07_{stage}_v1.json',r);return r

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['wiring','short','final']);p.add_argument('--jobs',type=int,default=10);a=p.parse_args();run(a.stage,a.jobs)
