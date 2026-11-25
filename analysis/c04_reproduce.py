"""Fresh independent joint-role fits, all200 minute draws and full legal-world replay."""
from __future__ import annotations
import argparse,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from analysis import c04_data as data,c04_models as models,c04_screen as screen,c04_rollout as rollout,c04_audit as audit
from analysis.c01_workbench import read,create_json
from analysis.c01_core import ContractError
from basketball_common import sha256_file


def source():
    p=data.verify()
    for f in 'ABC':
        m=models.Predictor(f).meta
        if m['code_sha256']!=sha256_file(ROOT/'analysis/c04_models.py') or m['data_sha256']!=sha256_file(data.WORK/'data.json'):raise ContractError('joint-role algorithm/data changed')
    for stage in ('wiring','short','final'):
        if (data.WORK/f'{stage}_plan.json').exists() and read(data.WORK/f'{stage}_plan.json')['sources']!=rollout.signature():raise ContractError('joint-role runtime source changed')
    return {'pinned_sources_passed':True,'games':len(p['game_ids'])}

def decision(rows):
    r=rows[rows.model.eq('native')].set_index(['game_id','player']).sort_index();out={}
    for f in 'ABC':
        q=rows[rows.model.eq(f)].set_index(['game_id','player']).sort_index()
        if not q.index.equals(r.index) or not np.array_equal(q.truth,r.truth):raise ContractError('independent minute decision support differs')
        change=float(np.sum(q.crps.to_numpy()-r.crps.to_numpy())/len(q));relative=change/r.crps.mean();coverage=float(abs(q.covered80.mean()-.8)-abs(r.covered80.mean()-.8));out[f]={'crps_change':change,'relative_change':relative,'coverage80':float(q.covered80.mean()),'coverage80_distance_deterioration':coverage,'coverage_rule_passed':coverage<=.03}
    return out

def reproduce(output):
    source();output=Path(output).resolve()
    if output.is_relative_to(ROOT) and not output.is_relative_to(ROOT/'data'):raise ContractError('private role reproduction must stay ignored')
    output.mkdir(parents=True,exist_ok=False);start=time.monotonic();fresh={};fits={}
    for f in 'ABC':
        meta=models.fit(f,output/'models');old=read(data.WORK/'models'/f/'fit.json')
        if meta['hashes']!=old['hashes']:raise ContractError('fresh joint-role models differ')
        fresh[f]=models.Predictor(f,output/'models');fits[f]={'fitted_files_identical':True,'training_credibility':meta['training_credibility']};print('Fresh joint-role fit identical',f,flush=True)
    plan=read(data.WORK/'data.json');rows=pd.read_parquet(data.WORK/'rows.parquet');count=0
    for j,ref in enumerate(plan['references']):
        gid=ref['game_id'];part=rows[rows.game_id.eq(gid)].set_index('player').loc[ref['captured_player_ids']].reset_index()
        with np.load(data.WORK/'minute_draws'/f'{gid}.npz',allow_pickle=False) as z:
            for f in 'ABC':
                for side in (0,1):
                    take=np.flatnonzero(z['side']==side);a=fresh[f].draw(part.iloc[take],1000,np.random.default_rng(screen.seed(gid,side)))
                    if not np.array_equal(a,z[f][:,take]):raise ContractError('fresh joint-minute draws differ')
                    count+=a.size
        if (j+1)%50==0:print('Fresh joint-minute draws identical',j+1,'/200',flush=True)
    rollout.init();gid=plan['game_ids'][0];replays={}
    for arm in ('bridge','A','B','C'):
        arrays,times,errors,_=rollout.generate(gid,(arm,),fresh=fresh);a=arrays[arm]
        with np.load(data.WORK/'games'/gid/f'{arm}.npz',allow_pickle=False) as z:
            if set(z.files)!=set(a) or any(not np.array_equal(z[k],a[k]) for k in z.files):raise ContractError('fresh single-worker role world replay differs')
        with (output/f'{arm}_replay.npz').open('xb') as stream:np.savez_compressed(stream,**a)
        replays[arm]={'all_arrays_exact':True,'worlds':1000,'seconds':times[arm],'decoder_fit':errors[arm]};print('Fresh joint-role game replay identical',arm,flush=True)
    decisions=decision(pd.read_parquet(data.WORK/'minute_scores.parquet'));stored=read(data.WORK/'minute_screen.json')
    for f in 'ABC':
        r=decisions[f]
        if abs(r['relative_change']-stored['changes'][f]['relative_change'])>1e-12 or r['coverage_rule_passed']!=stored['eligible'][f]['checks']['coverage80']:raise ContractError('independent minute decision differs')
    ids=plan['game_ids'] if (data.WORK/'final.json').exists() else plan['game_ids'][:20] if (data.WORK/'short.json').exists() else plan['game_ids'][:2];accounting=audit.world_audit(ids)
    result={'kind':'C04 fresh full-history fits/joint-minute draws/worker worlds and independent decision reproduction','fits':fits,'minute_forecast_values_exact':count,'minute_games':200,'replays':replays,'independent_decision':decisions,'minute_shortlist':stored['shortlist'],'accounting':accounting,'source':source(),'seconds':time.monotonic()-start,'retained_inputs':'immutable source-derived lag cache, native incumbent captures and original forecast rotation shapes; all new role fits/minute draws and replay worlds fresh','production_changed':False}
    create_json(output/'receipt.json',result);create_json(ROOT/'analysis/experiments/20261125_c04_reproduction_v1.json',result);print(result,flush=True);return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['source','run']);p.add_argument('--output',type=Path,default=ROOT/'data/derived/experiments/c04_reproduction_v1');a=p.parse_args();print(source()) if a.stage=='source' else reproduce(a.output)
