"""Exact weighted laws and bounded common-count expert pooling."""
import hashlib
import numpy as np
from analysis.c01_core import ContractError


def weights(w,n=None):
    a=np.asarray(w,float)
    if a.ndim!=1 or not len(a) or (n is not None and len(a)!=n) or not np.isfinite(a).all() or (a<0).any() or abs(a.sum()-1)>1e-12:raise ContractError('invalid exact probability mass')
    return a


def seed(*parts):return int.from_bytes(hashlib.sha256('|'.join(map(str,('c07',*parts))).encode()).digest()[:8],'little')


def prior_dates(days):
    if not len(days) or any(d<'2026-01-01' or d>'2026-01-21' for d in days):raise ContractError('future combination fitting outcome')


def crps(x,y,w):
    x=np.asarray(x,float);w=weights(w,len(x))
    if x.ndim!=1 or not np.isfinite(x).all() or not np.isfinite(y):raise ContractError('invalid weighted score')
    order=np.argsort(x,kind='stable');v=x[order];p=w[order];cdf=np.cumsum(p)
    return float(w@abs(x-y)-np.sum(p*v*(2*cdf-p-1)))


def record(x,y,w):
    x=np.asarray(x,float);w=weights(w,len(x));order=np.argsort(x,kind='stable');v=x[order];cdf=np.cumsum(w[order]);mean=float(w@x);r={'supported':True,'truth':float(y),'crps':crps(x,y,w),'mean':mean,'bias':mean-y,'absolute_error':abs(mean-y)}
    for level in (.5,.8,.95):
        lo,hi=[float(v[min(np.searchsorted(cdf,q),len(v)-1)]) for q in ((1-level)/2,(1+level)/2)];k=round(100*level);r.update({f'covered{k}':float(lo<=y<=hi),f'lo{k}':lo,f'hi{k}':hi,f'width{k}':hi-lo})
    for half in (0,1):
        ix=slice(half*500,(half+1)*500);wh=w[ix];r[f'crps_half{half+1}']=crps(x[ix],y,wh/wh.sum())
    return r


def cross(x,z):
    a=np.asarray(x,float);b=np.sort(np.asarray(z,float));prefix=np.r_[0,np.cumsum(b)];k=np.searchsorted(b,a)
    return float(np.mean(a*k-prefix[k]+prefix[-1]-prefix[k]-a*(len(b)-k))/len(b))


def counts(mass,total):
    p=weights(mass);active=p>0;out=active.astype(int);left=total-int(out.sum())
    if left<0:raise ContractError('insufficient mixture support')
    raw=left*p;out+=np.floor(raw).astype(int);remain=total-int(out.sum());out[np.argsort(-(raw-np.floor(raw)),kind='stable')[:remain]]+=1
    return out


def pool(members,mass,gid):
    names=list(members);p=weights(mass,len(names));keys=set.intersection(*[set(a) for a in members.values()]);fixed={'player_ids','side'};out={k:members[names[0]][k].copy() for k in fixed};chunks={k:[] for k in keys-fixed};ws=[];tags=[];ids=[]
    for a in members.values():
        if any(not np.array_equal(a[k],out[k]) for k in fixed):raise ContractError('mixture roster/key mismatch')
    for half in (0,1):
        allocation=counts(p,500)
        for j,name in enumerate(names):
            n=allocation[j]
            if not n:continue
            ix=np.random.default_rng(seed(gid,name,half)).permutation(500)[:n]+500*half
            for k in chunks:chunks[k].append(members[name][k][ix])
            ws.extend([.5*p[j]/n]*n);tags.extend([j]*n);ids.extend(ix.tolist())
    out.update({k:np.concatenate(v) for k,v in chunks.items()});out['weight']=weights(ws,1000);out['member']=np.array(tags,np.int8);out['member_world']=np.array(ids,np.int16)
    if 1/np.sum(out['weight']**2)<990 or not np.allclose([out['weight'][:500].sum(),out['weight'][500:].sum()],[.5,.5],atol=1e-12,rtol=0):raise ContractError('mixture Monte Carlo mass/count fault')
    if not np.allclose(np.bincount(out['member'],weights=out['weight'],minlength=len(p)),p,atol=1e-12,rtol=0):raise ContractError('expert mass changed')
    return out


def team_mass(p):
    h,a=np.asarray(p,float)
    if not np.isfinite([h,a]).all() or min(h,a)<0 or max(h,a)>1:raise ContractError('invalid team gate')
    return weights([(1-h)*(1-a),h*(1-a),(1-h)*a,h*a])
