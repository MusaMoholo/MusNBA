"""Independent raw-event history versus cached training/runtime feature meanings."""
from __future__ import annotations
from pathlib import Path
from types import SimpleNamespace
import sys
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import pyarrow as pa
from scripts import nodes
from analysis import c02_data as data
from analysis.c02_features import View,selected
from analysis.c01_localise import start_histories
from analysis.c01_core import ContractError
from analysis.c01_workbench import read,read_panel,create_json
from basketball_common import sha256_file


def run(output=None):
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    plan=data.verify();ids=plan['game_ids'];output=Path(output or data.WORK/'feature_parity.json')
    if output.exists():raise FileExistsError(output)
    with data.Boundary(ids,'panel').installed(),patch.object(nodes,'segment_files',return_value=[ROOT/'data/derived/history/2026/segments.parquet']):
        seg=nodes.load_segments();pre=pd.read_parquet(data.PROFILE);teams=pd.read_parquet(data.PROFILE.parent/'team_pregame.parquet')
    cached={n:pd.read_parquet(data.WORK/f'panel_{n}.parquet') for n in ('who','what')}
    totals={};count=0;unsupported=0
    for j,ref in enumerate(plan['references']):
        gid=ref['game_id'];g=SimpleNamespace(game={'game_id':gid,'home_id':ref['home'],'away_id':ref['away']},ids=ref['captured_player_ids'],day=ref['date_et'])
        s=seg[seg.game_id.eq(gid)].copy();lookup={p:i for i,p in enumerate(g.ids)};hist=start_histories(s,g.ids)
        known=s[[f'{side}_{i}' for side in ('off','def') for i in range(1,6)]].isin(g.ids).all(axis=1).to_numpy()
        unsupported+=int((~known).sum());s=s[known].copy();n=len(s);A=np.arange(n)
        lo=np.vectorize(lookup.__getitem__)(np.sort(s[[f'off_{i}' for i in range(1,6)]].to_numpy(),axis=1))
        ld=np.vectorize(lookup.__getitem__)(np.sort(s[[f'def_{i}' for i in range(1,6)]].to_numpy(),axis=1))
        off=np.where(s.off_home,0,1);score=np.zeros((n,2));fouls=np.zeros((n,2))
        score[A,off]=s.score_off;score[A,1-off]=s.score_def;fouls[A,off]=s.fouls_off;fouls[A,1-off]=s.fouls_def
        st=SimpleNamespace(off=off,period=s.period.to_numpy(),clock=s.start_clock.to_numpy(),score=score,tfouls=fouls,start=s.start_code.to_numpy(),ingame={k:v[known].copy() for k,v in hist.items()})
        for lineup in (lo,ld):st.ingame['sec_so_far'][A[:,None],lineup]+=s.shot_time.to_numpy()[:,None]
        view=View(g,pre,teams);ctx=view.context(g,st,A,lo,ld);ctx['shot_time']=s.shot_time.to_numpy(np.float32)
        five=view.five(st,A,lo);who={**{k:np.repeat(v,5) for k,v in ctx.items()},**{k:v.ravel() for k,v in five.items()},'foul_event':np.repeat(s.end_type.eq('foul').to_numpy(np.float32),5)}
        actors=s.actor.map(lookup).fillna(-1).to_numpy(int);slot=np.argmax(lo==actors[:,None],axis=1)
        what={**ctx,**view.actor(five,slot)}
        for name,cols in (('who',who),('what',what)):
            f=pd.DataFrame(selected(name,cols));f['seg_id']=np.repeat(s.seg_id.to_numpy(),5) if name=='who' else s.seg_id.to_numpy()
            expected=cached[name][cached[name].game_id.eq(gid)].copy()
            keep=f.seg_id.isin(expected.seg_id);f=f[keep].reset_index(drop=True);expected=expected.reset_index(drop=True)
            if not np.array_equal(f.seg_id.to_numpy(),expected.seg_id.to_numpy()):raise ContractError('source/runtime parity keys differ')
            for c in data.COLS[name]:
                a,b=f[c].to_numpy(float),expected[c].to_numpy(float);same=np.isclose(a,b,atol=1e-5,rtol=1e-5,equal_nan=True)
                delta=np.abs(a-b);finite=np.isfinite(delta);key=f'{name}/{c}'
                r=totals.setdefault(key,{'rows':0,'mismatches':0,'max_abs_error':0.})
                r['rows']+=len(a);r['mismatches']+=int((~same).sum());r['max_abs_error']=max(r['max_abs_error'],float(delta[finite].max()) if finite.any() else 0.)
        count+=n
        if (j+1)%40==0:print('Independent event feature parity',j+1,'/200',flush=True)
    result={'kind':'C02 runtime feature view versus cached datasets; independent raw-event histories','games':200,'recorded_segments':count,'unsupported_roster_segments':unsupported,
        'features':totals,'mismatches':sum(v['mismatches'] for v in totals.values()),'view_sha256':sha256_file(ROOT/'analysis/c02_features.py'),
        'parity_source_sha256':sha256_file(Path(__file__)),'no_candidate_predictions':True}
    create_json(output,result)
    if result['mismatches']:raise ContractError('candidate feature parity mismatch; inspect immutable receipt')
    print({k:v for k,v in result.items() if k!='features'},flush=True);return result

if __name__=='__main__':run()
