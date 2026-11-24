#!/usr/bin/env python3
"""Independent reconstruction of stored playback, full zones and exact weighted cases."""
from pathlib import Path
from fractions import Fraction
from collections import defaultdict
import sys,gzip,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from basketball_common import read_json,write_json,sha256_file
from scripts.world_mass import WorldMass

def audit(report):
 totals={'games':0,'examples':0,'segments':0,'legal_fives':0,'worlds':0,'cases':0,'max_minute_error':0.,'max_weighted_zone_error':0.,'max_replay_gzip_bytes':0}
 for row in report['games']:
  replay=read_json(ROOT/row['replay']);court=read_json(ROOT/row['court']);players={p['id']:p for p in replay['players']};roster=list(players)
  if len(replay['examples'])!=5 or replay['source_id']!=court['source_id']:raise ValueError('source/selection differs')
  for example in replay['examples']:
   boxes={p:defaultdict(int) for p in players};seconds=defaultdict(float);stints=defaultdict(float);score=[0,0];period=1;clock=720.
   if Fraction(*map(int,example['world_mass']))<=0:raise ValueError('zero-mass example')
   for e in example['events']:
    if e['score_before']!=score or not 0<=e['after_clock']<=e['action_clock']<=e['before_clock']:raise ValueError('score/clock interval differs')
    if e['period']==period:
     if e['before_clock']!=clock:raise ValueError('clock gap')
    elif e['period']!=period+1 or clock!=0 or e['before_clock']!=(720 if e['period']<=4 else 300):raise ValueError('period transition gap')
    for fives,start,stop in [(e['lineups'],e['before_clock'],e['action_clock']),(e['lineups_after'],e['action_clock'],e['after_clock'])]:
     for side,five in enumerate(fives):
      if len(five)!=5 or len(set(five))!=5 or any(players[p]['side']!=side for p in five):raise ValueError('illegal recorded five')
      for p in five:stints[p]+=start-stop
      totals['legal_fives']+=1
    delta=[0,0]
    for pid,stat,amount in e['credits']:
     if pid not in players or not isinstance(amount,int) or amount<0:raise ValueError('invalid credit')
     boxes[pid][stat]+=amount
     if stat=='pts':delta[players[pid]['side']]+=amount
    if [a+b for a,b in zip(score,delta)]!=e['score_after']:raise ValueError('event points do not match scoreboard')
    for pid,value in e['seconds']:seconds[pid]+=value
    score=e['score_after'];period=e['period'];clock=e['after_clock'];totals['segments']+=1
   if score!=example['final_score'] or clock!=0 or period<4 or score[0]==score[1]:raise ValueError('unfinished playback')
   for p,final in example['final_box'].items():
    for stat,value in final.items():
     if stat!='min' and boxes[p][stat]!=value:raise ValueError('final box differs')
    error=max(abs(seconds[p]/60-final['min']),abs(stints[p]/60-final['min']));totals['max_minute_error']=max(error,totals['max_minute_error'])
    if error>1e-8:raise ValueError('minutes/rotation differs')
   for side in (0,1):
    expected=5*(2880+300*(period-4))
    if abs(sum(seconds[p] for p in players if players[p]['side']==side)-expected)>1e-5:raise ValueError('team seconds differ')
   totals['examples']+=1
  size=len(gzip.compress((ROOT/row['replay']).read_bytes(),compresslevel=6));totals['max_replay_gzip_bytes']=max(size,totals['max_replay_gzip_bytes'])
  if size>2097152:raise ValueError('replay size limit')
  path=Path(row['zone_worlds']['path'])
  if sha256_file(path)!=row['zone_worlds']['sha256']:raise ValueError('zone digest differs')
  with np.load(path,allow_pickle=False) as z:
   ids=list(map(str,z['player_ids']));sides=z['side'];a=z['zone_fga'];m=z['zone_fgm'];weights=z['weights']
  if a.dtype!=np.uint16 or m.dtype!=np.uint16 or a.shape!=m.shape or a.shape[2:]!=(5,5) or (m>a).any():raise ValueError('zone arrays differ')
  folder=ROOT/f"data/snapshots/2026-11-23/lineups/{row['game']}";plan=read_json(folder/'work-plan.json');offset=0;spans=[]
  for b in plan['batches']:
   end=offset+b['worlds'];original=folder/'capture.npz' if b['branch_id']=='unconditional' else folder/'branches'/Path(b['capture']).name
   with np.load(original,allow_pickle=False) as raw:
    if not np.array_equal(raw['player_ids'],np.array(ids)) or not np.array_equal(raw['side'],sides):raise ValueError('original roster differs')
    for values,key in [(a[offset:end].sum(3),'fga'),(m[offset:end].sum(3),'fgm'),(a[offset:end,:,:,3:].sum(3),'fg3a'),(m[offset:end,:,:,3:].sum(3),'fg3m')]:
     if not np.array_equal(values,raw['box_'+key]):raise ValueError('full player/period zone totals differ')
   spans.append(({str(pid):bool(plays) for team,pid,plays in b['assignments']},offset,end));offset=end
  if offset!=len(a):raise ValueError('world count differs')
  for case in court['cases'].values():
   mask=np.zeros(len(a),bool)
   for choices,start,end in spans:
    if all(choices.get(p)==value for p,value in case['choices'].items()):mask[start:end]=True
   mass=WorldMass(int(mask.sum()),weights[mask]);aa=a[mask].sum(2);mm=m[mask].sum(2)
   for key,indices in [('home',np.flatnonzero(sides==0)),('away',np.flatnonzero(sides==1))]+[(pid,[i]) for i,pid in enumerate(ids)]:
    expected=case[key] if key in ('home','away') else case['players'][key]
    for stat,values in [('attempts',aa),('makes',mm)]:
     error=float(np.max(np.abs(mass.mean(values[:,indices].sum(1))-expected[stat])));totals['max_weighted_zone_error']=max(error,totals['max_weighted_zone_error'])
     if error>1e-10:raise ValueError('weighted case zone summary differs')
   totals['cases']+=1
  totals['games']+=1;totals['worlds']+=len(a)
 return totals

def main():
 source=ROOT/'analysis/experiments/20261124_c4_retained_capture_v1.json';out=ROOT/'analysis/experiments/20261124_c4_accounting_v1.json'
 if out.exists():raise FileExistsError(out)
 result=audit(read_json(source));write_json(out,{'kind':'independent stored-zone/event/box/clock/rotation/weighted-case accounting','source_sha256':sha256_file(source),'counts':result,'result':'all exact within declared floating minute/weighted tolerance','accuracy_scored':False},pretty=True);print(result,flush=True)
if __name__=='__main__':main()
