#!/usr/bin/env python3
"""Single C01 operation entry point; each command declares its actual scope."""
from __future__ import annotations

import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="command",required=True)
    sub.add_parser("source",help="Read-only pinned source/integration check, no accuracy job")
    r=sub.add_parser("reproduce",help="Fresh fits/samples/event/oracle scores and aggregate conclusions from pinned inputs")
    r.add_argument("--output",type=Path,help="New private/scratch namespace; default is a new timestamped ignored data directory")
    r.add_argument("--jobs",type=int,default=10,choices=range(1,11))
    c=sub.add_parser("ledger-capture",help="Capture only a genuinely pre-tip forecast with complete supplied timing evidence")
    c.add_argument("--request",type=Path,required=True)
    c.add_argument("--ledger",type=Path,default=ROOT/"data/derived/forecast_ledger/c01_v1")
    a=sub.add_parser("ledger-audit",help="Read-only hash/timing audit; no reconstruction or historical backfill")
    a.add_argument("--ledger",type=Path,default=ROOT/"data/derived/forecast_ledger/c01_v1")
    args=parser.parse_args()
    if args.command in ("source","reproduce"):
        if any(os.environ.get(k)!="1" for k in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","VECLIB_MAXIMUM_THREADS")):
            parser.error("set OMP_NUM_THREADS, OPENBLAS_NUM_THREADS, MKL_NUM_THREADS and VECLIB_MAXIMUM_THREADS to1")
        from analysis import c01_reproduce
        if args.command=="source":result=c01_reproduce.check_sources()
        else:
            output=args.output or ROOT/"data/derived/experiments"/f"c01_reproduce_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}"
            result=c01_reproduce.reproduce(output,args.jobs)
            result={**result,"private_output":str(output)}
    else:
        from analysis import c01_ledger
        if args.command=="ledger-audit":result=c01_ledger.audit(args.ledger)
        else:result=c01_ledger.capture(args.ledger,json.loads(args.request.read_text()))
    print(json.dumps(result,indent=2,allow_nan=False))


if __name__=="__main__":main()
