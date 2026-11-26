"""Uncapped chronological conditional-actor examples from the audited C03 builder."""
from __future__ import annotations
import argparse,gc,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pyarrow as pa
from analysis import c03_data as old
from analysis.c01_workbench import read,create_json
from analysis.c01_core import ContractError
from analysis.c06_core import dates_before
from basketball_common import sha256_file
WORK=ROOT/'data/derived/experiments/c06_actor_full_history_v1';CONTRACT=ROOT/'analysis/c06_contract_v1.json'


def sources():
    return {**old.sources(),**{str(p.relative_to(ROOT)):sha256_file(p) for p in (CONTRACT,Path(__file__),ROOT/'analysis/c06_core.py')}}


def actor_rows(a):
    a=old.subset(a,a['y']<40);a['y']=a['y']//8
    if not np.isin(a['y'],np.arange(5)).all():raise ContractError('invalid actor label')
    return a


def prepare():
    old.verify();p=old.bench.pinned();sig=sources();start=time.monotonic();WORK.mkdir(parents=True,exist_ok=False);summaries=[];hashes={};reads=[]
    for year in range(2023,2027):
        a,s,r=old.build(year,p['game_ids'],'training');a=actor_rows(a);dates_before(a['date_et'].tolist(),'2025-12-31');name=f'year{year}.npz';old.save(WORK/name,a);hashes[name]=sha256_file(WORK/name);s.update(actor_actions=len(a['y']),train=int((a['date_et']<='2025-09-30').sum()),selection=int(((a['date_et']>='2025-10-01')&(a['date_et']<='2025-11-30')).sum()),final=int((a['date_et']<='2025-12-31').sum()));summaries.append(s);reads+=r;print('C06 uncapped source block',s,flush=True);del a;gc.collect()
    a=actor_rows(old.load('panel'));old.save(WORK/'panel.npz',a);hashes['panel.npz']=sha256_file(WORK/'panel.npz');panel={'events':len(a['y']),'games':len(np.unique(a['game_id']))}
    if sig!=sources():raise ContractError('C06 source changed during build')
    result={'sources':sig,'game_ids':p['game_ids'],'references':p['references'],'source_reads':reads,'blocks':summaries,'panel':panel,'artifacts':hashes,'sample_cap':None,'sorted_slots':'C03 builder sorts exact seg_id then player string; all five source-player candidates retained','production_changed':False,'seconds':time.monotonic()-start};create_json(WORK/'data.json',result);create_json(ROOT/'analysis/experiments/20261126_c06_data_v1.json',{k:v for k,v in result.items() if k not in ('game_ids','references','source_reads')})


def verify():
    p=read(WORK/'data.json')
    if p['sources']!=sources() or any(sha256_file(WORK/k)!=h for k,h in p['artifacts'].items()):raise ContractError('C06 pinned source/arrays changed')
    return p


def load(name):
    if name=='panel':
        with np.load(WORK/'panel.npz',allow_pickle=False) as z:return {k:z[k] for k in z.files}
    parts=[]
    for year in range(2023,2027):
        with np.load(WORK/f'year{year}.npz',allow_pickle=False) as z:a={k:z[k] for k in z.files}
        day=a['date_et'];mask=day<='2025-09-30' if name=='train' else (day>='2025-10-01')&(day<='2025-11-30') if name=='selection' else day<='2025-12-31' if name=='final' else None
        if mask is None:raise ContractError('unknown actor block')
        if mask.any():parts.append(old.subset(a,mask))
    return old.combine(parts)

if __name__=='__main__':
    pa.set_cpu_count(1);pa.set_io_thread_count(1);p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','verify']);a=p.parse_args();prepare() if a.stage=='prepare' else print(verify()['blocks'])
