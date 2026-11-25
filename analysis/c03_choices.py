"""C03 common causal choice interface: forty actor/actions and three actorless events."""
from __future__ import annotations
import numpy as np
from analysis.c01_core import ContractError
from analysis.c02_data import COMMON
from scripts import nodes

CONTEXT=list(dict.fromkeys(COMMON))
PLAYER=nodes.PROFILE+nodes.IN_GAME+['grp_code','usage_share','usage_rank','usage_mult_now']
K=43

def check(p):
    p=np.asarray(p,float)
    if p.ndim!=2 or p.shape[1]!=K or not np.isfinite(p).all() or (p<=0).any() or not np.allclose(p.sum(1),1,rtol=0,atol=1e-8):
        raise ContractError('invalid C03 legal choice law')
    return p

def law(logits):
    z=np.asarray(logits,float);z=z-z.max(axis=1,keepdims=True);p=np.maximum(np.exp(z),1e-12)
    return check(p/p.sum(1,keepdims=True))

def decode(p):
    p=check(p);a=p[:,:40].reshape(-1,5,8);event=np.column_stack([a.sum((1,2)),p[:,40:]])
    who=a.sum(2)/event[:,0,None];what=a/a.sum(2,keepdims=True)
    return event,who,what

def validate_inputs(ctx,players,dates=None,training=False):
    if set(ctx)!=set(CONTEXT) or set(players)!=set(PLAYER):raise ContractError('C03 unapproved feature or current-label input')
    n=len(next(iter(ctx.values())))
    if any(np.asarray(v).shape!=(n,) for v in ctx.values()) or any(np.asarray(v).shape!=(n,5) for v in players.values()):raise ContractError('C03 feature shape')
    if any(np.isinf(v).any() for v in [*ctx.values(),*players.values()]):raise ContractError('C03 infinite feature')
    if dates is not None and training and any(d<'2022-12-01' or d>'2025-12-31' for d in dates):raise ContractError('C03 future training input')
    return n

def long_features(ctx,players):
    """All 43 alternatives exist before the event; no truth-dependent mask."""
    n=validate_inputs(ctx,players);out={k:np.repeat(v,K) for k,v in ctx.items()}
    for k,v in players.items():
        x=np.full((n,K),np.nan,np.float32);x[:,:40]=np.repeat(v,8,axis=1);out['player_'+k]=x.ravel()
    out['choice_type']=np.tile(np.r_[np.tile(np.arange(8),5),8,9,10],n).astype(np.float32)
    return np.column_stack(list(out.values())).astype(np.float32),list(out)
