#!/usr/bin/env python3
"""One exact S06 current-r3 screen with private audited worlds and aggregate reports."""
from concurrent.futures import ProcessPoolExecutor,as_completed
from pathlib import Path
import sys,os,time,copy,argparse
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import pyarrow as pa
from basketball_common import read_json,write_json,sha256_file
from scripts import backtest,engine,state_rotations,a1_substitution_engine as old,lineup_forecast
from scripts.late_clock import ContextClock
from analysis import rule3_confirmation as paired,rule3_capture_audit as audit
from analysis.c2_engine_runner import CLOCK,CLOCK_REPORT,REFERENCE
RECIPE=ROOT/'analysis/experiments/20261124_c3_frozen_recipe_v1.json'
MANIFEST=ROOT/'analysis/experiments/20261124_c3_engine_runtime_v3.json'
STATE={}

def sources():
 recipe=read_json(RECIPE);model=read_json(ROOT/recipe['model_report'])
 paths=[RECIPE,Path(__file__),ROOT/recipe['features'],ROOT/recipe['model_report'],ROOT/'analysis/experiments/20261124_c3_input_audit_v1.json',ROOT/'analysis/experiments/20261124_c3_default_off_parity_v1.json']
 paths += [ROOT/f'scripts/{name}.py' for name in ['state_rotations','a1_substitution_engine','foul_out','engine','lineup_forecast']]
 paths += [ROOT/p for p in model['output_sha256']]
 paths += [ROOT/'analysis/rule3_confirmation.py',ROOT/'analysis/rule3_capture_audit.py']
 return {str(p.relative_to(ROOT)):sha256_file(p) for p in sorted(set(paths))}

def reference_receipt(gid):
 records=read_json(ROOT/'analysis/experiments/20261124_c2_engine_development_v2.json')['captures']
 row=next(r for r in records if r['game']==gid)['arms']['reference']
 path=ROOT/row['receipt']
 if sha256_file(path)!=row['sha256']:raise ValueError('C2 reference receipt changed')
 return path

def unchanged_reference():
 # Compare every C2 input/model/source fingerprint except its controller and newly composable observer.
 prior=read_json(ROOT/'analysis/experiments/20261124_c2_engine_runtime_v2.json')['source_sha256']
 changed=[]
 for name,digest in prior.items():
  if name in ['analysis/c2_engine_runner.py','analysis/rule3_confirmation.py']:continue
  if sha256_file(ROOT/name)!=digest:changed.append(name)
 return changed

def freeze():
 if MANIFEST.exists():raise FileExistsError(MANIFEST)
 a=read_json(ROOT/'analysis/experiments/20261124_c3_input_audit_v1.json')
 if a['max_proxy_error']!=0 or a['development_games_covered']!=200:raise ValueError('input reproduction incomplete')
 parity=read_json(ROOT/'analysis/experiments/20261124_c3_default_off_parity_v1.json')
 if len(parity['games'])!=3 or not all(r['all_raw_arrays_identical'] for r in parity['games']):raise ValueError('default parity incomplete')
 changed=unchanged_reference()
 if changed:raise ValueError(f'C2 reference sources changed:{changed}')
 recipe=read_json(RECIPE);panels=read_json(ROOT/recipe['panels_from'])
 write_json(MANIFEST,{'kind':'single unchanged S06 policy test, r3 Rule3 legality and independent fitting',
  'development':panels['development_F4'],'wiring':panels['development_F4'][:3],
  'worlds':1000,'seed_key':'v1.2d_F4','source_sha256':sources(),'reference_source_changes':changed,
  'earlier_preparation_repairs':'filtered all-source schedule to NBA regular-season games before any proxy output; no change to model/target recipe',
  'original_prepare_sha256':read_json(RECIPE)['source_sha256']['analysis/c3_prepare.py'],
  'current_prepare_sha256':sha256_file(ROOT/'analysis/c3_prepare.py')},pretty=True)
 print('Frozen3-game wiring and200-game MIN-primary screen; exact C2 r3 controls eligible after wiring parity',flush=True)

def init_worker():
 pa.set_cpu_count(1);backtest._W.clear()
 backtest._init(REFERENCE,str(ROOT/'models/v1.2d.json'),'F4',1000,rotation='targets',pool=0,seed_key='v1.2d_F4')
 eng=backtest._W['engine'];eng.runtime={**engine.ENGINE,'models':REFERENCE,'clock_recipe':CLOCK}
 training=read_json(ROOT/CLOCK_REPORT)['folds']['F4']['training']
 eng.clock_policy=ContextClock(read_json(ROOT/CLOCK),training['cells'])
 recipe=read_json(RECIPE)
 STATE['outgoing'],STATE['incoming'],STATE['timing']=old.load_candidate(ROOT/recipe['model_report'],'F4')
 STATE['features']=pd.read_parquet(ROOT/recipe['features'])

def policy():
 return state_rotations.StateRotations(STATE['outgoing'],STATE['incoming'],STATE['timing'],STATE['features'])

def raw_state(st):
 return {'minutes':st.minutes.copy(),'points':st.pts.copy(),'period':st.period.copy(),'possessions':st.poss.copy(),
         **{'box_'+k:v.copy() for k,v in st.box.items()}}

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
  eng.rotation_policy=policy()
  try:pub=lineup_forecast.simulate(eng,saved['game'],saved['worlds'],saved['seed'])
  finally:eng.rotation_policy=None
  replay=raw_state(eng.last)
  if any(not np.array_equal(replay[k],v,equal_nan=True) for k,v in saved['raw'].items()):raise ValueError('publication selected-policy raw arrays differ')
  public={'all_raw_arrays_identical':True,'checked_fives':pub['counts']['independently_checked_fives'],'timeout_outgoing':pub['counts']['timeout_outgoing']}
 out={'game':gid,'arm':arm,'entry':entry,'audit':checked,'publication_parity':public,'seconds':time.monotonic()-started}
 write_json(receipt,out,pretty=False)
 return str(receipt.relative_to(ROOT))

def run(phase,jobs):
 plan=read_json(MANIFEST)
 if sources()!=plan['source_sha256'] or unchanged_reference():raise ValueError('frozen input/source changed')
 ids=plan['wiring'] if phase=='wiring' else plan['development'];root=ROOT/f'data/derived/experiments/c3_engine_{phase}_v3'
 out=ROOT/f'analysis/experiments/20261124_c3_engine_{phase}_v3.json'
 if out.exists():raise FileExistsError(out)
 sig={'manifest_sha256':sha256_file(MANIFEST),'game_ids':ids}
 if root.exists():
  if read_json(root/'plan.json')!=sig:raise ValueError('resume signature differs')
 else:root.mkdir(parents=True);write_json(root/'plan.json',sig,pretty=True)
 done={};pending=[];references={};start=time.monotonic()
 for gid in ids:
  oldreceipt=reference_receipt(gid)
  reference=read_json(oldreceipt)
  if sha256_file(ROOT/reference['entry']['capture'])!=reference['entry']['sha256']:raise ValueError('reference capture changed')
  references[gid]=reference
  for arm in (('reference','candidate') if phase=='wiring' else ('candidate',)):
   receipt=root/gid/arm/'receipt.json'
   if not receipt.exists() and phase=='development' and gid in plan['wiring']:
    receipt=ROOT/f'data/derived/experiments/c3_engine_wiring_v3/{gid}/{arm}/receipt.json'
   if receipt.exists():
    row=read_json(receipt)
    if sha256_file(ROOT/row['entry']['capture'])!=row['entry']['sha256']:raise ValueError('saved arm changed')
    done[gid,arm]=(row,receipt)
   else:pending.append((gid,arm,str(root),phase=='wiring' and arm=='candidate'))
 if phase=='development':
  wiring=read_json(ROOT/'analysis/experiments/20261124_c3_engine_wiring_v3.json')
  if len(wiring['reference_raw_parity'])!=3 or len(wiring['publication_raw_parity'])!=3:raise ValueError('wiring parity incomplete')
  for gid,row in references.items():done[gid,'reference']=(row,reference_receipt(gid))
 init_worker();STATE.clear();backtest._W.clear()
 total=len(ids)*2;finished=len(done)
 if pending:
  with ProcessPoolExecutor(max_workers=min(jobs,len(pending)),initializer=init_worker) as pool:
   for f in as_completed([pool.submit(task,job) for job in pending]):
    path=ROOT/f.result();row=read_json(path);done[row['game'],row['arm']]=(row,path);finished+=1
    if phase=='wiring' or finished%20==0:print(f'{finished}/{total} arms complete ({len(references) if phase=="development" else 0} references reused);{time.monotonic()-start:.1f}s',flush=True)
 if sources()!=plan['source_sha256']:raise ValueError('source changed during run')
 parity=[];publication=[]
 if phase=='wiring':
  for gid in ids:
   if done[gid,'reference'][0]['entry']['world_sha256']!=references[gid]['entry']['world_sha256']:raise ValueError('r3 reference raw parity differs')
   parity.append(gid)
   if not done[gid,'candidate'][0]['publication_parity']['all_raw_arrays_identical']:raise ValueError('publication parity differs')
   publication.append(gid)
 outputs={}
 for arm in ('reference','candidate'):
  values=[copy.deepcopy(done[gid,arm][0]['entry']['result']) for gid in ids];players=[r for row in values for r in row.pop('players')]
  name=f'c3_engine_{phase}_v3_{arm}'
  for path,frame in [(ROOT/f'data/derived/experiments/{name}.parquet',pd.DataFrame(values)),(ROOT/f'data/derived/experiments/{name}_players.parquet',pd.DataFrame(players))]:
   if path.exists():raise FileExistsError(path)
   frame.to_parquet(path,index=False);outputs[str(path.relative_to(ROOT))]=sha256_file(path)
  path=ROOT/f'analysis/experiments/{name}.json'
  write_json(path,{'run':name,'fold':'F4','games':len(ids),'game_ids':ids,'worlds':1000,'models':REFERENCE,'config':'models/v1.2d.json','rotation':'targets','pool':0,'known_starters':False,'simulation_stream':None,'seed_key':'v1.2d_F4','kind':'research only conditional participants'},pretty=True)
 receipts=[{'game':gid,'arm':arm,'receipt':str(done[gid,arm][1].relative_to(ROOT)),'sha256':sha256_file(done[gid,arm][1])} for gid in ids for arm in ('reference','candidate')]
 write_json(out,{'kind':'C3 exact S06 screen; no promotion','game_ids':ids,'worlds':1000,'arms':2,'reference_raw_parity':parity,'publication_raw_parity':publication,'receipts':receipts,'derived_outputs':outputs,'seconds':time.monotonic()-start,'fresh_jobs':len(pending),'production_model_changed':False},pretty=True)
 print(f'{phase} complete:{len(ids)} games,2 arms; no promotion',flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','wiring','development']);p.add_argument('--jobs',type=int,default=10);a=p.parse_args()
 if not 1<=a.jobs<=10 or any(os.environ.get(k)!='1' for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS']):raise ValueError('max10 single-thread workers')
 if a.action=='freeze':freeze()
 else:run(a.action,a.jobs)
