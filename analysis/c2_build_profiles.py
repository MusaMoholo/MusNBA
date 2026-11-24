#!/usr/bin/env python3
"""Build isolated C2 causal profiles in a fresh namespace; never overwrite inputs."""
import argparse
import os
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pyarrow as pa
import pandas as pd
import numpy as np
from basketball_common import write_json,sha256_file,NBA_TEAM_IDS
from scripts import nodes,court_profiles


def main():
    if os.environ.get('OPENBLAS_NUM_THREADS')!='1' or os.environ.get('OMP_NUM_THREADS')!='1':
        raise ValueError('use one OMP/BLAS thread for profile preparation')
    pa.set_cpu_count(1)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('data/derived/experiments/c2_profiles_v2'))
    parser.add_argument('--report',type=Path,default=Path('analysis/experiments/20261124_c2_profiles_audit_v2.json'))
    args=parser.parse_args();work=args.output
    if work.exists() or args.report.exists():raise FileExistsError('fresh profile/report namespace required')
    work.mkdir(parents=True)
    paths=nodes.segment_files();parts=[];hashes={}
    cols=['game_id','date_et','season','actor','end_type','value','x','y','heave','made','game_ok','offense','defense']+[f'{side}_{i}' for side in ['off','def'] for i in range(1,6)]
    for p in paths:
     d=pd.read_parquet(p,columns=cols);d['source_row']=np.arange(len(d));d['source_file']=str(p);parts.append(d);hashes[str(p.relative_to(Path.cwd()))]=sha256_file(p)
    s=pd.concat(parts,ignore_index=True);s=s[s.offense.astype(str).isin(NBA_TEAM_IDS)&s.defense.astype(str).isin(NBA_TEAM_IDS)]
    pre=Path('data/derived/variants/a1_scheduled_F4_20261122_v3/features/pregame.parquet')
    r=pd.read_parquet(pre,columns=['game_id','date_et','season','player']);hashes[str(pre)]=sha256_file(pre)
    # Restrict profile updates to the existing dated roster universe; no node rows change.
    excluded_games=sorted(set(s.game_id)-set(r.game_id))
    excluded_rows=int((~s.game_id.isin(r.game_id)).sum())
    s=s[s.game_id.isin(r.game_id)]
    start=time.monotonic()
    f,a=court_profiles.build(s,r,lambda n,total:print(f'days {n}/{total}; seconds {time.monotonic()-start:.1f}',flush=True))
    f.to_parquet(work/'pregame.parquet',index=False)
    a.update({'source_roster_excluded_games':excluded_games,'source_roster_excluded_segments':excluded_rows,'elapsed_seconds':time.monotonic()-start,'input_sha256':hashes,'output_sha256':sha256_file(work/'pregame.parquet'),'source_identity':'input file SHA256 plus original parquet row index; no parser or eligibility change to node control','profile_code_sha256':sha256_file('scripts/court_profiles.py'),'recipe_sha256':sha256_file('analysis/experiments/20261124_c2_frozen_recipe_v2.json')})
    write_json(args.report,a,pretty=True)
    print(a,flush=True)


if __name__=='__main__':
    main()
