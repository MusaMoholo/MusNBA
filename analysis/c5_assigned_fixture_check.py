"""Assigned-provider draws replace all31 hypothetical Cup-window slots exactly once."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from scripts import competitions,master_fixtures
from scripts.season_stats import team_table
from scripts.box_scores import load_csv
from basketball_common import DERIVED,read_json

def check():
    teams=read_json(DERIVED/'teams.json');master=master_fixtures.load();day='2026-11-23'
    T,lg=team_table(load_csv('team_games.csv'),day,teams);p=competitions.prepare(master,teams,day)
    x=competitions.run_chunk((T,lg,p,{},1,2026,None));competitions.audit(x)
    actual=[];engine={}
    for j,e in enumerate(x.events):
        if e['stage'] in ('playin','round1','round2','conference','finals'):continue
        eid=e['id']
        if eid.startswith('c5:'):
            eid='fixture'+str(j)
            notes={'cup_qf':'NBA Cup - Quarterfinal','cup_sf':'NBA Cup - Semifinal','cup_final':'NBA Cup - Championship'}.get(e['stage'],'')
            actual.append({'game_id':eid,'season':'2026-27','date_et':e['date'],'tip_utc':e['date']+'T23:00Z','home_id':x.ids[e['home'][0]],'away_id':x.ids[e['away'][0]],'notes':notes,'status':'scheduled','neutral':int(e['neutral'])})
        if e['date']>=day:
            arr=np.zeros((1,2,5),np.int32);arr[:,:,0]=e['reg'];arr[:,:,4]=e['final']-e['reg'];engine[eid]=arr
    p2=competitions.prepare(master+actual,teams,day)
    y=competitions.run_chunk((T,lg,p2,engine,1,2026,None));a=competitions.audit(y)
    assert len(actual)==31 and len(y.used_actual)==31
    assert np.array_equal(x.wins,y.wins)
    assert not any(e['id'].startswith('c5:2026') for e in y.events)
    return {'assigned_slots':31,'all_consumed_once':True,'regular_wins_exact':True,'ledger_audit':a}

if __name__=='__main__':
    result=check();p=ROOT/'analysis/experiments/20261124_c5_assigned_fixture_v1.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n');print(result)
