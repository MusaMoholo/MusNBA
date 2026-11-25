"""Full chronological joint-role training data; targets never enter same-origin inputs."""
from __future__ import annotations
import argparse,sys,time
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import pyarrow as pa
from analysis import c01_benchmark as bench,c03_data as c03
from analysis.c04_core import COLS,inputs,prior
from analysis.c01_workbench import read,create_json
from analysis.c01_core import ContractError
from basketball_common import NBA_TEAM_IDS,sha256_file
from scripts import minutes
WORK=ROOT/'data/derived/experiments/c04_joint_roles_v1';CONTRACT=ROOT/'analysis/c04_contract_v1.json'
CUPS={'401607495','401734908','401809839'}

def features(pg,rosters=None):
    """All per-player outcomes are consumed only after their origin's features are emitted."""
    pg=pg.sort_values(['date_et','game_id','team','player'],kind='stable').reset_index(drop=True)
    if pg.duplicated(['date_et','player']).any():raise ContractError('same-day player ambiguity')
    base,_,_=minutes.state_pass(pg,ramp=None);base=base.set_index(['game_id','player'])
    history=defaultdict(list);out=[]
    for (day,gid,team),part in pg.groupby(['date_et','game_id','team'],sort=False):
        rows=[]
        visible=part[part.player.isin(rosters[gid])] if rosters and gid in rosters else part
        for r in visible.itertuples():
            h=history[r.player];prior([v[0] for v in h],day);v=np.array([x[1] for x in h],float);starts=np.array([x[2] for x in h],float)
            def ew(a,hl,default):
                if not len(a):return default
                w=np.exp2(-np.arange(len(a)-1,-1,-1)/hl);return float(w@a/w.sum())
            b=base.loc[(gid,r.player)]
            f=dict(n_history=len(h),last1=v[-1] if len(v) else 10.,mean3=v[-3:].mean() if len(v) else 10.,mean10=v[-10:].mean() if len(v) else 10.,sd10=v[-10:].std() if len(v)>1 else 6.,ewm5=ew(v,5,10),ewm20=ew(v,20,10),start5=ew(starts,5,0),start20=ew(starts,20,0),days_since=min(365,(pd.Timestamp(day)-pd.Timestamp(h[-1][0])).days) if h else 365,team_changed=float(bool(h) and h[-1][3]!=team))
            f.update({k:float(b[k]) for k in ('healthy','cap','priority','start_share','missed','k_back','alloc')})
            rows.append({**f,'game_id':gid,'player':r.player,'team':team,'date_et':day,'reg':r.reg,'sec':r.sec})
        f=pd.DataFrame(rows);f['alloc']=minutes.allocate(f.healthy.to_numpy(),f.cap.to_numpy(),f.priority.to_numpy(),gamma=0,room=1);f['roster_n']=len(f);f['healthy_sum']=f.healthy.sum();f['mean10_sum']=f.mean10.sum();f['healthy_rank']=f.healthy.rank(method='average',ascending=False)/len(f);f['alloc_gap']=f.alloc-f.alloc.mean();inputs(f[COLS]);out.extend(f.to_dict('records'))
        for r in part.itertuples():history[r.player].append((day,float(r.reg),float(r.starter),team))
    return pd.DataFrame(out)

def sources():
    paths=[CONTRACT,Path(__file__),ROOT/'analysis/c04_core.py',ROOT/'scripts/minutes.py',bench.WORK/'plan.json']+[ROOT/f'data/derived/history/{y}/{n}.parquet' for y in range(2023,2027) for n in ('on_court','segments')]
    return {str(p.relative_to(ROOT)):sha256_file(p) for p in paths}

def prepare():
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    if WORK.exists():raise FileExistsError(WORK)
    p=bench.pinned();last=max(r['date_et'] for r in p['references']);sig=sources();frames=[];reads=[];bad=[]
    cols=['game_id','date_et','season','season_type','team','player','pos','starter','sec']+[f'm{k:02d}' for k in range(1,49)]
    for year in range(2023,2027):
        filters=[('date_et','>=','2022-12-01'),('date_et','<=',last),('season_type','==',2)]
        seg=pd.read_parquet(ROOT/f'data/derived/history/{year}/segments.parquet',filters=filters,columns=['game_id','date_et','game_ok','offense','defense'])
        ids=seg.loc[seg.game_ok&seg.offense.isin(NBA_TEAM_IDS)&seg.defense.isin(NBA_TEAM_IDS)&~seg.game_id.isin(CUPS),'game_id'].unique().tolist()
        f=pd.read_parquet(ROOT/f'data/derived/history/{year}/on_court.parquet',filters=[*filters,('game_id','in',ids)],columns=cols)
        for k in ('game_id','team','player'):f[k]=f[k].astype(str)
        f=f[f.team.isin(NBA_TEAM_IDS)&f.sec.gt(0)].copy();f['reg']=f[[f'm{k:02d}' for k in range(1,49)]].sum(1);f=f.drop(columns=[f'm{k:02d}' for k in range(1,49)])
        sums=f.groupby(['game_id','team']).reg.sum();invalid=set(sums[~np.isclose(sums,240,rtol=0,atol=1e-6)].index.get_level_values(0));bad+=sorted(invalid) # observational reconciliation flags; never rescale or discard declared panel truth
        frames.append(f);reads.append({'year':year,'rows':len(f),'games':f.game_id.nunique(),'predicate':filters,'flagged_reconstructed_minute_games':len(invalid)});print('Full-history read',reads[-1],flush=True)
    pg=pd.concat(frames,ignore_index=True).sort_values(['date_et','game_id','team','player']);WORK.mkdir(parents=True)
    if set(p['game_ids'])-set(pg.game_id):raise ContractError('missing panel minute truth')
    if pg.duplicated(['game_id','player']).any() or not pg.reg.between(0,48).all():raise ContractError('invalid minute source rows')
    started=time.monotonic();f=features(pg,{r['game_id']:r['captured_player_ids'] for r in p['references']});f.to_parquet(WORK/'rows.parquet',index=False)
    # Native forecast draws and source truth must have identical player keys.
    for ref in p['references']:
        q=f[f.game_id.eq(ref['game_id'])]
        if set(q.player)!=set(ref['captured_player_ids']):raise ContractError('native/player minute support differs')
    if sig!=sources():raise ContractError('source changed during role data build')
    result={'sources':sig,'game_ids':p['game_ids'],'references':p['references'],'features':COLS,'source_reads':reads,'flagged_reconstructed_minute_ids':bad,'training_rows':int(f.date_et.le('2025-12-31').sum()),'selection_rows':int(f.date_et.between('2025-10-01','2025-11-30').sum()),'calibration_rows':int(f.date_et.between('2025-12-01','2025-12-31').sum()),'panel_rows':int(f.game_id.isin(p['game_ids']).sum()),'total_rows':len(f),'rows_sha256':sha256_file(WORK/'rows.parquet'),'seconds':time.monotonic()-started,'source_population':'actual participants with original reconstructed regulation seconds, reconciliation flags retained; no current starter/label features','production_changed':False}
    create_json(WORK/'data.json',result);create_json(ROOT/'analysis/experiments/20261125_c04_data_v1.json',{k:v for k,v in result.items() if k not in ('game_ids','references','flagged_reconstructed_minute_ids')})

def verify():
    p=read(WORK/'data.json')
    if p['sources']!=sources() or sha256_file(WORK/'rows.parquet')!=p['rows_sha256']:raise ContractError('C04 source/role rows changed')
    return p

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','verify']);a=p.parse_args();prepare() if a.stage=='prepare' else print(verify()['training_rows'])
