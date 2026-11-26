"""Three earlier-only expert learners: global, team context and player reliability."""
from __future__ import annotations
import argparse,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from scipy.special import expit
from scipy.optimize import minimize,minimize_scalar
from analysis import c07_data as data,c07_members as members,c05_models as roles,c02_rollout as engine
from analysis.c07_core import cross,prior_dates,team_mass
from analysis.c07_score import truths
from analysis.c01_metrics import crps
from analysis.c01_workbench import read,create_json
from analysis.c01_core import ContractError
from basketball_common import sha256_file


def feature_rows(gid):
    n,r=members.draws(gid);ref=members.STATE['refs'][gid];ids=ref['captured_player_ids'];prior=engine.STATE['causal'];prior=prior[prior.game_id.eq(gid)].set_index('player').loc[ids];rows=members.old.STATE['rows'];rows=rows[rows.game_id.eq(gid)].set_index('player').loc[ids]
    x=np.column_stack([prior.usage.to_numpy(),np.log1p(rows.n_history),abs(r.mean(0)-n.mean(0))])
    if not np.isfinite(x).all():raise ContractError('unknown expert gate feature')
    side=np.array(ref['captured_sides']);team=np.stack([np.r_[x[side==s,0].max(),x[side==s,1:].mean(0)] for s in (0,1)])
    return x,team


def scale(x,fit=None):
    if fit is None:fit={'mean':x.reshape(-1,3).mean(0).tolist(),'sd':np.maximum(x.reshape(-1,3).std(0),1e-12).tolist()};fit['sd']=[v if v>1e-7 else 1. for v in fit['sd']]
    return (x-np.array(fit['mean']))/np.array(fit['sd']),fit


def moments(arrays,box,prior,team_truth):
    names=['N','H','V','R'];L=np.zeros(4);D=np.zeros((4,4));ids=arrays['N']['player_ids'];critical=np.array([prior.loc[p,'usage']>=.25 for p in ids]);critical=critical if critical.any() else np.ones(len(ids),bool)
    samples=[]
    for i,pid in enumerate(ids):samples.append(([arrays[k]['pts'][:,i] for k in names],float(box.loc[pid,'points']),.5/(3*len(ids))+(.25/(4*critical.sum()) if critical[i] else 0)))
    for side in (0,1):samples.append(([arrays[k]['team'][:,side] for k in names],team_truth[side],.25/12))
    for xs,y,w in samples:
        L+=w*np.array([abs(x-y).mean() for x in xs])
        for i in range(4):
            for j in range(i,4):
                value=w*cross(xs[i],xs[j]);D[i,j]+=value
                if i!=j:D[j,i]+=value
    return L,D


def fit(output=None):
    p=data.verify();root=Path(output or data.WORK);out=root/'fit.json'
    if out.exists():raise FileExistsError(out)
    root.mkdir(parents=True,exist_ok=True);members.init();start=time.monotonic();ls=[];ds=[];teams=[];px=[];py=[];archive={}
    refs={r['game_id']:r for r in p['references']};prior_dates([refs[g]['date_et'] for g in p['train_ids']])
    for gid in p['train_ids']:
        a={k:members.load(gid,k) for k in ('N','H','V','R')};ref,box,on,prior,tt=truths(gid);L,D=moments(a,box,prior,tt);ls.append(L);ds.append(D);x,t=feature_rows(gid);teams.append(t);px.append(x);py.extend([float(crps(a['R']['pts'][:,i],float(box.loc[pid,'points']))<crps(a['N']['pts'][:,i],float(box.loc[pid,'points']))) for i,pid in enumerate(a['N']['player_ids'])]);archive[gid]={k:read(members.path(gid,k)/'receipt.json')['sha256'] for k in a}
    L=np.stack(ls);D=np.stack(ds)
    def loss(pi):return float(np.mean(np.sum(pi*L,axis=1)-.5*np.einsum('gi,gij,gj->g',pi,D,pi)))
    def global_loss(w):return loss(np.tile([1-w,0,0,w],(len(L),1)))
    opt=minimize_scalar(global_loss,bounds=(0,1),method='bounded',options={'xatol':1e-12});candidates=[0.,float(opt.x),1.];w=min(candidates,key=global_loss)
    z,tn=scale(np.stack(teams));tx=np.concatenate([np.ones((*z.shape[:2],1)),z],axis=2)
    def tloss(coef):
        prob=expit(tx@coef);pi=np.stack([team_mass(t) for t in prob]);return loss(pi)+.05*float(coef[1:]@coef[1:])
    trace=[]
    def cb(coef):trace.append(float(tloss(coef)))
    b=minimize(tloss,np.zeros(4),method='L-BFGS-B',callback=cb,options={'maxiter':500,'ftol':1e-12,'gtol':1e-7,'maxls':40})
    player,cn=scale(np.concatenate(px));X=np.column_stack([np.ones(len(player)),player]);y=np.array(py)
    def closs(coef):
        eta=X@coef;pr=expit(eta);value=float(np.mean(np.logaddexp(0,eta)-y*eta)+.05*(coef[1:]@coef[1:]));gradient=X.T@(pr-y)/len(y)+.1*np.r_[0,coef[1:]];return value,gradient
    c=minimize(closs,np.zeros(4),jac=True,method='L-BFGS-B',options={'maxiter':500,'ftol':1e-12,'gtol':1e-7,'maxls':40})
    models={'fit_through':'2026-01-21','A':{'role_mass':float(w)},'B':{'normalisation':tn,'coef':b.x.tolist()},'C':{'normalisation':cn,'coef':c.x.tolist()}};create_json(root/'models.json',models)
    info={'A':{'converged':bool(opt.success),'role_mass':float(w),'training_composite':global_loss(w),'native_composite':global_loss(0),'role_composite':global_loss(1),'pool_composite':global_loss(.5)},'B':{'converged':bool(b.success or np.max(abs(b.jac))<=1e-5),'iterations':int(b.nit),'gradient_inf':float(np.max(abs(b.jac))),'training_regularised_composite':float(b.fun),'initial_composite':tloss(np.zeros(4)),'curve':trace},'C':{'converged':bool(c.success or np.max(abs(c.jac))<=1e-5),'iterations':int(c.nit),'gradient_inf':float(np.max(abs(c.jac))),'training_bce_regularised':float(c.fun),'constant_bce':float(-(y.mean()*np.log(max(y.mean(),1e-12))+(1-y.mean())*np.log(max(1-y.mean(),1e-12)))),'players':len(y)}}
    meta={'training_games':41,'training_through':'2026-01-21','code_sha256':sha256_file(Path(__file__)),'contract_sha256':sha256_file(data.CONTRACT),'data_sha256':sha256_file(data.WORK/'data.json'),'models_sha256':sha256_file(root/'models.json'),'archive':archive,'training':info,'seconds':time.monotonic()-start,'production_changed':False};create_json(out,meta)
    if root==data.WORK:create_json(ROOT/'analysis/experiments/20261126_c07_fits_v1.json',{k:v for k,v in meta.items() if k!='archive'})
    print('C07 gates fitted',info,flush=True);return meta

class Predictor:
    def __init__(self,root=None):
        root=Path(root or data.WORK);self.meta=read(root/'fit.json')
        if self.meta['code_sha256']!=sha256_file(Path(__file__)) or self.meta['contract_sha256']!=sha256_file(data.CONTRACT) or self.meta['data_sha256']!=sha256_file(data.WORK/'data.json') or self.meta['models_sha256']!=sha256_file(root/'models.json'):raise ContractError('expert fitted source/artifact changed')
        self.models=read(root/'models.json')
    def guard(self,gid):
        if members.STATE['refs'][gid]['date_et']<=self.models['fit_through']:raise ContractError('future/same-day gate fit')
    def masses(self,gid,family):
        self.guard(gid)
        if family=='pool':return np.array([.5,0,0,.5])
        if family=='A':w=self.models['A']['role_mass'];return np.array([1-w,0,0,w])
        _,team=feature_rows(gid);m=self.models['B'];z,_=scale(team,m['normalisation']);p=expit(np.column_stack([np.ones(2),z])@np.array(m['coef']));return team_mass(p)
    def player_prob(self,gid):
        self.guard(gid);x,_=feature_rows(gid);m=self.models['C'];z,_=scale(x,m['normalisation']);return expit(np.column_stack([np.ones(len(z)),z])@np.array(m['coef']))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args();fit(a.output)
