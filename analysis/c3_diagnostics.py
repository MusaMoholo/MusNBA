#!/usr/bin/env python3
"""MIN/PTS tail and zero-mass accounting from the fixed S06 saved worlds."""
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import sys,os,argparse
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from basketball_common import read_json,write_json,sha256_file
from analysis.c2_world_diagnostics import extract,dispersion

def main(jobs):
 if any(os.environ.get(k)!='1' for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS']):raise ValueError('single-thread workers required')
 phase=ROOT/'analysis/experiments/20261124_c3_engine_development_v3.json';r=read_json(phase)
 output=ROOT/'analysis/experiments/20261124_c3_diagnostics_v1.json'
 if output.exists():raise FileExistsError(output)
 ids=sorted(r['game_ids'])
 if len(ids)!=200 or len(r['receipts'])!=400:raise ValueError('complete200 pairs required')
 tasks=[(x['game'],x['arm'],{**x,'entry_selector':'entry'}) for x in r['receipts']]
 with ProcessPoolExecutor(max_workers=jobs) as pool:rows=list(pool.map(extract,tasks))
 weights=np.random.default_rng(20261122).multinomial(200,np.full(200,1/200),size=10000).astype(float)
 reports={}
 for arm in ['reference','candidate']:
  games={x['game']:x for x in rows if x['arm']==arm}
  frame=pd.DataFrame([p for gid in ids for p in games[gid]['rows']]);groups={}
  for tier in ['all','star','starter','bench','unknown']:
   part=frame if tier=='all' else frame[frame.prior_tier.eq(tier)]
   groups[tier]={}
   for stat in ['min','pts']:
    valid=part[part[stat+'_low5'].notna()&part[stat+'_high5'].notna()]
    agg=valid.groupby('game_id').agg(n=('player','size'),low=(stat+'_low5','sum'),high=(stat+'_high5','sum'),zero=(stat+'_zero','sum'),sd=(stat+'_sd','sum')).reindex(ids,fill_value=0)
    n=len(valid);count=int((agg.n>0).sum());supported=n>=100 and count>=30
    record={'player_games':n,'games':count,'missing':len(part)-n,'status':'supported' if supported else 'insufficient'}
    if n:
     for key in ['low','high','zero','sd']:
      record[key]=float(agg[key].sum()/n)
      if supported:
       boot=weights@agg[key].to_numpy()/(weights@agg.n.to_numpy());record[key+'_ci95']=np.quantile(boot,[.025,.975]).tolist()
    groups[tier][stat]=record
  reports[arm]={'tails':groups,'pace':dispersion([games[gid]['pace'] for gid in ids],weights),'team_points':dispersion([games[gid]['points'] for gid in ids],weights)}
 write_json(output,{'kind':'S06 fixed-panel diagnostic; no fitted correction or new gate','phase_sha256':sha256_file(phase),'games':200,'arms':reports,
  'definitions':{'tails':'Expected randomized PIT below5%/above95%, preserving atoms; zero is conditional actual-participant mass','bootstrap':'10000 complete games, seed20261122'},
  'limits':['Actual-participant rosters do not grade live DNP/availability.','Tail error does not identify a latent variance mechanism.']},pretty=True)
 print('Two-arm saved-world tails/dispersion complete; no new simulation',flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--jobs',type=int,default=8);a=p.parse_args()
 if not 1<=a.jobs<=10:raise ValueError('max10 workers')
 main(a.jobs)
