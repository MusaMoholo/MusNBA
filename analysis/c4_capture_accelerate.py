#!/usr/bin/env python3
"""Finish a disjoint tail while the original two capture workers are paused.
The original workers resume afterwards and verify/reuse these identical receipts.
"""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
import sys,time,os
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from basketball_common import read_json,write_json,sha256_file
from analysis import c4_capture_retained as original
PLAN=ROOT/'analysis/experiments/20261124_c4_capture_tail_runtime_v1.json'
OUT=ROOT/'analysis/experiments/20261124_c4_capture_tail_v1.json'

def freeze():
 if PLAN.exists():raise FileExistsError(PLAN)
 baseline=read_json(original.FROZEN)
 if original.sources()!=baseline['sources']:raise ValueError('source changed')
 tasks=baseline['tasks'];complete=[i for i,t in enumerate(tasks) if original.path_for(*t).with_suffix('.receipt.json').exists()]
 # With two original workers, the current task index is at most max completed+2.
 # Leave two additional queued positions untouched as well. Both workers must be STOPped.
 first=max(complete,default=-1)+5
 paused=read_json(ROOT/'data/derived/experiments/c4_browser_pause_v1.json')
 import subprocess
 states=subprocess.check_output(['ps','-p',','.join(map(str,paused['workers'])),'-o','state='],text=True).split()
 if len(states)!=2 or any(not state.startswith('T') for state in states):raise ValueError('both original workers must be paused')
 write_json(PLAN,{'kind':'mechanical disjoint tail acceleration; only process assignment changes','original_runtime_sha256':sha256_file(original.FROZEN),'sources':baseline['sources'],'tasks':tasks[first:],'first_index':first,'original_task_count':len(tasks),'workers':8,'original_workers_paused':paused['workers'],'reason':'confirmation workers have completed; keep compute queue occupied without editing running sources or colliding with original in-flight chunks'},pretty=True)
 print('Frozen disjoint tail',first,'through',len(tasks)-1,flush=True)

def run():
 if OUT.exists():raise FileExistsError(OUT)
 plan=read_json(PLAN)
 if original.sources()!=plan['sources']:raise ValueError('source changed')
 start=time.monotonic();done=0;rows=[];total=len(plan['tasks'])
 with ProcessPoolExecutor(max_workers=8,initializer=original.init) as pool:
  for f in as_completed([pool.submit(original.task,tuple(t)) for t in plan['tasks']]):
   rows.append(f.result());done+=1
   if done%max(1,total//10)==0 or done==total:print(f'{done}/{total} disjoint tail chunks exact;{time.monotonic()-start:.1f}s',flush=True)
 if original.sources()!=plan['sources']:raise ValueError('source changed')
 write_json(OUT,{'kind':'original full-chunk source/seed unchanged, verified independent worker assignment','plan_sha256':sha256_file(PLAN),'chunks':len(rows),'worlds':sum(row['worlds_replayed'] for row in rows),'all_raw_exact':all(r['raw_arrays_exact'] for r in rows),'workers':8,'seconds':time.monotonic()-start,'original_resume':'resume both original workers; they verify/reuse this tail without simulation'},pretty=True)
 print('Disjoint tail complete; resume original two workers',flush=True)
if __name__=='__main__':
 if any(os.environ.get(k)!='1' for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS']):raise ValueError('single thread required')
 freeze() if sys.argv[1]=='freeze' else run()
