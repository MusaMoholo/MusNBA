#!/usr/bin/env python3
"""Preserve dependencies, then time a fresh accepted-engine B1 checkpoint nightly."""
from pathlib import Path
import argparse
import os
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from basketball_common import archive_paths,read_json,write_json,sha256_file,today_et
from analysis.c5_nightly_release import sources,now


def archive(prefix):
    output=ROOT/f'analysis/experiments/{prefix}_archive_v1.json'
    if output.exists():raise FileExistsError(output)
    previous=read_json(ROOT/'analysis/experiments/20261124_u25_archive_v3.json')
    manifest=read_json(ROOT/'analysis/experiments/20261124_b1_runtime_v2.json')
    paths={Path(p) for p in previous['paths']}
    paths.update(ROOT/p for p in manifest['source_sha256'])
    paths.update([ROOT/f'data/snapshots/{today_et()}',ROOT/'data/views',ROOT/'exports',
                  ROOT/'data/derived/features',ROOT/'data/derived/features_variants',
                  ROOT/'data/derived/rotations',ROOT/'data/derived/nbastats'])
    cloud=Path.home()/'Library/Mobile Documents/com~apple~CloudDocs/MusNBA'
    paths.update(cloud/name for name in ['MusNBA.musnba.gz','MusNBA-laptop.musnba.gz'])
    # Avoid duplicate copies below already preserved directories.
    paths=sorted({p.resolve() for p in paths if p.exists()})
    paths=[p for p in paths if not any(q!=p and q in p.parents for q in paths)]
    inventory={str(f):sha256_file(f) for p in paths for f in (p.rglob('*') if p.is_dir() else [p]) if f.is_file()}
    destination=archive_paths(paths)
    write_json(output,{'kind':'Verified B1 checkpoint preservation before any replacement',
        'archive':str(destination),'paths':[str(p) for p in paths],
        'files':len(inventory),'inventory_sha256':inventory,
        'frozen_runtime_sha256':sha256_file(ROOT/'analysis/experiments/20261124_b1_runtime_v2.json'),
        'earlier_incomplete_archive': '/Users/moholom/Basketball_archive_ops/archive_20261124T152430Z_34003',
        'repair': 'Resolve symlink aliases before parent pruning; earlier copy stopped at duplicate shell destination before any replacement/nightly.'},pretty=True)
    print(f'Preserved and byte-verified{len(inventory)} files at{destination}',flush=True)


def nightly(prefix):
    start=ROOT/f'analysis/experiments/{prefix}_nightly_start_v1.json'
    finish=ROOT/f'analysis/experiments/{prefix}_nightly_result_v1.json'
    if start.exists() or finish.exists():raise FileExistsError('fresh immutable nightly receipt required')
    archive_path=ROOT/f'analysis/experiments/{prefix}_archive_v1.json'
    read_json(archive_path)
    development=read_json(ROOT/'analysis/experiments/20261124_b1_development_decision_v2.json')
    if development['qualified']:
        read_json(ROOT/'analysis/experiments/20261124_b1_confirmation_decision_v2.json')
    before=sources()
    command=[sys.executable,'-u','scripts/nightly_musnba.py','--engine','10000','--sims','10000']
    env={**os.environ,**{k:'1' for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','VECLIB_MAXIMUM_THREADS',
                                       'MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','ARROW_NUM_THREADS']}}
    write_json(start,{'kind':'B1 fresh full online accepted-engine nightly; research does not activate',
        'started':now(),'command':command,'offline':False,'required_rebuild':True,'max_heavy_threads':10,
        'source_sha256':before,'archive_sha256':sha256_file(archive_path),'protected_scoring':False},pretty=True)
    began=time.monotonic();code=subprocess.run(command,cwd=ROOT,env=env).returncode;elapsed=time.monotonic()-began
    after=sources()
    result={'kind':'B1 checkpoint full online nightly measured result','ended':now(),'exit_code':code,
        'seconds':elapsed,'limit_seconds':3600,'within_limit':elapsed<=3600,'source_exact':before==after,
        'changed_sources':[k for k in set(before)|set(after) if before.get(k)!=after.get(k)],
        'start_sha256':sha256_file(start)}
    write_json(finish,result,pretty=True);print(result,flush=True)
    if code or before!=after or elapsed>3600:raise SystemExit(1)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['archive','nightly'])
    parser.add_argument('--prefix',default='20261124_b1')
    args=parser.parse_args()
    if not args.prefix.replace('_','').isalnum():raise ValueError('simple immutable prefix required')
    {'archive':archive,'nightly':nightly}[args.action](args.prefix)
