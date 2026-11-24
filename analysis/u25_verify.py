"""Record real smoke/fault exit codes for a completed PWA release without altering data."""
import os,sys,time,subprocess,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from basketball_common import write_json,sha256_file
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--prefix',default='20261124_u25');args=parser.parse_args()
    if not args.prefix.replace('_','').isalnum():raise ValueError('simple immutable prefix required')
    out=ROOT/f'analysis/experiments/{args.prefix}_smoke_fault_v1.json';assert not out.exists()
    rows=[];env={**os.environ,**{k:'1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','VECLIB_MAXIMUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','ARROW_NUM_THREADS')}}
    for name,flags,expected in [('smoke',[],0),('fault',['--fault'],1)]:
        path=Path('/tmp')/f'musnba_{args.prefix}_{name}_v1.log';assert not path.exists();t=time.monotonic()
        with path.open('w') as stream:code=subprocess.run([sys.executable,'-u','scripts/smoke.py',*flags],cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT).returncode
        row={'name':name,'exit_code':code,'expected_exit_code':expected,'seconds':time.monotonic()-t,'summary':path.read_text().strip().splitlines()[-1],'log':str(path),'sha256':sha256_file(path)};rows.append(row);print(row,flush=True)
        if code!=expected:break
    ok=len(rows)==2 and all(r['exit_code']==r['expected_exit_code'] for r in rows)
    write_json(out,{'kind':'Real smoke and deliberate in-memory fault exit evidence','checks':rows,'status':'pass' if ok else 'fail'},pretty=True);raise SystemExit(0 if ok else 1)
