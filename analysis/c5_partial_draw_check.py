"""Exercise staged real-provider assignments, including interleaved QF/SF dates."""
import sys,json,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from scripts import competitions,master_fixtures
from scripts.season_stats import team_table
from scripts.box_scores import load_csv
from basketball_common import DERIVED,read_json,sha256_file

def check():
    teams=read_json(DERIVED/'teams.json');master=master_fixtures.load();day='2026-11-23'
    T,lg=team_table(load_csv('team_games.csv'),day,teams);p=competitions.prepare(master,teams,day)
    x=competitions.run_chunk((T,lg,p,{},1,2026,None));competitions.audit(x)
    fixtures=[];engine={}
    for j,e in enumerate(x.events):
        if e['stage'] in ('playin','round1','round2','conference','finals'):continue
        eid=e['id']
        if eid.startswith('c5:'):
            eid='assigned'+str(j)
            notes={'cup_qf':'NBA Cup - Quarterfinal','cup_sf':'NBA Cup - Semifinal','cup_final':'NBA Cup - Championship'}.get(e['stage'],'')
            fixtures.append({'game_id':eid,'season':'2026-27','date_et':e['date'],'tip_utc':e['date']+'T23:00Z','home_id':x.ids[e['home'][0]],'away_id':x.ids[e['away'][0]],'notes':notes,'status':'scheduled','neutral':int(e['neutral']),'test_slot':e['id'],'test_stage':e['stage']})
        if e['date']>=day:
            arr=np.zeros((1,2,5),np.int32);arr[:,:,0]=e['reg'];arr[:,:,4]=e['final']-e['reg'];engine[eid]=arr;engine[e['id']]=arr
    nonq=[g for g in fixtures if ':filler:' in g['test_slot']]
    qf=[g for g in fixtures if g['test_stage']=='cup_qf'];sf=[g for g in fixtures if g['test_stage']=='cup_sf']
    qfl=[g for g in fixtures if ':qf-loser:' in g['test_slot']]
    cases={'unassigned':[],'nonqualifiers22':nonq,'group_draw26':nonq+qf,'one_qf':qf[:1],
      'one_semifinal_and_loser':nonq+qf+sf[:1]+qfl[:1],'full31':fixtures}
    mixed=[dict(g) for g in fixtures]
    for g in mixed:
        slot=g['test_slot']
        if ':qf:0:1' in slot:g['date_et']='2026-12-05'
        if ':qf:1:0' in slot:g['date_et']='2026-12-04'
        if ':sf:0' in slot:g['date_et']='2026-12-09'
        if ':sf:1' in slot:g['date_et']='2026-12-08'
        g['tip_utc']=g['date_et']+'T23:00Z'
    cases['interleaved_qf_sf_dates']=mixed
    results={}
    for name,actual in cases.items():
        try:
            prep=competitions.prepare(master+actual,teams,day)
            y=competitions.run_chunk((T,lg,prep,engine,1,2026,None));a=competitions.audit(y)
            assert len(y.used_actual)==len(actual) and np.array_equal(x.wins,y.wins)
            results[name]={'pass':True,'assigned':len(actual),'consumed_once':len(y.used_actual),'audit':a}
        except Exception as e:results[name]={'pass':False,'assigned':len(actual),'error':type(e).__name__+': '+str(e)}
    return results

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--version',required=True);a=p.parse_args();assert a.version in ('v1','v2','v3')
    out=ROOT/f'analysis/experiments/20261124_c5_partial_draw_{a.version}.json';assert not out.exists()
    rows=check();out.write_text(json.dumps({'kind':'Staged assigned-fixture calendar probe','source_sha256':sha256_file(ROOT/'scripts/competitions.py'),'cases':rows,'all_pass':all(r['pass'] for r in rows.values())},indent=2)+'\n');print(json.dumps(rows,indent=2),flush=True)
    raise SystemExit(0 if all(r['pass'] for r in rows.values()) else 1)
