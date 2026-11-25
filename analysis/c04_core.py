"""C04 causal feature/target boundary and common legal joint-minute constraint."""
from __future__ import annotations
import numpy as np
from analysis.c01_core import ContractError
OWN=['n_history','last1','mean3','mean10','sd10','ewm5','ewm20','start5','start20','days_since','team_changed','healthy','cap','priority','start_share','missed','k_back','alloc']
ROSTER=['roster_n','healthy_sum','healthy_rank','mean10_sum','alloc_gap']
COLS=OWN+ROSTER

def legal(x):
    a=np.asarray(x,float)
    if a.ndim not in (1,2) or a.shape[-1]<5 or not np.isfinite(a).all():raise ContractError('invalid joint-minute targets/roster')
    a=np.atleast_2d(a);lo=-np.max(a,axis=1)-48;hi=48-np.min(a,axis=1)
    for _ in range(60):
        mid=(lo+hi)/2;total=np.clip(a+mid[:,None],0,48).sum(1);low=total<240;lo=np.where(low,mid,lo);hi=np.where(low,hi,mid)
    out=np.clip(a+((lo+hi)/2)[:,None],0,48)
    if not np.allclose(out.sum(1),240,rtol=0,atol=1e-8):raise ContractError('joint-minute conservation failed')
    return out[0] if np.asarray(x).ndim==1 else out

def inputs(frame):
    if set(frame)!=set(COLS):raise ContractError('unapproved/current-label joint-role input')
    a=np.column_stack([frame[k] for k in COLS]).astype(float)
    if not np.isfinite(a).all():raise ContractError('unknown joint-role feature')
    return a

def prior(history,origin):
    if len(history) and any(d>=origin for d in history):raise ContractError('future/same-day role history')

def quantiles(x):
    x=np.asarray(x,float)
    if x.ndim!=2 or x.shape[1]!=7 or not np.isfinite(x).all():raise ContractError('invalid minute quantile law')
    return np.column_stack([np.zeros(len(x)),np.sort(np.clip(x,0,48),axis=1),np.full(len(x),48.)])
