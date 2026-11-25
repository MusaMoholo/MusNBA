#!/usr/bin/env python3
"""Repeat one canonical 1k diagnostic replay in a fresh single-worker namespace."""
from __future__ import annotations
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import os
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import pyarrow as pa
from analysis import c01_diagnostics as diag,c01_benchmark as bench
from analysis.c01_core import ContractError
from analysis.c01_workbench import read,create_json
from basketball_common import sha256_file

OUTPUT=ROOT/'data/derived/experiments/c01_replay_worker_check_v1'


def init(path):
    diag.WORK=Path(path)
    diag.init_worker()


def run(output=OUTPUT):
    if any(os.environ.get(k)!='1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS')):raise ContractError('four inner thread caps must equal1')
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    plan=diag.pinned();gid=plan['wiring_ids'][0]
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    output.mkdir(parents=True,exist_ok=False)
    for name in ('plan.json','conversion.json'):shutil.copy2(diag.WORK/name,output/name)
    with ProcessPoolExecutor(max_workers=1,initializer=init,initargs=(str(output),)) as pool:
        result=pool.submit(diag.replay_job,gid).result()
    old=diag.WORK/'games'/gid;new=output/'games'/gid
    with np.load(old/'replay.npz',allow_pickle=False) as z:a={k:z[k] for k in z.files}
    with np.load(new/'replay.npz',allow_pickle=False) as z:b={k:z[k] for k in z.files}
    if set(a)!=set(b) or any(not np.array_equal(a[k],b[k]) for k in a):raise ContractError('single-worker replay arrays differ from10-worker run')
    pd.testing.assert_frame_equal(pd.read_parquet(old/'oracles.parquet'),pd.read_parquet(new/'oracles.parquet'),check_exact=True)
    receipt={'kind':'Independent worker/resume replay verification','game_id':gid,'worlds':1000,'ten_vs_one_worker_arrays_identical':True,
        'oracle_scores_identical':True,'all_generation_boundaries_passed':True,'source_signature':sha256_file(diag.WORK/'plan.json'),
        'original_receipt_sha256':sha256_file(old/'receipt.json'),'repeat_receipt_sha256':sha256_file(new/'receipt.json'),
        'repeat_array_digest':bench.arrays_digest(b),'seconds':result['seconds'],'production_changed':False}
    create_json(output/'comparison.json',receipt);print(receipt,flush=True)
    return receipt


if __name__=='__main__':run()
