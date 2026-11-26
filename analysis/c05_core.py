"""Exact second-resolution five-lane preemptive regulation scheduling."""
import numpy as np
from analysis.c01_core import ContractError


def seconds(target):
    x=np.asarray(target,float)
    if x.ndim!=1 or len(x)<5 or not np.isfinite(x).all() or (x<0).any() or (x>48+1e-8).any() or abs(x.sum()-240)>1e-7:
        raise ContractError('illegal target law')
    raw=x*60;v=np.floor(raw+1e-9).astype(int);left=14400-v.sum()
    if left<0 or left>len(v):raise ContractError('quantisation budget')
    v[np.argsort(-(raw-v),kind='stable')[:left]]+=1
    return v


def schedule(target,preference=None):
    """McNaughton wrap schedule; choose order/phase using original timing preferences.

    A player of at most one horizon cannot overlap itself when split over lanes.
    Counts are preserved to <one second; phase selection preserves every count.
    """
    v=seconds(target);n=len(v)
    pref=np.zeros((n,2880)) if preference is None else np.asarray(preference,float)
    if pref.shape!=(n,2880) or not np.isfinite(pref).all():raise ContractError('invalid timing preference')
    # Original forecast centres determine ordering; shift maximises original on-time overlap.
    centres=(pref@np.arange(2880))/np.maximum(pref.sum(1),1)
    order=np.argsort(centres,kind='stable');flat=np.empty(14400,np.int16);pos=0
    for i in order:flat[pos:pos+v[i]]=i;pos+=v[i]
    tab=flat.reshape(5,2880).T.copy()
    if preference is not None:
        mask=np.stack([(tab==i).any(1) for i in range(n)]).astype(float)
        overlap=np.fft.irfft(np.sum(np.conj(np.fft.rfft(mask))*np.fft.rfft(pref),axis=0),n=2880)
        tab=np.roll(tab,int(np.argmax(overlap)),axis=0)
    validate(tab,target)
    return np.sort(tab,axis=1)


def validate(tab,target):
    a=np.asarray(tab);v=seconds(target);n=len(v)
    if a.shape!=(2880,5) or not np.issubdtype(a.dtype,np.integer) or (a<0).any() or (a>=n).any() or (np.diff(np.sort(a,axis=1),axis=1)==0).any():raise ContractError('illegal rotation five')
    count=np.bincount(a.ravel(),minlength=n)
    if not np.array_equal(count,v) or np.max(np.abs(count/60-np.asarray(target)))>1/60+1e-9:raise ContractError('target-to-schedule fault')
    return count/60
