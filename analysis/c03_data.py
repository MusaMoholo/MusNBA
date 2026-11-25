"""C03 immutable common event arrays, outcome-blind sampling and source lineage."""
from __future__ import annotations
import argparse,gc,sys
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import pyarrow as pa
from analysis import c02_data as old,c01_benchmark as bench,c01_contexts as context
from analysis.c03_choices import CONTEXT,PLAYER,validate_inputs
from analysis.c01_workbench import read,create_json
from analysis.c01_core import ContractError
from basketball_common import sha256_file
from scripts import nodes

WORK=ROOT/'data/derived/experiments/c03_possession_options_v1'
CONTRACT=ROOT/'analysis/c03_contract_v1.json'
class Boundary(old.Boundary):
    def read(self,path,*args,**kwargs):
        # The inherited C02 lower bound is deliberately replaced, without editing its closed source.
        p=Path(path)
        if self.mode=='training' and p.name in ('segments.parquet','pregame.parquet','team_pregame.parquet'):
            kwargs['filters']=context.and_filters(kwargs.get('filters'),[('date_et','>=','2022-12-01')])
        if p.name=='segments.parquet':kwargs['filters']=context.and_filters(kwargs.get('filters'),[('game_id','not in',old.CUPS),('season_type','==',2)])
        return context.SourceBoundary.read(self,path,*args,**kwargs)

def unpack(a):
    return ({k:a['context'][:,i] for i,k in enumerate(CONTEXT)}, {k:a['players'][:,:,i] for i,k in enumerate(PLAYER)})

def subset(a,idx):return {k:v[idx] for k,v in a.items()}
def combine(parts):return {k:np.concatenate([p[k] for p in parts]) for k in parts[0]}
def save(path,a):
    with Path(path).open('xb') as f:np.savez_compressed(f,**a)
def load(name):
    with np.load(WORK/f'{name}.npz',allow_pickle=False) as z:return {k:z[k] for k in z.files}

def build(year,ids,mode):
    access=Boundary(ids,mode)
    with access.installed(),patch.object(nodes,'segment_files',return_value=[ROOT/f'data/derived/history/{year}/segments.parquet']),patch.object(nodes.Chain,'_relative',old.causal_relative):
        chain=nodes.Chain(pregame=old.PROFILE);s=chain.seg
        if 'lineup_valid' in s:s=s[s.lineup_valid]
        keep=s.end_type.isin(['shot','fouled','turnover','foul','violation','jump_ball'])
        s=s[keep].copy();team=s.end_type.eq('turnover')&s.actor.isna()
        ev=np.select([s.end_type.eq('foul'),s.end_type.isin(['violation','jump_ball']),team],[1,2,3],0)
        actor_ok=pd.DataFrame({i:s.actor.eq(s[f'off_{i}']) for i in range(1,6)}).any(axis=1)
        valid=(ev!=0)|(actor_ok & ~s.heave & (~s.end_type.eq('shot')|s.zone.isin(nodes.ZONES)))
        excluded=int((~valid).sum());s=s[valid].copy();ev=ev[valid]
        off=chain.off[chain.off.seg_id.isin(s.seg_id)].sort_values(['seg_id','player'])
        if not off.groupby('seg_id').size().eq(5).all():raise ContractError('incomplete five')
        s=s.set_index('seg_id').loc[off.seg_id.to_numpy()[::5]].reset_index()
        # Restore event labels after sorting by exact source key.
        team=s.end_type.eq('turnover')&s.actor.isna()
        ev=np.select([s.end_type.eq('foul'),s.end_type.isin(['violation','jump_ball']),team],[1,2,3],0)
        slot=(off.player.to_numpy().reshape(-1,5)==s.actor.to_numpy()[:,None]).argmax(1)
        action=np.where(s.end_type.eq('shot'),s.zone,np.where(s.end_type.eq('turnover'),'turnover',np.where(s.fta>=3,'fouled_3','fouled_2')))
        act=pd.Series(action).map(dict(zip(nodes.WHAT,range(8)))).fillna(0).to_numpy(int)
        y=np.where(ev==0,slot*8+act,39+ev)
        ctx=s[CONTEXT].to_numpy(np.float32);players=off[PLAYER].to_numpy(np.float32).reshape(-1,5,len(PLAYER))
        players[:,:,PLAYER.index('sec_so_far')]+=s.shot_time.to_numpy(np.float32)[:,None]
        a={'context':ctx,'players':players,'y':y,'seg_id':s.seg_id.to_numpy(),'game_id':s.game_id.to_numpy(str),'date_et':s.date_et.to_numpy(str)}
        validate_inputs(*unpack(a),a['date_et'],mode=='training')
        summary={'year':year,'supported':len(s),'excluded_actions':excluded,'games':s.game_id.nunique(),'first':str(s.date_et.min()),'last':str(s.date_et.max())}
    del chain;gc.collect();return a,summary,access.reads

def sources():
    paths=[CONTRACT,Path(__file__),ROOT/'analysis/c03_choices.py',old.PROFILE,old.PROFILE.parent/'team_pregame.parquet',old.PROFILE.parent/'features_report.json',ROOT/'scripts/nodes.py',ROOT/'scripts/features.py',ROOT/'analysis/c02_data.py',ROOT/'analysis/c01_contexts.py',bench.WORK/'plan.json']
    paths +=[ROOT/f'data/derived/history/{y}/segments.parquet' for y in range(2023,2027)]
    return {str(p.relative_to(ROOT)):sha256_file(p) for p in paths}

def sample(a,cap):
    h=pd.util.hash_pandas_object(pd.Series(a['seg_id']),index=False,hash_key='0123456789123456').to_numpy()
    idx=np.argsort(h,kind='stable')[:cap];idx=idx[np.lexsort((a['seg_id'][idx],a['date_et'][idx]))]
    return subset(a,idx)

def prepare():
    if WORK.exists():raise FileExistsError(WORK)
    report=read(old.PROFILE.parent/'features_report.json')
    if not all(report.get(k) for k in ('causal_first_priors','causal_positions','history_only')) or report.get('body') or report.get('matchup'):raise ContractError('unqualified feature lineage')
    p=bench.pinned();sig=sources();WORK.mkdir(parents=True);parts=[];summaries=[];reads=[]
    for year in range(2023,2027):
        a,s,r=build(year,p['game_ids'],'training');summaries.append(s);reads+=r
        # Each block's global smallest hashes are among its per-year smallest hashes.
        for label,mask,cap in [('train',a['date_et']<='2025-09-30',60000),('selection',a['date_et']>='2025-10-01',15000)]:
            q=subset(a,mask)
            if len(q['y']):parts.append((label,sample(q,cap)))
        print('Source build',s,flush=True);del a;gc.collect()
    for label,cap in [('train',60000),('selection',15000)]:save(WORK/f'{label}.npz',sample(combine([a for tag,a in parts if tag==label]),cap))
    del parts;gc.collect();a,s,r=build(2026,p['game_ids'],'panel');save(WORK/'panel.npz',a);summaries.append(s);reads+=r
    if sources()!=sig:raise ContractError('source changed during C03 data build')
    result={'sources':sig,'game_ids':p['game_ids'],'references':p['references'],'source_builds':summaries,'source_reads':reads,'features':{'context':CONTEXT,'player':PLAYER},'artifacts':{f'{n}.npz':sha256_file(WORK/f'{n}.npz') for n in ('train','selection','panel')},'production_changed':False}
    create_json(WORK/'data.json',result);create_json(ROOT/'analysis/experiments/20261125_c03_data_v1.json',{k:v for k,v in result.items() if k not in ('game_ids','references','source_reads')})

def verify():
    p=read(WORK/'data.json')
    if p['sources']!=sources():raise ContractError('C03 source changed')
    if any(sha256_file(WORK/k)!=v for k,v in p['artifacts'].items()):raise ContractError('C03 common arrays changed')
    return p

if __name__=='__main__':
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','verify']);a=p.parse_args()
    prepare() if a.stage=='prepare' else print(verify()['source_builds'])
