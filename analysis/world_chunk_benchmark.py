#!/usr/bin/env python3
"""Measure complete 10k games split over workers; independent-fit candidate, never a forecast."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import os
from pathlib import Path
import pickle
import resource
import signal
import subprocess
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from basketball_common import SNAPSHOTS, read_json, sha256_file, write_json
from analysis.a1_parallel_world_probe import capture_digest
from scripts import a1_lineup_branches, engine, lineup_forecast, live_forecast, projection, rotation_fit

ENG = None


def initialise():
    global ENG
    runtime = {**engine.ENGINE, 'id':'engine-v1.3-r2-candidate','rotation_fit':'independent-v1'}
    ENG = engine.Engine(runtime['models'],runtime=runtime)
    engine.Game._fit_offsets = staticmethod(lambda curves, targets: rotation_fit.independent(curves,targets,engine.ROTATION))


def one(task):
    path, gid, start, stop, seed, destination = task
    with Path(path).open('rb') as stream:
        saved = pickle.load(stream)
    ENG.m.median = saved['median']
    began = time.monotonic()
    before = resource.getrusage(resource.RUSAGE_SELF)
    result = lineup_forecast.simulate(ENG,saved['game'],stop-start,seed)
    raw = result['raw']
    target = Path(destination) / f'{gid}-{start:05d}-{stop:05d}.npz'
    np.savez_compressed(target,**raw)
    after = resource.getrusage(resource.RUSAGE_SELF)
    return {'game':gid,'start':start,'stop':stop,'seed':str(seed),'world_sha256':capture_digest(raw),
            'capture':str(target.relative_to(ROOT)),'sha256':sha256_file(target),
            'seconds':time.monotonic()-began,'cpu_seconds':after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,
            'worker':os.getpid(),'worker_peak_rss_bytes':int(after.ru_maxrss)*(1 if sys.platform=='darwin' else 1024)}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--game',action='append',required=True)
    p.add_argument('--jobs',type=int,required=True)
    p.add_argument('--chunk-worlds',type=int,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--queue',action='store_true',help='exercise the complete live chunk/merge/game queue, including branches')
    p.add_argument('--worlds',type=int,default=10000)
    p.add_argument('--max-seconds',type=float,help='stop a latency-only prototype attempt after this deadline; never a qualification run')
    a=p.parse_args()
    if not 1<=a.jobs<=10 or a.chunk_worlds not in (500,1000,2000,2500,5000,10000) or len(set(a.game))!=len(a.game):
        raise ValueError('1–10 workers, supported exact partitions and unique games required')
    if any(os.environ.get(k)!='1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS')):
        raise ValueError('set OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1')
    if a.max_seconds is not None:
        return capped(a)
    if a.queue:
        return queue_benchmark(a)
    if a.worlds != 10000:
        raise ValueError('prototype benchmark retains its fixed 10k population')
    folder=ROOT/'data/derived/experiments'/a.output.stem
    if a.output.exists() or folder.exists():raise FileExistsError('fresh benchmark namespace required')
    folder.mkdir()
    sources={**live_forecast.fingerprints(),str(Path(__file__).relative_to(ROOT)):sha256_file(Path(__file__)),
             'scripts/rotation_fit.py':sha256_file(ROOT/'scripts/rotation_fit.py')}
    tasks=[]
    for gid in a.game:
        parent=SNAPSHOTS/'2026-11-23/lineups'/gid
        game=read_json(parent/'game.json')
        if game.get('lineups'):raise ValueError('benchmark selects ordinary games; no silent lineup conditioning')
        path=parent/'inputs.pkl';sources[str(path.relative_to(ROOT))]=sha256_file(path)
        base=projection.seed_for('world-chunks-v1','2026-11-23',gid,'unconditional')
        for start in range(0,10000,a.chunk_worlds):
            stop=min(10000,start+a.chunk_worlds)
            tasks.append((str(path),gid,start,stop,projection.seed_for('chunk-v1',base,start,stop),str(folder)))
    write_json(folder/'plan.json',{'tasks':[[t[1],t[2],t[3],str(t[4])] for t in tasks],'sources':sources,'workers':a.jobs},pretty=True)
    began=time.monotonic();rows=[];worlds=0
    with ProcessPoolExecutor(max_workers=a.jobs,initializer=initialise) as pool:
        for future in as_completed([pool.submit(one,t) for t in tasks]):
            row=future.result();rows.append(row);worlds+=row['stop']-row['start']
            print(f'{worlds}/{10000*len(a.game)} worlds complete in {time.monotonic()-began:.1f}s',flush=True)
    elapsed=time.monotonic()-began
    if any(sha256_file(ROOT/name)!=digest for name,digest in sources.items()):raise ValueError('benchmark inputs/source changed')
    merged={}
    for gid in a.game:
        group=sorted((r for r in rows if r['game']==gid),key=lambda r:r['start'])
        assert [r['start'] for r in group]==list(range(0,10000,a.chunk_worlds))
        parts=[]
        for row in group:
            with np.load(ROOT/row['capture'],allow_pickle=False) as z:parts.append({'raw':{k:z[k] for k in z.files}})
        raw=lineup_forecast.merge(parts)
        assert len(raw['minutes'])==10000
        merged[gid]=capture_digest(raw)
    write_json(a.output,{'kind':'D56 independent-fit chunk performance only; unpromoted candidate','games':a.game,'worlds_per_game':10000,
             'workers':a.jobs,'chunk_worlds':a.chunk_worlds,'seconds':elapsed,'worlds_per_second':worlds/elapsed,
             'sum_task_cpu_seconds':sum(r['cpu_seconds'] for r in rows),'merged_world_sha256':merged,
             'sources':sources,'chunks':sorted(rows,key=lambda r:(r['game'],r['start']))},pretty=True)
    print(f'{worlds} complete worlds in {elapsed:.3f}s; {a.jobs} workers / {a.chunk_worlds}-world chunks',flush=True)


def queue_benchmark(args):
    from analysis.a1_delivery_audit import audit
    folder=ROOT/'data/derived/experiments'/args.output.stem
    if args.output.exists() or folder.exists():raise FileExistsError('fresh queue benchmark namespace required')
    folder.mkdir()
    sources={**live_forecast.fingerprints(),str(Path(__file__).relative_to(ROOT)):sha256_file(Path(__file__))}
    tasks=[];median=None
    runtime={**engine.ENGINE,'id':'engine-v1.3-r2-candidate','rotation_fit':'independent-v1'}
    for gid in args.game:
        parent=SNAPSHOTS/'2026-11-23/lineups'/gid
        path=parent/'inputs.pkl';sources[str(path.relative_to(ROOT))]=sha256_file(path)
        with path.open('rb') as stream:saved=pickle.load(stream)
        if median is not None and median != saved['median']:
            raise ValueError('probe inputs have different median recipes')
        median=saved['median']
        selected=([a1_lineup_branches.SelectedPlayer(**p) for p in read_json(parent/'worlds.json')['selected_players']]
                  if (parent/'worlds.json').exists() else [])
        tasks.append((saved['game'],selected,args.worlds,str(folder/gid),{'kind':'D56 queue probe'}))
    write_json(folder/'plan.json',{'sources':sources,'games':args.game,'worlds':args.worlds,
                                 'chunk_worlds':args.chunk_worlds,'workers':args.jobs},pretty=True)
    began=time.monotonic()
    completed=list(live_forecast.run(tasks,runtime,median,workers=args.jobs,chunk_worlds=args.chunk_worlds))
    elapsed=time.monotonic()-began
    rows=[]
    for path in sorted(completed):
        parent=Path(path);plan=read_json(parent/'work-plan.json');digests=[]
        for batch in plan['batches']:
            with np.load(batch['capture'],allow_pickle=False) as z:
                digests.append(capture_digest({k:z[k] for k in z.files}))
        rows.append({'game':parent.name,'raw_sha256':digests,'audit':audit(parent)})
    if any(sha256_file(ROOT/name)!=digest for name,digest in sources.items()):raise ValueError('queue probe sources changed')
    write_json(args.output,{'kind':'D56 complete live queue; unpromoted independent-fit candidate','sources':sources,
               'workers':args.jobs,'worlds_per_branch':args.worlds,'chunk_worlds':args.chunk_worlds,
               'seconds':elapsed,'games':rows},pretty=True)
    print(f'{len(rows)} complete checked games in {elapsed:.3f}s',flush=True)


def capped(args):
    if args.queue or len(args.game)!=1 or args.worlds!=10000 or args.max_seconds<=0:
        raise ValueError('positive deadline requires a single-game 10k prototype latency attempt')
    folder=ROOT/'data/derived/experiments'/args.output.stem
    if args.output.exists() or folder.exists():raise FileExistsError('fresh capped benchmark namespace required')
    cmd=[sys.executable,str(Path(__file__)), '--jobs',str(args.jobs),'--chunk-worlds',str(args.chunk_worlds),
         '--game',args.game[0],'--output',str(args.output)]
    began=time.monotonic()
    process=subprocess.Popen(cmd,cwd=ROOT,start_new_session=True)
    try:
        status=process.wait(timeout=args.max_seconds)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid,signal.SIGTERM)  # only this explicitly isolated benchmark and its own workers
        process.wait()
        plan=read_json(folder/'plan.json')
        if any(sha256_file(ROOT/name)!=digest for name,digest in plan['sources'].items()):
            raise ValueError('censored benchmark sources changed')
        write_json(args.output,{'kind':'D56 latency-only benchmark; incomplete at the predeclared deadline',
             'game':args.game[0],'workers':args.jobs,'chunk_worlds':args.chunk_worlds,'target_worlds':10000,
             'complete':False,'latency_lower_bound_seconds':args.max_seconds,
             'attempt_seconds_including_shutdown':time.monotonic()-began,'plan':plan,
             'limitation':'No accuracy result or selected forecast. Partial attempt files retained; no promotion/accounting claim.'},pretty=True)
        print(f'10k incomplete at {args.max_seconds:.1f}s; latency lower bound only; benchmark workers stopped',flush=True)
    else:
        if status:raise SystemExit(status)
        print(f'complete within the {args.max_seconds:.1f}s benchmark deadline',flush=True)


if __name__=='__main__':main()
