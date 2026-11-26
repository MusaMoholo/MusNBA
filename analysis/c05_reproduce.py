"""Fresh fits/draws and worker replay, independent score/coverage/decision audit."""
from __future__ import annotations
import argparse,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from analysis import c05_models as models,c05_data as data,c05_screen as screen,c05_rollout as rollout,c05_audit as audit
from analysis.c01_workbench import read,create_json
from analysis.c01_core import ContractError


def independent_decision():
    rows=pd.read_parquet(data.WORK/'minute_scores.parquet');r=rows[rows.model.eq('native')].set_index(['game_id','player']).sort_index();stored=read(data.WORK/'minute_screen.json');out={};bad=set(data.verify()['flagged_reconstructed_minute_ids'])
    for family in 'ABC':
        q=rows[rows.model.eq(family)].set_index(['game_id','player']).sort_index()
        if not q.index.equals(r.index) or not np.array_equal(q.truth,r.truth):raise ContractError('independent support differs')
        delta=q.crps-r.crps;critical=q.critical;change=float(delta.mean());cover={level:float(q[f'covered{level}'].mean()) for level in (50,80,95)}
        numerical={'minute_gain':change/r.crps.mean()<=-.02,'halves':all(q[f'crps_half{k}'].mean()<r[f'crps_half{k}'].mean() for k in (1,2)),'support':q.reset_index().game_id.nunique()>=100 and len(q)>=2000,'critical_harm':float(delta[critical].mean()/r.loc[critical,'crps'].mean())<=.02,'coverage50':.45<=cover[50]<=.55,'coverage80':.76<=cover[80]<=.84,'coverage95':.92<=cover[95]<=.98,'critical_coverage80':.73<=q.loc[critical,'covered80'].mean()<=.87}
        for k,v in numerical.items():
            if bool(v)!=stored['eligible'][family]['checks'][k]:raise ContractError('independent acceptance mismatch:'+k)
        if abs(change-stored['changes'][family]['overall']['change'])>1e-10:raise ContractError('independent change mismatch')
        sensitivities={}
        for label,mask in [('reconciled',~q.index.get_level_values('game_id').isin(bad)),('flagged',q.index.get_level_values('game_id').isin(bad))]:sensitivities[label]={'rows':int(sum(mask)),'crps_change':float(delta[mask].mean()),'coverage80':float(q.loc[mask,'covered80'].mean())}
        out[family]={'checks_independently_matched':list(numerical),'change_minutes':change,'coverage':cover,'critical_coverage80':float(q.loc[critical,'covered80'].mean()),'source_quality':sensitivities,'eligibility':stored['eligible'][family]['eligible']}
    return out


def run(output):
    data.verify();output=Path(output).resolve()
    if not output.is_relative_to(ROOT/'data'):raise ContractError('private reproduction must stay under ignored data')
    start=time.monotonic();meta=models.fit(output);old=read(data.WORK/'fit.json')
    if meta['hashes']!=old['hashes']:raise ContractError('fresh model differs')
    fresh={f:models.Predictor(f,output) for f in 'ABC'};rows=pd.read_parquet(models.data.WORK/'rows.parquet');plan=data.verify();count=0
    for j,ref in enumerate(plan['references']):
        gid=ref['game_id'];part=rows[rows.game_id.eq(gid)].set_index('player').loc[ref['captured_player_ids']].reset_index()
        with np.load(data.WORK/'minute_draws'/f'{gid}.npz',allow_pickle=False) as z:
            for f in 'ABC':
                for side in (0,1):
                    take=np.flatnonzero(z['side']==side);a=fresh[f].draw(part.iloc[take],1000,np.random.default_rng(screen.seed(gid,side)))
                    if not np.array_equal(a,z[f][:,take]):raise ContractError('fresh draws differ')
                    count+=a.size
        if (j+1)%50==0:print('C05 fresh draws identical',j+1,'/200',flush=True)
    rollout.init();gid=plan['game_ids'][0];replays={}
    for arm in ('bridge','A','B','C'):
        arrays,times,errors,_=rollout.generate(gid,(arm,),fresh=fresh)
        with np.load(data.WORK/'games'/gid/f'{arm}.npz',allow_pickle=False) as z:
            if set(z.files)!=set(arrays[arm]) or any(not np.array_equal(z[k],arrays[arm][k]) for k in z.files):raise ContractError('single-worker replay differs')
        with (output/f'{arm}_replay.npz').open('xb') as stream:np.savez_compressed(stream,**arrays[arm])
        replays[arm]={'all_arrays_exact':True,'worlds':1000,'seconds':times[arm],'decoder_error':errors[arm]};print('C05 worker replay exact',arm,flush=True)
    result={'kind':'C05 fresh fit/draw/world reproduction','fresh_fit_hashes_exact':True,'minute_values_exact':count,'replays':replays,'minute_accounting':audit.minute_audit(),'world_accounting':audit.world_audit(plan['game_ids'][:2]),'independent_decision':independent_decision(),'seconds':time.monotonic()-start,'production_changed':False};create_json(output/'reproduction.json',result);create_json(ROOT/'analysis/experiments/20261126_c05_reproduction_v1.json',result)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ROOT/'data/derived/experiments/c05_reproduction_v1');a=p.parse_args();run(a.output)
