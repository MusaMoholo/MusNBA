"""Force new accepted season worlds in an empty namespace and compare all published values."""
import sys,time,copy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from basketball_common import read_json,write_json,sha256_file,DERIVED
from scripts import competitions,projection,forecast_output,master_fixtures
if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--prefix',default='20261124_u25');parser.add_argument('--day');args=parser.parse_args();prefix=args.prefix
    if not prefix.replace('_','').isalnum():raise ValueError('simple immutable prefix required')
    out=ROOT/f'analysis/experiments/{prefix}_fresh_season_v1.json';namespace=ROOT/f'data/derived/experiments/{prefix}_fresh_season_v1'
    assert not out.exists() and not namespace.exists()
    day=args.day or read_json(ROOT/'data/views/api/meta.json')['latest'];snap=ROOT/'data/snapshots'/day;stored=read_json(snap/'season.json');st=read_json(snap/'stats.json')
    files=[snap/f for f in ('season.json','stats.json','season_engine_worlds.npz')];before={str(p):sha256_file(p) for p in files}
    with np.load(snap/'season_engine_worlds.npz') as z:weights=z['weights'];engine={k:z[k] for k in z.files if k!='weights'}
    teams=read_json(DERIVED/'teams.json');master=master_fixtures.load();t=time.monotonic()
    # Nine one-thread workers leave one slot for final view/export work.
    played=competitions.play(st['teams'],st['league'],master,day,teams,engine,len(weights),stored['pathway'],weights,jobs=9,namespace=namespace)
    execution=played['competition_execution'];assert not any(c['reused'] for c in execution['chunks'])
    fresh=forecast_output.season(st['teams'],master,day,teams,played,projection.rng_for('team-pathway-v1',day,'season'),engine,stored['pathway'],weights)
    identity=fresh['competitions']['receipt']['identity'];assert identity==stored['competitions']['receipt']['identity']
    left=copy.deepcopy(fresh);right=copy.deepcopy(stored)
    left['competitions'].pop('receipt');right['competitions'].pop('receipt')
    assert json.dumps(left,sort_keys=True)==json.dumps(right,sort_keys=True),'Fresh season differs from saved current inputs'
    assert before=={str(p):sha256_file(p) for p in files}
    write_json(out,{'kind':'Fresh full accepted season generation, empty explicit namespace; no cache reuse or scoring','worlds':len(weights),'probability_mass':int(weights.sum()),'fresh_chunks':len(execution['chunks']),'reused_chunks':0,'jobs':9,'inner_threads':1,'seconds':time.monotonic()-t,'namespace':str(namespace.relative_to(ROOT)),'identity':identity,'every_published_value_exact':True,'input_sha256':before,'protected_scoring':False,'result':'pass'},pretty=True);print('Fresh season exact',out,flush=True)
