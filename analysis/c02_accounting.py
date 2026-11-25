"""Independent saved-world and scalar-score accounting for C02 research."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from analysis.c01_core import ContractError
from analysis.c01_workbench import read
from analysis import c02_data as data
from basketball_common import sha256_file


def reference_crps(samples,truth):
    """Order-statistic reference, independent of production integrated-CDF scorer."""
    u=np.sort(np.asarray(samples,float));n=len(u)
    if not n or not np.isfinite(u).all() or not np.isfinite(truth):raise ContractError('invalid independent score input')
    i=np.arange(n,dtype=float)
    return float(np.mean(np.abs(u-truth))-np.mean((2*i-n+1)*u)/n)


def check_arrays(a):
    n=len(a['final_period']);side=a['side']
    if n!=1000 or len(np.unique(a['player_ids']))!=len(side):raise ContractError('saved world support differs')
    for stat in ('pts','fgm','fga','fg3m','fg3a','ftm','fta','oreb','dreb','ast','tov','pf'):
        v=a[stat]
        if v.shape!=(n,len(side)) or not np.issubdtype(v.dtype,np.integer) or (v<0).any():raise ContractError('invalid saved count')
    if not np.array_equal(a['pts'],2*a['fgm']+a['fg3m']+a['ftm']):raise ContractError('saved player scoring identity')
    if not np.array_equal(a['reb'],a['oreb']+a['dreb']):raise ContractError('saved rebound identity')
    if (a['fgm']>a['fga']).any() or (a['fg3m']>a['fg3a']).any() or (a['fg3a']>a['fga']).any() or (a['ftm']>a['fta']).any():raise ContractError('saved attempt bounds')
    for k in (0,1):
        if not np.array_equal(a['pts'][:,side==k].sum(1),a['team'][:,k]):raise ContractError('saved player/team identity')
        if not np.allclose(a['minutes'][:,side==k].sum(1),240+25*(a['final_period']-4),atol=1e-8,rtol=0):raise ContractError('saved minute identity')
    if np.any(a['team'][:,0]==a['team'][:,1]):raise ContractError('completed game ties')


def check_game(gid,root=None):
    root=Path(root or data.WORK/'rollout');folder=root/gid;receipt=read(folder/'receipt.json')
    if any(sha256_file(folder/n)!=h for n,h in receipt['hashes'].items()):raise ContractError('saved rollout hash changed')
    arrays={}
    for arm in ('control','candidate'):
        with np.load(folder/f'{arm}.npz',allow_pickle=False) as z:arrays[arm]={k:z[k] for k in z.files}
        check_arrays(arrays[arm])
    scores=pd.read_parquet(folder/'scores.parquet');joints=pd.read_parquet(folder/'joint.parquet');maximum=0.;count=0
    if scores.duplicated(['model','entity','stat','player','side']).any():raise ContractError('duplicate forecast score key')
    for r in scores.itertuples():
        a=arrays[r.model]
        if r.entity=='player':
            ids=a['player_ids'].tolist();i=ids.index(r.player);x=a['minutes'][:,i] if r.stat=='min' else a[r.stat][:,i]
        elif r.entity=='team':x=a['team'][:,0 if r.side=='home' else 1]
        else:x=a['team'].sum(1) if r.stat=='total' else a['team'][:,0]-a['team'][:,1]
        for value,part in ((r.crps,x),(r.crps_half1,x[:500]),(r.crps_half2,x[500:])):
            delta=abs(reference_crps(part,r.truth)-value);maximum=max(maximum,delta);count+=1
            if delta>1e-10:raise ContractError('independent scalar forecast score differs')
    for r in joints.itertuples():
        t=arrays[r.model]['team'];p=float((t[:,0]>t[:,1]).mean());brier=(p-r.home_won)**2
        if abs(p-r.p_home)>1e-12 or abs(brier-r.win_brier)>1e-12:raise ContractError('independent win score differs')
    return {'game_id':gid,'scalar_and_half_scores_checked':count,'max_score_difference':maximum,'saved_accounting_passed':True}


def run():
    p=read(data.WORK/'rollout_plan.json');results=[check_game(gid) for gid in p['game_ids']]
    return {'games':len(results),'scalar_and_half_scores_checked':sum(r['scalar_and_half_scores_checked'] for r in results),
            'max_score_difference':max(r['max_score_difference'] for r in results),'all_saved_world_identities_passed':True}

if __name__=='__main__':print(run())
