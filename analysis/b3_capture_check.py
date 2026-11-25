"""Independent old-world parity, regulation-clock reconstruction and exact weighted aggregation."""
import os,sys,pickle,time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from basketball_common import read_json,write_json,sha256_file

def check(gid):
 from scripts import engine,lineup_forecast,a1_lineup_branches
 from scripts.rotation_maps import summarise,SECONDS
 from scripts.world_detail import WorldDetail
 folder=ROOT/f'data/snapshots/2026-11-24/lineups/{gid}'
 with (folder/'inputs.pkl').open('rb') as stream:saved=pickle.load(stream)
 plan=read_json(folder/'work-plan.json');batch=plan['batches'][0]
 capture=folder/'branches/branch-000.npz' if plan['selected'] else folder/'capture.npz'
 meta=read_json(capture.with_suffix('.json'));first=meta['execution']['chunks'][0]
 g=saved['game'];g=a1_lineup_branches.prepare_branch(g,[tuple(a) for a in batch['assignments']]) if batch['assignments'] else g
 eng=engine.Engine(saved['runtime']['models'],runtime=saved['runtime']);eng.m.median=saved['median']
 detail=WorldDetail([0]);eng.world_observer=detail;t=time.monotonic()
 raw=lineup_forecast.simulate(eng,g,first['stop']-first['start'],int(first['seed']))['raw']
 with np.load(capture,allow_pickle=False) as z:
  assert set(raw)-set(z.files)=={'rotation_presence'}
  for key in z.files:assert np.array_equal(raw[key],z[key] if key in ('player_ids','side') else z[key][first['start']:first['stop']]),key
 # Independently reconstruct one complete world's sampled presence from source-identified segment intervals.
 expected=np.zeros((g.n,48),np.uint8);lookup={str(pid):i for i,pid in enumerate(g.ids)}
 for e in detail.events[0]:
  if e['period']>4:continue
  for fives,before,after in [(e['lineups'],e['before_clock'],e['action_clock']),(e['lineups_after'],e['action_clock'],e['after_clock'])]:
   for j,tick in enumerate(SECONDS):
    if (e['period']-1)*720+720-before<=tick<(e['period']-1)*720+720-after:
     for five in fives:
      for pid in five:expected[lookup[pid],j]=1
 assert np.array_equal(expected,raw['rotation_presence'][0])
 weights=np.arange(len(raw['minutes']),dtype=np.int64)%7+1;summary=summarise(raw,weights)
 for i,pid in enumerate(g.ids):
  for j in range(48):assert summary['players'][str(pid)]['on_court_mass'][j]==int(weights[raw['rotation_presence'][:,i,j].astype(bool)].sum())
 return {'game':gid,'worlds':len(weights),'old_fields_exact':True,'independent_interval_capture_exact':True,'weighted_counts_exact':True,'source_sha256':sha256_file(capture),'seconds':time.monotonic()-t}
if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('--version',default='v1',choices=['v1','v2']);args=parser.parse_args()
 out=ROOT/f'analysis/experiments/20261125_b3_capture_parity_{args.version}.json';assert not out.exists()
 with ProcessPoolExecutor(max_workers=3) as pool:rows=list(pool.map(check,['401909314','401909315','401909316']))
 write_json(out,{'kind':'Three complete original1k chunks; every old raw field bit-exact plus independent interval/count checks','jobs':3,'inner_threads':1,'checks':rows,'result':'pass','protected_scoring':False},pretty=True);print(rows,flush=True)
