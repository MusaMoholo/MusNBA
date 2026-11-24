#!/usr/bin/env python3
"""Benchmark original full-chunk observer parity before extending nightly delivery."""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import sys,os,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from basketball_common import read_json,write_json,sha256_file
from scripts import engine,visible_worlds

def worker(job):
 gid,branch,start,stop=job
 selected=read_json(ROOT/f'data/derived/experiments/c4_visible_selection_v1/{gid}.json')
 return visible_worlds.replay_chunk(engine.Engine('v1.3',runtime=engine.ENGINE),ROOT/f'data/snapshots/2026-11-23/lineups/{gid}',selected,branch,start,stop,
  ROOT/f'data/derived/experiments/c4_replay_probe_v1/{gid}/{start:05d}-{stop:05d}.json')

def main():
 out=ROOT/'analysis/experiments/20261124_c4_replay_probe_v1.json'
 if out.exists():raise FileExistsError(out)
 if any(os.environ.get(k)!='1' for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS']):raise ValueError('one OMP/BLAS thread')
 jobs=[]
 for gid in ['401910036','401910042']:
  selection=read_json(ROOT/f'data/derived/experiments/c4_visible_selection_v1/{gid}.json');e=selection['examples'][0]
  jobs.append((gid,e['branch_id'],e['chunk_start'],e['chunk_stop']))
 start=time.monotonic()
 with ProcessPoolExecutor(max_workers=2) as pool:rows=list(pool.map(worker,jobs))
 write_json(out,{'kind':'two original full1k source chunks, read-only exact zone/segment capture','receipts':rows,
  'elapsed_seconds':time.monotonic()-start,'workers':2,'source_sha256':{p:sha256_file(ROOT/p) for p in ['scripts/engine.py','scripts/world_detail.py','scripts/visible_worlds.py','scripts/lineup_forecast.py']},'source_accuracy_scored':False},pretty=True)
 print('2/2 original full1k chunks raw-exact; zone/segment/box/seconds accounting passed',flush=True)
if __name__=='__main__':main()
