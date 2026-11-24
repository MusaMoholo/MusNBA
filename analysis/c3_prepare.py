#!/usr/bin/env python3
"""Recover S06 without retuning and extend its strictly prior target proxies."""
import sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from basketball_common import read_json,write_json,sha256_file
from scripts import (a1_substitution_engine as old,a1_minutes_unconditional as u,
 a1_availability_cohort as cohort, a1_substitution_in_coverage as positions,minutes,projection)
OUT=ROOT/'analysis/experiments/20261124_c3_frozen_recipe_v1.json'
FEATURES=ROOT/'data/derived/experiments/c3_inputs_v1/features.parquet'

def freeze():
 if OUT.exists():raise FileExistsError(OUT)
 model=ROOT/'analysis/experiments/20261122_a1_s06_engine_models_F4.json'
 old.load_candidate(model,'F4');old.load_features('F4')
 paths=[model,ROOT/'scripts/a1_substitution_engine.py',ROOT/'scripts/a1_foul_penalty_engine.py',Path(__file__),ROOT/'analysis/experiments/20261124_c2_ready_panels_v1.json']
 write_json(OUT,{'kind':'single exact S06 current-r3 retest; frozen before candidate outcomes',
  'recipe':'original SelectedTimeoutPolicy out/in models, conditional exits, Gumbel incoming and timeout templates; retain current r3 Rule3 for all legality/penalties',
  'model_report':str(model.relative_to(ROOT)),'training_through':'2025-12-31',
  'auxiliary':'same original prior-box membership, prior roles/positions and D29 as-of player state; 1000 redraw mean, original a1_s05_unconditional seed; no outcomes in features',
  'features':str(FEATURES.relative_to(ROOT)),'panels_from':'analysis/experiments/20261124_c2_ready_panels_v1.json',
  'worlds':1000,'seed_key':'v1.2d_F4','reference':'folds/v1.2d_F4_all','primary':'players/all/min/crps','policy':'promotion-v3-20261123',
  'multiplicity':'one rotation candidate; primary paired95 upper<0; 27 proper bounds and coverage veto unchanged; independent C4 confirmation required',
  'budget':'3 wiring games; one200 development; no replacement/rescue/retune; no protected scoring',
  'composition':'r3 independent-v1 rotation fitting unchanged; S06 determines desired state; Rule3 owns legal repairs/exemptions and technical scoring; capture delegates without RNG draws',
  'source_sha256':{str(p.relative_to(ROOT)):sha256_file(p) for p in paths}},pretty=True)
 print('Exact S06 recipe, causal proxy rebuild and single MIN screen frozen',flush=True)

def build():
 if FEATURES.exists():raise FileExistsError(FEATURES)
 recipe=read_json(OUT);start=time.monotonic()
 seg=pd.read_parquet(ROOT/'data/derived/history/2026/segments.parquet',columns=['game_id','date_et','offense','defense','off_home','season_type'])
 seg=seg[seg.date_et.between('2026-01-01','2026-04-30') & seg.season_type.eq(2)].copy()
 teams=set(read_json(ROOT/'data/derived/teams.json'))
 seg=seg[seg.offense.isin(teams)&seg.defense.isin(teams)]
 seg['home']=np.where(seg.off_home,seg.offense,seg.defense);seg['away']=np.where(seg.off_home,seg.defense,seg.offense)
 games=seg[['game_id','date_et','home','away']].drop_duplicates()
 _,rows=cohort.build_for_games(games,'F4','C3 input-only all F4 games')
 pre=pd.read_parquet(u.a1_minutes_fold_eval.CAUSAL_PROFILES,columns=['date_et','player','usage','start_share','pos'])
 rows=u.attach_prior_roles(rows,pre)
 rows['date_et']=pd.to_datetime(rows.date_et).dt.strftime('%Y-%m-%d')
 rows['prior_profile_date']=pd.to_datetime(rows.prior_profile_date).dt.strftime('%Y-%m-%d')
 rows=positions.attach_positions(rows,pre)
 original=minutes.build('2026-01-01',include_current=False);coach=minutes.coach_dnps(include_current=False)
 parts=[];groups=0
 for day,daterows in rows.groupby('date_et',sort=True):
  model=u.as_of_model(original,day,coach)
  for (gid,team),part in daterows.groupby(['game_id','team'],sort=True):
   part=part.sort_values('player',kind='stable').copy()
   states=[minutes.player_state(model,str(team),str(pid),day) for pid in part.player]
   target=minutes.game_targets(states);spread=minutes.sd_for(original['sd'],target)
   seed=projection.seed_for('a1_s05_unconditional','F4',str(gid),str(team))
   part['control_mean']=minutes.redraw(target,[s['cap'] for s in states],spread,1000,np.random.default_rng(seed)).mean(0)
   parts.append(part[old.a1_substitution_dataset.TARGET_COLUMNS+['prior_position']]);groups+=1
  if groups//150!=(groups-len(daterows.groupby(['game_id','team'])))//150:print(f'{groups}/{2*len(games)} proxy team-games',flush=True)
 frame=pd.concat(parts,ignore_index=True)
 assert not frame.duplicated(['game_id','player']).any()
 assert frame.prior_day.lt(frame.date_et).all()
 assert (frame.prior_profile_date.isna()|frame.prior_profile_date.lt(frame.date_et)).all()
 saved=old.load_features('F4')
 overlap=frame.merge(saved,on=['game_id','team','player'],suffixes=('_new','_old'),validate='one_to_one')
 assert len(overlap)==len(saved)
 error=float(np.max(np.abs(overlap.control_mean_new-overlap.control_mean_old)))
 if error!=0:raise ValueError(f'original target proxy reproduction differs:{error}')
 for col in ['tier','prior_position','prior_day','prior_profile_date']:
  assert overlap[col+'_new'].fillna('MISSING').equals(overlap[col+'_old'].fillna('MISSING')),col
 FEATURES.parent.mkdir(parents=True,exist_ok=True);frame.to_parquet(FEATURES,index=False)
 panels=read_json(ROOT/recipe['panels_from'])
 write_json(ROOT/'analysis/experiments/20261124_c3_input_audit_v1.json',{'kind':'strict-prior exact original S06 proxy extension; no candidate evaluation',
  'rows':len(frame),'games':frame.game_id.nunique(),'old_rows_reproduced':len(overlap),'max_proxy_error':error,
  'development_games_covered':len(set(panels['development_F4'])&set(frame.game_id)),
  'features_sha256':sha256_file(FEATURES),'seconds':time.monotonic()-start,'fitted_auxiliary_cutoff':'2025-12-31'},pretty=True)
 print(f'{len(overlap)} original rows exactly reproduced; {len(frame)} causal feature rows saved',flush=True)
if __name__=='__main__':
 if sys.argv[1]=='freeze':freeze()
 else:build()
