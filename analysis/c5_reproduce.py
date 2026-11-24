"""Verify full production-format season replay and immutable unequal-mass paths."""
import sys,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from scripts import projection,master_fixtures
from scripts.season_stats import team_table
from scripts.box_scores import load_csv
from basketball_common import DERIVED,read_json
if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--version',choices=['v2','v3'],required=True);version=parser.parse_args().version
    out=ROOT/f'analysis/experiments/20261124_c5_reproduction_{version}.json';assert not out.exists()
    teams=read_json(DERIVED/'teams.json');m=master_fixtures.load();day='2026-11-23';T,lg=team_table(load_csv('team_games.csv'),day,teams)
    weights=np.tile([1,2,3,4],10)
    gid=next(g['game_id'] for g in m if g['date_et']>=day)
    e=np.zeros((40,2,5),np.int32);e[:,:,:4]=25;e[:,0,4]=15;e[:,1,4]=11;engine={gid:e}
    a=projection.simulate_season(T,lg,m,day,teams,engine_pts=engine,sims=40,weights=weights)
    row=next(g for g in a['games'] if g['game_id']==gid)
    assert row['p_home']==1 and row['mu_home']==115 and row['mu_away']==111, 'Engine summary must include OT points'
    b=projection.simulate_season(T,lg,m,day,teams,engine_pts=engine,sims=40,params=a['pathway'],weights=weights)
    text=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'))
    assert text(a)==text(b),'Production format not bit reproducible'
    out.write_text(json.dumps({'kind':'Production-format deterministic mechanical replay; no protected scoring','worlds':40,'probability_mass':100,'sha256':hashlib.sha256(text(a).encode()).hexdigest(),'exact':True,'engine_full_game_summary_includes_OT':True,'legacy_smoke_log':'/tmp/musnba_c5_preflight_smoke_v2.log'},indent=2)+'\n');print('Exact season reproduction',out)
