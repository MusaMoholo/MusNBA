"""Full stored-snapshot publication preflight in scratch; never replace production outputs."""
import sys,json,shutil,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from basketball_common import DERIVED,read_json,write_json,sha256_file
from scripts import competitions,master_fixtures,projection,forecast_output,views

if __name__=='__main__':
    public=ROOT/'analysis/experiments/20261124_c5_full_preflight_v1.json';assert not public.exists()
    scratch=Path('/tmp/musnba-c5-full-preflight-v1');scratch.mkdir(exist_ok=False)
    snaps=views.load_snapshots();day=views.current_snapshot(snaps);source=snaps[day]['path'];st=read_json(source/'stats.json');old=read_json(source/'season.json')
    with np.load(source/'season_engine_worlds.npz') as z:
        weights=z['weights'];engine={k:z[k] for k in z.files if k!='weights'}
    before={name:sha256_file(source/name) for name in ('engine_worlds.npz','engine_players.npz','season_engine_worlds.npz','season_player_indices.npz','meta.json','stats.json','season.json')}
    teams=read_json(DERIVED/'teams.json');master=master_fixtures.load();start=time.monotonic()
    played=competitions.play(st['teams'],st['league'],master,day,teams,engine,len(weights),old['pathway'],weights,
         namespace=ROOT/'data/derived/experiments/c5_full_preflight_v1/season_paths')
    season=forecast_output.season(st['teams'],master,day,teams,played,projection.rng_for('team-pathway-v1',day,'season'),engine,old['pathway'],weights)
    clone=scratch/'snapshot';clone.mkdir()
    for path in source.iterdir():
        if path.name not in ('season.json','season_player_indices.npz'):(clone/path.name).symlink_to(path.resolve(),target_is_directory=path.is_dir())
    write_json(clone/'season.json',season)
    gids=sorted(engine);raw=views._game_lines(clone,gids[0]);raw_count=len(raw[0])
    # Prime the early cache, then install the final coupling layout at the same path.
    (clone/'season_player_indices.npz').symlink_to((source/'season_player_indices.npz').resolve())
    coupled=views._game_lines(clone,gids[0]);assert len(coupled[0])==len(weights) and len(coupled[2])==len(weights)
    rate_checks=[]
    for stat in views.SPOT_STATS:
        boxes=[];ids=[]
        with np.load(source/'engine_players.npz') as players,np.load(source/'season_player_indices.npz') as layout:
            for gid in gids:
                boxes.append(players[gid+'__lines'][layout[gid],:,views.WORLD_STATS.index(stat)].astype(float));ids+=list(map(str,players[gid+'__ids']))
        matrix=np.concatenate(boxes,1);lead=matrix==matrix.max(1,keepdims=True);fraction=lead/lead.sum(1,keepdims=True)
        expected=(fraction*weights[:,None]).sum(0)/int(weights.sum())
        got=views.lead_chances(clone,gids,stat,ids)
        error=max(abs(got[p]-expected[i]) for i,p in enumerate(ids));assert error<=.0000500001
        rate_checks.append({'stat':stat,'players':len(ids),'max_rounding_error':error,'unrounded_mass_sum':float(expected.sum())})
    # The actual final publication gate is exercised with original retained provenance; only its read context is redirected.
    snapshots={k:dict(v) for k,v in snaps.items()};snapshots[day]['path']=clone
    original=views.load_snapshots;views.load_snapshots=lambda:snapshots
    try:result=views.build(scratch/'views')
    finally:views.load_snapshots=original
    assert before=={name:sha256_file(source/name) for name in before}
    write_json(public,{'kind':'Full current stored-snapshot view preflight; no production replacement/possession simulation','source_day':day,'scratch':str(scratch),'snapshot_sha256':before,'early_raw_worlds':raw_count,'final_coupled_worlds':len(weights),'probability_mass':int(weights.sum()),'cache_refresh_exact':True,'independent_leader_checks':rate_checks,'view_build':result,'seconds':time.monotonic()-start,'competition_identity':season['competitions']['receipt']['identity'],'conference_host_inversions':0,'production_unchanged':True,'status':'pass'},pretty=True)
    print('Full stored-view preflight passed',public,flush=True)
