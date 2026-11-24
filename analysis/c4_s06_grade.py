#!/usr/bin/env python3
"""Apply the prospectively frozen independent MIN-primary learned/v3 screen."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from basketball_common import read_json,write_json,sha256_file
from scripts import a1_compare,release_gate

def main():
 phase=ROOT/'analysis/experiments/20261124_c4_s06_confirmation_v1.json'
 out=ROOT/'analysis/experiments/20261124_c4_s06_independent_decision_v1.json'
 cp=ROOT/'analysis/experiments/20261124_c4_s06_independent_compare_v1.json';gp=ROOT/'analysis/experiments/20261124_c4_s06_independent_gate_v1.json'
 if any(p.exists() for p in [out,cp,gp]):raise FileExistsError('independent grading is immutable; inspect partial outputs')
 data=read_json(phase);contract=read_json(ROOT/'analysis/experiments/20261124_c3_survivor_v1.json');ready=read_json(ROOT/contract['panels_from'])
 if data['game_ids']!=ready['reserved_confirmation_F4'] or len(data['receipts'])!=400:raise ValueError('complete frozen independent200 required')
 if set(data['game_ids'])&set(ready['development_F4']):raise ValueError('independent panel overlaps development')
 for path,digest in data['derived_outputs'].items():
  if sha256_file(ROOT/path)!=digest:raise ValueError('grade input changed')
 report=a1_compare.compare('c4_s06_confirmation_v1_reference','c4_s06_confirmation_v1_candidate')
 gate=release_gate.assess(report,'learned',contract['independent_primary']['primary'],policy='v3')
 write_json(cp,report,pretty=True);write_json(gp,gate,pretty=True)
 passed=gate['decision']=='development_scores_compatible'
 write_json(out,{'kind':'independent200 F4 S06 decision; no promotion','phase_sha256':sha256_file(phase),
  'contract_sha256':sha256_file(ROOT/'analysis/experiments/20261124_c3_survivor_v1.json'),
  'comparison_sha256':sha256_file(cp),'gate_sha256':sha256_file(gp),'population':gate['population'],
  'primary':gate['primary'],'decision':gate['decision'],'proper_established':gate['core']['established'],
  'proper_checks':gate['core']['checks'],'coverage_unresolved':gate['coverage']['unresolved'],
  'coverage_harms':[x for x in gate['coverage']['details'] if x['status']=='material_harm'],
  'next':'unchanged broader1255/stream200/stress20x10k per frozen contract' if passed else 'close fixed attempt; retain r3, no retune/replacement or protected scoring',
  'production_changed':False,'protected_test_run':False},pretty=True)
 print(gate['decision'],gate['primary'],flush=True)
if __name__=='__main__':main()
