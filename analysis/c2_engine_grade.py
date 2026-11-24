#!/usr/bin/env python3
"""Apply the original v3 PTS primary to both fixed C2 engine controls."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from basketball_common import read_json,write_json,sha256_file
from scripts import a1_compare,release_gate


def main():
    phase=ROOT/'analysis/experiments/20261124_c2_engine_development_v2.json'
    result=read_json(phase)
    for name,digest in result['derived_outputs'].items():
        if sha256_file(ROOT/name)!=digest:raise ValueError('derived score input changed')
    if len(result['game_ids'])!=200 or result['arms']!=3:raise ValueError('complete200-game three-arm screen required')
    output=ROOT/'analysis/experiments/20261124_c2_engine_decision_v1.json'
    if output.exists():raise FileExistsError(output)
    candidate='c2_engine_development_v1_candidate';checks={}
    for arm in ['reference','bridge']:
        control='c2_engine_development_v1_'+arm
        path=ROOT/f'analysis/experiments/20261124_c2_engine_vs_{arm}_v1.json'
        gatepath=ROOT/f'analysis/experiments/20261124_c2_engine_vs_{arm}_gate_v1.json'
        if path.exists() or gatepath.exists():raise FileExistsError('partial grading requires inspection; preserve existing reports')
        report=a1_compare.compare(control,candidate)
        gate=release_gate.assess(report,'learned','players/all/pts/crps',policy='v3')
        write_json(path,report,pretty=True)
        gate['comparison_sha256']=sha256_file(path);write_json(gatepath,gate,pretty=True)
        checks[arm]={'comparison':str(path.relative_to(ROOT)),'comparison_sha256':sha256_file(path),
                     'gate':str(gatepath.relative_to(ROOT)),'gate_sha256':sha256_file(gatepath),
                     'decision':gate['decision'],'primary':gate['primary'],'compatible':gate['statistical_compatibility']}
    survivor=all(row['decision']=='development_scores_compatible' for row in checks.values())
    write_json(output,{'kind':'one C2 development decision, not a promotion','phase_sha256':sha256_file(phase),
                       'controls':checks,'source_only_promotion_allowed':False,
                       'independent_confirmation_required':survivor,'decision':'freeze_for_C4_confirmation' if survivor else 'retain_r3_no_replacement_search','protected_test_run':False,
                       'production_changed':False},pretty=True)
    for arm,row in checks.items():print(arm,row['decision'],row['primary'],flush=True)

if __name__=='__main__':main()
