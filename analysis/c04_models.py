"""Full-history C04 joint-minute forecasters: residual, distributional and analogue."""
from __future__ import annotations
import argparse,gc,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import lightgbm as lgb
from analysis import c04_data as data
from analysis.c04_core import COLS,inputs,legal,quantiles
from analysis.c01_workbench import read,create_json
from analysis.c01_core import ContractError
from basketball_common import sha256_file
Q=np.array([.02,.1,.25,.5,.75,.9,.98]);GRID=np.r_[0,Q,1]

def ordered(f):return f.sort_values(['alloc','player'],ascending=[False,True],kind='stable')
def norm(x,fit=None):
    if fit is None:fit={'mean':x.mean(0).tolist(),'sd':np.where(x.std(0)>1e-7,x.std(0),1).tolist()}
    return (x-np.array(fit['mean']))/np.array(fit['sd']),fit

def ridge_fit(f):
    x,n=norm(inputs(f[COLS]));x=np.column_stack([x,np.ones(len(x))]);penalty=np.diag(np.r_[np.full(len(COLS),100.),0.]);y=(f.reg-f.alloc).to_numpy()
    return {'normalisation':n,'coef':np.linalg.solve(x.T@x+penalty,x.T@y).tolist()}
def ridge_mean(f,m):
    x,_=norm(inputs(f[COLS]),m['normalisation']);return f.alloc.to_numpy()+np.column_stack([x,np.ones(len(x))])@np.array(m['coef'])

def mapped(v,n):
    return np.interp(np.linspace(0,1,n),np.linspace(0,1,len(v)),v)
def descriptor(f):
    f=ordered(f);x=inputs(f[COLS]);return np.r_[len(f),np.concatenate([mapped(x[:,i],12) for i in range(x.shape[1])])]
def library(f):
    groups=[ordered(g) for _,g in f.groupby(['date_et','game_id','team'],sort=True)]
    return np.stack([descriptor(g) for g in groups]),[g.reg.to_numpy().tolist() for g in groups]

def mae(f,predict):
    errors=[];neutral=[];base=[]
    for _,g in f.groupby(['game_id','team'],sort=True):
        y=g.reg.to_numpy();p=legal(predict(g));errors.extend(np.abs(p-y));neutral.extend(np.abs(240/len(g)-y));base.extend(np.abs(g.alloc-y))
    a,b,c=map(lambda v:float(np.mean(v)),(errors,neutral,base));return {'minute_mae':a,'neutral_240_per_roster_mae':b,'dated_allocator_mae':c,'relative_gain_vs_neutral':1-a/b,'rows':len(errors)}

def fit(family,root=None):
    data.verify();root=Path(root or data.WORK/'models');folder=root/family;folder.mkdir(parents=True,exist_ok=False);start=time.monotonic();allrows=pd.read_parquet(data.WORK/'rows.parquet');train=allrows[allrows.date_et.le('2025-06-30')];val=allrows[allrows.date_et.between('2025-10-01','2025-11-30')];final=allrows[allrows.date_et.le('2025-11-30')];cal=allrows[allrows.date_et.between('2025-12-01','2025-12-31')];meta={'family':family,'training_through':'2025-12-31','full_mean_fit_rows':len(final),'selection_fit_rows':len(train),'selection_rows':len(val),'joint_calibration_rows':len(cal),'code_sha256':sha256_file(Path(__file__)),'contract_sha256':sha256_file(data.CONTRACT),'data_sha256':sha256_file(data.WORK/'data.json')};hashes={}
    def save(name,value):create_json(folder/name,value);hashes[name]=sha256_file(folder/name)
    if family=='A':
        selected=ridge_fit(train);meta['training_credibility']=mae(val,lambda f:ridge_mean(f,selected));model=ridge_fit(final);save('ridge.json',model);res=[]
        for _,g in cal.groupby(['game_id','team'],sort=True):
            g=ordered(g);res.append((g.reg.to_numpy()-legal(ridge_mean(g,model))).tolist())
        save('residuals.json',res);meta['capacity']='closed-form ridge lambda100; all rows; no optimisation cap'
    elif family=='B':
        meta['quantile_fits']=[];selected_models=[];x=inputs(train[COLS]);vx=inputs(val[COLS]);fx=inputs(final[COLS]);fitted=[]
        for i,q in enumerate(Q):
            params=dict(objective='quantile',alpha=float(q),metric='quantile',learning_rate=.03,num_leaves=31,min_data_in_leaf=100,lambda_l2=10,max_bin=127,seed=20261125,num_threads=10,verbosity=-1,deterministic=True,force_col_wise=True,feature_pre_filter=False)
            tr=lgb.Dataset(x,label=train.reg);va=lgb.Dataset(vx,label=val.reg,reference=tr);history={}
            s=lgb.train(params,tr,num_boost_round=1500,valid_sets=[va],callbacks=[lgb.early_stopping(60,verbose=False),lgb.record_evaluation(history),lgb.log_evaluation(250)])
            rounds=s.best_iteration;selected_models.append(s)
            info={'q':float(q),'rounds':rounds,'selection_pinball':float(s.best_score['valid_0']['quantile']),'budget_bound':rounds==1500,'learning_curve':{str(k+1):float(v) for k,v in enumerate(history['valid_0']['quantile']) if k%100==0 or k+1==rounds}}
            m=lgb.train(params,lgb.Dataset(fx,label=final.reg),num_boost_round=rounds);path=folder/f'q{i}.txt';m.save_model(str(path));hashes[path.name]=sha256_file(path);fitted.append(m);meta['quantile_fits'].append(info);print('C04 B quantile fit',info,flush=True);del tr,va;gc.collect()
        meta['training_credibility']=mae(val,lambda f:selected_models[3].predict(inputs(f[COLS]),num_threads=1));pits=[]
        for _,g in cal.groupby(['game_id','team'],sort=True):
            g=ordered(g);q=quantiles(np.column_stack([m.predict(inputs(g[COLS]),num_threads=1) for m in fitted]));pit=[]
            for y,law in zip(g.reg,q):pit.append(float((np.interp(y-1e-9,law,GRID)+np.interp(y+1e-9,law,GRID))/2))
            pits.append(pit)
        save('pits.json',pits)
    else:
        x,targets=library(train);z,n=norm(x)
        def predict(f):
            v,_=norm(descriptor(f)[None,:],n);distance=np.sum((z-v)**2,axis=1);idx=np.argsort(distance,kind='stable')[:64];v=np.mean([mapped(np.array(targets[i]),len(f)) for i in idx],axis=0);order=ordered(f).index;return pd.Series(v,index=order).reindex(f.index).to_numpy()
        meta['training_credibility']=mae(val,predict);x,targets=library(allrows[allrows.date_et.le('2025-12-31')]);_,n=norm(library(final)[0]);save('analogues.json',{'descriptors':x.tolist(),'targets':targets,'normalisation':n});meta['team_library_size']=len(targets)
    meta.update(hashes=hashes,seconds=time.monotonic()-start,selection_only_before_panel=True,production_changed=False);create_json(folder/'fit.json',meta);print('C04 fit complete',family,meta['seconds'],meta['training_credibility'],flush=True);return meta

class Predictor:
    def __init__(self,family,root=None):
        self.family=family;self.folder=Path(root or data.WORK/'models')/family;self.meta=read(self.folder/'fit.json')
        if self.meta['contract_sha256']!=sha256_file(data.CONTRACT):raise ContractError('role fit contract changed')
        for n,h in self.meta['hashes'].items():
            if sha256_file(self.folder/n)!=h:raise ContractError('joint-role fitted artifact changed')
        if family=='A':self.model=read(self.folder/'ridge.json');self.noise=read(self.folder/'residuals.json')
        elif family=='B':self.models=[lgb.Booster(model_file=str(self.folder/f'q{i}.txt')) for i in range(7)];self.noise=read(self.folder/'pits.json')
        else:self.model=read(self.folder/'analogues.json');self.z,_=norm(np.array(self.model['descriptors']),self.model['normalisation'])
    def draw(self,f,W,rng):
        if (f.date_et<=self.meta['training_through']).any():raise ContractError('future joint-role model/calibration')
        original=f.index;f=ordered(f);n=len(f);inputs(f[COLS])
        if self.family=='C':
            v,_=norm(descriptor(f)[None,:],self.model['normalisation']);d=np.sum((self.z-v)**2,axis=1);near=np.argsort(d,kind='stable')[:64];picks=near[rng.integers(len(near),size=W)];a=np.stack([mapped(np.array(self.model['targets'][i]),n) for i in picks])
        else:
            picks=rng.integers(len(self.noise),size=W);noise=np.stack([mapped(np.array(self.noise[i]),n) for i in picks])
            if self.family=='A':a=ridge_mean(f,self.model)[None,:]+noise
            else:
                q=quantiles(np.column_stack([m.predict(inputs(f[COLS]),num_threads=1) for m in self.models]));a=np.column_stack([np.interp(noise[:,i],GRID,q[i]) for i in range(n)])
        a=legal(a);return a[:,f.index.get_indexer(original)]

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('family',choices=['A','B','C','all']);a=p.parse_args()
    for f in ('ABC' if a.family=='all' else a.family):fit(f)
