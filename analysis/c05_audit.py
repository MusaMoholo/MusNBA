"""Independent lag/truth/score accounting for joint-role forecasts and worlds."""
from __future__ import annotations
import sys
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from analysis import c05_data as data,c02_accounting as account

from analysis.c01_workbench import read,create_json
from analysis.c01_core import ContractError
from basketball_common import sha256_file

def minute_audit(output=None):
    p=read(data.WORK/'minute_screen.json');scores=pd.read_parquet(data.WORK/'minute_scores.parquet');plan=data.verify();maximum=0.;count=0
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
    result={'games':200,'scalar_half_scores_checked':count,'maximum_difference':maximum,'coverage_independently_verified':True,'all_joint_targets_legal':True};create_json(Path(output) if output is not None else data.WORK/'minute_audit.json',result);return result

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

if __name__=='__main__':print(minute_audit())
