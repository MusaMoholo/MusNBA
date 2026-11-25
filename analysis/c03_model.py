"""Three frozen C03 families, common joint prediction and complete fit ledger."""
from __future__ import annotations
import argparse,gc,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import lightgbm as lgb
from analysis import c03_data as data
from analysis.c03_choices import CONTEXT,PLAYER,long_features,law,check
from analysis.c01_workbench import read,create_json
from analysis.c01_core import ContractError
from basketball_common import sha256_file


def softmax(x,k):
    z=np.asarray(x,float).reshape(-1,k);z-=z.max(1,keepdims=True);p=np.maximum(np.exp(z),1e-12);return p/p.sum(1,keepdims=True)
def objective(k):
    def calc(pred,ds):
        p=softmax(pred,k).ravel();return p-ds.get_label(),2*np.maximum(p*(1-p),1e-6)
    return calc
def metric(k):
    def calc(pred,ds):
        p=softmax(pred,k);y=ds.get_label().reshape(-1,k);return 'nll',float(-np.sum(y*np.log(p))/len(p)),False
    return calc

def head_arrays(a,name):
    c,p=a['context'],a['players'];y=a['y'];action=y<40
    if name=='event':return c,np.where(action,0,y-39),4,False
    if name=='who':
        x=np.concatenate([np.repeat(c[action,None,:],5,axis=1),p[action]],axis=2).reshape(-1,len(CONTEXT)+len(PLAYER));labels=(np.arange(5)[None,:]==(y[action]//8)[:,None]).astype(float).ravel()
        return x,labels,5,True
    slot=y[action]//8;x=np.concatenate([c[action],p[action][np.arange(action.sum()),slot]],axis=1)
    return x,y[action]%8,8,False

def transform(x,fit=None):
    if fit is None:
        with np.errstate(invalid='ignore'):
            mean=np.nanmean(x,axis=0);mean=np.nan_to_num(mean);std=np.nanstd(x,axis=0);std=np.where(np.isfinite(std)&(std>1e-5),std,1.)
        fit={'mean':mean.tolist(),'std':std.tolist()}
    z=np.nan_to_num((x-np.array(fit['mean']))/np.array(fit['std']));z=np.clip(z,-8,8)
    return np.column_stack([z,np.isnan(x),np.ones(len(x))]).astype(float),fit

def linear_fit(x,y,vx,vy,k,group,epochs=None):
    z,norm=transform(x);vz,_=transform(vx,norm);w=np.zeros((z.shape[1],1 if group else k));best=(np.inf,1);curve=[]
    # Every iteration is deterministic full-batch gradient descent; strong L2 shrinks sparse roles.
    for epoch in range(1,(epochs or 120)+1):
        p=softmax(z@w,k)
        target=y.reshape(-1,k) if group else np.eye(k)[y.astype(int)]
        residual=(p-target).reshape(-1,1) if group else p-target
        grad=z.T@residual/len(p)+.02*np.r_[w[:-1],np.zeros_like(w[-1:])]
        w-=.08*grad
        if epochs is None:
            q=softmax(vz@w,k);t=vy.reshape(-1,k) if group else np.eye(k)[vy.astype(int)];loss=float(-np.sum(t*np.log(q))/len(q));curve.append(loss)
            if loss<best[0]:best=(loss,epoch)
    return {'normalisation':norm,'weights':w.tolist()},({'rounds':epochs} if epochs else {'rounds':best[1],'selection_nll':best[0],'curve':curve})

def tree_fit(x,y,vx,vy,k,group,family,rounds=None):
    cfg=read(data.CONTRACT)['recipes'][family]
    params={key:cfg[key] for key in ('num_leaves','learning_rate','min_data_in_leaf','lambda_l2','max_bin')}
    params.update(objective=objective(k) if group else 'multiclass',metric='None' if group else 'multi_logloss',num_threads=10,seed=20261125,verbosity=-1,deterministic=True,force_col_wise=True,feature_pre_filter=False)
    if not group:params['num_class']=k
    tr=lgb.Dataset(x,label=y,free_raw_data=True)
    if rounds is None:
        va=lgb.Dataset(vx,label=vy,reference=tr,free_raw_data=True)
        model=lgb.train(params,tr,num_boost_round=cfg['rounds_max'],valid_sets=[va],feval=metric(k) if group else None,callbacks=[lgb.early_stopping(10 if family=='C' else 15,verbose=False),lgb.log_evaluation(20)])
        return model,{'rounds':model.best_iteration,'selection_score':dict(model.best_score['valid_0'])}
    return lgb.train(params,tr,num_boost_round=int(rounds)),{'rounds':rounds}

def shared(a):
    x,cols=long_features(*data.unpack(a));labels=np.zeros((len(a['y']),43),np.float32);labels[np.arange(len(labels)),a['y']]=1
    return x,labels.ravel(),43,True

def fit_family(family,root=None):
    data.verify();root=Path(root or data.WORK/'models');folder=root/family;folder.mkdir(parents=True,exist_ok=False);started=time.monotonic();info={};hashes={}
    tr,va=data.load('train'),data.load('selection');full=data.combine([tr,va])
    for name in (('shared',) if family=='C' else ('event','who','what')):
        print('Fitting',family,name,flush=True)
        x,y,k,group=shared(tr) if family=='C' else head_arrays(tr,name)
        vx,vy,_,_=shared(va) if family=='C' else head_arrays(va,name)
        fn=linear_fit if family=='A' else lambda *args,**kwargs:tree_fit(*args,family=family,**kwargs)
        _,selection=fn(x,y,vx,vy,k,group);del x,y,vx,vy;gc.collect()
        x,y,k,group=shared(full) if family=='C' else head_arrays(full,name)
        # Refit includes only the common pre-origin training and training-selection rows.
        if family=='A':
            model,_=linear_fit(x,y,x[:k],y[:k],k,group,epochs=selection['rounds']);path=folder/f'{name}.json';create_json(path,model)
        else:
            model,_=tree_fit(x,y,None,None,k,group,family,rounds=selection['rounds']);path=folder/f'{name}.txt';model.save_model(str(path))
        info[name]=selection;hashes[path.name]=sha256_file(path);del x,y,model;gc.collect();print('Fitted',family,name,selection['rounds'],flush=True)
    meta={'family':family,'training_through':'2025-12-31','heads':info,'hashes':hashes,'seconds':time.monotonic()-started,'data_sha256':sha256_file(data.WORK/'data.json'),'code_sha256':sha256_file(Path(__file__)),'contract_sha256':sha256_file(data.CONTRACT),'configuration_count':1,'development_tuning':False}
    create_json(folder/'fit.json',meta);return meta

class Predictor:
    def __init__(self,family,root=None):
        self.family=family;self.folder=Path(root or data.WORK/'models')/family;self.meta=read(self.folder/'fit.json');self.models={}
        if self.meta['contract_sha256']!=sha256_file(data.CONTRACT):raise ContractError('C03 fit contract changed')
        for n,h in self.meta['hashes'].items():
            if sha256_file(self.folder/n)!=h:raise ContractError('C03 fitted artifact changed')
            self.models[n.split('.')[0]]=read(self.folder/n) if family=='A' else lgb.Booster(model_file=str(self.folder/n))
    def head(self,name,x,k,group=False):
        m=self.models[name]
        if self.family=='A':z,_=transform(x,m['normalisation']);return softmax(z@np.array(m['weights']),k)
        p=m.predict(x,raw_score=group,num_threads=1);return softmax(p,k) if group else p
    def predict(self,ctx,players):
        from analysis.c03_choices import validate_inputs
        n=validate_inputs(ctx,players)
        if self.family=='C':x,_=long_features(ctx,players);return law(self.models['shared'].predict(x,raw_score=True,num_threads=1).reshape(n,43))
        c=np.column_stack([ctx[k] for k in CONTEXT]);p=np.stack([players[k] for k in PLAYER],axis=2)
        e=self.head('event',c,4);x=np.concatenate([np.repeat(c[:,None,:],5,axis=1),p],axis=2).reshape(n*5,-1)
        w=self.head('who',x,5,True);a=self.head('what',x,8).reshape(n,5,8)
        out=np.column_stack([(e[:,0,None,None]*w[:,:,None]*a).reshape(n,40),e[:,1:]])
        out=np.maximum(out,1e-12);return check(out/out.sum(1,keepdims=True))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('family',choices=['A','B','C','all']);a=p.parse_args()
    for f in ('ABC' if a.family=='all' else a.family):print(fit_family(f),flush=True)
