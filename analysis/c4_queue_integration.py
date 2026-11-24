#!/usr/bin/env python3
"""Real bounded C4 queue/resume test using saved pre-origin game inputs."""
from pathlib import Path
import os,sys,pickle,time
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from basketball_common import read_json,write_json,sha256_file
from scripts import live_forecast as live,engine,a1_lineup_branches as branches

def main():
 out=ROOT/'analysis/experiments/20261124_c4_queue_integration_v1.json'
 if out.exists():raise FileExistsError(out)
 source=ROOT/'data/snapshots/2026-11-23/lineups/401910037';plan=read_json(source/'work-plan.json')
 with (source/'inputs.pkl').open('rb') as f:saved=pickle.load(f)
 selected=[branches.SelectedPlayer(**p) for p in plan['selected']]
 folder=ROOT/'data/derived/experiments/c4_queue_integration_v1/game';runtime={**saved['runtime'],'world_details':'visible-worlds-v1'}
 provenance={'origin':saved['game'].input_before,'sources':live.fingerprints(runtime),'kind':'isolated real queue integration; no published forecast'}
 task=(saved['game'],selected,1000,str(folder),provenance);start=time.monotonic()
 completed=list(live.run([task],runtime,saved['median'],workers=1))
 if completed!=[str(folder)] or not live.verified_completion(folder):raise ValueError('complete queue output missing')
 hashes={str(p.relative_to(folder)):sha256_file(p) for p in folder.rglob('*') if p.is_file()}
 with patch.object(live,'ProcessPoolExecutor',side_effect=AssertionError('complete resume must not launch workers')):
  if list(live.run([task],runtime,saved['median'],workers=1,resume=True))!=completed:raise ValueError('resume differs')
  try:list(live.run([task],runtime,{**saved['median'],'future_injection':1},workers=1,resume=True))
  except ValueError as error:
   if 'changed inputs' not in str(error):raise
  else:raise ValueError('changed input accepted')
 if hashes!={str(p.relative_to(folder)):sha256_file(p) for p in folder.rglob('*') if p.is_file()}:raise ValueError('resume changed saved bytes')
 for batch in read_json(folder/'work-plan.json')['batches']:
  original=next(b for b in plan['batches'] if b['branch_id']==batch['branch_id'])
  with np.load(batch['capture'],allow_pickle=False) as actual,np.load(source/'branches'/Path(original['capture']).name,allow_pickle=False) as expected:
   for key in expected.files:
    value=expected[key] if key in ('player_ids','side') else expected[key][:1000]
    if not np.array_equal(actual[key],value):raise ValueError('original first full chunk differs:'+key)
 replay=read_json(folder/'replay.json');court=read_json(folder/'zones.json')
 if len(replay['examples'])!=5 or len(court['cases'])<3:raise ValueError('branch exploration incomplete')
 write_json(out,{'kind':'real two-branch1k queue, complete replay and unchanged-input resume','branches':len(plan['batches']),'worlds_per_branch':1000,'examples':len(replay['examples']),'cases':len(court['cases']),'original_full_chunk_raw_exact':True,'complete_resume_no_worker':True,'changed_input_rejected':True,'all_saved_bytes_preserved':True,'completion_sha256':sha256_file(folder/'completion.json'),'seconds':time.monotonic()-start,'workers':1,'published':False},pretty=True)
 print('Real queue passed: original raw identity, five examples, cases, complete resume/no workers, changed-input rejection',flush=True)
if __name__=='__main__':main()
