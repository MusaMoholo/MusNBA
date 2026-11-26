"""Chronological common mean; empirical, latent and learned legacy-mixture laws."""
from __future__ import annotations
import argparse,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from scipy.special import expit,logit
from analysis import c04_data as data,c04_models as base
from analysis.c04_core import legal,inputs,COLS
from analysis.c05_core import seconds
from analysis.c01_workbench import read,create_json
from analysis.c01_core import ContractError
from basketball_common import sha256_file
WORK=ROOT/'data/derived/experiments/c05_joint_role_laws_v1';CONTRACT=ROOT/'analysis/c05_contract_v1.json'


def quantise(a):return np.stack([seconds(x)/60 for x in a])
def latent(z):
    lo=np.full(len(z),-100.);hi=-lo
    for _ in range(60):
        mid=(lo+hi)/2;small=(48*expit(z+mid[:,None])).sum(1)<240;lo=np.where(small,mid,lo);hi=np.where(small,hi,mid)
    return 48*expit(z+((lo+hi)/2)[:,None])
def logits(x):return logit(np.clip(x,.25,47.75)/48)
def make_library(groups):
    emp=[];lat=[];bands=[[] for _ in range(14)];allres=[]
    for g,mu in groups:
        res=g.reg.to_numpy()-mu;emp.append(res.tolist());lat.append(base.mapped(logits(g.reg.to_numpy())-logits(mu),12));idx=np.digitize(g.alloc,np.arange(0,50,4.))
        for r,b in zip(res,idx):bands[b].append(r);allres.append(r)
    z=np.stack(lat);cov=np.cov(z,rowvar=False);value,vec=np.linalg.eigh(cov)
    return {'empirical':emp,'latent_mean':z.mean(0).tolist(),'latent_root':(vec*np.sqrt(np.maximum(value,0))).tolist(),'sd':[float(np.std(v,ddof=1)) if len(v)>1 else float(np.std(allres,ddof=1)) for v in bands],'team_games':len(emp),'min_cov_eigenvalue':float(value.min())}

class Predictor:
    def __init__(self,family,root=None,model=None,library=None,weight=None):
        self.family=family
        if model is None:
            root=Path(root or WORK);meta=read(root/'fit.json')
            if meta['contract_sha256']!=sha256_file(CONTRACT) or meta['code_sha256']!=sha256_file(Path(__file__)):raise ContractError('C05 contract/code changed')
            for p,h in meta['hashes'].items():
                if sha256_file(root/p)!=h:raise ContractError('C05 fitted artifact changed')
            fitted=read(root/'model.json');model=fitted['mean'];library=fitted['library'];weight=fitted['weight']
        self.model=model;self.lib=library;self.weight=weight;self.training_through='2025-12-31'
    def draw(self,f,W,rng,training=False):
        if not training and (f.date_et<=self.training_through).any():raise ContractError('future mean/calibration input')
        inputs(f[COLS]);original=f.index;f=base.ordered(f);n=len(f);mu=legal(base.ridge_mean(f,self.model));lib=self.lib
        if self.family in ('A','C'):
            picks=rng.integers(len(lib['empirical']),size=W);noise=np.stack([base.mapped(np.array(lib['empirical'][i]),n) for i in picks]);a=quantise(legal(mu[None,:]+noise))
            if self.family=='C':
                sd=np.array(lib['sd'])[np.digitize(f.alloc,np.arange(0,50,4.))];b=quantise(legal(mu[None,:]+rng.normal(size=(W,n))*sd));take=rng.random(W)>=self.weight;a[take]=b[take]
        elif self.family=='L':
            sd=np.array(lib['sd'])[np.digitize(f.alloc,np.arange(0,50,4.))];a=quantise(legal(mu[None,:]+rng.normal(size=(W,n))*sd))
        else:
            z=rng.normal(size=(W,12))@np.array(lib['latent_root']).T+np.array(lib['latent_mean']);z=np.stack([base.mapped(v,n) for v in z]);a=quantise(latent(logits(mu)[None,:]+z))
        return a[:,f.index.get_indexer(original)]


def fit(root=None):
    data.verify();root=Path(root or WORK);root.mkdir(parents=True,exist_ok=False);start=time.monotonic();f=pd.read_parquet(data.WORK/'rows.parquet');means={};counts={}
    for end in ('2024-06-30','2025-06-30','2025-11-30'):
        train=f[f.date_et.le(end)];means[end]=base.ridge_fit(train);counts[end]=len(train)
    groups=[];dec=[];mae=[]
    for (day,gid,team),g in f[f.date_et.between('2024-07-01','2025-12-31')].groupby(['date_et','game_id','team'],sort=True):
        g=base.ordered(g);origin='2024-06-30' if day<='2025-06-30' else '2025-06-30' if day<='2025-11-30' else '2025-11-30';mu=legal(base.ridge_mean(g,means[origin]));groups.append((g,mu))
        if day>='2025-12-01':dec.append((g,mu));mae.extend(abs(mu-g.reg.to_numpy()))
    early=[v for v in groups if v[0].date_et.iloc[0]<'2025-12-01'];lib=make_library(early);pa=Predictor('A',model=means['2025-11-30'],library=lib,weight=1);pl=Predictor('L',model=means['2025-11-30'],library=lib,weight=0)
    # Exact empirical CRPS quadratic for mixture w*A+(1-w)*L.
    numerator=0.;denominator=0.;components=[]
    from analysis.c01_metrics import crps
    for j,(g,mu) in enumerate(dec):
        a=pa.draw(g,1000,np.random.default_rng(20261126+j),training=True);b=pl.draw(g,1000,np.random.default_rng(30261126+j),training=True)
        for i,y in enumerate(g.reg):
            x=a[:,i];z=b[:,i];ca=crps(x,y);cb=crps(z,y);aa=2*(abs(x-y).mean()-ca);bb=2*(abs(z-y).mean()-cb)
            # Sum absolute cross-distances by sorted-vector prefix sums (no quadratic array).
            sz=np.sort(z);prefix=np.r_[0,np.cumsum(sz)];k=np.searchsorted(sz,x);cross=np.mean((x*k-prefix[k]+prefix[-1]-prefix[k]-x*(len(z)-k))/len(z))
            curvature=cross-(aa+bb)/2;linear=ca-cb-curvature;numerator-=linear;denominator+=2*curvature;components.append((ca,cb,curvature))
    weight=float(np.clip(numerator/denominator,0,1)) if denominator>0 else 1.;loss=np.array(components);fitloss=lambda w:float(np.mean(w*loss[:,0]+(1-w)*loss[:,1]-w*(1-w)*loss[:,2]))
    model={'mean':means['2025-11-30'],'library':make_library(groups),'weight':weight};create_json(root/'model.json',model);create_json(root/'chronological_means.json',means)
    result={'code_sha256':sha256_file(Path(__file__)),'contract_sha256':sha256_file(CONTRACT),'data_sha256':sha256_file(data.WORK/'data.json'),'hashes':{p:sha256_file(root/p) for p in ('model.json','chronological_means.json')},'training_rows_by_origin':counts,'residual_team_games':len(groups),'selection_team_games':len(dec),'all_residual_predictions_precede_origin':True,'shared_mean':'ridge100 exact closed form; no capped iterations or training subsampling','training_minute_mae':float(np.mean(mae)),'training_only_mixture_weight_A':weight,'selection_crps':{'A':fitloss(1),'legacy':fitloss(0),'mixture':fitloss(weight)},'latent_min_cov_eigenvalue':model['library']['min_cov_eigenvalue'],'seconds':time.monotonic()-start,'production_changed':False};create_json(root/'fit.json',result);print(result,flush=True);return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args();fit(a.output)
