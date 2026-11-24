#!/usr/bin/env python3
"""Select five genuine positive-mass examples from retained complete source games."""
from pathlib import Path
import sys,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from basketball_common import read_json,write_json,sha256_file
from scripts.visible_worlds import select

def main():
 output=ROOT/'analysis/experiments/20261124_c4_example_selection_v1.json'
 directory=ROOT/'data/derived/experiments/c4_visible_selection_v1'
 if output.exists() or directory.exists():raise FileExistsError('immutable selection namespace exists')
 directory.mkdir();start=time.monotonic();rows=[]
 for folder in sorted((ROOT/'data/snapshots/2026-11-23/lineups').iterdir()):
  if not (folder/'work-plan.json').exists():continue
  record=select(folder);path=directory/(folder.name+'.json');write_json(path,record,pretty=True)
  chunks={(e['branch_id'],e['chunk_start'],e['chunk_stop']) for e in record['examples']}
  rows.append({'game':folder.name,'examples':len(record['examples']),'unique_worlds':len({(e['branch_id'],e['world_index']) for e in record['examples']}),'original_chunks':len(chunks),'private_selection':str(path.relative_to(ROOT)),'sha256':sha256_file(path)})
  print(folder.name,'five real examples;',len(chunks),'unique full chunks',flush=True)
 write_json(output,{'kind':'five fixed source-identified real worlds per game; no capture or delivery acceptance yet',
  'design_sha256':sha256_file(ROOT/'analysis/experiments/20261124_c4_capture_design_v1.json'),
  'selector_sha256':sha256_file(ROOT/'scripts/visible_worlds.py'),'games':rows,'seconds':time.monotonic()-start,'source_mutated':False},pretty=True)
if __name__=='__main__':main()
