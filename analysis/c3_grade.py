#!/usr/bin/env python3
"""Frozen MIN-primary learned/v3 decision for the single S06 current-r3 screen."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from basketball_common import read_json,write_json,sha256_file
from scripts import a1_compare,release_gate

def main():
 phase=ROOT/'analysis/experiments/20261124_c3_engine_development_v3.json';r=read_json(phase)
 out=ROOT/'analysis/experiments/20261124_c3_decision_v1.json'
 if out.exists():raise FileExistsError(out)
 if len(r['game_ids'])!=200 or len(r['receipts'])!=400:raise ValueError('complete paired200 required')
 for path,digest in r['derived_outputs'].items():
  if sha256_file(ROOT/path)!=digest:raise ValueError('grade source changed')
 report=a1_compare.compare('c3_engine_development_v3_reference','c3_engine_development_v3_candidate')
 gate=release_gate.assess(report,'learned','players/all/min/crps',policy='v3')
 path=ROOT/'analysis/experiments/20261124_c3_compare_v1.json';gp=ROOT/'analysis/experiments/20261124_c3_gate_v1.json'
 if path.exists() or gp.exists():raise FileExistsError('partial grade requires inspection')
 write_json(path,report,pretty=True);write_json(gp,gate,pretty=True)
 totals={};audits={};maximum=0.
 for ref in r['receipts']:
  p=ROOT/ref['receipt']
  if sha256_file(p)!=ref['sha256']:raise ValueError('private receipt changed')
  row=read_json(p)
  if ref['arm']=='candidate':
   for key,value in row['entry']['counts'].items():totals[key]=totals.get(key,0)+value
  for key,value in row['audit'].items():
   if isinstance(value,(int,float)):
    if key.startswith('max_'):audits[key]=max(audits.get(key,0),value)
    else:audits[key]=audits.get(key,0)+value
 write_json(out,{'kind':'single S06 current-r3 development decision; no promotion',
  'phase_sha256':sha256_file(phase),'comparison_sha256':sha256_file(path),'gate_sha256':sha256_file(gp),
  'primary':gate['primary'],'decision':gate['decision'],'compatible':gate['statistical_compatibility'],
  'next':'freeze unchanged for C4 independent confirmation' if gate['decision']=='development_scores_compatible' else 'retain r3; no replacement or retune',
  'candidate_policy_counts':totals,'independent_accounting':audits,'protected_evaluation':False,'production_model_changed':False},pretty=True)
 print(gate['decision'],gate['primary'],flush=True)
if __name__=='__main__':main()
