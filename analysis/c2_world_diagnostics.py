#!/usr/bin/env python3
"""Fixed-panel C2 tails/dependence from saved worlds; no new simulation or factors."""
from concurrent.futures import ProcessPoolExecutor
import argparse,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import pyarrow as pa
from basketball_common import read_json,write_json,sha256_file
from analysis.a2_world_diagnostics import joint


def pit_tails(values,actual):
    if not np.isfinite(actual):return np.nan,np.nan
    lo=float((values<actual).mean());hi=float((values<=actual).mean())
    if hi==lo:return float(lo<.05),float(lo>.95)
    return max(0.,min(hi,.05)-lo)/(hi-lo),max(0.,hi-max(lo,.95))/(hi-lo)


def extract(item):
    pa.set_cpu_count(1)
    gid,arm,descriptor=item
    receipt=ROOT/descriptor['receipt']
    if sha256_file(receipt)!=descriptor['sha256']:raise ValueError('private arm metadata changed')
    entry=read_json(receipt)
    for key in descriptor['entry_selector'].split('/'):entry=entry[key]
    path=ROOT/entry['capture']
    if sha256_file(path)!=entry['sha256']:raise ValueError('capture changed')
    game=entry['result'];by_player={row['player']:row for row in game['players']}
    with np.load(path,allow_pickle=False) as z:
        ids=z['player_ids'].tolist();side=z['side'];usage=z['prior_usage'];starts=z['prior_start_share']
        minutes=z['minutes'].sum(2);points=z['player_points'].sum(2)
        ot=float((z['final_period']>4).mean());poss=z['possessions'].astype(float)
        final=z['team_points'].sum(2)
    rows=[]
    for i,pid in enumerate(ids):
        source=by_player.get(pid)
        if source is None:continue
        row={**source,'game_id':gid,'team':str(side[i]),'player':pid,
             'prior_tier':'unknown' if not np.isfinite([usage[i],starts[i]]).all() else 'star' if usage[i]>=.25 else 'starter' if starts[i]>=.5 else 'bench'}
        for stat,values in [('min',minutes[:,i]),('pts',points[:,i])]:
            actual=source.get(stat+'_actual');actual=np.nan if actual is None else float(actual)
            low,high=pit_tails(values,actual)
            row.update({stat+'_low5':low,stat+'_high5':high,stat+'_sd':float(values.std()),stat+'_zero':float((values==0).mean())})
        rows.append(row)
    return {'game':gid,'arm':arm,'rows':rows,'worlds':{'ids':ids,'minutes':minutes,'points':points},
            'pace':[game['real_poss_home'],game['real_poss_away'],*poss.mean(0),*poss.var(0),float(np.cov(poss.T,bias=True)[0,1])],
            'points':[game['real_home'],game['real_away'],*final.mean(0),*final.var(0),float(np.cov(final.T,bias=True)[0,1])],
            'ot':[game['real_ot'],ot]}


def dispersion(values,weights):
    a=np.asarray(values,float);error=a[:,:2]-a[:,2:4]
    means=weights@error/len(a);observed=weights@(error**2)/len(a)-means**2
    simulated=weights@a[:,4:6]/len(a)
    cross=weights@(error[:,0]*error[:,1])/len(a)-means[:,0]*means[:,1]
    within=weights@a[:,6]/len(a)
    return {'observed_error_variance':error.var(0).tolist(),'within_world_variance':a[:,4:6].mean(0).tolist(),
            'variance_gap_ci95':np.quantile(observed-simulated,[.025,.975],axis=0).T.tolist(),
            'observed_opponent_error_covariance':float(np.cov(error.T,bias=True)[0,1]),'within_world_opponent_covariance':float(a[:,6].mean()),
            'covariance_gap_ci95':np.quantile(cross-within,[.025,.975]).tolist()}


def main(jobs):
    if any(os.environ.get(n)!='1' for n in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS']):raise ValueError('one OMP/BLAS thread required')
    pa.set_cpu_count(1)
    phase=ROOT/'analysis/experiments/20261124_c2_engine_development_v2.json'
    output=ROOT/'analysis/experiments/20261124_c2_world_diagnostics_v1.json'
    if output.exists():raise FileExistsError(output)
    run=read_json(phase);gids=sorted(run['game_ids'])
    for name,digest in run['derived_outputs'].items():
        if sha256_file(ROOT/name)!=digest:raise ValueError('derived score input changed')
    if len(gids)!=200 or len(run['captures'])!=200:raise ValueError('complete fixed screen required')
    tasks=[(r['game'],arm,descriptor) for r in run['captures'] for arm,descriptor in r['arms'].items()]
    if len(tasks)!=600:raise ValueError('complete600-arm source metadata required')
    with ProcessPoolExecutor(max_workers=jobs) as pool:collected=list(pool.map(extract,tasks))
    # All large parent bootstrap/matrix work follows worker shutdown.
    data={arm:{r['game']:r for r in collected if r['arm']==arm} for arm in ['reference','bridge','candidate']}
    frames={arm:pd.DataFrame([row for gid in gids for row in data[arm][gid]['rows']]).set_index(['game_id','player']) for arm in data}
    reference=frames['reference'];role=reference['prior_tier']
    fixed=(role.ne('unknown') & reference[['min_actual','min_sim','pts_actual','pts_sim']].notna().all(axis=1)
           & reference.min_actual.ge(8)&reference.min_sim.ge(8))
    weights=np.random.default_rng(20261122).multinomial(200,np.full(200,1/200),size=10000).astype(float)
    report={}
    for arm,frame in frames.items():
        if set(frame.index)!=set(reference.index):raise ValueError('diagnostic player identity differs')
        frame=frame.reindex(reference.index).copy();frame['tier']=role
        frame['minutes']=frame.min_actual-frame.min_sim;frame['points']=frame.pts_actual-frame.pts_sim
        dependent=frame[fixed].reset_index();worlds={gid:data[arm][gid]['worlds'] for gid in gids}
        dependence={}
        for scope,star in [('all',False),('stars_starters',True)]:
            result=joint(dependent,worlds,gids,weights,star);counts=result['counts']
            supported=counts['games']>=50 and counts['teammate_team_games']>=100
            result['status']='supported' if supported else 'insufficient'
            if not supported:result.pop('metrics',None)
            dependence[scope]=result
        tails={}
        for cohort in ['all','star','starter','bench','unknown']:
            part=frame if cohort=='all' else frame[frame.tier.eq(cohort)]
            tails[cohort]={}
            for stat in ['min','pts']:
                valid=part[part[stat+'_low5'].notna() & part[stat+'_high5'].notna()]
                grouped=valid.reset_index().groupby('game_id').agg(n=('player','size'),low=(stat+'_low5','sum'),high=(stat+'_high5','sum'),sd=(stat+'_sd','sum'),zero=(stat+'_zero','sum')).reindex(gids,fill_value=0)
                n=len(valid);games=int((grouped.n>0).sum());supported=n>=100 and games>=30
                value={'player_games':n,'games':games,'status':'supported' if supported else 'insufficient','missing_outcomes':len(part)-n}
                if n:
                    for key in ['low','high','sd','zero']:
                        value[key]=float(grouped[key].sum()/n)
                        if supported:
                            boot=weights@grouped[key].to_numpy()/(weights@grouped.n.to_numpy())
                            value[key+'_ci95']=np.quantile(boot,[.025,.975]).tolist()
                tails[cohort][stat]=value
        ot=np.asarray([data[arm][gid]['ot'] for gid in gids])
        report[arm]={'tails':tails,'dependence':dependence,'pace':dispersion([data[arm][gid]['pace'] for gid in gids],weights),
                     'team_points':dispersion([data[arm][gid]['points'] for gid in gids],weights),
                     'overtime':{'actual':float(ot[:,0].mean()),'predicted':float(ot[:,1].mean()),'gap_ci95':np.quantile(weights@(ot[:,1]-ot[:,0])/200,[.025,.975]).tolist()}}
        print(arm,'tails, fixed-cohort dependence, team dispersion complete',flush=True)
    write_json(output,{'kind':'C2 stored-world diagnostics; no fitted factor or promotion rule','phase_sha256':sha256_file(phase),
                       'games':200,'arms':report,'fixed_dependence_player_games':int(fixed.sum()),'unknown_prior_roles':int(role.eq('unknown').sum()),
                       'bootstrap':{'unit':'game','replicates':10000,'seed':20261122},
                       'definitions':{'tails':'Expected randomized-PIT mass below0.05/above0.95; no probability or truth clamping.',
                                      'dependence':'Same reference-prior role and actual/reference-predicted MIN>=8 eligibility in every arm; role means re-estimated per bootstrap.',
                                      'zero':'Saved-world probability of zero minutes/points, conditional on actual-participant rosters.'},
                       'limits':['Source/mean error and latent variance are not identified separately.','Additional tail/dependence summaries are diagnostics, not replacement benefit claims.','Cohorts, axes and missingness remain explicit; unknown role is not assigned to bench.']},pretty=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--jobs',type=int,choices=range(1,11),default=8);args=parser.parse_args();main(args.jobs)
