#!/usr/bin/env python3
"""Fixed seed-noise diagnostics, then three F4 fits for the single C2 nominee."""
import os
from pathlib import Path
import sys,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pyarrow as pa
from basketball_common import read_json,sha256_file,write_json
from analysis import c2_node_screen as screen,c2_prepare_engine


def main():
    if os.environ.get('OMP_NUM_THREADS')!='10' or os.environ.get('OPENBLAS_NUM_THREADS')!='1':raise ValueError('10 OMP/1 BLAS required')
    pa.set_cpu_count(1)
    grade=ROOT/'analysis/experiments/20261124_c2_node_screen_v2.json'
    selected=read_json(grade)['provisional_survivor_for_seed_noise']
    guard=read_json(ROOT/'analysis/experiments/20261124_c2_execution_guard_v1.json')
    seed=guard['secondary_seed'];start=time.monotonic()
    tasks=[(f,n,v) for f in ['F1','F2','F3'] for n in ['shot_result','what'] for v in ['control',selected]]
    for i,(fold,node,variant) in enumerate(tasks,1):
        for name,digest in guard['input_guard'].items():
            if sha256_file(ROOT/name)!=digest:raise ValueError('frozen fitter/profile source changed')
        folder=screen.WORK/f'{fold}_{node}_{variant}_s{seed}';receipt=folder/'receipt.json'
        if receipt.exists():
            r=read_json(receipt)
            if r['recipe_sha256']!=sha256_file(screen.PLAN):raise ValueError('noise recipe differs')
            for file,key in [('model.txt','model_sha256'),('validation.npz','validation_sha256')]:
                if sha256_file(folder/file)!=r[key]:raise ValueError('noise artifact changed')
        else:screen.run(fold,node,variant,seed)
        print(f'NOISE {i}/12 complete; elapsed {time.monotonic()-start:.2f}s',flush=True)
    output=ROOT/'analysis/experiments/20261124_c2_nominee_fit_execution_v1.json'
    if not output.exists():
        write_json(output,{'nominee':selected,'seed':seed,'fits':12,'seconds':time.monotonic()-start,
                           'grade_sha256':sha256_file(grade),'threads':10,'blas_threads':1},pretty=True)
    c2_prepare_engine.main()

if __name__=='__main__':main()
