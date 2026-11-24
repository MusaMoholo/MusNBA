#!/usr/bin/env python3
"""Frozen independent S06 F4 confirmation in isolated C3 checkout; no promotion."""
from concurrent.futures import ProcessPoolExecutor,as_completed
from pathlib import Path
import os,sys,time,copy,argparse
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import pyarrow as pa
from basketball_common import read_json,write_json,sha256_file
from scripts import backtest,engine,state_rotations,a1_substitution_engine as old,lineup_forecast,foul_out
from scripts.late_clock import ContextClock
from analysis import rule3_confirmation as paired,rule3_capture_audit as audit
from analysis.c2_engine_runner import CLOCK,CLOCK_REPORT,REFERENCE
RECIPE=ROOT/'analysis/experiments/20261124_c3_frozen_recipe_v1.json'
SURVIVOR=ROOT/'analysis/experiments/20261124_c3_survivor_v1.json'
MANIFEST=ROOT/'analysis/experiments/20261124_c4_s06_runtime_v1.json'
STATE={}

def sources():
 prior=read_json(ROOT/'analysis/experiments/20261124_c3_engine_runtime_v3.json')['source_sha256']
 # Every frozen C3 source is local to this detached checkout or immutable shared data.
 hashes={p:sha256_file(ROOT/p) for p in prior}
 for p,digest in prior.items():
  if hashes[p]!=digest:raise ValueError(f'C3 source changed:{p}')
 for p in [Path(__file__),SURVIVOR]:hashes[str(p.relative_to(ROOT))]=sha256_file(p)
 return hashes

def freeze():
 if MANIFEST.exists():raise FileExistsError(MANIFEST)
 contract=read_json(SURVIVOR);ready=read_json(ROOT/contract['panels_from'])
 ids=ready[contract['independent_primary']['panel_key']]
 if len(ids)!=200 or set(ids)&set(ready['development_F4']):raise ValueError('independent panel overlaps development')
 if read_json(ROOT/'analysis/experiments/20261124_c3_gate_v1.json')['decision']!='development_scores_compatible':raise ValueError('no C3 survivor')
 write_json(MANIFEST,{'kind':'prospective independent200 F4 S06; frozen C3 checkout; no promotion',
  'checkout_commit':'08677dc','wiring':ids[:3],'confirmation':ids,'worlds':1000,'seed_key':'v1.2d_F4','primary':'players/all/min/crps','policy':'v3',
  'source_sha256':sources(),'control_reuse':'Fresh references: old A2 sources differ from current C3 controls, and reserved panel is disjoint from C3. Reuse only six verified current wiring arms.',
  'workers':8,'omp_threads':1,'blas_threads':1,'arrow_threads':1},pretty=True)
 print('Frozen independent200/three-case wiring; eight single-thread workers, fresh matched references',flush=True)

def init_worker():
 pa.set_cpu_count(1);backtest._W.clear()
 backtest._init(REFERENCE,str(ROOT/'models/v1.2d.json'),'F4',1000,rotation='targets',pool=0,seed_key='v1.2d_F4')
 eng=backtest._W['engine'];eng.runtime={**engine.ENGINE,'models':REFERENCE,'clock_recipe':CLOCK}
 training=read_json(ROOT/CLOCK_REPORT)['folds']['F4']['training']
 if training['cutoff']!='2025-12-31' or training['latest_training_date']>training['cutoff']:raise ValueError('clock fit crosses origin')
 eng.clock_policy=ContextClock(read_json(ROOT/CLOCK),training['cells'])
 recipe=read_json(RECIPE)
 STATE['outgoing'],STATE['incoming'],STATE['timing']=old.load_candidate(ROOT/recipe['model_report'],'F4')
 STATE['features']=pd.read_parquet(ROOT/recipe['features'])

def policy():return state_rotations.StateRotations(STATE['outgoing'],STATE['incoming'],STATE['timing'],STATE['features'])
def raw_state(st):return {'minutes':st.minutes.copy(),'points':st.pts.copy(),'period':st.period.copy(),'possessions':st.poss.copy(),**{'box_'+k:v.copy() for k,v in st.box.items()}}

def task(job):
 gid,arm,directory,publish_check=job;folder=Path(directory)/gid/arm;folder.mkdir(parents=True,exist_ok=True)
 receipt=folder/'receipt.json'
 if receipt.exists():raise FileExistsError(receipt)
 eng=backtest._W['engine'];original=eng.simulate;saved={};started=time.monotonic()
 def simulate(g,worlds,seed):
  result=original(g,worlds,seed)
  if publish_check:saved.update(game=g,worlds=worlds,seed=seed,raw=raw_state(eng.last))
  return result
 factory=(lambda label:policy()) if arm=='candidate' else None
 with patch.object(eng,'simulate',side_effect=simulate):
  result=paired.paired_game((gid,str(folder)),labels=('candidate',),corrected=(True,True),persist=False,policy_factory=factory)
 entry=result['outputs']['candidate']
 with np.load(ROOT/entry['capture'],allow_pickle=False) as z:data={k:z[k] for k in z.files}
 if audit.capture_digest(data)!=entry['world_sha256']:raise ValueError('world digest differs')
 checked=audit.audit_worlds({**data,'trace_phase':data['trace_phase'].astype(np.int16)},foul_penalty=True)
 checked.update(audit.team_fouls(data,True));audit.audit_metrics(data,entry['result'])
 public=None
 if publish_check:
  eng.rotation_policy=policy() if arm=='candidate' else foul_out.Rule3Policy()
  try:pub=lineup_forecast.simulate(eng,saved['game'],saved['worlds'],saved['seed'])
  finally:eng.rotation_policy=None
  replay=raw_state(eng.last)
  if any(not np.array_equal(replay[k],v,equal_nan=True) for k,v in saved['raw'].items()):raise ValueError('publication raw arrays differ')
  public={'all_raw_arrays_identical':True,'checked_fives':pub['counts']['independently_checked_fives']}
 write_json(receipt,{'game':gid,'arm':arm,'entry':entry,'audit':checked,'publication_parity':public,'seconds':time.monotonic()-started},pretty=False)
 return str(receipt.relative_to(ROOT))

def run(phase,jobs):
 plan=read_json(MANIFEST)
 if sources()!=plan['source_sha256']:raise ValueError('frozen sources changed')
 ids=plan['wiring'] if phase=='wiring' else plan['confirmation'];root=ROOT/f'data/derived/experiments/c4_s06_{phase}_v1'
 out=ROOT/f'analysis/experiments/20261124_c4_s06_{phase}_v1.json'
 if out.exists():raise FileExistsError(out)
 sig={'manifest_sha256':sha256_file(MANIFEST),'game_ids':ids}
 if root.exists():
  if read_json(root/'plan.json')!=sig:raise ValueError('resume signature differs')
 else:root.mkdir(parents=True);write_json(root/'plan.json',sig,pretty=True)
 done={};pending=[];start=time.monotonic()
 if phase=='confirmation':
  wiring=read_json(ROOT/'analysis/experiments/20261124_c4_s06_wiring_v1.json')
  if len(wiring['publication_raw_parity'])!=6:raise ValueError('six wiring publication identities required')
 for gid in ids:
  for arm in ('reference','candidate'):
   receipt=root/gid/arm/'receipt.json'
   if not receipt.exists() and phase=='confirmation' and gid in plan['wiring']:receipt=ROOT/f'data/derived/experiments/c4_s06_wiring_v1/{gid}/{arm}/receipt.json'
   if receipt.exists():
    row=read_json(receipt)
    if row['game']!=gid or row['arm']!=arm or sha256_file(ROOT/row['entry']['capture'])!=row['entry']['sha256']:raise ValueError('completed arm changed')
    done[gid,arm]=(row,receipt)
   else:
    folder=root/gid/arm
    if folder.exists() and any(folder.iterdir()):raise ValueError('partial arm requires inspection, no overwrite')
    pending.append((gid,arm,str(root),phase=='wiring'))
 init_worker();STATE.clear();backtest._W.clear();total=len(ids)*2;finished=len(done)
 if pending:
  with ProcessPoolExecutor(max_workers=min(jobs,len(pending)),initializer=init_worker) as pool:
   for f in as_completed([pool.submit(task,job) for job in pending]):
    path=ROOT/f.result();row=read_json(path);done[row['game'],row['arm']]=(row,path);finished+=1
    if phase=='wiring' or finished%40==0:print(f'{finished}/{total} arms complete;{time.monotonic()-start:.1f}s',flush=True)
 if sources()!=plan['source_sha256']:raise ValueError('sources changed during run')
 outputs={}
 for arm in ('reference','candidate'):
  values=[copy.deepcopy(done[gid,arm][0]['entry']['result']) for gid in ids];players=[r for row in values for r in row.pop('players')]
  name=f'c4_s06_{phase}_v1_{arm}'
  for path,frame in [(ROOT/f'data/derived/experiments/{name}.parquet',pd.DataFrame(values)),(ROOT/f'data/derived/experiments/{name}_players.parquet',pd.DataFrame(players))]:
   if path.exists():raise FileExistsError(path)
   frame.to_parquet(path,index=False);outputs[str(path.relative_to(ROOT))]=sha256_file(path)
  write_json(ROOT/f'analysis/experiments/{name}.json',{'run':name,'fold':'F4','games':len(ids),'game_ids':ids,'worlds':1000,'models':REFERENCE,'config':'models/v1.2d.json','rotation':'targets','pool':0,'known_starters':False,'simulation_stream':None,'seed_key':'v1.2d_F4','kind':'independent conditional-participant S06 research'},pretty=True)
 receipts=[{'game':gid,'arm':arm,'receipt':str(done[gid,arm][1].relative_to(ROOT)),'sha256':sha256_file(done[gid,arm][1])} for gid in ids for arm in ('reference','candidate')]
 public=[{'game':gid,'arm':arm} for gid in ids for arm in ('reference','candidate') if done[gid,arm][0]['publication_parity']]
 write_json(out,{'kind':'C4 independent S06 confirmation; no promotion','game_ids':ids,'worlds':1000,'arms':2,'publication_raw_parity':public,'receipts':receipts,'derived_outputs':outputs,'seconds':time.monotonic()-start,'fresh_jobs':len(pending),'production_model_changed':False},pretty=True)
 print(f'{phase} complete:{len(ids)} games,two arms; no promotion',flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','wiring','confirmation']);p.add_argument('--jobs',type=int,default=8);a=p.parse_args()
 if not 1<=a.jobs<=8 or any(os.environ.get(k)!='1' for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS']):raise ValueError('max8 single-thread workers; reserve2 for app checks')
 if a.action=='freeze':freeze()
 else:run(a.action,a.jobs)
