"""C03 recorded-context proper scores and selection-aware paired intervals."""
from __future__ import annotations
import argparse,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import pyarrow as pa
pa.set_cpu_count(1);pa.set_io_thread_count(1)
from analysis import c03_data as data,c03_model as model,c01_contexts as context,c01_metrics as metrics,c02_data as c02
from analysis.c03_choices import decode,check
from analysis.c01_workbench import create_json,read
from analysis.c01_core import ContractError
from basketball_common import sha256_file


def interval(frame,pooled=True):
    r=metrics.bootstrap_change(frame,pooled);g=frame.groupby('game_id',sort=True).change.agg(['sum','count','mean']);days=frame.groupby('game_id').date_et.first().reindex(g.index)
    num=g['sum'].to_numpy() if pooled else g['mean'].to_numpy();den=g['count'].to_numpy() if pooled else np.ones(len(g))
    n=len(g);w=np.random.default_rng(20261125).multinomial(n,np.full(n,1/n),size=10000);boot=(w@num)/(w@den)
    block=pd.to_datetime(days).map(lambda d:d.date().toordinal()//7).to_numpy();_,code=np.unique(block,return_inverse=True);nb=code.max()+1
    bn,bd=np.bincount(code,weights=num),np.bincount(code,weights=den);w=np.random.default_rng(20261125).multinomial(nb,np.full(nb,1/nb),size=10000)
    q=[.05/6,1-.05/6];r['familywise_game']=np.quantile(boot,q).tolist();r['familywise_week']=np.quantile((w@bn)/(w@bd),q).tolist();r['families_counted']=3
    return r

def event_record(a,p,family):
    check(p);y=a['y'];chosen=p[np.arange(len(y)),y];b=np.square(p).sum(1)+1-2*chosen
    e,w,act=decode(p);ey=np.where(y<40,0,y-39);correct=e[np.arange(len(y)),ey]
    out=pd.DataFrame({k:a[k] for k in ('seg_id','game_id','date_et')});out['model']=family;out['loss']=-np.log(chosen);out['brier']=b;out['event_loss']=-np.log(correct);out['branch']=ey
    out['confidence']=p.max(1);out['correct']=p.argmax(1)==y;out['margin_band']=np.where(np.abs(a['context'][:,data.CONTEXT.index('margin')])<=5,'close','other')
    return out

def incumbent(a):
    ids=read(data.WORK/'data.json')['game_ids'];chain,ds,_=context.load_chain(ids);e,_=context.load_engine(ids)
    result={}
    for name in ('event','who','what'):
        d=ds[name];raw=e.m.boosters[name].predict(d['X'][e.m.nodes[name]['columns']].to_numpy(np.float32),raw_score=name=='who',num_threads=1)
        groups=d['group'] if 'group' in d else d['seg_id']
        if name=='who':
            p=model.softmax(raw/float(e.m.nodes['who']['temperature']),5);y=d['y'].reshape(-1,5);keys=groups[::5];chosen=(p*y).sum(1)
        else:p=raw;keys=groups;chosen=p[np.arange(len(p)),d['y']]
        result[name]=pd.Series(chosen,index=keys)
    keys=a['seg_id'];p=result['event'].reindex(keys).to_numpy().copy();action=a['y']<40
    p[action]*=result['who'].reindex(keys[action]).to_numpy()*result['what'].reindex(keys[action]).to_numpy()
    if not np.isfinite(p).all() or (p<=0).any():raise ContractError('incumbent event support differs')
    return pd.DataFrame({'seg_id':keys,'game_id':a['game_id'],'date_et':a['date_et'],'loss':-np.log(p),'model':'control'})

def screen():
    data.verify();output=data.WORK/'events.json'
    if output.exists():raise FileExistsError(output)
    a=data.load('panel');records=[];report={'models':{},'changes':{},'population':'known200, source-supported next choices; no confirmation','production_changed':False}
    ref=incumbent(a);records.append(ref)
    for family in 'ABC':
        predictor=model.Predictor(family);parts=[]
        for start in range(0,len(a['y']),1000):
            q=data.subset(a,slice(start,start+1000));parts.append(event_record(q,predictor.predict(*data.unpack(q)),family))
        f=pd.concat(parts,ignore_index=True);records.append(f)
        report['models'][family]={'events':len(f),'games':f.game_id.nunique(),'nll':float(f.loss.mean()),'joint_brier':float(f.brier.mean()),'event_nll':float(f.event_loss.mean()),'contexts':{f'{field}/{label}':{'events':len(q),'nll':float(q.loss.mean()),'brier':float(q.brier.mean())} for field in ('branch','margin_band') for label,q in f.groupby(field)},'reliability':{str(k):{'rows':len(q),'confidence':float(q.confidence.mean()),'correct':float(q.correct.mean())} for k,q in f.groupby(pd.cut(f.confidence,[0,.1,.2,.4,.6,.8,1]),observed=True)}}
        pair=f[['game_id','date_et']].assign(change=f.loss.to_numpy()-ref.loss.to_numpy());report['changes'][family]=interval(pair)
        print('Recorded-context scores',family,report['models'][family]['nll'],flush=True)
    report['models']['control']={'events':len(ref),'games':ref.game_id.nunique(),'nll':float(ref.loss.mean()),'brier_note':'legacy conditional chain true-label probability only; joint candidate Brier diagnostic, not paired vs control'}
    pd.concat(records,ignore_index=True).to_parquet(data.WORK/'events.parquet',index=False)
    create_json(output,report);create_json(ROOT/'analysis/experiments/20261125_c03_events_v1.json',report);return report

if __name__=='__main__':screen()
