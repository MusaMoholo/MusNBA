"""Matched conditional-actor proper scoring and the frozen full-history screen."""
from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from analysis import c06_data as data,c06_model as model,c01_contexts as context
from analysis.c03_data import unpack,subset
from analysis.c06_core import softmax,usage,check,CONTEXT,PLAYER
from analysis.c04_compare import interval
from analysis.c01_workbench import create_json,read
from analysis.c01_core import ContractError
from basketball_common import sha256_file


def incumbent(a):
    ids=read(data.WORK/'data.json')['game_ids'];chain,ds,_=context.load_chain(ids);e,_=context.load_engine(ids);d=ds['who'];groups=d['group'].reshape(-1,5)
    if not np.all(groups==groups[:,:1]):raise ContractError('incumbent actor group order')
    raw=e.m.boosters['who'].predict(d['X'][e.m.nodes['who']['columns']].to_numpy(np.float32),raw_score=True,num_threads=1);p=softmax(raw/float(e.m.nodes['who']['temperature']));keys=groups[:,0];index=pd.Series(np.arange(len(keys)),index=keys).reindex(a['seg_id'])
    if index.isna().any():raise ContractError('incumbent actor support differs')
    ix=index.to_numpy(int);labels=d['y'].reshape(-1,5)[ix]
    if not np.array_equal(labels.argmax(1),a['y']) or not np.all(labels.sum(1)==1):raise ContractError('independent source actor label/order differs')
    if d['X'].foul_event.to_numpy().reshape(-1,5)[ix].any():raise ContractError('defensive foul in conditional actor population')
    return p[ix]


def record(a,p,family):
    check(p);ctx,players=unpack(a);y=a['y'];star=players['usage']>=.25;known=np.isfinite(players['usage']).all(1);truth_star=star[np.arange(len(y)),y];star_prob=(p*star).sum(1);chosen=p[np.arange(len(y)),y];onehot=np.eye(5)[y]
    return pd.DataFrame({'seg_id':a['seg_id'],'game_id':a['game_id'],'date_et':a['date_et'],'model':family,'loss':-np.log(chosen),'brier':np.square(p-onehot).sum(1),'star_known':known,'star_brier':np.where(known,(star_prob-truth_star)**2,np.nan),'star_bias':np.where(known,star_prob-truth_star,np.nan),'nonstar_context':known&~star.any(1),'close':abs(ctx['margin'])<=5,'confidence':p.max(1),'correct':p.argmax(1)==y})


def decision(rows,meta):
    references={f:rows[rows.model.eq(f)].set_index('seg_id').sort_index() for f in ('native','usage')};out={'models':{},'changes':{},'eligible':{}}
    for family,q in rows.groupby('model'):
        out['models'][family]={'actions':len(q),'games':q.game_id.nunique(),'nll':float(q.loss.mean()),'brier':float(q.brier.mean()),'star_known_actions':int(q.star_known.sum()),'star_brier':float(q.star_brier.mean()),'star_calibration_gap':float(q.star_bias.mean()),'contexts':{label:{'actions':int(q[label].sum()),'games':int(q.loc[q[label],'game_id'].nunique()),'nll':float(q.loc[q[label],'loss'].mean())} for label in ('close','nonstar_context','star_known')},'reliability':{str(k):{'rows':len(g),'confidence':float(g.confidence.mean()),'correct':float(g.correct.mean())} for k,g in q.groupby(pd.cut(q.confidence,[0,.2,.3,.4,.5,.7,1]),observed=True)}}
    for family in 'ABC':
        q=rows[rows.model.eq(family)].set_index('seg_id').sort_index();changes={};checks={}
        for name,r in references.items():
            if not q.index.equals(r.index):raise ContractError('conditional actor keys differ')
            z=interval(q[['game_id','date_et']].assign(change=q.loss-r.loss).reset_index(drop=True),6);changes[name]=z;checks[f'{name}/benefit']=z['change']<=-.005;checks[f'{name}/support']=max(z['familywise_game'][1],z['familywise_week'][1])<0
        r=references['native'];checks['population']=q.game_id.nunique()>=100 and len(q)>=20000;checks['critical_brier']=q.star_brier.mean()-r.star_brier.mean()<=.005;checks['critical_calibration']=abs(q.star_bias.mean())<=.03
        for label in ('nonstar_context','close'):
            use=q[label];checks[label]=float((q.loc[use,'loss']-r.loc[use,'loss']).mean())<=.01
        checks['training_convergence']=meta[family]['converged'];out['changes'][family]=changes;out['eligible'][family]={'eligible':bool(all(checks.values())),'checks':{k:bool(v) for k,v in checks.items()}}
    out['shortlist']=sorted([f for f in 'ABC' if out['eligible'][f]['eligible']],key=lambda f:out['models'][f]['nll'])[:2];return out


def screen():
    data.verify();out=data.WORK/'events.json'
    if out.exists():raise FileExistsError(out)
    a=data.load('panel');predictions={'native':incumbent(a)};ctx,players=unpack(a);predictions['usage']=usage(players);predictions['uniform']=np.full((len(a['y']),5),.2);metas={}
    for family in 'ABC':
        predictor=model.Predictor(family);metas[family]=predictor.meta;predictions[family]=np.concatenate([predictor.predict(*unpack(subset(a,slice(start,start+2000)))) for start in range(0,len(a['y']),2000)]);print('C06 actor probabilities',family,flush=True)
    rows=pd.concat([record(a,p,f) for f,p in predictions.items()],ignore_index=True);rows.to_parquet(data.WORK/'events.parquet',index=False)
    with (data.WORK/'probabilities.npz').open('xb') as stream:np.savez_compressed(stream,**predictions)
    result=decision(rows,metas);result.update(kind='C06 conditional actor screen, known development only',probabilities_sha256=sha256_file(data.WORK/'probabilities.npz'),scores_sha256=sha256_file(data.WORK/'events.parquet'),training={f:{k:m[k] for k in ('train_actions','selection_actions','final_actions','converged','seconds')} for f,m in metas.items()},production_changed=False);create_json(out,result);create_json(ROOT/'analysis/experiments/20261126_c06_events_v1.json',result);print(result['models'],result['eligible'],'shortlist',result['shortlist'],flush=True);return result

if __name__=='__main__':screen()
