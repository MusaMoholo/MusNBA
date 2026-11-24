#!/usr/bin/env python3
"""Paired process-isolated memory/time measurement; no output changes or accuracy scoring."""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import multiprocessing,pickle,resource,time,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from basketball_common import read_json,write_json
from scripts import engine,lineup_forecast,projection,visible_worlds

def task(detailed):
 folder=ROOT/'data/snapshots/2026-11-23/lineups/401910036'
 with (folder/'inputs.pkl').open('rb') as f:saved=pickle.load(f)
 runtime={**saved['runtime']}
 if detailed:runtime['world_details']='visible-worlds-v1'
 model=engine.Engine(runtime['models'],runtime=runtime);model.m.median=saved['median']
 batch=read_json(folder/'work-plan.json')['batches'][0]
 selected=read_json(ROOT/'data/derived/experiments/c4_visible_selection_v1/401910036.json')
 from collections import Counter
 start_chunk=max(Counter(e['chunk_start'] for e in selected['examples']).items(),key=lambda pair:(pair[1],-pair[0]))[0]
 seed=projection.seed_for('world-chunk-v1',int(batch['seed']),start_chunk,start_chunk+1000)
 if detailed:
  from scripts.world_detail import WorldDetail
  model.world_observer=WorldDetail([e['within_chunk'] for e in selected['examples'] if e['chunk_start']==start_chunk])
 start=time.monotonic();raw=lineup_forecast.simulate(model,saved['game'],1000,seed)['raw'];seconds=time.monotonic()-start
 with np.load(folder/'capture.npz',allow_pickle=False) as old:
  for k in old.files:
   expected=old[k] if k in ('player_ids','side') else old[k][start_chunk:start_chunk+1000]
   if not np.array_equal(raw[k],expected):raise ValueError('paired benchmark raw differs:'+k)
 return {'capture':detailed,'seconds':seconds,'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'worlds':1000,'chunk_start':start_chunk,'selected_examples':sum(e['chunk_start']==start_chunk for e in selected['examples']) if detailed else 0,'raw_exact':True}

def main():
 out=ROOT/'analysis/experiments/20261124_c4_capture_benchmark_v1.json'
 if out.exists():raise FileExistsError(out)
 with ProcessPoolExecutor(max_workers=2,mp_context=multiprocessing.get_context('spawn'),max_tasks_per_child=1) as pool:rows=list(pool.map(task,[False,True]))
 delta=rows[1]['peak_rss_bytes']-rows[0]['peak_rss_bytes']
 if delta>1073741824:raise ValueError('capture exceeds frozen extraRSS limit')
 write_json(out,{'kind':'isolated paired original1k capture CPU/RSS benchmark; macOS ru_maxrss bytes','runs':rows,'extra_rss_bytes':delta,'extra_seconds':rows[1]['seconds']-rows[0]['seconds'],'rss_limit_bytes':1073741824,'extra_rss_passed':True,'limits':'One game/chunk under concurrent confirmation load; final full-nightly time acceptance remains separate.'},pretty=True)
 print('Capture benchmark:',rows,'deltaRSS',delta,flush=True)
if __name__=='__main__':main()
