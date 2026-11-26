"""Independent source labels/in-game counters versus C06 cached feature rows."""
from __future__ import annotations
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import pyarrow as pa
from scripts import nodes
from analysis import c06_data as data,c03_data as old
from analysis.c02_features import View
from analysis.c01_localise import start_histories
from analysis.c06_core import pack,CONTEXT,PLAYER
from analysis.c01_workbench import create_json
from analysis.c01_core import ContractError


def run(output=None):
    pa.set_cpu_count(1);pa.set_io_thread_count(1);plan=data.verify();output=Path(output or data.WORK/'parity.json')
    if output.exists():raise FileExistsError(output)
    ids=plan['game_ids']
    with old.Boundary(ids,'panel').installed(),patch.object(nodes,'segment_files',return_value=[ROOT/'data/derived/history/2026/segments.parquet']):
        seg=nodes.load_segments();pre=pd.read_parquet(old.old.PROFILE);teams=pd.read_parquet(old.old.PROFILE.parent/'team_pregame.parquet')
    cached=data.load('panel');checked=0;labels=0;unsupported=0;maximum=0.;names=CONTEXT+PLAYER;mismatches={k:0 for k in names}
    for j,ref in enumerate(plan['references']):
        gid=ref['game_id'];g=SimpleNamespace(game={'game_id':gid,'home_id':ref['home'],'away_id':ref['away']},ids=ref['captured_player_ids'],day=ref['date_et']);s=seg[seg.game_id.eq(gid)].copy();lookup={p:i for i,p in enumerate(g.ids)};hist=start_histories(s,g.ids);known=s[[f'{side}_{i}' for side in ('off','def') for i in range(1,6)]].isin(g.ids).all(axis=1).to_numpy();unsupported+=int((~known).sum());s=s[known].copy();n=len(s);A=np.arange(n)
        lo=np.vectorize(lookup.__getitem__)(np.sort(s[[f'off_{i}' for i in range(1,6)]].to_numpy(),axis=1));ld=np.vectorize(lookup.__getitem__)(np.sort(s[[f'def_{i}' for i in range(1,6)]].to_numpy(),axis=1));off=np.where(s.off_home,0,1);score=np.zeros((n,2));fouls=np.zeros((n,2));score[A,off]=s.score_off;score[A,1-off]=s.score_def;fouls[A,off]=s.fouls_off;fouls[A,1-off]=s.fouls_def
        st=SimpleNamespace(off=off,period=s.period.to_numpy(),clock=s.start_clock.to_numpy(),score=score,tfouls=fouls,start=s.start_code.to_numpy(),ingame={k:v[known].copy() for k,v in hist.items()})
        for lineup in (lo,ld):st.ingame['sec_so_far'][A[:,None],lineup]+=s.shot_time.to_numpy()[:,None]
        view=View(g,pre,teams);ctx=view.context(g,st,A,lo,ld);ctx['shot_time']=s.shot_time.to_numpy(np.float32);five=view.five(st,A,lo);actual=pack({k:ctx[k] for k in CONTEXT},{k:five[k] for k in PLAYER}).reshape(n,5,-1)
        take=np.flatnonzero(cached['game_id']==gid);index=pd.Series(take,index=cached['seg_id'][take]);match=index.reindex(s.seg_id);keep=match.notna().to_numpy();ix=match[keep].to_numpy(int);expected=pack(*old.unpack(old.subset(cached,ix))).reshape(len(ix),5,-1);observed=actual[keep];same=np.isclose(expected,observed,rtol=1e-5,atol=1e-5,equal_nan=True);delta=abs(expected-observed);finite=np.isfinite(delta);maximum=max(maximum,float(delta[finite].max()) if finite.any() else 0.)
        for k,count in zip(names,(~same).sum((0,1))):mismatches[k]+=int(count)
        actors=s.actor.map(lookup).fillna(-1).to_numpy(int);slot=np.argmax(lo==actors[:,None],axis=1)
        if not np.array_equal(slot[keep],cached['y'][ix]):raise ContractError('independent source actor labels differ')
        checked+=expected.size;labels+=len(ix)
        if (j+1)%50==0:print('C06 independent feature/actor parity',j+1,'/200',flush=True)
    result={'games':200,'feature_values_checked':checked,'actor_labels_checked':labels,'unsupported_roster_segments':unsupported,'maximum_absolute_difference':maximum,'feature_mismatches':mismatches,'all_features_match':not any(mismatches.values()),'labels_match':True,'scope':'Raw recorded event counters rebuilt before each action; known captured-roster subset only, full support and exclusions retained.'};create_json(output,result)
    if any(mismatches.values()):raise ContractError('C06 independent feature parity differs')
    return result

if __name__=='__main__':print(run())
