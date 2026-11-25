"""Independent lag/truth/score accounting for joint-role forecasts and worlds."""
from __future__ import annotations
import sys
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from analysis import c04_data as data,c02_accounting as account
data.pa.set_cpu_count(1);data.pa.set_io_thread_count(1)
from analysis.c01_workbench import read,create_json
from analysis.c01_core import ContractError
from basketball_common import sha256_file

def history_audit():
    data.verify();f=pd.read_parquet(data.WORK/'rows.parquet');ids=f.game_id.unique().tolist();raw=[]
    for year in range(2023,2027):
        q=pd.read_parquet(ROOT/f'data/derived/history/{year}/on_court.parquet',filters=[('game_id','in',ids)],columns=['game_id','date_et','team','player','sec','starter']+[f'm{k:02d}' for k in range(1,49)])
        q=q[q.sec.gt(0)].copy();q['reg']=q[[f'm{k:02d}' for k in range(1,49)]].sum(axis=1);raw.append(q[['game_id','date_et','team','player','sec','starter','reg']])
    raw=pd.concat(raw,ignore_index=True).sort_values(['date_et','game_id','team','player'],kind='stable');expected=f.set_index(['game_id','player']);h=defaultdict(list);checked=0;maximum=0.
    for r in raw.itertuples():
        key=(r.game_id,r.player);old=h[r.player]
        if key in expected.index:
            a=expected.loc[key];v=np.array([x[1] for x in old]);starts=np.array([x[2] for x in old]);values={'n_history':len(old),'last1':v[-1] if len(v) else 10.,'mean3':float(sum(v[-3:])/len(v[-3:])) if len(v) else 10.,'mean10':float(sum(v[-10:])/len(v[-10:])) if len(v) else 10.,'sd10':float(np.sqrt(np.mean((v[-10:]-np.mean(v[-10:]))**2))) if len(v)>1 else 6.,'days_since':min(365,(pd.Timestamp(r.date_et)-pd.Timestamp(old[-1][0])).days) if old else 365,'team_changed':float(bool(old) and old[-1][3]!=r.team),'reg':r.reg,'sec':r.sec}
            for label,hl,x,default in [('ewm5',5,v,10),('ewm20',20,v,10),('start5',5,starts,0),('start20',20,starts,0)]:
                w=np.array([2**(-(len(x)-i-1)/hl) for i in range(len(x))]);values[label]=float(sum(w*x)/sum(w)) if len(x) else default
            if old and old[-1][0]>=r.date_et:raise ContractError('independent same-day/future input')
            for k,v in values.items():
                d=abs(float(a[k])-v);maximum=max(maximum,d);checked+=1
                if d>1e-9:raise ContractError('independent role lag/truth mismatch:'+k)
        old.append((r.date_et,r.reg,float(r.starter),r.team))
    result={'rows':len(f),'independent_lag_truth_values_checked':checked,'maximum_difference':maximum,'future_and_current_outcomes_excluded':True};create_json(data.WORK/'history_audit.json',result);return result

def minute_audit():
    p=read(data.WORK/'minute_screen.json');scores=pd.read_parquet(data.WORK/'minute_scores.parquet');plan=read(data.WORK/'data.json');maximum=0.;count=0
    for ref in plan['references']:
        gid=ref['game_id'];path=data.WORK/'minute_draws'/f'{gid}.npz'
        if sha256_file(path)!=p['draw_hashes'][gid]:raise ContractError('minute draw hash changed')
        with np.load(path,allow_pickle=False) as z:
            ids=z['player_ids'].tolist();side=z['side']
            for model in ('A','B','C'):
                a=z[model]
                if not np.isfinite(a).all() or (a<0).any() or (a>48).any() or any(not np.allclose(a[:,side==s].sum(1),240,atol=1e-8,rtol=0) for s in (0,1)):raise ContractError('saved minute law violates time constraint')
            for r in scores[scores.game_id.eq(gid)].itertuples():
                a=z[r.model][:,ids.index(r.player)]
                for value,x in [(r.crps,a),(r.crps_half1,a[:500]),(r.crps_half2,a[500:])]:
                    d=abs(account.reference_crps(x,r.truth)-value);count+=1;maximum=max(maximum,d)
                    if d>1e-10:raise ContractError('independent minute score differs')
                lo,hi=np.quantile(a,[.1,.9],method='inverted_cdf')
                if bool(lo<=r.truth<=hi)!=bool(r.covered80):raise ContractError('independent minute coverage differs')
    result={'games':200,'scalar_half_scores_checked':count,'maximum_difference':maximum,'coverage_independently_verified':True,'all_joint_targets_legal':True};create_json(data.WORK/'minute_audit.json',result);return result

def world_audit(ids):
    count=0;maximum=0.;worlds=0
    for gid in ids:
        folder=data.WORK/'games'/gid;receipt=read(folder/'receipt.json');arrays={}
        if any(sha256_file(folder/k)!=v for k,v in receipt['hashes'].items()):raise ContractError('role game receipt changed')
        for model in receipt['arms']:
            with np.load(folder/f'{model}.npz',allow_pickle=False) as z:arrays[model]={k:z[k] for k in z.files}
            if model!='native':account.check_arrays(arrays[model]);worlds+=1000
        for r in pd.read_parquet(folder/'scores.parquet').itertuples():
            a=arrays[r.model]
            if r.entity=='player':i=a['player_ids'].tolist().index(r.player);x=a['minutes' if r.stat=='min' else r.stat][:,i]
            elif r.entity=='team':x=a['team'][:,0 if r.side=='home' else 1]
            else:x=a['team'].sum(1) if r.stat=='total' else a['team'][:,0]-a['team'][:,1]
            for expected,y in [(r.crps,x),(r.crps_half1,x[:500]),(r.crps_half2,x[500:])]:
                d=abs(expected-account.reference_crps(y,r.truth));maximum=max(maximum,d);count+=1
                if d>1e-10:raise ContractError('independent role-world score differs')
    return {'games':len(ids),'new_worlds_checked':worlds,'scalar_half_scores_checked':count,'maximum_difference':maximum,'all_world_accounting_passed':True}

if __name__=='__main__':print(history_audit());print(minute_audit())
