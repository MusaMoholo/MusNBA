"""Five-actor law and causal feature boundary shared by all C06 learners."""
import numpy as np
from analysis.c01_core import ContractError
from analysis.c03_choices import CONTEXT,PLAYER,validate_inputs


def check(p):
    a=np.asarray(p,float)
    if a.ndim!=2 or a.shape[1]!=5 or not np.isfinite(a).all() or (a<=0).any() or not np.allclose(a.sum(1),1,rtol=0,atol=1e-9):raise ContractError('invalid five-actor probability law')
    return a


def softmax(z):
    a=np.asarray(z,float).reshape(-1,5)
    if not np.isfinite(a).all():raise ContractError('invalid actor logits')
    a=np.maximum(np.exp(a-a.max(1,keepdims=True)),1e-12)
    return check(a/a.sum(1,keepdims=True))


def normalise(p):
    a=np.asarray(p,float).reshape(-1,5)
    if not np.isfinite(a).all() or (a<0).any():raise ContractError('invalid pointwise actor probability')
    a=np.maximum(a,1e-12);return check(a/a.sum(1,keepdims=True))


def pack(ctx,players):
    n=validate_inputs(ctx,players)
    c=np.column_stack([ctx[k] for k in CONTEXT]);p=np.stack([players[k] for k in PLAYER],axis=2)
    return np.concatenate([np.repeat(c[:,None,:],5,axis=1),p],axis=2).reshape(n*5,-1).astype(np.float32)


def dates_before(dates,cutoff):
    if any(not isinstance(d,str) or d<'2022-12-01' or d>cutoff for d in dates):raise ContractError('future/unsupported actor training input')


def usage(players):
    a=np.asarray(players['usage_share'],float)
    # Training/runtime causal relative_lineup already imputes only within the current five.
    a=np.where(np.isfinite(a),np.maximum(a,1e-8),1e-8)
    return normalise(a)
