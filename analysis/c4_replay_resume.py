#!/usr/bin/env python3
"""Interrupt after one real original-chunk replay, then prove verified resume.
Reuse the two raw, seed-identical chunks from the completed real queue trial;
a single-thread executor permits controlled fault injection without shared-engine races.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import sys,pickle,shutil,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from basketball_common import read_json,write_json,sha256_file
from scripts import live_forecast as live,engine,a1_lineup_branches as branches

def main():
 out=ROOT/'analysis/experiments/20261124_c4_replay_resume_v1.json'
 folder=ROOT/'data/derived/experiments/c4_replay_resume_v1/game'
 if out.exists() or folder.exists():raise FileExistsError('immutable fault-injection namespace exists')
 source=ROOT/'data/derived/experiments/c4_queue_integration_v1/game';plan=read_json(source/'work-plan.json')
 with (source/'inputs.pkl').open('rb') as f:saved=pickle.load(f)
 runtime=saved['runtime'];selected=[branches.SelectedPlayer(**p) for p in plan['selected']]
 live._ENGINE=engine.Engine(runtime['models'],runtime=runtime);live._ENGINE.m.median=saved['median']
 fingerprint=live.fingerprints(runtime)
 provenance={'origin':saved['game'].input_before,'sources':fingerprint,'kind':'isolated real replay interruption; raw verified chunks reused; no forecast publication'}
 task=(saved['game'],selected,1000,str(folder),provenance)
 def chunk(job):
  batch=next(b for b in plan['batches'] if b['branch_id']==job['plan']['branch_id'])
  if int(batch['seed'])!=int(job['plan']['seed']) or job['start']!=0 or job['stop']!=1000:raise ValueError('raw reuse seed/group differs')
  name='00000-01000.npz';old=Path(batch['chunks'])/name;new=Path(job['plan']['chunks'])/name
  shutil.copyfile(old,new);shutil.copyfile(old.with_suffix('.json'),new.with_suffix('.json'))
  if not live.verified_chunk(job['plan'],0,1000):raise ValueError('reused raw chunk failed verification')
  return read_json(new.with_suffix('.json'))
 original=live._replay;attempts=[];compute=[];injected=False
 def replay(job):
  nonlocal injected
  attempts.append(job['branch'])
  if not injected and len(attempts)==2:
   injected=True;raise RuntimeError('intentional interruption before second replay compute')
  if not live._replay_path(job).exists():compute.append(job['branch'])
  return original(job)
 start=time.monotonic()
 with patch.object(live,'ProcessPoolExecutor',ThreadPoolExecutor),patch.object(live,'initialise'),patch.object(live,'_chunk',side_effect=chunk),patch.object(live,'_replay',side_effect=replay):
  try:list(live.run([task],runtime,saved['median'],workers=1))
  except RuntimeError as error:
   if 'intentional interruption' not in str(error):raise
  else:raise ValueError('fault did not stop queue')
  if live.verified_completion(folder) or len(compute)!=1:raise ValueError('incomplete game qualified for publication')
  first=next((folder/'replay-chunks').glob('*.receipt.json'));digest=sha256_file(first);count_before=len(compute)
  completed=list(live.run([task],runtime,saved['median'],workers=1,resume=True))
 if completed!=[str(folder)] or not live.verified_completion(folder):raise ValueError('resumed game did not complete exactly once')
 if sha256_file(first)!=digest or len(compute)-count_before!=1:raise ValueError('completed replay was recomputed or changed')
 if live.fingerprints(runtime)!=fingerprint:raise ValueError('source changed during fault-injection trial')
 write_json(out,{'kind':'controlled interruption after one real full1k replay; exact verified resume','raw_chunks_reused':2,'original_seed_group_verified':True,'first_run_actual_replays':count_before,'resume_actual_replays':len(compute)-count_before,'first_replay_receipt_unchanged':True,'partial_game_ineligible':True,'completed_game_events':len(completed),'final_receipt_sha256':sha256_file(folder/'completion.json'),'seconds':time.monotonic()-start,'executor':'one thread, real engine/replay with deterministic fault injection; multiprocessing/parallel scheduling tested separately','published':False,'sources':fingerprint},pretty=True)
 print('Replay interruption/resume passed: old receipt unchanged, only missing1k replay computed, one final game event',flush=True)
if __name__=='__main__':main()
