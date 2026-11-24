#!/usr/bin/env python3
"""Verify prospectively frozen indirect C4 dependencies before opening outcomes."""
import argparse,hashlib,json,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();out=ROOT/a.output
 if out.exists():raise FileExistsError(out)
 reports=['analysis/experiments/20261124_c2_engine_runtime_v2.json','analysis/experiments/20261124_c3_engine_runtime_v3.json','analysis/experiments/20261124_c4_s06_runtime_v1.json']
 checked={};manifests={}
 for rel in reports:
  path=ROOT/rel;manifests[rel]=sha(path)
  for source,digest in json.loads(path.read_text())['source_sha256'].items():
   if rel==reports[0] and not (source.startswith('data/') or source.startswith('models/')):continue
   if source in checked and checked[source]!=digest:raise ValueError('inconsistent frozen binding:'+source)
   if sha(ROOT/source)!=digest:raise ValueError('input/source changed:'+source)
   checked[source]=digest
 record={'kind':'C4 indirect input dependency closure; no outcomes opened by this audit','verified_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'manifests':manifests,'source_sha256':checked,'verified_files':len(checked),'result':'all exact','limits':'C4 direct manifest binds C3; C2 manifest freezes indirect control/history/athlete/model inputs. This closes traceability only; recipes, panels, sources and criteria unchanged.'}
 out.write_text(json.dumps(record,indent=2)+'\n');print('All',len(checked),'frozen sources/inputs exact')
if __name__=='__main__':main()
