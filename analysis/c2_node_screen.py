#!/usr/bin/env python3
"""Finite C2 common-row node comparison; all artifacts isolated from production."""
from __future__ import annotations
import argparse,gc,os,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import lightgbm as lgb
import pyarrow as pa
from basketball_common import read_json,write_json,sha256_file
from scripts import nodes,train,court_zones as cz,court_profiles as cp

PLAN=ROOT/'analysis/experiments/20261124_c2_frozen_recipe_v2.json'
WORK=ROOT/'data/derived/experiments/c2_court_v2'


def source_rows(name):
    s=nodes.load_segments()
    shots=s.end_type.eq('shot') & ~s.heave & s.zone.isin(nodes.ZONES)
    if name=='what':
        m=s.actor.notna() & s.end_type.isin(['shot','fouled','turnover']) & ~s.heave
        m &= ~s.end_type.eq('shot') | s.zone.isin(nodes.ZONES)
        rows=s[m]
        label=np.where(rows.end_type.eq('shot'),rows.zone,np.where(rows.end_type.eq('turnover'),'turnover',np.where(rows.fta>=3,'fouled_3','fouled_2')))
        y=pd.Series(label).map(dict(zip(nodes.WHAT,range(8)))).to_numpy()
    else:
        rows=s[shots & (s.distance.notna() if name=='location' else True)]
        y=(nodes.location_band(rows.zone,rows.distance) if name=='location' else np.where(rows.made==1,np.where(rows.and_one,2,1),0))
    return rows.reset_index(drop=True),y


def augment(d,rows,profiles,variant,name,tr):
    """Append only prior features; original context/target/order must remain exact."""
    X=d['X'].copy()
    idx=pd.MultiIndex.from_frame(rows[['game_id','actor']].rename(columns={'actor':'player'}))
    off=profiles.reindex(idx)
    for col in cp.COLS[:44]+[f'court_rate_{i}' for i in range(22)]:X['actor_'+col]=off[col].to_numpy(np.float32)
    X['actor_court_uses_eff']=off.court_uses_eff.to_numpy(np.float32)
    X['actor_court_shots_eff']=off.court_shots_eff.to_numpy(np.float32)
    if variant=='defence':
        block=[]
        for slot in range(1,6):
            di=pd.MultiIndex.from_arrays([rows.game_id,rows[f'def_{slot}']])
            block.append(profiles.reindex(di)[cp.COLS[44:88]+[f'court_d_rate_{i}' for i in range(22)]].to_numpy(np.float32))
        vals=np.mean(np.stack(block),axis=0)
        for j,col in enumerate(cp.COLS[44:88]+[f'court_d_rate_{i}' for i in range(22)]):X['lineup_'+col]=vals[:,j]
    cell=cz.derive(rows.x,rows.y,rows.value)
    spec=cz.layout(variant!='zone')
    if name=='location':
        target=cz.encode(spec,rows.x.to_numpy(),rows.y.to_numpy(),rows.value.to_numpy())
        if np.any(target<0):raise ValueError('undeclared location support')
        coarse,fine,mask=cz.decoder(spec)
        if not mask[d['X'].zone.to_numpy(int),target].all():raise ValueError('legacy parent changed')
        return X,target,mask[d['X'].zone.to_numpy(int)],spec
    if name=='shot_result':
        X['court_cell']=cell.astype(np.float32)
        selected=np.maximum(cell,0)
        X['actor_court_fg_selected']=off[[f'court_fg_{i}' for i in range(22)]].to_numpy()[np.arange(len(rows)),selected].astype(np.float32)
        if variant=='zone':X=X.drop(columns=['distance','lateral'])
        else:
            label=cz.encode(spec,rows.x.to_numpy(),rows.y.to_numpy(),rows.value.to_numpy())
            for col in ['distance','lateral']:
                means=pd.Series(rows[col].to_numpy()[tr]).groupby(label[tr]).mean()
                X[col]=pd.Series(label).map(means).to_numpy(np.float32)
    return X,d['y'],d.get('class_mask'),spec


def run(fold,name,variant,seed=7):
    plan=read_json(PLAN);start=time.monotonic()
    pre=ROOT/f'data/derived/variants/a1_scheduled_{fold}_20261122_v3/features/pregame.parquet'
    d=next(nodes.datasets([name],pregame=pre))
    rows,y=source_rows(name)
    for key,col in [('game','game_id'),('date','date_et'),('period','period')]:
        np.testing.assert_array_equal(d[key],rows[col].to_numpy())
    np.testing.assert_array_equal(d['y'],y)
    # Independent raw target/context parity before any candidate feature enters.
    if 'zone' in d['X']:np.testing.assert_array_equal(d['X'].zone.to_numpy(),rows.zone.map(dict(zip(nodes.ZONES,range(5)))).to_numpy())
    cut=train.FOLDS[fold];date=d['date'];tr_all=(date>=train.BURN_IN)&(date<=cut[0]);va=(date>=cut[1])&(date<=cut[2])
    date_ns=pd.to_datetime(pd.Series(date)).astype('int64').to_numpy()
    es_from=np.quantile(date_ns[tr_all],.9);es=tr_all&(date_ns>=es_from);tr=tr_all&~es
    cfg=read_json(ROOT/'models/v1.3.json');cfg={**cfg['default'],**cfg['nodes'].get(name,{}),'threads':10,'seed':seed}
    profilepath=ROOT/'data/derived/experiments/c2_profiles_v2/pregame.parquet'
    spec=None
    if variant=='control':
        X=train.band_distances(d['X'],tr) if cfg['banded'] else d['X'];target=y;mask=d.get('class_mask')
    else:
        profiles=pd.read_parquet(profilepath).set_index(['game_id','player'])
        X,target,mask,spec=augment(d,rows,profiles,variant,name,tr)
        del profiles
    cols=train.model_columns(X,cfg['drop']);Xm=X[cols];del X;gc.collect()
    params=train.params('multiclass',int(tr.sum()),cfg);params['num_class']=int(target.max())+1 if name!='location' or variant=='control' else len(spec['pairs'])
    params['num_class']=d['classes'] if variant=='control' or name!='location' else len(spec['pairs'])
    cats=[c for c in train.CATEGORICAL+['court_cell'] if c in cols]
    dt=lgb.Dataset(Xm[tr],label=target[tr],weight=train.sample_weights(d,tr,cut[0],cfg),categorical_feature=cats)
    de=lgb.Dataset(Xm[es],label=target[es],reference=dt,categorical_feature=cats)
    folder=WORK/f'{fold}_{name}_{variant}_s{seed}'
    recovered=folder.exists()
    if recovered:
        if (folder/'receipt.json').exists():raise FileExistsError('completed namespace is immutable')
        model=lgb.Booster(model_file=str(folder/'model.txt'));model.best_iteration=model.current_iteration()
    else:
        model=lgb.train(params,dt,num_boost_round=3000,valid_sets=[de],callbacks=[lgb.early_stopping(50,verbose=False)])
    pred=model.predict(Xm[va],num_iteration=model.best_iteration)
    if mask is not None:
        pred*=mask[va];pred/=pred.sum(axis=1,keepdims=True)
    if not recovered:
        folder.mkdir(parents=True,exist_ok=False)
        model.save_model(str(folder/'model.txt'))
    artifacts={'game':d['game'][va].astype(str),'date':date[va].astype(str),'source_seg_id':rows.seg_id.to_numpy()[va],'target':target[va],'pred':pred,'cell':cz.derive(rows.x,rows.y,rows.value)[va]}
    if name=='shot_result':
        made=(y[va]>0);pm=pred[:,1:].sum(axis=1)
        artifacts['loss']=-np.log(np.maximum(np.where(made,pm,1-pm),train.EPS));artifacts['brier']=(pm-made)**2
    elif name=='what':artifacts['loss']=-np.log(np.maximum(pred[np.arange(va.sum()),target[va]],train.EPS))
    else:
        # Project both partitions to the same22-cell target conditional on old coarse zone.
        if variant=='control':
            cells=cz.derive(rows.x,rows.y,rows.value);bridge=np.zeros((nodes.LOCATION_BANDS,22))
            coarse=rows.zone.map(dict(zip(nodes.ZONES,range(5)))).to_numpy()
            for band in range(nodes.LOCATION_BANDS):
                z=np.flatnonzero(nodes.LOCATION_MASK[:,band])[0]
                league=np.bincount(cells[tr & (coarse==z)],minlength=22)+1
                counts=np.bincount(cells[tr & (y==band)],minlength=22)
                bridge[band]=(counts+50*league/league.sum())/(counts.sum()+50)
        else:
            _,fine,_=cz.decoder(spec);bridge=np.eye(22)[fine]
        fine_pred=pred@bridge
        artifacts['fine_pred']=fine_pred
        artifacts['loss']=-np.log(np.maximum(fine_pred[np.arange(va.sum()),artifacts['cell']],train.EPS))
    if recovered:
        saved=np.load(folder/'validation.npz',allow_pickle=False)
        if set(saved.files)!=set(artifacts):raise ValueError('recovery artifact contract changed')
        for key,val in artifacts.items():np.testing.assert_array_equal(saved[key],val)
    else:np.savez(folder/'validation.npz',**artifacts)
    info={'fold':fold,'node':name,'variant':variant,'seed':seed,'rows_train':int(tr.sum()),'rows_early_stop':int(es.sum()),'rows_validation':int(va.sum()),'training_cutoff':cut[0],'latest_training_date':str(max(date[tr_all].tolist())),'iterations':model.best_iteration,'seconds':time.monotonic()-start,'metadata_recovery':recovered,'recovery_note':'If true: retained fit/predictions replayed exactly, no refit; seconds measure metadata recovery only.','threads':10,'blas_threads':1,'matched_control_parity':True,'columns':cols,'layout':spec,'recipe_sha256':sha256_file(PLAN),'runner_sha256':sha256_file(Path(__file__)),'profile_sha256':sha256_file(profilepath),'base_cache_sha256':sha256_file(nodes.cache_dir(pre)/f'{name}.npz'),'source_sha256':{str(p.relative_to(ROOT)):sha256_file(p) for p in nodes.segment_files()},'validation_sha256':sha256_file(folder/'validation.npz'),'model_sha256':sha256_file(folder/'model.txt')}
    write_json(folder/'receipt.json',info,pretty=True)
    print(f'{fold} {name} {variant} seed{seed}: {info["rows_validation"]} rows, {info["iterations"]} rounds, {info["seconds"]:.2f}s',flush=True)


if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--fold',choices=['F1','F2','F3'],required=True);a.add_argument('--node',choices=['what','location','shot_result'],required=True);a.add_argument('--variant',choices=['control','zone','distance','defence'],required=True);a.add_argument('--seed',type=int,default=7);args=a.parse_args()
    if os.environ.get('OPENBLAS_NUM_THREADS')!='1' or os.environ.get('OMP_NUM_THREADS')!='10':raise ValueError('explicit10-thread compute and1-thread BLAS required')
    pa.set_cpu_count(1);run(args.fold,args.node,args.variant,args.seed)
