#!/usr/bin/env python3
"""Grade frozen C2 node comparisons on common decision identities and labels."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from basketball_common import read_json,write_json,sha256_file
from scripts import compare,train,nodes,court_zones as cz
from analysis.c2_node_screen import WORK,PLAN,source_rows


def load(fold,node,variant,seed=7):
    folder=WORK/f'{fold}_{node}_{variant}_s{seed}';r=read_json(folder/'receipt.json')
    if r['recipe_sha256']!=sha256_file(PLAN):raise ValueError('recipe changed')
    if r['validation_sha256']!=sha256_file(folder/'validation.npz'):raise ValueError('predictions changed')
    if r['model_sha256']!=sha256_file(folder/'model.txt'):raise ValueError('fit changed')
    return dict(np.load(folder/'validation.npz',allow_pickle=False)),r


def pair(a,b,metric='loss'):
    for key in ['game','date','source_seg_id','cell']:np.testing.assert_array_equal(a[key],b[key])
    delta,se,_=compare.paired(a[metric],b[metric],a['game'])
    return {'delta':delta,'se':se,'z':compare.z_value(delta,se),'base':float(a[metric].mean()),'relative':delta/float(a[metric].mean()),'rows':len(a[metric]),'games':len(np.unique(a['game']))}


def bootstrap(parts,repeats=10000,seed=20261122):
    """Game-cluster bootstrap, stratified by fixed fold, weighted by decisions."""
    rng=np.random.default_rng(seed);sums=np.zeros(repeats);counts=np.zeros(repeats)
    for games,delta in parts:
        agg=pd.DataFrame({'game':games,'d':delta}).groupby('game').d.agg(['sum','size']).to_numpy()
        # Batch to keep scratch bounded while preserving the RNG stream.
        for start in range(0,repeats,100):
            end=min(start+100,repeats);idx=rng.integers(0,len(agg),size=(end-start,len(agg)))
            sums[start:end]+=agg[idx,0].sum(axis=1);counts[start:end]+=agg[idx,1].sum(axis=1)
    values=sums/counts
    return {'low_95':float(np.quantile(values,.025)),'high_95':float(np.quantile(values,.975)),
            'benefit_upper_bonferroni3':float(np.quantile(values,1-.05/3)),'repeats':repeats,'seed':seed,
            'pooled_delta':float(sum(d.sum() for g,d in parts)/sum(len(d) for g,d in parts))}


def supported_location_control(artifact,fold,rows):
    """Training-only bridge with structural zeroes for impossible fine cells.

    This diagnostic projection never changes a fit or the common make/miss primary.
    Preserve the originally saved predictions and derive this comparison in memory.
    """
    cut=train.FOLDS[fold];date=rows.date_et.to_numpy()
    tr_all=(date>=train.BURN_IN)&(date<=cut[0])
    date_ns=pd.to_datetime(rows.date_et).astype('int64').to_numpy()
    tr=tr_all & (date_ns<np.quantile(date_ns[tr_all],.9))
    cells=cz.derive(rows.x,rows.y,rows.value)
    coarse=rows.zone.map(dict(zip(nodes.ZONES,range(5)))).to_numpy()
    band=nodes.location_band(rows.zone,rows.distance)
    support=np.zeros((5,22),bool)
    for parent,cell in cz.layout(False)['pairs']:support[parent,cell]=True
    bridge=np.zeros((nodes.LOCATION_BANDS,22))
    for b in range(nodes.LOCATION_BANDS):
        parent=np.flatnonzero(nodes.LOCATION_MASK[:,b])[0]
        league=np.bincount(cells[tr & (coarse==parent)],minlength=22)+support[parent]
        counts=np.bincount(cells[tr & (band==b)],minlength=22)
        bridge[b]=(counts+50*league/league.sum())/(counts.sum()+50)
        assert not bridge[b,~support[parent]].any()
    out=dict(artifact);pred=artifact['pred']@bridge
    out['loss']=-np.log(np.maximum(pred[np.arange(len(pred)),artifact['cell']],train.EPS))
    return out


def grade(output):
    if output.exists():raise FileExistsError(output)
    ready=ROOT/'analysis/experiments/20261124_c2_ready_panels_v1.json'
    if read_json(ready)['training_recipe_sha256']!=sha256_file(PLAN):raise ValueError('panels have another recipe')
    variants={};receipts={}
    location_rows,_=source_rows('location')
    for variant in ['zone','distance','defence']:
        all_nodes={}
        for node in ['shot_result','what','location']:
            folds={};parts=[];brier={}
            for fold in ['F1','F2','F3']:
                a,ar=load(fold,node,'control');b,br=load(fold,node,variant)
                for key in ['base_cache_sha256','source_sha256']:assert ar[key]==br[key]
                if node=='location':a=supported_location_control(a,fold,location_rows)
                folds[fold]=pair(a,b);parts.append((a['game'],b['loss']-a['loss']))
                if node=='shot_result':brier[fold]=pair(a,b,'brier')
                for v,r in [('control',ar),(variant,br)]:
                    path=WORK/f'{fold}_{node}_{v}_s7/receipt.json';receipts[str(path.relative_to(ROOT))]=sha256_file(path)
            pooled=bootstrap(parts)
            all_nodes[node]={'folds':folds,'pooled':pooled,'brier':brier,
                             'interpretation':'Projected common22-cell loss, not raw differing categorical NLL' if node=='location' else 'Common make/miss loss' if node=='shot_result' else 'Identical8 WHAT labels'}
        primary=all_nodes['shot_result']['pooled']
        variants[variant]={'nodes':all_nodes,'primary_statistical_benefit':primary['benefit_upper_bonferroni3']<0}
    qualification=ROOT/'analysis/experiments/20261124_c2_qualification_v3.json'
    policy=read_json(qualification)
    if policy['training_recipe_sha256']!=sha256_file(PLAN):raise ValueError('qualification recipe differs')
    selected=min(variants,key=lambda v:variants[v]['nodes']['shot_result']['pooled']['pooled_delta'])
    result={'kind':'C2 predeclared node screen, not an engine qualification or promotion','recipe_sha256':sha256_file(PLAN),'location_projection':'supported-common-cells-v2; training-only K50 bridge; structural zeroes follow frozen geometry; saved model/primary unchanged','grader_sha256':sha256_file(Path(__file__)),'variants':variants,
            'panels_sha256':sha256_file(ready),'qualification_sha256':sha256_file(qualification),'provisional_survivor_for_seed_noise':selected,'decision':'One F1-F3 nominee for fixed seed-noise diagnostics and single whole-engine PTS screen; conditional node null alone cannot reject a location/frequency change',
            'receipt_sha256':receipts,'production_changed':False,'protected_evaluation_run':False,
            'limits':['Derived rounded coordinates are not native spatial truth.','On-court defenders are not primary defender assignments.','Source snapshots lack verified original revision/publication timing.','No claim of predictive harm merely from neutral/unsupported benefit.']}
    write_json(output,result,pretty=True)
    for v,r in variants.items():
        print(v,r['nodes']['shot_result']['pooled'],flush=True)
    print('Provisional survivor:',selected,flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);args=ap.parse_args();grade(args.output)
