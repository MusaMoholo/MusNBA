"""Observed ESPN shot support, separately labelled from generated model-zone forecasts."""
from functools import lru_cache
import numpy as np
import pandas as pd
import pyarrow as pa
from basketball_common import DERIVED
from scripts import court_zones,possessions

@lru_cache(maxsize=1)
def rows(signature):
 pa.set_cpu_count(1)
 names=['game_id','date_et','season','season_type','offense','defense','end_type','actor','value','x','y','made','heave','game_ok']+[f'{side}_{i}' for side in ['off','def'] for i in range(1,6)]
 frame=pd.read_parquet(DERIVED/'segments.parquet',columns=names)
 return frame[frame.end_type.eq('shot')&frame.value.isin([2,3])&frame.season_type.eq(2)].copy()

def build(game,players):
 path=DERIVED/'segments.parquet'
 source=rows((path.stat().st_mtime_ns,path.stat().st_size));origin=game['date'];selected=[];scopes={};windows={}
 season=int(origin[:4])+(origin[5:7]>='07')
 source=source[source.season.eq(season)]
 for side in ['home','away']:
  team=str(game[side]['id']);part=source[(source.offense.eq(team)|source.defense.eq(team))&source.date_et.lt(origin)]
  dates=part[['game_id','date_et']].drop_duplicates().sort_values(['date_et','game_id'],kind='stable').tail(10)
  gids=set(dates.game_id);windows[side]=set(map(str,gids));selected.extend(source[source.game_id.isin(gids)].index.tolist());scopes[side]={'team':team,'games':len(gids),'from':dates.date_et.min() if len(dates) else None,'through':dates.date_et.max() if len(dates) else None}
 # Source row identity is retained locally; API only carries one shared point table per game.
 part=source.loc[sorted(set(selected))].copy();part['fine_cell']=court_zones.derive(part.x,part.y,part.value)
 samples=[]
 for row in part.itertuples():
  cols=pd.to_numeric(pd.Series([getattr(row,f'{side}_{i}') for side in ['off','def'] for i in range(1,6)]),errors='coerce').to_numpy(dtype=float,na_value=np.nan)
  actor_value=pd.to_numeric(row.actor,errors='coerce')
  legal=np.isfinite(cols).all() and len(set(cols.tolist()))==10 and pd.notna(actor_value) and np.isfinite(actor_value) and actor_value in cols[:5] and pd.notna(row.game_ok) and bool(row.game_ok)
  actor=str(int(actor_value)) if pd.notna(actor_value) and np.isfinite(actor_value) else None
  known=np.isfinite([row.x,row.y]).all() and 0<=row.x<=50 and -5.25<=row.y<=88.75
  coarse=possessions.zone(float(row.x),float(row.y),int(row.value)) if known else 'unknown'
  if pd.notna(row.made) and row.made not in (0,1):raise ValueError('unsupported observed shot outcome')
  samples.append({'game':str(row.game_id),'date':str(row.date_et),'team':str(row.offense),'against':str(row.defense),'player':actor,
   'x':float(row.x) if known else None,'y':float(row.y) if known else None,'value':int(row.value),'made':None if pd.isna(row.made) else bool(row.made==1),
   'cell':int(row.fine_cell),'zone':coarse,'flagged_heave':bool(row.heave) if pd.notna(row.heave) else None,
   'on_court':list(map(lambda x:str(int(x)),cols[5:])) if legal else None})
 subjects={}
 for side in ['home','away']:
  tid=str(game[side]['id']);eligible=[i for i,p in enumerate(samples) if p['game'] in windows[side]]
  unassigned=sum(samples[i]['against']==tid and samples[i]['on_court'] is None for i in eligible)
  subjects['t:'+side]={'offense':[i for i in eligible if samples[i]['team']==tid],
   'defense':[i for i in eligible if samples[i]['against']==tid],'window':scopes[side],
   'unassigned_defense_attempts':unassigned}
  for player in players[side]:
   pid=str(player['id']);subjects['p:'+pid]={'offense':[i for i in eligible if samples[i]['player']==pid],
    'defense':[i for i in eligible if samples[i]['on_court'] is not None and pid in samples[i]['on_court']],
    'window':scopes[side],'unassigned_defense_attempts':unassigned}
 return {'source':'retained ESPN segments, rounded shot coordinates in feet','before':origin,'schema':court_zones.SCHEMA,
  'cells':[{'basic':b,'area':a,'range':r} for b,a,r in court_zones.CELLS],'shots':samples,'subjects':subjects,
  'definition':'Current-season shots in each team’s last10 recorded regular-season games before the forecast ET date. Player views use that team window.',
  'limits':'Coordinates are rounded recorded shots, not tracking. Derived22 cells differ from the forecast’s five pooled model regions. Missing/invalid coordinates remain unplotted and counted; heave flags retain source semantics. Opponent shots with a player in a legal recorded five are on-court exposure, not nearest-defender or causal attribution. Historical maps describe recorded games; forecast availability filters do not change them.'}
