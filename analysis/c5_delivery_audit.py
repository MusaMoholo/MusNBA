"""Account fresh stored C5 output independently of its serving views, without simulation."""
import sys,json,hashlib
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from basketball_common import read_json,write_json,sha256_file
from analysis.c4_accounting import audit
from analysis.a1_delivery_audit import audit_view_rates


def rates(task):
    day,gid=task
    return audit_view_rates(ROOT/f'data/snapshots/{day}/lineups/{gid}',ROOT/'data/views')

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--prefix',default='20261124_c5');prefix=parser.parse_args().prefix
    if not prefix.replace('_','').isalnum():raise ValueError('simple immutable report prefix required')
    out=ROOT/f'analysis/experiments/{prefix}_delivery_audit_v1.json';assert not out.exists()
    meta=read_json(ROOT/'data/views/api/meta.json');day=meta['latest'];snapshot=ROOT/'data/snapshots'/day
    seasons=read_json(snapshot/'season.json');comp=seasons['competitions'];assert seasons['as_of']==day and not meta.get('delivery')
    slate=read_json(ROOT/f'data/views/api/slate/{day}.json');games=[]
    for g in slate['games']:
        gid=g['id'];folder=snapshot/'lineups'/gid
        if not folder.exists():continue
        court=read_json(folder/'zones.json');zone=folder/'players.npz'
        assert court['zone_worlds']['sha256']==sha256_file(zone)
        games.append({'game':gid,'replay':str((folder/'replay.json').relative_to(ROOT)),'court':str((folder/'zones.json').relative_to(ROOT)),
                      'zone_worlds':{'path':str(zone.relative_to(ROOT)),'sha256':sha256_file(zone)}})
    assert games,'No newly generated games to audit'
    manifest=ROOT/f'analysis/experiments/{prefix}_fresh_capture_v1.json';assert not manifest.exists()
    write_json(manifest,{'kind':'fresh nightly capture inventory; no enrichment or reconstruction','day':day,'games':games},pretty=True)
    counts=audit({'games':games},snapshot=snapshot)
    with ProcessPoolExecutor(max_workers=min(10,len(games))) as pool:rate_reports=list(pool.map(rates,[(day,g['game']) for g in games]))
    arrays={k:np.concatenate([dict(np.load(ROOT/r['path'],allow_pickle=False))[k] for r in comp['receipt']['chunks']]) for k in ('seed','wins','reach','cup_champion','champion','series','cup_matches')}
    import base64
    for k,a in arrays.items():assert base64.b64decode(comp['paths'][k])==np.asarray(a,np.uint8).tobytes()
    mass=np.asarray(comp['weights'],np.int64);assert mass.sum()==comp['mass'] and len(mass)==comp['worlds']==seasons['sims']
    for i,t in enumerate(comp['ids']):
        assert seasons['teams'][t]['scheduled']==82
        for key,v in [('playoffs',1),('round2',2),('conference',3),('finals',4),('title',5)]:
            expected=int(mass[arrays['reach'][:,i]>=v].sum())/int(mass.sum());assert expected==comp['teams'][t][key]
        hist=seasons['teams'][t]['wins'];assert sum(hist['hist'])==comp['mass']
        expected=np.zeros(max(arrays['wins'][:,i])+1,np.int64);np.add.at(expected,arrays['wins'][:,i],mass)
        assert hist['min']==0 and hist['hist']==expected.tolist()
    for key,count in [('cup_title',1),('cup_qf',8),('cup_sf',4),('cup_final',2),('playoffs',16),('round2',8),('conference',4),('finals',2),('title',1)]:
        assert abs(sum(t[key] for t in comp['teams'].values())-count)<1e-12
    # Actual engine totals and exact coupling mass are checked by smoke; this audit never fits/reconstructs.
    write_json(out,{'kind':'fresh C5 event/zone/box/minute/weighted-rate/path accounting','day':day,'counts':counts,'rate_distributions':sum(r['rate_distributions_checked'] for r in rate_reports),'rate_reports':rate_reports,'season_worlds':comp['worlds'],'season_probability_mass':comp['mass'],'competition_schema':comp['schema'],'competition_identity':comp['receipt']['identity'],'season_sha256':sha256_file(snapshot/'season.json'),'capture_manifest_sha256':sha256_file(manifest),'result':'pass','protected_scoring':False},pretty=True)
    print('C5 fresh delivery accounting passed',out,flush=True)
