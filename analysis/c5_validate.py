"""Prospective mechanical/calendar audit and frozen matching sensitivity; no protected scoring."""
import sys,json,time,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from scripts import competitions,master_fixtures,forecast_output
from scripts.box_scores import load_csv
from scripts.season_stats import team_table
from basketball_common import DERIVED,read_json

def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--version',default='v2',choices=['v2','v3','v4','v5','v6','v7']);version=parser.parse_args().version
    target=ROOT/f'analysis/experiments/20261124_c5_mechanics_{version}.json';assert not target.exists()
    teams=read_json(DERIVED/'teams.json');master=master_fixtures.load();day='2026-11-23'
    T,lg=team_table(load_csv('team_games.csv'),day,teams);prep=competitions.prepare(master,teams,day)
    args=(T,lg,prep,{},40,123,None)
    x=competitions.run_chunk(args);audit=competitions.audit(x)
    future=[dict(g,home_pts='9999',away_pts='-123',status='final') if g['date_et']>=day else g for g in master]
    injected=competitions.prepare(future,teams,day)
    y=competitions.run_chunk((T,lg,injected,{},40,123,None))
    assert all(np.array_equal(getattr(x,k),getattr(y,k)) for k in ('wins','seed','reach','cup_champion','champion'))
    # Exact accepted-horizon outcomes, regulation/full OT separated. No synthetic periods claimed for combined OT.
    gid=next(g['game_id'] for g in master if g['date_et']>=day)
    e=np.zeros((40,2,5),np.int32);e[:,:,0:4]=25;e[:,0,4]=15;e[:,1,4]=11
    z=competitions.run_chunk((T,lg,prep,{gid:e},40,123,None));competitions.audit(z)
    row=next(r for r in z.events if r['id']==gid)
    assert np.array_equal(row['final'],e.sum(2)) and np.array_equal(row['reg'],e[:,:,:4].sum(2)) and np.all(row['ot']==255)
    # Stable per-canonical-chunk identity independently of worker assignment, plus immutable resume.
    base=ROOT/f'data/derived/experiments/c5_validation_{version}';base.mkdir(parents=True,exist_ok=True)
    one=competitions.play(T,lg,master,day,teams,None,2000,jobs=1,namespace=base/'serial')
    two=competitions.play(T,lg,master,day,teams,None,2000,jobs=2,namespace=base/'parallel')
    assert one['competitions']['paths']==two['competitions']['paths']
    resumed=competitions.play(T,lg,master,day,teams,None,2000,jobs=2,namespace=base/'parallel')
    assert all(r['reused'] for r in resumed['competition_execution']['chunks'])
    changed=dict(T);changed[next(iter(T))]={**T[next(iter(T))],'w':999}
    try:competitions.play(changed,lg,master,day,teams,None,2000,jobs=2,namespace=base/'parallel')
    except ValueError:pass
    else:raise AssertionError('Changed-input receipt reused')
    start=time.monotonic();a=competitions.play(T,lg,master,day,teams,None,10000,jobs=10,namespace=base/'primary10k')
    seconds=time.monotonic()-start
    b=competitions.play(T,lg,master,day,teams,None,10000,jobs=10,alternative=True,namespace=base/'alternative10k')
    weighted=competitions.play(T,lg,master,day,teams,None,40,weights=np.tile([1,2,3,4],10),jobs=1,namespace=base/'weighted40')
    assert weighted['competitions']['mass']==100
    # Package exact unequal-mass paths without recomputing them; probabilities independently recounted.
    for played in (a,b,weighted):
        c=played['competitions'];w=np.array(c['weights']);total=int(w.sum())
        reach=np.frombuffer(__import__('base64').b64decode(c['paths']['reach']),np.uint8).reshape(-1,30)
        for i,t in enumerate(c['ids']):
            for key,v in (('playoffs',1),('round2',2),('conference',3),('finals',4),('title',5)):
                assert c['teams'][t][key]==float(w[reach[:,i]>=v].sum()/total)
        for key,count in (('playoffs',16),('round2',8),('conference',4),('finals',2),('title',1),('cup_qf',8),('cup_sf',4),('cup_final',2),('cup_title',1)):
            assert abs(sum(t[key] for t in c['teams'].values())-count)<1e-12
    f=forecast_output.season(T,master,day,teams,a,np.random.default_rng(321))
    assert all(t['scheduled']==82 for t in f['teams'].values())
    delta={t:{k:b['competitions']['teams'][t][k]-a['competitions']['teams'][t][k] for k in ('cup_title','playoffs','title')} for t in a['competitions']['ids']}
    target.write_text(json.dumps({'kind':'C5 mechanical audit; no learned promotion/protected scoring','small_ledger_audit':audit,'future_score_injection':'exact unchanged','engine_OT_final':'exact retained; combined period count remains missing','serial_parallel':'exact packed paths,2x1k chunks','resume':'all receipts reused; changed T rejected','primary10k_seconds':seconds,'primary':a['competitions']['receipt'],'alternative':b['competitions']['receipt'],'matching_sensitivity_probability_delta':delta,'protected_rescored':False,'rating_parameters_changed':False},indent=2)+'\n')
    (base/'preview_season.json').write_text(json.dumps(f)+'\n')
    print('C5 validation complete',target,flush=True)

if __name__=='__main__':main()
