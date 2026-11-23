#!/usr/bin/env python3
"""Frozen contextual-clock engine panels; reuse r2 controls and audit inside the worker budget."""
import argparse
from datetime import datetime,timezone
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from basketball_common import read_json,write_json,sha256_file
from analysis import rule3_confirmation as paired,rule3_pipeline_audit as auditor
from scripts import backtest,engine
from scripts.late_clock import ContextClock

MANIFEST=ROOT/'analysis/experiments/20261123_a2_clock_engine_runtime_manifest_v1.json'
PANELS=ROOT/'analysis/experiments/20261123_a2_clock_engine_panels_v1.json'
ROTATION=ROOT/'analysis/experiments/20261123_independent_rotation_panels_v2.json'
FOLD=os.environ.get('MUSNBA_CLOCK_FOLD','F4')
PHASE=os.environ.get('MUSNBA_CLOCK_PHASE','development')
ORIGINAL_GAME,ORIGINAL_READ=paired.paired_game,paired.read_json
BASE={'pilot':'independent_rotation_pilot_20261123_v1','development':'independent_rotation_f4_20261123_v1',
      'confirmation':'independent_rotation_policy_confirmation_20261123_v1'}
CLOCK=None


def metadata(fold):
    if fold=='F4':return {'fold':fold,'config':'models/v1.2d.json','models':'folds/v1.2d_F4_all'}
    entry=ORIGINAL_READ(PANELS)['earlier_fold_panels'][fold]
    preparation=ORIGINAL_READ(ROOT/f'analysis/experiments/20261122_a1_dated_{fold.lower()}_exhaustion_v1.json')
    if preparation['model_version']!=entry['models']:raise ValueError('dated fold model identity differs')
    return {'fold':fold,'config':preparation['config'],'models':entry['models']}


def pool_paths(fold):
    phase='confirmation' if fold=='F4' else 'screen'
    return (ROOT/f'data/derived/experiments/20261123_a2_late_clock_{phase}_v1/{fold}_pools.json',
            ROOT/f'analysis/experiments/20261123_a2_late_clock_{phase}_v1.json')


def sources():
    prior=ORIGINAL_READ(ROOT/'analysis/experiments/20261123_rotation_policy_confirmation_manifest_v1.json')['sources']
    paths={ROOT/name for name in prior}
    paths.update([Path(__file__),PANELS,ROTATION,Path(auditor.__file__),ROOT/'scripts/late_clock.py',
                  ROOT/'analysis/a2_clock_scores.py',ROOT/'docs/protocols/a2_clock_engine_20261123.md',
                  ROOT/'docs/protocols/a2_clock_v3_development_20261123.md',
                  ROOT/'analysis/experiments/20261123_r2_release_v1.json',
                  ROOT/'analysis/experiments/20261123_a2_clock_off_parity_v1.json'])
    for fold in ('F1','F2','F3','F4'):
        paths.update(pool_paths(fold))
        info=metadata(fold);cfg=ROOT/info['config'];model=ROOT/'data/models'/info['models']
        paths.add(cfg);paths.update(model.glob('*'))
        fitted=ORIGINAL_READ(model/'config.json');feature=ROOT/Path(fitted['features']).parent
        if fold!='F4':paths.add(ROOT/f'analysis/experiments/20261122_a1_dated_{fold.lower()}_exhaustion_v1.json')
        paths.update(feature/name for name in ('pregame.parquet','team_pregame.parquet','features_report.json'))
        paths.add(ROOT/fitted['matchup'])
    return {str(p.relative_to(ROOT)):sha256_file(p) for p in sorted(paths)}


def freeze():
    if MANIFEST.exists():raise FileExistsError('clock engine runtime is already frozen')
    off=ORIGINAL_READ(ROOT/'analysis/experiments/20261123_a2_clock_off_parity_v1.json')
    if len(off['games'])!=3 or not all(g['raw_world_parity'] for g in off['games']):
        raise ValueError('three independent-fit hook-off raw replays required')
    if engine.ENGINE['id']!='engine-v1.3-r2' or engine.ENGINE.get('rotation_fit')!='independent-v1':
        raise ValueError('A1-qualified independent fitter required')
    plan=ORIGINAL_READ(PANELS);rot=ORIGINAL_READ(ROTATION)
    for fold in ('F1','F2','F3','F4'):
        pool,report=pool_paths(fold);result=ORIGINAL_READ(report)
        if sha256_file(pool)!=result['fitted_pools_sha256'][fold]:raise ValueError('frozen clock pool differs')
        info=result['folds'][fold]
        if not info['primary_pass'] or not info['component_compatible']:raise ValueError('node primary not established')
        ContextClock(ORIGINAL_READ(pool),info['training']['cells'])
    write_json(MANIFEST,{'frozen_at':datetime.now(timezone.utc).isoformat(),
        'baseline':'engine-v1.3-r2','candidate':'engine-v1.3-r3','policy':'promotion-v3-20261123',
        'development':rot['development'],'confirmation':plan['F4_confirmation'],
        'pilot':rot['pilot'],'stream':plan['independent_stream_ids'],'stress':plan['stress_10000_ids'],
        'earlier':{fold:entry['game_ids'] for fold,entry in plan['earlier_fold_panels'].items()},
        'worlds':1000,'stress_worlds':10000,
        'runner_metadata':{fold:metadata(fold) for fold in ('F1','F2','F3','F4')},
        'path_resolution':'Original earlier-fold model identities/IDs/seeds unchanged; resolve planned config aliases through their retained preparation records.',
        'stress_execution':'ten deterministic 1k chunks per game/arm; three real games, never thirty independent games; seed namespace a2-clock-stress-chunk-v1',
        'primary':'frozen conditional joint time/no-action proper loss vs legacy AND clean bridge, with original component bounds',
        'source_sha256':sources()},pretty=True)
    print('Frozen clock recipe/panels/primary and r2 baseline before clock engine outcomes.',flush=True)


def fingerprints():
    return {**sources(),str(MANIFEST.relative_to(ROOT)):sha256_file(MANIFEST)}


def declaration(path):
    result=ORIGINAL_READ(path)
    if Path(path)==MANIFEST:
        ids=(result['earlier'][FOLD] if PHASE=='earlier' else result['confirmation'] if PHASE=='confirmation' else result['development'])
        return {**result,'game_ids':ids,'pilot_games':result['pilot'],'stress_10000_games':result['stress'],
                'independent_stream_games':result['stream'],'runner_metadata':metadata(FOLD)}
    return result


def init_worker(worlds,stream):
    global CLOCK
    info=metadata(FOLD);plan=ORIGINAL_READ(PANELS)
    key=plan['earlier_fold_panels'][FOLD]['seed_key'] if FOLD!='F4' else None
    backtest._W.clear()
    backtest._init(info['models'],str(ROOT/info['config']),FOLD,worlds,rotation='targets',pool=0,stream=stream,seed_key=key)
    # Explicit runtime: an explicit node version otherwise intentionally selects legacy replay.
    backtest._W['engine'].runtime={**engine.ENGINE,'models':info['models']}
    pool,report=pool_paths(FOLD);training=ORIGINAL_READ(report)['folds'][FOLD]['training']
    if training['cutoff']!=backtest.FOLDS[FOLD][0] or training['latest_training_date']>training['cutoff']:
        raise ValueError('clock pool crosses fold cutoff')
    CLOCK=ContextClock(ORIGINAL_READ(pool),training['cells'])


def game(task):
    gid,directory=task;eng=backtest._W['engine'];runtime=dict(eng.runtime)
    result={'game':gid,'outputs':{},'control_corrected':True,'recipe':'qualified r2 plus frozen contextual clock only'}
    if FOLD=='F4' and PHASE in BASE:
        run=BASE[PHASE];source=ROOT/f'data/derived/experiments/{run}/{gid}.json'
        declared=next(row for row in ORIGINAL_READ(ROOT/f'analysis/experiments/{run}.json')['captures'] if row['game']==gid)
        if sha256_file(source)!=declared['meta_sha256']:raise ValueError('changed retained r2 metadata')
        control=ORIGINAL_READ(source)['outputs']['candidate']
        if sha256_file(ROOT/control['capture'])!=control['sha256']:raise ValueError('changed r2 capture')
        result['outputs']['control']=control
        result['reused_control']={'meta':str(source.relative_to(ROOT)),'sha256':sha256_file(source)}
    for label in ('control','candidate'):
        if label in result['outputs']:continue
        eng.clock_policy=CLOCK if label=='candidate' else None
        eng.runtime={**runtime,'id':'engine-v1.3-r3-candidate' if label=='candidate' else 'engine-v1.3-r2'}
        try:row=ORIGINAL_GAME(task,labels=(label,),corrected=(True,True),persist=False)
        finally:eng.clock_policy=None;eng.runtime=runtime
        result['outputs'].update(row['outputs'])
        result.update({k:row[k] for k in ('worker_pid','worker_peak_rss_bytes')})
    path=Path(directory)/f'{gid}.json';write_json(path,result,pretty=False)
    cache=Path(directory).with_name(Path(directory).name+'_independent_audits');cache.mkdir(exist_ok=True)
    auditor.audit_pair((str(path),str(cache/f'{gid}.json')))
    return result


def finish_audit(run):
    folder=ROOT/f'data/derived/experiments/{run}';cache=folder.with_name(folder.name+'_independent_audits')
    cache.mkdir(exist_ok=True)
    plan={'plan_sha256':sha256_file(folder/'plan.json'),'auditor_sha256':sha256_file(Path(auditor.audit.__file__)),
          'pipeline_sha256':sha256_file(Path(auditor.__file__))}
    if (cache/'plan.json').exists() and ORIGINAL_READ(cache/'plan.json')!=plan:raise ValueError('audit cache source differs')
    if not (cache/'plan.json').exists():write_json(cache/'plan.json',plan,pretty=True)
    sys.argv=[sys.argv[0],run,'--jobs','1','--resume','--output',str(ROOT/f'analysis/experiments/{run}_audit.json')]
    auditor.main()


if __name__=='__main__':
    p=argparse.ArgumentParser(add_help=False);p.add_argument('action',choices=('freeze','run'))
    p.add_argument('--phase',choices=('pilot','development','confirmation','earlier','stream'),default='development')
    p.add_argument('--fold',choices=('F1','F2','F3','F4'),default='F4')
    args,remaining=p.parse_known_args();FOLD,PHASE=args.fold,args.phase
    os.environ['MUSNBA_CLOCK_FOLD'],os.environ['MUSNBA_CLOCK_PHASE']=FOLD,PHASE
    if args.action=='freeze':freeze()
    else:
        if (FOLD!='F4')!=(PHASE=='earlier'):raise ValueError('earlier phase requires F1–F3; other phases use F4')
        if ORIGINAL_READ(MANIFEST)['source_sha256']!=sources():raise ValueError('frozen clock recipe/input changed')
        name=remaining[remaining.index('--name')+1] if '--name' in remaining else None
        if not name:raise ValueError('explicit fresh run name required')
        mode={'pilot':'--pilot','stream':'--stream-check'}.get(PHASE)
        sys.argv=[sys.argv[0],*remaining,*([mode] if mode else [])]
        paired.PLAN,paired.paired_game,paired.init_worker=MANIFEST,game,init_worker
        paired.fingerprints,paired.read_json=fingerprints,declaration
        paired.main()
        if (ROOT/f'analysis/experiments/{name}.json').exists():finish_audit(name)
