"""Time the full authorised online C5 nightly, freezing production code through its finish."""
import os,sys,time,json,hashlib,subprocess
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from basketball_common import sha256_file,write_json

def now():return datetime.now(timezone.utc).isoformat()
def sources():
    paths=list((ROOT/'scripts').rglob('*.py'))+list((ROOT/'scripts/webapp').glob('*'))+list((ROOT/'models').glob('*.json'))+[ROOT/'basketball_common.py']
    return {str(p.relative_to(ROOT)):sha256_file(p) for p in sorted(paths) if p.is_file()}
if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--version',choices=['v2','v3','v4','v5'],required=True);version=parser.parse_args().version
    root=ROOT/'analysis/experiments';start_report=root/f'20261124_c5_nightly_start_{version}.json';final=root/f'20261124_c5_nightly_result_{version}.json'
    assert not start_report.exists() and not final.exists()
    qualifier=json.loads((root/'20261124_c4_qualifier_v1.json').read_text());assert qualifier['learned_qualifier'] is None
    before=sources();command=[sys.executable,'-u','scripts/nightly_musnba.py','--engine','10000','--sims','10000']
    env={**os.environ,**{k:'1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','VECLIB_MAXIMUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','ARROW_NUM_THREADS')}}
    write_json(start_report,{'kind':'Frozen C5 final full online nightly','started':now(),'command':command,'offline':False,'rebuild_required':True,'max_heavy_threads':10,'source_sha256':before,'qualifier_sha256':sha256_file(root/'20261124_c4_qualifier_v1.json'),'protected_scoring':False,'archive':f'20261124_c5_pre_nightly_archive_{version}.json'},pretty=True)
    start=time.monotonic();code=subprocess.run(command,cwd=ROOT,env=env).returncode;elapsed=time.monotonic()-start
    after=sources();same=before==after
    result={'kind':'C5 full online nightly measured result','ended':now(),'exit_code':code,'seconds':elapsed,'limit_seconds':3600,'within_limit':elapsed<=3600,'source_exact':same,'changed_sources':[k for k in set(before)|set(after) if before.get(k)!=after.get(k)],'start_report_sha256':sha256_file(start_report)}
    write_json(final,result,pretty=True);print(json.dumps(result),flush=True)
    raise SystemExit(0 if code==0 and same and elapsed<=3600 else 1)
