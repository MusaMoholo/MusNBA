#!/usr/bin/env python3
"""Frozen B1 whole-game team-score benefit plus player-first v3 safeguards."""
from pathlib import Path
import argparse
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from basketball_common import read_json,write_json,sha256_file
from scripts import a1_compare,release_gate


def team_metrics(control,candidate):
    ids=sorted(control.game_id.tolist())
    a,b=control.set_index('game_id').loc[ids],candidate.set_index('game_id').loc[ids]
    if len(ids)!=200 or set(ids)!=set(candidate.game_id) or len(candidate)!=200:
        raise ValueError('two complete identical200-game panels required')
    truth=np.column_stack([a.real_home,a.real_away]).astype(float)
    if not np.array_equal(truth,np.column_stack([b.real_home,b.real_away])):
        raise ValueError('truth differs')
    weights=np.random.default_rng(20261122).multinomial(200,np.full(200,1/200),size=10000).astype(float)
    summaries={};vectors={}
    for label,frame in [('control',a),('candidate',b)]:
        error=np.column_stack([frame.home_sim,frame.away_sim])-truth
        vectors[label]={'bias':error.mean(1),'mae':np.abs(error).mean(1),'mse':(error**2).mean(1),
                        'crps':np.column_stack([frame.home_crps,frame.away_crps]).mean(1)}
        summaries[label]={}
        for metric,vector in vectors[label].items():
            mean=vector.mean();boot=weights@vector/200
            if metric=='mse':metric,mean,boot='rmse',np.sqrt(mean),np.sqrt(boot)
            summaries[label][metric]={'mean':float(mean),'ci95':np.quantile(boot,[.025,.975]).tolist()}
    gain=vectors['control']['crps']-vectors['candidate']['crps']
    ci=np.quantile(weights@gain/200,[.025,.975]).tolist()
    primary={'control':summaries['control']['crps']['mean'],'candidate':summaries['candidate']['crps']['mean'],
             'change':float(-gain.mean()),'ci_95':[-ci[1],-ci[0]]}
    baseline=summaries['control']['bias']
    detectable=baseline['ci95'][0]>0 or baseline['ci95'][1]<0
    bias_pass=(abs(summaries['candidate']['bias']['mean'])<=.75*abs(baseline['mean']) if detectable else
               abs(summaries['candidate']['bias']['mean'])<=1.)
    checks={'primary_ci95_lower_above_zero':ci[0]>0,'primary_mean_gain_at_least_point05':float(gain.mean())>=.05,
            'mae_not_increased':summaries['candidate']['mae']['mean']<=summaries['control']['mae']['mean'],
            'rmse_not_increased':summaries['candidate']['rmse']['mean']<=summaries['control']['rmse']['mean'],
            'owner_bias_target':bias_pass}
    return {'arms':summaries,'primary_gain':{'mean':float(gain.mean()),'ci95':ci},
            'control_bias_detectable':detectable,'checks':checks},primary


def strata(control,candidate):
    """Descriptive support stays visible; these do not replace frozen primary gates."""
    output={}
    for arm,frame in [('control',control),('candidate',candidate)]:
        parts=[]
        for side in ('home','away'):
            parts.append(pd.DataFrame({'game_id':frame.game_id,'side':side,'team':frame[side],
                'actual':frame['real_'+side],'sim':frame[side+'_sim'],'crps':frame[side+'_crps'],
                'coverage80':frame[side+'_coverage_expected'],
                'actual_pace':(frame.real_poss_home+frame.real_poss_away)/2}))
        rows=pd.concat(parts,ignore_index=True)
        rows['pace']=pd.qcut(rows.actual_pace,3,labels=['low','middle','high'])
        output[arm]={}
        for column in ('side','team','pace'):
            output[arm][column]={}
            for label,part in rows.groupby(column,observed=True):
                error=part.sim-part.actual;n=part.game_id.nunique()
                output[arm][column][str(label)]={'games':n,'team_games':len(part),
                    'support':'supported' if n>=30 else 'small descriptive stratum',
                    'bias':float(error.mean()),'mae':float(error.abs().mean()),
                    'rmse':float(np.sqrt((error**2).mean())),'crps':float(part.crps.mean()),
                    'coverage80':float(part.coverage80.mean())}
    return output


def main(phase):
    name=f'b1_{phase}_v2';phase_path=ROOT/f'analysis/experiments/20261124_{name}.json'
    result=read_json(phase_path)
    output=ROOT/f'analysis/experiments/20261124_b1_{phase}_decision_v2.json'
    comparison_path=ROOT/f'analysis/experiments/20261124_b1_{phase}_compare_v2.json'
    gate_path=ROOT/f'analysis/experiments/20261124_b1_{phase}_gate_v2.json'
    if any(p.exists() for p in [output,comparison_path,gate_path]):
        raise FileExistsError('grade is immutable; inspect any partial outputs')
    recipe_path=ROOT/'analysis/experiments/20261124_b1_frozen_recipe_v2.json'
    recipe=read_json(recipe_path)
    if result['game_ids']!=recipe['panels'][phase] or len(result['receipts'])!=400:
        raise ValueError('complete frozen pairs required')
    for path,digest in result['derived_outputs'].items():
        if sha256_file(ROOT/path)!=digest:raise ValueError('grade arrays changed')
    frames={arm:pd.read_parquet(ROOT/f'data/derived/experiments/{name}_{arm}.parquet') for arm in ['reference','candidate']}
    team,primary=team_metrics(frames['reference'],frames['candidate'])
    report=a1_compare.compare(name+'_reference',name+'_candidate')
    report['team_points']={'crps':primary}
    gate=release_gate.assess(report,'learned','team_points/crps',policy='v3')
    qualified=all(team['checks'].values()) and gate['statistical_compatibility']
    checked={};counts={};component_checks=0
    for descriptor in result['receipts']:
        path=ROOT/descriptor['receipt']
        if sha256_file(path)!=descriptor['sha256']:raise ValueError('receipt changed')
        row=read_json(path)
        # Independent scoring identity: inferred makes must equal the separately stored engine FGM means.
        with np.load(ROOT/row['entry']['capture'],allow_pickle=False) as raw:
            made=(raw['player_points'].astype(np.int64)-raw['player_ftm']-raw['player_fg3m'])/2
            if (made!=np.floor(made)).any() or (made<raw['player_fg3m']).any() or (made>raw['player_fga']).any():
                raise ValueError('captured field-goal identity failed')
            for side,label in enumerate(('home','away')):
                inferred=float(made[:,raw['side']==side].sum((1,2)).mean())
                if abs(inferred-row['entry']['result']['sim_fgm_'+label])>1e-10:
                    raise ValueError('independently reconstructed FGM differs from stored engine means')
                component_checks+=1
        for key,value in row['audit'].items():
            if isinstance(value,(int,float)):
                checked[key]=max(checked.get(key,0),value) if key.startswith('max_') else checked.get(key,0)+value
        if descriptor['arm']=='candidate':
            for key,value in row['mechanism'].items():counts[key]=counts.get(key,0)+value
    write_json(comparison_path,report,pretty=True);write_json(gate_path,gate,pretty=True)
    write_json(output,{'kind':'B1 fixed team-score development/independent decision; no automatic promotion',
        'phase':phase,'policy':recipe['policy'],'qualified':qualified,'team_score_objective_met':False,
        'team_metrics':team,'descriptive_strata':strata(frames['reference'],frames['candidate']),
        'player_first_gate':{'compatible':gate['statistical_compatibility'],
            'proper_established':gate['core']['established'],'proper_checks':gate['core']['checks'],
            'coverage_harms':[x for x in gate['coverage']['details'] if x['status']=='material_harm'],
            'unresolved_proper':[x for x in gate['core']['details'] if x['status']!='established']},
        'mechanism_counts':counts,'independent_accounting':checked,'independent_fgm_component_checks':component_checks,
        'next':('Run unchanged independent200 screen' if phase=='development' else 'Freeze applicable broader/seed/stress qualification')
                if qualified else 'Retain r3; close this single recipe without rescue, independent or protected scoring. Owner team-score objective remains unmet.',
        'production_changed':False,'protected_scoring':False,
        'source_sha256':{str(p.relative_to(ROOT)):sha256_file(p) for p in
            [Path(__file__),recipe_path,phase_path,comparison_path,gate_path]}},pretty=True)
    print({'qualified':qualified,'team_metrics':team,'proper':f"{gate['core']['established']}/{gate['core']['checks']}"},flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=['development','confirmation'])
    main(parser.parse_args().phase)
