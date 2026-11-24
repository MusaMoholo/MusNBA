#!/usr/bin/env python3
"""Enrich retained forecasts by full original-chunk replay, without changing their outcomes."""
from concurrent.futures import ProcessPoolExecutor,as_completed
from pathlib import Path
import argparse,sys,os,time,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from basketball_common import read_json,write_json,sha256_file
from scripts import engine,visible_worlds
OUTPUT=ROOT/'analysis/experiments/20261124_c4_retained_capture_v1.json'
FROZEN=ROOT/'analysis/experiments/20261124_c4_retained_runtime_v1.json'
DIRECTORY=ROOT/'data/derived/experiments/c4_retained_capture_v1'
MODEL=None
FILES=['scripts/engine.py','scripts/world_detail.py','scripts/visible_worlds.py','scripts/lineup_forecast.py','scripts/player_worlds.py','scripts/shot_zones.py','analysis/c4_capture_retained.py']
def sources():return {p:sha256_file(ROOT/p) for p in FILES}
def init():
 global MODEL
 MODEL=engine.Engine('v1.3',runtime=engine.ENGINE)
def path_for(gid,branch,start,stop):return DIRECTORY/gid/(hashlib.sha256(branch.encode()).hexdigest()[:12]+f'-{start:05d}-{stop:05d}.json')
def task(job):
 gid,branch,start,stop=job;selection=read_json(ROOT/f'data/derived/experiments/c4_visible_selection_v1/{gid}.json')
 return visible_worlds.replay_chunk(MODEL,ROOT/f'data/snapshots/2026-11-23/lineups/{gid}',selection,branch,start,stop,path_for(*job))
def main(jobs):
 if OUTPUT.exists():raise FileExistsError(OUTPUT)
 selection=read_json(ROOT/'analysis/experiments/20261124_c4_example_selection_v1.json');tasks=[]
 for row in selection['games']:
  gid=row['game'];plan=read_json(ROOT/f'data/snapshots/2026-11-23/lineups/{gid}/work-plan.json')
  for batch in plan['batches']:
   tasks.extend((gid,batch['branch_id'],start,min(start+batch['chunk_worlds'],batch['worlds'])) for start in range(0,batch['worlds'],batch['chunk_worlds']))
 current={'sources':sources(),'selection_sha256':sha256_file(ROOT/'analysis/experiments/20261124_c4_example_selection_v1.json'),'tasks':tasks,'workers':jobs}
 from basketball_common import packed
 if FROZEN.exists():
  if read_json(FROZEN)!=__import__('json').loads(packed(current)):raise ValueError('retained capture source/plan changed')
 else:write_json(FROZEN,current,pretty=True)
 started=time.monotonic();done=[]
 with ProcessPoolExecutor(max_workers=jobs,initializer=init) as pool:
  for f in as_completed([pool.submit(task,t) for t in tasks]):
   done.append(f.result())
   if len(done)%max(1,len(tasks)//10)==0 or len(done)==len(tasks):print(f'{len(done)}/{len(tasks)} original full chunks reconciled;{time.monotonic()-started:.1f}s',flush=True)
 if sources()!=current['sources']:raise ValueError('capture code changed during replay')
 reports=[]
 for row in selection['games']:
  gid=row['game'];selected=read_json(ROOT/row['private_selection']);paths=[path_for(*t) for t in tasks if t[0]==gid]
  folder=DIRECTORY/gid
  result=visible_worlds.finish_replays(selected,paths,folder/'replay.json','v1.3','engine-v1.3-r3')
  zones=visible_worlds.collect_zones(ROOT/f'data/snapshots/2026-11-23/lineups/{gid}',selected,paths,folder/'zones.npz')
  reports.append({'game':gid,**result,'replay':str((folder/'replay.json').relative_to(ROOT)),
                  'zone_worlds':zones['zone_worlds'],'court':str((folder/'zones.json').relative_to(ROOT))})
 write_json(OUTPUT,{'kind':'retained original-world enrichment; no forecast/model/outcome changes','runtime_sha256':sha256_file(FROZEN),'games':reports,'original_chunks':len(tasks),'worlds_replayed':sum(t[3]-t[2] for t in tasks),'examples':sum(r['examples'] for r in reports),'seconds':time.monotonic()-started},pretty=True)
 print('All original chunks exact; complete zone worlds and50 reconciled examples saved',flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--jobs',type=int,choices=[1,2],default=2);a=p.parse_args()
 if any(os.environ.get(k)!='1' for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS']):raise ValueError('single-thread workers')
 main(a.jobs)
