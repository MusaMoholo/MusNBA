"""Final weighted player/team scoring and independent conservation boundary."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from analysis.c07_core import weights,record
from analysis.c01_core import ContractError
from analysis import c02_rollout as engine


def check_worlds(a):
    side=a['side'];n=len(a['final_period']);w=weights(a.get('weight',np.full(n,1/n)),n)
    if n!=1000 or len(set(a['player_ids']))!=len(side):raise ContractError('expert world support/count mismatch')
    for stat in ('pts','fgm','fga','fg3m','fg3a','ftm','fta','oreb','dreb','ast','pf'):
        v=a[stat]
        if v.shape!=(n,len(side)) or not np.issubdtype(v.dtype,np.integer) or (v<0).any():raise ContractError('illegal expert count')
    if not np.array_equal(a['pts'],2*a['fgm']+a['fg3m']+a['ftm']) or not np.array_equal(a['reb'],a['oreb']+a['dreb']):raise ContractError('expert scoring/rebound identity')
    if (a['fg3m']>a['fgm']).any() or (a['fgm']>a['fga']).any() or (a['fg3a']>a['fga']).any() or (a['ftm']>a['fta']).any():raise ContractError('expert attempt bounds')
    for s in (0,1):
        ix=side==s
        if not np.array_equal(a['pts'][:,ix].sum(1),a['team'][:,s]) or not np.allclose(a['minutes'][:,ix].sum(1),240+25*(a['final_period']-4),atol=1e-8,rtol=0):raise ContractError('expert team/count/time identity')
    if (a['team'][:,0]==a['team'][:,1]).any():raise ContractError('expert completed ties')
    return w


def truths(gid):
    s=engine.STATE;ref=s['refs'][gid];box=s['box'][gid].copy();box['player']=box.athlete_id.astype('int64').astype(str);box=box.set_index('player');on=s['on'][gid].set_index('player').sec;prior=s['causal'][s['causal'].game_id.eq(gid)].set_index('player');team=np.array([ref['official_points'][ref[k]] for k in ('home','away')],float)
    return ref,box,on,prior,team


def score_game(gid,arrays):
    ref,box,on,prior,truth=truths(gid);rows=[];joint=[];common={'game_id':gid,'date_et':ref['date_et']}
    for name,a in arrays.items():
        w=check_worlds(a);t=a['team'];p=float(w@(t[:,0]>t[:,1]));y=float(truth[0]>truth[1]);smooth=(p+.0005)/1.001;prob=p if y else 1-p
        distance=np.linalg.norm(t[:,None,:]-t[None,:,:],axis=2);energy=float(w@np.linalg.norm(t-truth,axis=1)-.5*w@distance@w)
        joint.append({**common,'model':name,'p_home':p,'home_won':y,'win_brier':(p-y)**2,'energy':energy,'win_log_loss_smoothed':float(-np.log(smooth if y else 1-smooth)),'win_log_loss':float(-np.log(prob)) if prob else None,'raw_log_loss_infinite':not bool(prob)})
        for ent,stat,side,x,y in [('team','points','home',t[:,0],truth[0]),('team','points','away',t[:,1],truth[1]),('game','total','both',t.sum(1),truth.sum()),('game','margin','both',t[:,0]-t[:,1],truth[0]-truth[1])]:rows.append({**common,'model':name,'entity':ent,'stat':stat,'side':side,'player':'','role':'all',**record(x,y,w)})
        for i,pid in enumerate(a['player_ids']):
            z=prior.loc[pid];role='unknown' if not np.isfinite([z.usage,z.start_share]).all() else 'star' if z.usage>=.25 else 'starter' if z.start_share>=.5 else 'bench'
            for stat,col in [('min',None),('pts','points'),('reb','rebounds'),('ast','assists'),('fg3m','three_point_field_goals_made')]:
                y=float(on[pid])/60 if col is None else float(box.loc[pid,col]);x=a['minutes' if stat=='min' else stat][:,i];rows.append({**common,'model':name,'entity':'player','stat':stat,'side':str(a['side'][i]),'player':pid,'role':role,**record(x,y,w)})
    return pd.DataFrame(rows),pd.DataFrame(joint)
