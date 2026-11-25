"""Immutable source-bound datasets for pure possession actor/action learning."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from datetime import datetime,timezone
import gc
from pathlib import Path
import sys
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import pyarrow as pa
from analysis.c01_core import ContractError
from analysis.c01_workbench import read,create_json,digest
from analysis import c01_contexts as old,c01_benchmark as bench
from basketball_common import sha256_file
from scripts import nodes

WORK=ROOT/'data/derived/experiments/c02_possession_v1'
CONTRACT=ROOT/'analysis/c02_contract_v1.json'
PROFILE=ROOT/read(CONTRACT)['profiles']
START='2024-10-01';CUTOFF='2025-12-31'
CUPS=['401607495','401734908','401809839']
COMMON=[c for c in nodes.CONTEXT if c!='season']+nodes.LINEUP+['shot_time']
WHO=list(dict.fromkeys(nodes.PROFILE+nodes.IN_GAME+['grp_code','usage_share','usage_rank','usage_mult_now']+COMMON+['foul_event']))
WHAT=list(dict.fromkeys(COMMON+[f'actor_{c}' for c in nodes.PROFILE+nodes.IN_GAME+['grp_code','usage_share','usage_rank','usage_mult_now']]))
COLS={'who':WHO,'what':WHAT}

class Boundary(old.SourceBoundary):
    def read(self,path,*args,**kwargs):
        p=Path(path)
        if self.mode=='training' and p.name in ('segments.parquet','pregame.parquet','team_pregame.parquet'):
            kwargs['filters']=old.and_filters(kwargs.get('filters'),[('date_et','>=',START)])
        if p.name=='segments.parquet':
            kwargs['filters']=old.and_filters(kwargs.get('filters'),[('game_id','not in',CUPS),('season_type','==',2)])
        return super().read(path,*args,**kwargs)


def validate(frame,name,training=False):
    if frame.empty or set(COLS[name])-set(frame):raise ContractError('missing possession features')
    if training and (frame.date_et.isna().any() or frame.date_et.lt(START).any() or frame.date_et.gt(CUTOFF).any()):
        raise ContractError('future/unknown possession training row')
    if np.isinf(frame[COLS[name]].to_numpy()).any():raise ContractError('infinite possession feature')
    if not np.isin(frame.y,[0,1] if name=='who' else np.arange(8)).all():raise ContractError('invalid action label')
    if name=='who':
        g=frame.groupby('seg_id',sort=False).y.agg(['size','sum'])
        if not g['size'].eq(5).all() or not g['sum'].eq(1).all():raise ContractError('actor candidates must be five with exactly one chosen')
        if not np.array_equal(frame.seg_id.to_numpy().reshape(-1,5),np.repeat(frame.seg_id.to_numpy()[::5,None],5,axis=1)):
            raise ContractError('actor groups not contiguous')
    return True


def build(ids,mode):
    access=Boundary(ids,mode)
    pack=nodes.Chain._pack
    def packed(self,name,kind,X,y,rows,classes=None,profile=None):
        out=pack(self,name,kind,X,y,rows,classes,profile);out['seg_id']=rows.seg_id.to_numpy();return out
    paths=[ROOT/f'data/derived/history/{y}/segments.parquet' for y in range(2023,2027)] if mode=='training' else [ROOT/'data/derived/history/2026/segments.parquet']
    with access.installed(),patch.object(nodes,'segment_files',return_value=paths),patch.object(nodes.Chain,'_pack',packed):
        chain=nodes.Chain(pregame=PROFILE)
        supported=chain.seg.actor.notna() & pd.DataFrame({i:chain.seg.actor.eq(chain.seg[f'off_{i}']) for i in range(1,6)}).any(axis=1)
        actor_support=pd.Series(supported.to_numpy(),index=chain.seg.seg_id)
        summary={'segments':len(chain.seg),'games':chain.seg.game_id.nunique(),'actor_outside_five':int((chain.seg.actor.notna()&~supported).sum()),
                 'earliest_date':str(chain.seg.date_et.min()),'latest_date':str(chain.seg.date_et.max())}
        result={}
        for name in ('who','what'):
            d=chain.dataset(name);groups=d.get('group',d.get('seg_id'))
            keep=actor_support.reindex(groups).fillna(False).to_numpy(bool)
            f=d['X'][COLS[name]].copy()
            # Runtime selects the actor after elapsed duration, before the action.
            sec='sec_so_far' if name=='who' else 'actor_sec_so_far'
            f[sec]=f[sec]+f.shot_time
            f['y']=d['y'];f['seg_id']=groups;f['game_id']=d['game'];f['date_et']=d['date']
            f=f[keep].sort_values('seg_id',kind='stable').reset_index(drop=True)
            validate(f,name,mode=='training');result[name]=f
            summary[name]={'rows':len(f),'events':f.seg_id.nunique(),'games':f.game_id.nunique(),'missing_by_feature':f[COLS[name]].isna().sum().astype(int).to_dict()}
    del chain;gc.collect()
    return result,summary,access.reads


def sources():
    paths=[CONTRACT,Path(__file__),ROOT/'analysis/c01_contexts.py',ROOT/'scripts/nodes.py',ROOT/'scripts/features.py',PROFILE,
           PROFILE.parent/'team_pregame.parquet',PROFILE.parent/'features_report.json',bench.WORK/'plan.json']
    paths += [ROOT/f'data/derived/history/{y}/segments.parquet' for y in range(2023,2027)]
    return {str(p.relative_to(ROOT)):sha256_file(p) for p in paths}


def prepare():
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    if WORK.exists():raise FileExistsError('immutable C02 namespace already exists')
    report=read(PROFILE.parent/'features_report.json')
    if not all(report.get(x) for x in ('causal_first_priors','causal_positions','history_only')) or report.get('body') or report.get('matchup'):
        raise ContractError('candidate profiles lack causal/body-free provenance')
    source=sources();p=bench.pinned();ids=p['game_ids']
    WORK.mkdir(parents=True)
    summaries={};access=[];artifacts={}
    for mode in ('training','panel'):
        data,summary,reads=build(ids,mode);summaries[mode]=summary;access+=reads
        for name,f in data.items():
            path=WORK/f'{mode}_{name}.parquet';f.to_parquet(path,index=False);artifacts[path.name]=sha256_file(path)
        del data;gc.collect();print(mode,summary['games'],summary['segments'],flush=True)
    if sources()!=source:raise ContractError('source changed during dataset build')
    plan={'kind':'C02 source-bound pure possession data; no candidate predictions','created_at':datetime.now(timezone.utc).isoformat(),
          'sources':source,'artifacts':artifacts,'game_ids':ids,'wiring_ids':ids[:20],'references':p['references'],'features':COLS,
          'data':summaries,'source_reads':access,'protected_or_reserved_outcomes_opened':False,'production_changed':False}
    create_json(WORK/'data.json',plan)
    create_json(ROOT/'analysis/experiments/20261125_c02_data_v1.json',{k:v for k,v in plan.items() if k not in ('source_reads','references','game_ids','wiring_ids')})
    print('C02 source dataset ready; no model fit or scores',flush=True)


def verify():
    p=read(WORK/'data.json')
    if p['sources']!=sources():raise ContractError('C02 source signature changed')
    for name,want in p['artifacts'].items():
        if sha256_file(WORK/name)!=want:raise ContractError('C02 dataset changed')
    return p

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['prepare','verify']);a=parser.parse_args()
    prepare() if a.stage=='prepare' else print(verify()['data'])
