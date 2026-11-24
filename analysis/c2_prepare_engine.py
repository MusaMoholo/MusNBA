#!/usr/bin/env python3
"""Fit only the frozen C2 nominee's three F4 nodes and reuse13 safe control nodes."""
import copy
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import lightgbm as lgb
import pyarrow as pa
from basketball_common import read_json,write_json,sha256_file
from analysis import c2_node_screen as screen
from analysis.c2_prepare_aux import prepare


def main():
    if os.environ.get('OMP_NUM_THREADS')!='10' or os.environ.get('OPENBLAS_NUM_THREADS')!='1':raise ValueError('10 OMP/1 BLAS required')
    pa.set_cpu_count(1)
    grade=ROOT/'analysis/experiments/20261124_c2_node_screen_v2.json'
    ready=ROOT/'analysis/experiments/20261124_c2_ready_panels_v1.json'
    read_json(ready)
    selected=read_json(grade)['provisional_survivor_for_seed_noise']
    if selected not in ['zone','distance','defence']:raise ValueError('no frozen nominee')
    base=ROOT/'data/models/folds/a1_s02_f4_causal_guarded_diagnostic_F4_all'
    folder=ROOT/'data/models/folds/c2_court_F4_v2'
    if folder.exists():raise FileExistsError('candidate engine namespace is immutable; reuse its retained config after hash verification')
    for name in ['what','location','shot_result']:
        source=screen.WORK/f'F4_{name}_{selected}_s7'
        if not (source/'receipt.json').exists():screen.run('F4',name,selected)
        receipt=read_json(source/'receipt.json')
        if receipt['recipe_sha256']!=sha256_file(screen.PLAN):raise ValueError('F4 fit recipe differs')
        for filename,key in [('model.txt','model_sha256'),('validation.npz','validation_sha256')]:
            if sha256_file(source/filename)!=receipt[key]:raise ValueError('saved F4 model or validation changed')
    cfg=copy.deepcopy(read_json(base/'config.json'))
    cfg.update(version='c2_court_F4_v2',research_only=True,court_variant=selected)
    dependencies={str((base/'config.json').relative_to(ROOT)):sha256_file(base/'config.json')}
    for name,entry in cfg['nodes'].items():
        if name in ['what','location','shot_result']:
            source=screen.WORK/f'F4_{name}_{selected}_s7';r=read_json(source/'receipt.json')
            file=source/'model.txt';model=lgb.Booster(model_file=str(file))
            if model.feature_name()!=r['columns']:raise ValueError('model and feature interface differ')
            classes=len(r['layout']['pairs']) if name=='location' else 3 if name=='shot_result' else 8
            cfg['nodes'][name]={'file':str(file),'kind':'multiclass','classes':classes,'columns':r['columns'],
                                'categorical':[c for c in ['start_code','zone','season_type','grp_code','court_cell'] if c in r['columns']],
                                'temperature':1.,'intercepts':None}
            dependencies[str((source/'receipt.json').relative_to(ROOT))]=sha256_file(source/'receipt.json')
        else:
            file=base/entry['file'];entry['file']=str(file)
        dependencies[str(file.relative_to(ROOT))]=sha256_file(file)
    aux=prepare('F4',selected)
    folder.mkdir(parents=True)
    auxfile=folder/'court.json';write_json(auxfile,aux,pretty=True)
    cfg.update(court_aux=str(auxfile.relative_to(ROOT)),court_aux_sha256=sha256_file(auxfile))
    write_json(folder/'config.json',cfg,pretty=True)
    output=ROOT/'analysis/experiments/20261124_c2_f4_preparation_v1.json'
    if output.exists():raise FileExistsError(output)
    write_json(output,{'kind':'isolated research engine; no promotion','nominee':selected,'grade_sha256':sha256_file(grade),
                       'model_version':str(folder.relative_to(ROOT/'data/models')),'training_through':cfg['train_through'],
                       'config_sha256':sha256_file(folder/'config.json'),'aux_sha256':sha256_file(auxfile),
                       'reused_nodes':13,'retrained_nodes':['what','location','shot_result'],
                       'dependency_sha256':dependencies,'production_changed':False},pretty=True)
    print('Prepared',selected,'F4 engine;13 safe control nodes reused',flush=True)

if __name__=='__main__':main()
