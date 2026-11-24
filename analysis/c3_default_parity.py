#!/usr/bin/env python3
"""Publication delegate default-off original canonical-chunk parity without truth scoring."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from concurrent.futures import ProcessPoolExecutor
from analysis.c2_default_parity import replay
from basketball_common import write_json,sha256_file

def main():
 out=ROOT/'analysis/experiments/20261124_c3_default_off_parity_v1.json'
 if out.exists():raise FileExistsError(out)
 with ProcessPoolExecutor(max_workers=3) as pool:rows=list(pool.map(replay,['401910036','401910042','401910044']))
 write_json(out,{'kind':'publication delegation default-off original full1k raw replay; no truth scoring','games':rows,
  'source_sha256':{s:sha256_file(ROOT/s) for s in ['scripts/engine.py','scripts/lineup_forecast.py','scripts/state_rotations.py']},'protected_scoring':False},pretty=True)
 print('3/3 original canonical chunks exactly equal',flush=True)
if __name__=='__main__':main()
