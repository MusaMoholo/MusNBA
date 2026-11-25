"""Complete C04 equal-game, calibration uncertainty and simulation-half reporting."""
from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pandas as pd
from analysis import c04_data as data,c03_evaluate as ev
from analysis.c01_workbench import create_json
from analysis.c01_core import ContractError


def run():
    rows=pd.read_parquet(data.WORK/'minute_scores.parquet');ref=rows[rows.model.eq('native')].set_index(['game_id','player']).sort_index();result={'known_development_games':200,'equal_game_changes':{},'simulation_half_changes':{},'coverage80_uncertainty':{},'decision_changed':False}
    for f in ('native','A','B','C'):
        q=rows[rows.model.eq(f)];r=ev.interval(q[['game_id','date_et']].assign(change=q.covered80.to_numpy()));result['coverage80_uncertainty'][f]={'estimate':r['change'],'ci95_game':r['ci95_game'],'ci95_calendar_week':r['ci95_calendar_week'],'units':'fraction of observed player outcomes within nominal80% interval; descriptive uncertainty'}
        if f=='native':continue
        c=q.set_index(['game_id','player']).sort_index()
        if not c.index.equals(ref.index):raise ContractError('equal-game role support differs')
        pair=ref.reset_index()[['game_id','date_et']];pair['change']=c.crps.to_numpy()-ref.crps.to_numpy();g=pair.groupby('game_id',sort=True).agg(date_et=('date_et','first'),change=('change','mean')).reset_index();result['equal_game_changes'][f]=ev.interval(g)
        result['simulation_half_changes'][f]={}
        for field in ('crps_half1','crps_half2'):
            p=ref.reset_index()[['game_id','date_et']];p['change']=c[field].to_numpy()-ref[field].to_numpy();result['simulation_half_changes'][f][field]=ev.interval(p)
    create_json(data.WORK/'supplement.json',result);create_json(ROOT/'analysis/experiments/20261125_c04_supplement_v1.json',result);print({f:{'equal_game':result['equal_game_changes'][f]['change'],'half1':result['simulation_half_changes'][f]['crps_half1']['change'],'half2':result['simulation_half_changes'][f]['crps_half2']['change']} for f in 'ABC'},flush=True);return result

if __name__=='__main__':run()
