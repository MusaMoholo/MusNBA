#!/usr/bin/env python3
"""One frozen C2 F4 screen, with r3 and matched causal controls and exact reuse."""
from concurrent.futures import ProcessPoolExecutor,as_completed
from datetime import datetime,timezone
import argparse,copy,os,resource,sys,time
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import pyarrow as pa
from basketball_common import read_json,write_json,sha256_file
from scripts import backtest,engine,court_runtime
from scripts.late_clock import ContextClock
from analysis import rule3_confirmation as paired,rule3_capture_audit as audit

MANIFEST=ROOT/'analysis/experiments/20261124_c2_engine_runtime_v2.json'
READY=ROOT/'analysis/experiments/20261124_c2_ready_panels_v1.json'
OLD=ROOT/'analysis/experiments/a2_clock_development_20261123_v1.json'
REFERENCE='folds/v1.2d_F4_all'
BRIDGE='folds/a1_s02_f4_causal_guarded_diagnostic_F4_all'
CANDIDATE='folds/c2_court_F4_v2'
CLOCK='data/derived/experiments/20261123_a2_late_clock_confirmation_v1/F4_pools.json'
CLOCK_REPORT='analysis/experiments/20261123_a2_late_clock_confirmation_v1.json'
ARMS=('reference','bridge','candidate')
STATE={}


def sources():
    paths=[Path(__file__).resolve(),READY,OLD,ROOT/'analysis/experiments/20261124_c2_engine_design_v1.json',
           ROOT/'analysis/experiments/20261124_c2_f4_preparation_v1.json',ROOT/'analysis/experiments/20261124_c2_seed_noise_v1.json',ROOT/CLOCK,ROOT/CLOCK_REPORT,
           ROOT/'data/derived/experiments/c2_profiles_v2/pregame.parquet',ROOT/'basketball_common.py',
           ROOT/'analysis/rule3_confirmation.py',ROOT/'analysis/rule3_capture_audit.py']
    paths += [ROOT/f'scripts/{name}.py' for name in ['engine','backtest','nodes','minutes','rotations','foul_out','late_clock','matchups','projection','court_runtime','court_profiles','court_zones']]
    for version in [REFERENCE,BRIDGE,CANDIDATE]:
        folder=ROOT/'data/models'/version;cfg=read_json(folder/'config.json')
        paths.append(folder/'config.json')
        paths += [folder/entry['file'] for entry in cfg['nodes'].values()]
        feature=ROOT/Path(cfg['features']).parent
        paths += [feature/name for name in ['pregame.parquet','team_pregame.parquet','features_report.json']]
        paths.append(ROOT/cfg['matchup'])
        if cfg.get('court_aux'):paths.append(ROOT/cfg['court_aux'])
    paths += [ROOT/'data/derived/athletes.parquet',ROOT/'data/derived/teams.json']
    for year in range(2023,2027):
        paths += [ROOT/f'data/derived/history/{year}/{name}' for name in ['segments.parquet','stints.parquet','on_court.parquet','player_periods.csv.gz']]
        paths.append(ROOT/f'data/raw/hoopr/player_box_{year}.parquet')
    return {str(path.relative_to(ROOT)):sha256_file(path) for path in sorted(set(paths))}


def reference_sources_unchanged():
    old=read_json(OLD)['fingerprints'];changed=[]
    folder=ROOT/'data/models'/REFERENCE;cfg=read_json(folder/'config.json')
    feature=ROOT/Path(cfg['features']).parent
    required={folder/'config.json',*(folder/m['file'] for m in cfg['nodes'].values()),
              *(feature/name for name in ['pregame.parquet','team_pregame.parquet','features_report.json']),
              ROOT/cfg['matchup'],ROOT/'data/derived/athletes.parquet',ROOT/'data/derived/teams.json',
              ROOT/CLOCK,ROOT/CLOCK_REPORT,ROOT/'basketball_common.py',ROOT/'analysis/rule3_confirmation.py',
              ROOT/'analysis/a1_parallel_world_probe.py'}
    required.update(ROOT/f'scripts/{name}.py' for name in ['backtest','nodes','minutes','rotations','foul_out','late_clock','matchups','projection'])
    for year in range(2023,2027):
        required.update(ROOT/f'data/derived/history/{year}/{name}' for name in ['segments.parquet','stints.parquet','on_court.parquet','player_periods.csv.gz'])
        required.add(ROOT/f'data/raw/hoopr/player_box_{year}.parquet')
    for path in required:
        name=str(path.relative_to(ROOT))
        if name not in old or not path.is_file() or sha256_file(path)!=old[name]:changed.append(name)
    return sorted(changed)


def freeze():
    if MANIFEST.exists():raise FileExistsError(MANIFEST)
    panels=read_json(READY);prep=read_json(ROOT/'analysis/experiments/20261124_c2_f4_preparation_v1.json')
    if not read_json(ROOT/'analysis/experiments/20261124_c2_seed_noise_v1.json')['engine_screen_permitted']:raise ValueError('predeclared common-WHAT material-harm veto; engine screen not permitted')
    parity=read_json(ROOT/'analysis/experiments/20261124_c2_default_off_parity_v1.json')
    if parity['engine_sha256']!=sha256_file(ROOT/'scripts/engine.py'):raise ValueError('engine changed after default-off raw parity')
    if len(parity['games'])!=3 or not all(g['all_raw_arrays_identical'] for g in parity['games']):raise ValueError('three default-off replays required')
    cfg=read_json(ROOT/'data/models'/CANDIDATE/'config.json')
    if cfg['court_variant']!=prep['nominee'] or cfg['train_through']!='2025-12-31':raise ValueError('F4 nominee/cutoff differs')
    write_json(MANIFEST,{'frozen_at':datetime.now(timezone.utc).isoformat(),'kind':'one C2 engine development screen; no promotion',
                        'nominee':prep['nominee'],'development':panels['development_F4'],'wiring':panels['development_F4'][:3],
                        'worlds':1000,'seed_key':'v1.2d_F4','policy':'promotion-v3-20261123','primary':'players/all/pts/crps',
                        'required_comparisons':['reference vs candidate','bridge vs candidate'],
                        'reference_source_changes':reference_sources_unchanged(),'old_reference_manifest_sha256':sha256_file(OLD),
                        'source_sha256':sources()},pretty=True)
    print('Frozen200-game three-arm PTS screen and source/model/auxiliary identities',flush=True)


def init_worker():
    pa.set_cpu_count(1)
    backtest._W.clear()
    backtest._init(REFERENCE,str(ROOT/'models/v1.2d.json'),'F4',1000,rotation='targets',pool=0,seed_key='v1.2d_F4')
    eng=backtest._W['engine'];reference_inputs=backtest._W['inputs']
    bridge=engine.Models(BRIDGE);candidate=engine.Models(CANDIDATE)
    aux=read_json(ROOT/candidate.cfg['court_aux'])
    if sha256_file(ROOT/candidate.cfg['court_aux'])!=candidate.cfg['court_aux_sha256']:raise ValueError('court auxiliary changed')
    court_runtime.attach(candidate,aux)
    report=read_json(ROOT/CLOCK_REPORT)['folds']['F4']['training']
    if report['cutoff']!='2025-12-31' or report['latest_training_date']>report['cutoff']:raise ValueError('clock fitted after origin')
    eng.clock_policy=ContextClock(read_json(ROOT/CLOCK),report['cells'])
    safe_inputs=backtest.load_inputs(read_json(ROOT/'models/a1_s02_f4_causal_guarded.json'),'F4')
    profiles=pd.read_parquet(ROOT/'data/derived/experiments/c2_profiles_v2/pregame.parquet')
    STATE.update(models={'reference':eng.m,'bridge':bridge,'candidate':candidate},
                 inputs={'reference':reference_inputs,'bridge':safe_inputs,'candidate':safe_inputs},
                 profiles={gid:part for gid,part in profiles.groupby('game_id')})


def task(job):
    gid,arm,directory=job;folder=Path(directory)/gid/arm;folder.mkdir(parents=True,exist_ok=True)
    receipt=folder/'receipt.json'
    if receipt.exists():raise FileExistsError(receipt)
    eng=backtest._W['engine'];eng.m=STATE['models'][arm];backtest._W['inputs']=STATE['inputs'][arm]
    eng.runtime={**engine.ENGINE,'models':{'reference':REFERENCE,'bridge':BRIDGE,'candidate':CANDIDATE}[arm],
                 'id':'engine-v1.3-r3' if arm=='reference' else f'c2-{arm}-research-v2','clock_recipe':CLOCK}
    original=eng.simulate
    def simulate(g,worlds,seed):
        if arm=='candidate':court_runtime.attach_game(g,STATE['profiles'][gid])
        return original(g,worlds,seed)
    label='candidate' if arm=='candidate' else 'control'
    started=time.monotonic()
    with patch.object(eng,'simulate',side_effect=simulate):
        result=paired.paired_game((gid,str(folder)),labels=(label,),corrected=(True,True),persist=False)
    entry=result['outputs'][label]
    capture=ROOT/entry['capture']
    with np.load(capture,allow_pickle=False) as z:data={k:z[k] for k in z.files}
    if audit.capture_digest(data)!=entry['world_sha256']:raise ValueError('canonical raw digest differs')
    checked=audit.audit_worlds({**data,'trace_phase':data['trace_phase'].astype(np.int16)},foul_penalty=True)
    checked.update(audit.team_fouls(data,True));audit.audit_metrics(data,entry['result'])
    out={'game':gid,'arm':arm,'entry':entry,'audit':checked,'seconds':time.monotonic()-started,
         'worker_pid':os.getpid(),'worker_peak_rss_bytes':result['worker_peak_rss_bytes']}
    write_json(receipt,out,pretty=False)
    return {'game':gid,'arm':arm,'receipt':str(receipt.relative_to(ROOT)),'sha256':sha256_file(receipt)}


def retained_reference(gid):
    folder=ROOT/'data/derived/experiments/a2_clock_development_20261123_v1';path=folder/f'{gid}.json'
    if not path.exists():return None
    declared=next((r for r in read_json(OLD)['captures'] if r['game']==gid),None)
    if declared is None:return None
    if sha256_file(path)!=declared['meta_sha256']:raise ValueError('retained r3 metadata changed')
    entry=read_json(path)['outputs']['candidate']
    if sha256_file(ROOT/entry['capture'])!=entry['sha256']:raise ValueError('retained r3 capture changed')
    return entry,path


def run(phase,jobs):
    plan=read_json(MANIFEST)
    if plan['source_sha256']!=sources():raise ValueError('frozen runtime/model/input changed')
    ids=plan['wiring'] if phase=='wiring' else plan['development']
    root=ROOT/f'data/derived/experiments/c2_engine_{phase}_v1'
    output=root/'report.json'
    if output.exists():raise FileExistsError(output)
    signature={'manifest_sha256':sha256_file(MANIFEST),'game_ids':ids,'worlds':1000}
    if root.exists():
        if read_json(root/'plan.json')!=signature:raise ValueError('resume inputs differ')
    else:root.mkdir(parents=True);write_json(root/'plan.json',signature,pretty=True)
    done={};reused={};pending=[]
    wiring=read_json(ROOT/'data/derived/experiments/c2_engine_wiring_v1/report.json') if phase=='development' else None
    can_reuse=bool(wiring and wiring['reference_raw_parity'] and not plan['reference_source_changes'])
    for gid in ids:
        for arm in ARMS:
            receipt=root/gid/arm/'receipt.json'
            if receipt.exists():
                row=read_json(receipt);entry=row['entry']
                if row['game']!=gid or row['arm']!=arm or sha256_file(ROOT/entry['capture'])!=entry['sha256']:raise ValueError('completed arm changed')
                done[(gid,arm)]=row;continue
            old=(ROOT/f'data/derived/experiments/c2_engine_wiring_v1/{gid}/{arm}/receipt.json') if wiring and gid in plan['wiring'] else None
            if old is not None and old.exists():
                row=read_json(old)
                if sha256_file(ROOT/row['entry']['capture'])!=row['entry']['sha256']:raise ValueError('wiring capture changed')
                done[(gid,arm)]=row;reused[(gid,arm)]={'receipt':str(old.relative_to(ROOT)),'sha256':sha256_file(old)};continue
            retained=retained_reference(gid) if can_reuse and arm=='reference' else None
            if retained is not None:
                entry,path=retained;done[(gid,arm)]={'game':gid,'arm':arm,'entry':entry,'audit':'retained qualified r3 independent audit'}
                reused[(gid,arm)]={'reference_meta':str(path.relative_to(ROOT)),'sha256':sha256_file(path)};continue
            if (root/gid/arm).exists() and any((root/gid/arm).iterdir()):raise ValueError('partial arm requires explicit inspection; refusing overwrite')
            pending.append((gid,arm,str(root)))
    started=time.monotonic();finished=len(done);total=len(ids)*3
    # Parent preflight catches decoder/cutoff errors before starting the worker pool.
    init_worker();STATE.clear();backtest._W.clear()
    if pending:
        with ProcessPoolExecutor(max_workers=min(jobs,len(pending)),initializer=init_worker) as pool:
            for future in as_completed([pool.submit(task,job) for job in pending]):
                record=future.result();row=read_json(ROOT/record['receipt']);done[(row['game'],row['arm'])]=row;finished+=1
                if phase=='wiring' or finished%max(1,total//10)==0:print(f'{finished}/{total} arms complete; {time.monotonic()-started:.1f}s',flush=True)
    if plan['source_sha256']!=sources():raise ValueError('runtime/model/input changed during screen')
    raw_parity=[]
    if phase=='wiring':
        for gid in ids:
            retained=retained_reference(gid)
            if retained is None:raise ValueError('wiring reference lacks original capture')
            old,_=retained;new=done[(gid,'reference')]['entry']
            if old['world_sha256']!=new['world_sha256']:
                if not plan['reference_source_changes']:raise ValueError('F4 reference raw parity differs on unchanged inputs; repair required')
            else:raw_parity.append(gid)
    for arm in ARMS:
        values=[copy.deepcopy(done[(gid,arm)]['entry']['result']) for gid in ids]
        players=[r for game in values for r in game.pop('players')]
        name=f'c2_engine_{phase}_v1_{arm}'
        for path,frame in [(ROOT/f'data/derived/experiments/{name}.parquet',pd.DataFrame(values)),
                           (ROOT/f'data/derived/experiments/{name}_players.parquet',pd.DataFrame(players))]:
            if path.exists():raise FileExistsError(path)
            frame.to_parquet(path,index=False)
        write_json(ROOT/f'analysis/experiments/{name}.json',{'run':name,'fold':'F4','games':len(ids),'game_ids':ids,'worlds':1000,
                    'models':{'reference':REFERENCE,'bridge':BRIDGE,'candidate':CANDIDATE}[arm],'config':'models/v1.2d.json' if arm=='reference' else 'models/a1_s02_f4_causal_guarded.json',
                    'rotation':'targets','pool':0,'known_starters':False,'simulation_stream':None,'seed_key':'v1.2d_F4',
                    'kind':'conditional actual-participant research; no availability claim'},pretty=True)
    receipts=[{'game':gid,'arm':arm,'entry':done[(gid,arm)]['entry'],'reused':reused.get((gid,arm))} for gid in ids for arm in ARMS]
    write_json(output,{'kind':'fixed C2 three-arm wiring' if phase=='wiring' else 'single C2 three-arm development screen',
                       'manifest_sha256':sha256_file(MANIFEST),'game_ids':ids,'worlds':1000,'arms':3,'receipts':receipts,
                       'reference_raw_parity':raw_parity,'reference_reuse_enabled':can_reuse,'elapsed_seconds':time.monotonic()-started,
                       'fresh_arm_jobs':len(pending),'workers':min(jobs,len(pending)),'production_changed':False},pretty=True)
    print(f'{phase}: {len(ids)} games,3 arms complete; no promotion',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['freeze','wiring','development']);parser.add_argument('--jobs',type=int,default=10);args=parser.parse_args()
    if not 1<=args.jobs<=10 or any(os.environ.get(n)!='1' for n in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS']):raise ValueError('1-10 workers, one OMP/BLAS thread each')
    pa.set_cpu_count(1)
    if args.action=='freeze':freeze()
    else:run(args.action,args.jobs)
