"""Full-history independent, conditional-linear and conditional-tree actor laws."""
from __future__ import annotations
import argparse,gc,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import lightgbm as lgb
from scipy.optimize import minimize
from analysis import c06_data as data
from analysis.c06_core import CONTEXT,PLAYER,pack,softmax,normalise,dates_before
from analysis.c03_data import unpack
from analysis.c01_workbench import read,create_json
from analysis.c01_core import ContractError
from basketball_common import sha256_file


def transform(x,fit=None):
    if fit is None:
        with np.errstate(invalid='ignore'):
            mean=np.nan_to_num(np.nanmean(x,axis=0,dtype=np.float64));sd=np.nanstd(x,axis=0,dtype=np.float64);sd=np.where(np.isfinite(sd)&(sd>1e-7),sd,1.)
        fit={'mean':mean.tolist(),'sd':sd.tolist()}
    z=np.clip(np.nan_to_num((x-np.array(fit['mean']))/np.array(fit['sd'])),-8,8).astype(np.float32)
    u=np.nan_to_num(x[:,len(CONTEXT)+PLAYER.index('usage_share')],nan=.2).reshape(-1,5);u=(u-u.mean(1,keepdims=True)).ravel()
    out=np.concatenate([z,np.isnan(x).astype(np.float32),z[:,:len(CONTEXT)]*u[:,None]],axis=1)
    return out,fit


def linear(x,y):
    z,n=transform(x);labels=np.eye(5,dtype=np.float32)[y];curve=[];start=time.monotonic();last={}
    def objective(w):
        p=softmax(z@w.astype(np.float32));loss=float(-np.log(p[np.arange(len(y)),y]).mean()+.0005*(w@w));gradient=(z.T@(p-labels).ravel().astype(np.float32))/len(y)+.001*w
        last.update(loss=loss,gradient=float(abs(gradient).max()))
        return loss,gradient.astype(float)
    def callback(w):
        if len(curve)%25==0:
            print('C06 conditional logit',len(curve)+1,last['loss'],last['gradient'],round(time.monotonic()-start,1),flush=True)
        curve.append(float(last['loss']))
    result=minimize(objective,np.zeros(z.shape[1]),method='L-BFGS-B',jac=True,callback=callback,options={'maxiter':500,'ftol':1e-10,'gtol':1e-6,'maxls':40});loss,grad=objective(result.x);info={'iterations':int(result.nit),'converged':bool(result.success or abs(grad).max()<=1e-4),'gradient_inf':float(abs(grad).max()),'objective':loss,'message':str(result.message),'curve':{str(i+1):v for i,v in enumerate(curve) if i%25==0 or i+1==len(curve)}}
    return {'normalisation':n,'weights':result.x.tolist()},info


def tree(x,y,vx,vy,family,rounds=None):
    cfg=read(data.CONTRACT)['recipes'][family];labels=np.eye(5,dtype=np.float32)[y].ravel()
    def objective(pred,ds):
        p=softmax(pred).ravel();return p-ds.get_label(),2*np.maximum(p*(1-p),1e-6)
    def metric(pred,ds):
        p=normalise(pred) if family=='A' else softmax(pred);target=ds.get_label().reshape(-1,5);return 'actor_nll',float(-np.sum(target*np.log(p))/len(p)),False
    params={k:cfg[k] for k in ('num_leaves','learning_rate','min_data_in_leaf','lambda_l2','max_bin','num_threads','seed')};params.update(objective='binary' if family=='A' else objective,metric='None',verbosity=-1,deterministic=True,force_col_wise=True,feature_pre_filter=False)
    train=lgb.Dataset(x,label=labels);history={}
    if rounds is None:
        valid=lgb.Dataset(vx,label=np.eye(5,dtype=np.float32)[vy].ravel(),reference=train);model=lgb.train(params,train,num_boost_round=1500,valid_sets=[valid],feval=metric,callbacks=[lgb.early_stopping(60,verbose=False),lgb.record_evaluation(history),lgb.log_evaluation(100)]);curve=history['valid_0']['actor_nll'];info={'rounds':int(model.best_iteration),'selection_nll':float(min(curve)),'budget_bound':len(curve)==1500,'validation_curve':{str(i+1):float(v) for i,v in enumerate(curve) if i%50==0 or i+1==model.best_iteration or i+1==len(curve)}}
    else:model=lgb.train(params,train,num_boost_round=rounds);info={'rounds':rounds}
    return model,info


def fit(family,root=None):
    data.verify();root=Path(root or data.WORK/'models');folder=root/family;folder.mkdir(parents=True,exist_ok=False);start=time.monotonic();tr=data.load('train');va=data.load('selection');dates_before(tr['date_et'].tolist(),'2025-09-30');dates_before(va['date_et'].tolist(),'2025-11-30');x=pack(*unpack(tr));vx=pack(*unpack(va));y=tr['y'];vy=va['y'];ntrain=len(y);nselection=len(vy);del tr,va;gc.collect()
    print('C06 selection',family,'all_actions',ntrain,'selection',nselection,'candidate_rows',len(x),flush=True)
    if family=='B':
        m,selection=linear(x,y);z,_=transform(vx,m['normalisation']);p=softmax(z@np.array(m['weights'],np.float32));selection['selection_nll']=float(-np.log(p[np.arange(len(vy)),vy]).mean());del z,p
    else:m,selection=tree(x,y,vx,vy,family)
    del x,vx,y,vy,m;gc.collect();full=data.load('final');dates_before(full['date_et'].tolist(),'2025-12-31');x=pack(*unpack(full));y=full['y'];nfinal=len(y);del full;gc.collect();print('C06 final',family,'all_actions',nfinal,flush=True)
    if family=='B':m,final=linear(x,y);path=folder/'model.json';create_json(path,m)
    else:m,final=tree(x,y,None,None,family,selection['rounds']);path=folder/'model.txt';m.save_model(str(path))
    meta={'family':family,'training_through':'2025-12-31','train_actions':ntrain,'selection_actions':nselection,'final_actions':nfinal,'sample_cap':None,'selection':selection,'final':final,'converged':bool(selection['converged'] and final['converged']) if family=='B' else not selection['budget_bound'],'hashes':{path.name:sha256_file(path)},'code_sha256':sha256_file(Path(__file__)),'contract_sha256':sha256_file(data.CONTRACT),'data_sha256':sha256_file(data.WORK/'data.json'),'seconds':time.monotonic()-start,'production_changed':False};create_json(folder/'fit.json',meta);print('C06 fitted',family,meta['seconds'],'converged',meta['converged'],flush=True);return meta

class Predictor:
    def __init__(self,family,root=None):
        self.family=family;folder=Path(root or data.WORK/'models')/family;self.meta=read(folder/'fit.json')
        if self.meta['contract_sha256']!=sha256_file(data.CONTRACT) or self.meta['code_sha256']!=sha256_file(Path(__file__)) or self.meta['data_sha256']!=sha256_file(data.WORK/'data.json'):raise ContractError('C06 actor fit provenance changed')
        for p,h in self.meta['hashes'].items():
            if sha256_file(folder/p)!=h:raise ContractError('C06 actor fitted artifact changed')
        self.model=read(folder/'model.json') if family=='B' else lgb.Booster(model_file=str(folder/'model.txt'))
    def predict(self,ctx,players):
        x=pack(ctx,players)
        if self.family=='B':z,_=transform(x,self.model['normalisation']);return softmax(z@np.array(self.model['weights'],np.float32))
        raw=self.model.predict(x,raw_score=self.family=='C',num_threads=1)
        return normalise(raw) if self.family=='A' else softmax(raw)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('family',choices=['A','B','C','all']);p.add_argument('--output',type=Path);a=p.parse_args()
    for f in ('ABC' if a.family=='all' else a.family):fit(f,a.output)
