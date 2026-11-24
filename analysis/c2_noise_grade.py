#!/usr/bin/env python3
"""Frozen seed-only relative-RMS diagnostics for the one C2 nominee."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from basketball_common import read_json,write_json,sha256_file
from analysis.c2_node_grade import load,pair


def main():
    output=ROOT/'analysis/experiments/20261124_c2_seed_noise_v1.json'
    if output.exists():raise FileExistsError(output)
    gradepath=ROOT/'analysis/experiments/20261124_c2_node_screen_v2.json'
    selected=read_json(gradepath)['provisional_survivor_for_seed_noise']
    guardpath=ROOT/'analysis/experiments/20261124_c2_execution_guard_v1.json'
    seed=read_json(guardpath)['secondary_seed'];nodes={}
    for name in ['shot_result','what']:
        arms={};folds={}
        for arm in ['control',selected]:
            noise=[];changes={}
            for fold in ['F1','F2','F3']:
                a,_=load(fold,name,arm,7);b,_=load(fold,name,arm,seed)
                changes[fold]=pair(a,b);noise.append(changes[fold]['relative'])
            arms[arm]={'relative_RMS':float(np.sqrt(np.mean(np.square(noise)))),'folds':changes}
        noise=max(a['relative_RMS'] for a in arms.values())
        for fold in ['F1','F2','F3']:
            a,_=load(fold,name,'control',7);b,_=load(fold,name,selected,7);folds[fold]=pair(a,b)
        mean_rel=float(np.mean([r['relative'] for r in folds.values()]))
        pooled=float(np.mean([r['delta'] for r in folds.values()]))
        se=float(np.sqrt(sum(r['se']**2 for r in folds.values()))/3)
        bad_fold=any(r['delta']>2*r['se'] and r['relative']>2*noise for r in folds.values())
        verdict=('better' if mean_rel < -noise and pooled<=-2*se and not bad_fold else
                 'worse' if (mean_rel>noise and pooled>=2*se) or bad_fold else 'neutral')
        nodes[name]={'arms':arms,'noise':noise,'folds':folds,'mean_relative':mean_rel,'pooled_delta':pooled,'pooled_se':se,
                     'material_bad_fold':bad_fold,'verdict':verdict}
    veto=nodes['what']['verdict']=='worse'
    write_json(output,{'kind':'predeclared seed-only noise and common-WHAT harm check; no model/seed replacement',
                       'nominee':selected,'secondary_seed':seed,'nodes':nodes,'what_material_harm_veto':veto,
                       'engine_screen_permitted':not veto,'grade_sha256':sha256_file(gradepath),'execution_guard_sha256':sha256_file(guardpath),
                       'limits':'Conditional conversion uncertainty alone does not reject a location/frequency change. Material common-WHAT harm veto remains the pre-outcome execution_guard_v1 rule. Full-engine points benefit still required for qualification.'},pretty=True)
    for name,row in nodes.items():print(name,row['verdict'],'relative RMS',row['noise'],'mean relative',row['mean_relative'],flush=True)
    print('WHAT material-harm veto:',veto,flush=True)

if __name__=='__main__':main()
