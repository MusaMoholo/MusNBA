#!/usr/bin/env python3
"""Three original canonical-chunk replays; no outcome evaluation or protected rescore."""
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import sys,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from basketball_common import read_json,write_json,sha256_file


def replay(gid):
    from scripts.smoke import replay_saved_chunk
    folder=ROOT/f'data/snapshots/2026-11-23/lineups/{gid}'
    start=time.monotonic()
    if not replay_saved_chunk(folder,'v1.3'):raise ValueError('default-off raw replay differs')
    plan=read_json(folder/'work-plan.json')
    return {'game':gid,'worlds':1000,'all_raw_arrays_identical':True,'seconds':time.monotonic()-start,
            'work_plan_sha256':sha256_file(folder/'work-plan.json'),'private_input_sha256':plan['provenance']['replay_input_sha256']}


def main():
    if any(os.environ.get(n)!='1' for n in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS']):raise ValueError('one OMP/BLAS thread per worker required')
    output=ROOT/'analysis/experiments/20261124_c2_default_off_parity_v1.json'
    if output.exists():raise FileExistsError(output)
    start=time.monotonic()
    with ProcessPoolExecutor(max_workers=3) as pool:rows=list(pool.map(replay,['401910036','401910042','401910044']))
    write_json(output,{'kind':'inactive optional court decoder; original full chunk replay, no truth scoring',
                       'engine_sha256':sha256_file(ROOT/'scripts/engine.py'),'games':rows,'workers':3,'omp_threads':1,
                       'elapsed_seconds':time.monotonic()-start,'protected_accuracy_evaluated':False},pretty=True)
    print('3/3 canonical1k chunks: all raw arrays exactly equal',flush=True)

if __name__=='__main__':main()
