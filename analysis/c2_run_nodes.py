#!/usr/bin/env python3
"""Resume the finite C2 node queue without overwriting completed artifacts."""
import os
from pathlib import Path
import subprocess
import sys
import time
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from basketball_common import write_json, read_json, sha256_file


def main():
    if os.environ.get('OPENBLAS_NUM_THREADS') != '1' or os.environ.get('OMP_NUM_THREADS') != '10':
        raise ValueError('set OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=10')
    plan = ROOT / 'analysis/experiments/20261124_c2_frozen_recipe_v2.json'
    guard = read_json(ROOT / 'analysis/experiments/20261124_c2_execution_guard_v1.json')
    audit = read_json(ROOT / 'analysis/experiments/20261124_c2_profiles_audit_v2.json')
    inputs = {**audit['input_sha256'], **guard['input_guard']}
    tasks = [(f,n,v) for f in ['F1','F2','F3'] for n in ['shot_result','what','location']
             for v in ['control','zone','distance','defence']]
    start = time.monotonic()
    for i, (fold,node,variant) in enumerate(tasks, 1):
        for name,digest in inputs.items():
            if sha256_file(ROOT / name) != digest:
                raise ValueError(f'frozen C2 input changed: {name}')
        folder = ROOT / f'data/derived/experiments/c2_court_v2/{fold}_{node}_{variant}_s7'
        receipt = folder / 'receipt.json'
        if receipt.exists():
            row = read_json(receipt)
            if row['recipe_sha256'] != sha256_file(plan):
                raise ValueError('completed fit has another recipe')
            for name,key in [('model.txt','model_sha256'),('validation.npz','validation_sha256')]:
                if sha256_file(folder/name) != row[key]:
                    raise ValueError('completed fit or predictions changed')
        else:
            print(f'START {i}/36 {fold} {node} {variant}', flush=True)
            subprocess.run([sys.executable,'-u','analysis/c2_node_screen.py','--fold',fold,
                            '--node',node,'--variant',variant], cwd=ROOT, check=True)
        print(f'COMPLETED {i}/36; elapsed {time.monotonic()-start:.2f}s', flush=True)
    output = ROOT / 'analysis/experiments/20261124_c2_node_execution_v2.json'
    if not output.exists():
        write_json(output, {'completed':len(tasks),'elapsed_seconds':time.monotonic()-start,
                           'recipe_sha256':sha256_file(plan),'threads':10,'blas_threads':1}, pretty=True)
    elif read_json(output)['recipe_sha256'] != sha256_file(plan):
        raise ValueError('execution receipt belongs to another recipe')


if __name__ == '__main__':
    main()
