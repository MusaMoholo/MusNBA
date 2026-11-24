#!/usr/bin/env python3
"""Audit every displayed rate/case independently of the view producer; no simulation."""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import sys,os
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from basketball_common import read_json,write_json,sha256_file
from analysis.a1_delivery_audit import audit_view_rates

def task(gid):return audit_view_rates(ROOT/f'data/snapshots/2026-11-23/lineups/{gid}',ROOT/'data/views')
def main():
 out=ROOT/'analysis/experiments/20261124_c4_rate_audit_v1.json'
 if out.exists():raise FileExistsError(out)
 report=read_json(ROOT/'analysis/experiments/20261124_c4_retained_capture_v1.json');ids=[r['game'] for r in report['games']]
 paths=[ROOT/f'data/views/api/game/{gid}.json' for gid in ids]+[ROOT/f'data/views/api/game/{gid}/worlds.json' for gid in ids]
 before={str(p.relative_to(ROOT)):sha256_file(p) for p in paths}
 with ProcessPoolExecutor(max_workers=9) as pool:rows=list(pool.map(task,ids))
 if before!={str(p.relative_to(ROOT)):sha256_file(p) for p in paths}:raise ValueError('view sources changed during audit')
 write_json(out,{'kind':'all full-game player/team advanced rates, exact supports, weighted means/quantiles/histograms and all lineup cases','games':rows,'rate_distributions_checked':sum(r['rate_distributions_checked'] for r in rows),'view_sha256':before,'auditor_sha256':sha256_file(ROOT/'analysis/a1_delivery_audit.py'),'workers':9,'omp_threads':1,'blas_threads':1,'accuracy_scored':False,'status':'pass'},pretty=True);print('Passed',sum(r['rate_distributions_checked'] for r in rows),'rate distributions across10games/allcases',flush=True)
if __name__=='__main__':
 if any(os.environ.get(k)!='1' for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS']):raise ValueError('one inner thread required')
 main()
