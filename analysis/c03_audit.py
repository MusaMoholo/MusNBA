"""Independent source/feature, probability and saved-score checks for C03."""
from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from types import SimpleNamespace
import numpy as np
import pandas as pd
from unittest.mock import patch
from analysis import c03_data as data,c02_data as old,c02_accounting as accounting
data.pa.set_cpu_count(1);data.pa.set_io_thread_count(1)
from analysis.c03_choices import CONTEXT,PLAYER
from analysis.c02_features import View
from analysis.c01_localise import start_histories
from analysis.c01_workbench import read,create_json
from analysis.c01_core import ContractError
from basketball_common import sha256_file
from scripts import nodes


def parity(output=None):
    """Reconstruct counters from source events, then compare runtime causal view to arrays."""
    p=data.verify();a=data.load('panel');output=Path(output or data.WORK/'feature_parity.json')
    if output.exists():raise FileExistsError(output)
    with data.Boundary(p['game_ids'],'panel').installed(),patch.object(nodes,'segment_files',return_value=[ROOT/'data/derived/history/2026/segments.parquet']):
        seg=nodes.load_segments();pre=pd.read_parquet(old.PROFILE);teams=pd.read_parquet(old.PROFILE.parent/'team_pregame.parquet')
    mismatches=0;count=0;maximum=0.;comparisons=0
    for j,ref in enumerate(p['references']):
        gid=ref['game_id'];mask=a['game_id']==gid;q=data.subset(a,mask);keys=q['seg_id'];full=seg[seg.game_id.eq(gid)].copy()
        ids=sorted(set(full[[f'{side}_{k}' for side in ('off','def') for k in range(1,6)]].to_numpy().ravel())- {None})
        # Source roster/lineup IDs, rather than simulated participating-player order, define feature support.
        ids=[x for x in ids if pd.notna(x)];lookup={v:i for i,v in enumerate(ids)}
        g=SimpleNamespace(game={'game_id':gid,'home_id':ref['home'],'away_id':ref['away']},ids=ids,day=ref['date_et'])
        hist=start_histories(full,ids);pick=full.reset_index(drop=True).reset_index().set_index('seg_id').loc[keys,'index'].to_numpy();s=full.set_index('seg_id').loc[keys];n=len(s);A=np.arange(n)
        lo=np.vectorize(lookup.__getitem__)(np.sort(s[[f'off_{k}' for k in range(1,6)]].to_numpy(),axis=1));ld=np.vectorize(lookup.__getitem__)(np.sort(s[[f'def_{k}' for k in range(1,6)]].to_numpy(),axis=1))
        off=np.where(s.off_home,0,1);score=np.zeros((n,2));fouls=np.zeros((n,2));score[A,off]=s.score_off;score[A,1-off]=s.score_def;fouls[A,off]=s.fouls_off;fouls[A,1-off]=s.fouls_def
        st=SimpleNamespace(off=off,period=s.period.to_numpy(),clock=s.start_clock.to_numpy(),score=score,tfouls=fouls,start=s.start_code.to_numpy(),ingame={k:v[pick].copy() for k,v in hist.items()})
        view=View(g,pre,teams);ctx=view.context(g,st,A,lo,ld);ctx['shot_time']=s.shot_time.to_numpy(np.float32)
        for lineup in (lo,ld):st.ingame['sec_so_far'][A[:,None],lineup]+=s.shot_time.to_numpy(np.float32)[:,None]
        five=view.five(st,A,lo)
        for x,y in [(np.column_stack([ctx[k] for k in CONTEXT]),q['context']),(np.stack([five[k] for k in PLAYER],axis=2),q['players'])]:
            same=np.isclose(x,y,atol=1e-5,rtol=1e-5,equal_nan=True);mismatches+=int((~same).sum());comparisons+=x.size;d=np.abs(x-y);finite=np.isfinite(d)
            if finite.any():maximum=max(maximum,float(d[finite].max()))
        # Label arithmetic independent of builder's vectorised mapping.
        for i,r in enumerate(s.itertuples()):
            y=int(q['y'][i])
            if y<40:
                actor=list(np.sort([getattr(r,f'off_{k}') for k in range(1,6)])).index(r.actor)
                label=nodes.ZONES.index(r.zone) if r.end_type=='shot' else 5 if r.end_type=='turnover' else 7 if r.fta>=3 else 6
                if y!=8*actor+label:raise ContractError('independent choice label differs')
            elif y!={'foul':40,'violation':41,'jump_ball':41,'turnover':42}[r.end_type]:raise ContractError('independent actorless label differs')
        count+=n
        if (j+1)%40==0:print('C03 independent feature/label check',j+1,'/200',flush=True)
    result={'games':200,'events':count,'feature_values_checked':comparisons,'mismatches':mismatches,'max_absolute_difference':maximum,'independent_history_and_label_checks':True}
    create_json(output,result)
    if mismatches:raise ContractError('C03 feature parity mismatch')
    return result


def check_saved(ids):
    count=0;worlds=0;maximum=0.;arms=set()
    for gid in ids:
        folder=data.WORK/'rollout'/gid;r=read(folder/'receipt.json');arrays={}
        if any(sha256_file(folder/k)!=v for k,v in r['hashes'].items()):raise ContractError('C03 saved game hash changed')
        for arm in r['arms']:
            with np.load(folder/f'{arm}.npz',allow_pickle=False) as z:arrays[arm]={k:z[k] for k in z.files}
            accounting.check_arrays(arrays[arm]);worlds+=1000;arms.add(arm)
        scores=pd.read_parquet(folder/'scores.parquet')
        for row in scores.itertuples():
            a=arrays[row.model]
            if row.entity=='player':i=a['player_ids'].tolist().index(row.player);x=a['minutes'][:,i] if row.stat=='min' else a[row.stat][:,i]
            elif row.entity=='team':x=a['team'][:,0 if row.side=='home' else 1]
            else:x=a['team'].sum(1) if row.stat=='total' else a['team'][:,0]-a['team'][:,1]
            for expected,part in [(row.crps,x),(row.crps_half1,x[:500]),(row.crps_half2,x[500:])]:
                delta=abs(accounting.reference_crps(part,row.truth)-expected);count+=1;maximum=max(maximum,delta)
                if delta>1e-10:raise ContractError('independent C03 CRPS differs')
        for row in pd.read_parquet(folder/'joint.parquet').itertuples():
            x=arrays[row.model]['team'];prob=float((x[:,0]>x[:,1]).mean())
            if abs(prob-row.p_home)>1e-12 or abs((prob-row.home_won)**2-row.win_brier)>1e-12:raise ContractError('independent C03 win score differs')
    return {'games':len(ids),'arms':sorted(arms),'worlds':worlds,'scalar_and_half_scores_checked':count,'maximum_score_difference':maximum,'all_saved_accounting_passed':True}

if __name__=='__main__':print(parity())
