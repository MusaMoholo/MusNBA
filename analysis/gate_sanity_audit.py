#!/usr/bin/env python3
"""Audit existing gate arithmetic/objectives; no fitting, new forecasts or revised release decision."""
import argparse
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from basketball_common import read_json,sha256_file,write_json


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise FileExistsError('fresh audit path required')
    report_path=ROOT/f'analysis/experiments/{args.run}_compare.json'
    report=read_json(report_path)
    gate=read_json(report_path.with_name(report_path.stem+'_gate.json'))
    run=read_json(ROOT/f'analysis/experiments/{args.run}.json')
    stars=set()
    for item in run['captures']:
        row=read_json(ROOT/item['meta'])
        with np.load(ROOT/row['outputs']['control']['capture'],allow_pickle=False) as z:
            for pid,usage,start in zip(z['player_ids'],z['prior_usage'],z['prior_start_share']):
                if np.isfinite(usage) and np.isfinite(start) and usage>=.25:
                    stars.add((item['game'],str(pid)))
    paths=[ROOT/f'data/derived/experiments/{args.run}_{side}_players.parquet' for side in ('control','candidate')]
    left,right=map(pd.read_parquet,paths)
    rows=left.merge(right,on=['game_id','player'],suffixes=('_a','_b'),validate='one_to_one')
    rows=rows[[tuple(key) in stars for key in rows[['game_id','player']].to_numpy()]]
    ids=sorted(report['population']['game_ids']);positions={gid:i for i,gid in enumerate(ids)}
    draws=np.random.default_rng(20261122).integers(len(ids),size=(10000,len(ids)))
    estimates={}
    for stat in ('min','pts'):
        actual=rows[stat+'_actual_a'].to_numpy(float)
        assert np.array_equal(actual,rows[stat+'_actual_b'])
        a=rows[stat+'_sim_a'].to_numpy(float)-actual
        b=rows[stat+'_sim_b'].to_numpy(float)-actual
        grouped=np.zeros((len(ids),3))
        for gid,aa,bb in zip(rows['game_id'],a,b):
            grouped[positions[gid]] += (aa,bb,1)
        resampled=grouped[draws].sum(1)
        delta=np.abs(resampled[:,1]/resampled[:,2])-np.abs(resampled[:,0]/resampled[:,2])
        result={'control':float(a.mean()),'candidate':float(b.mean()),
                'change':float(abs(b.mean())-abs(a.mean())),
                'ci_95':np.quantile(delta,[.025,.975]).tolist()}
        saved=report['players']['star'][stat]['bias']
        for key in result:assert np.allclose(result[key],saved[key],rtol=0,atol=1e-12),(stat,key)
        estimates[stat]=result
    actual=np.array([30.,18.,30.,18.])
    control=np.array([28.,20.,32.,16.]);candidate=np.array([29.,19.,30.,18.])
    star=np.array([True,False,True,False])
    toy={'actual_minutes':actual.tolist(),'control_minutes':control.tolist(),'candidate_minutes':candidate.tolist(),
         'every_player_absolute_error_improves':bool((abs(candidate-actual)<abs(control-actual)).all()),
         'team_pair_sums_unchanged':bool(np.array_equal(control.reshape(2,2).sum(1),candidate.reshape(2,2).sum(1))),
         'mean_point_forecast_crps':[float(abs(x-actual).mean()) for x in (control,candidate)],
         'star_absolute_cohort_bias_change':float(abs((candidate-actual)[star].mean())-abs((control-actual)[star].mean())),
         'note':'Two star/bench pairs on different teams; four unchanged 48-minute players can pad each team to240. Point-mass CRPS is absolute error.'}
    proper=[r for r in gate['core']['details'] if r['metric'] in ('crps','brier','log_loss')]
    previous=ROOT/'analysis/experiments/20261123_gate_framework_audit_v1.json'
    aa=read_json(previous)['v2_same_model_independent_seed']
    write_json(args.output,{'kind':'audit of stored estimates and gate objectives; no new protected evaluation',
       'run':args.run,'star_player_games':len(rows),'independently_reproduced_bias':estimates,
       'proper_score_bounds':{'checks':len(proper),'established':sum(r['status']=='established' for r in proper)},
       'same_model_existing_audit':{'checks':aa['core']['checks'],'established':aa['core']['established'],
          'meaning':'A finite-resolution inconclusive check can occur for unchanged physics; not proof of harm.'},
       'synthetic_pareto_counterexample':toy,
       'interpretation':['Stored bias arithmetic and 10k paired game-bootstrap intervals reproduce independently.',
          'Cohort bias is absolute average signed error, not each player average absolute error.',
          'A universal cohort-bias veto can reject improvement for every player while team sums remain exact.',
          'This is evidence about acceptance objectives/power, not automatic approval or proof this candidate dominates.',
          'Original protected score/gates remain unchanged; no resimulation or threshold adjustment was performed.'],
       'evidence_sha256':{str(p.relative_to(ROOT)):sha256_file(p) for p in [Path(__file__),report_path,previous,*paths]}},pretty=True)
    print('bias arithmetic verified; proper scores',sum(r['status']=='established' for r in proper),'/',len(proper),flush=True)


if __name__=='__main__':main()
