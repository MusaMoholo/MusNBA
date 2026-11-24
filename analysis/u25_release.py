"""Freeze and time a fresh full accepted-engine nightly for the PWA polish release."""
import os,sys,time,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from basketball_common import write_json,sha256_file,read_json
from analysis.c5_nightly_release import sources,now
if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--version',choices=['v1','v2','v3'],default='v1');version=parser.parse_args().version
    out=ROOT/'analysis/experiments';start=out/f'20261124_u25_nightly_start_{version}.json';finish=out/f'20261124_u25_nightly_result_{version}.json'
    assert not start.exists() and not finish.exists()
    assert (out/f'20261124_u25_archive_{version}.json').exists()
    assert read_json(out/'20261124_c4_qualifier_v1.json')['learned_qualifier'] is None
    command=[sys.executable,'-u','scripts/nightly_musnba.py','--engine','10000','--sims','10000'];before=sources()
    env={**os.environ,**{k:'1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','VECLIB_MAXIMUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','ARROW_NUM_THREADS')}}
    write_json(start,{'kind':'U25 fresh full online nightly; accepted engines unchanged','started':now(),'command':command,'source_sha256':before,'offline':False,'required_rebuild':True,'protected_scoring':False,'max_heavy_threads':10,'archive':f'20261124_u25_archive_{version}.json'},pretty=True)
    t=time.monotonic();code=subprocess.run(command,cwd=ROOT,env=env).returncode;elapsed=time.monotonic()-t;after=sources()
    result={'kind':'U25 full nightly measured result','ended':now(),'exit_code':code,'seconds':elapsed,'limit_seconds':3600,'within_limit':elapsed<=3600,'source_exact':before==after,'changed_sources':[k for k in set(before)|set(after) if before.get(k)!=after.get(k)],'start_sha256':sha256_file(start)}
    write_json(finish,result,pretty=True);print(result,flush=True);raise SystemExit(0 if code==0 and before==after and elapsed<=3600 else 1)
