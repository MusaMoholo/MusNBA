#!/usr/bin/env python3
"""Clock learned-primary evidence plus paired v3 engine compatibility; no publication."""
import argparse
from pathlib import Path
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from basketball_common import read_json,write_json,sha256_file
from analysis.rule3_scores import distribution
from scripts import a1_compare,release_gate


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run');p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();gate_path=args.output.with_name(args.output.stem+'_gate.json')
    if args.output.exists() or gate_path.exists():raise FileExistsError('fresh score/gate paths required')
    with patch.object(a1_compare,'distribution',side_effect=distribution):
        report=a1_compare.compare(args.run+'_control',args.run+'_candidate')
    fold=report['population']['fold'];phase='confirmation' if fold=='F4' else 'screen'
    path=ROOT/f'analysis/experiments/20261123_a2_late_clock_{phase}_v1.json';node_report=read_json(path)
    node=node_report['pooled'] if fold=='F1-F3' else node_report['folds'][fold]
    if not node['primary_pass'] or not node['component_compatible']:raise ValueError('frozen clock benefit not established')
    report['clock_node_primary']={'source':str(path.relative_to(ROOT)),'source_sha256':sha256_file(path),
        'kind':'conditional joint normalized-time CRPS/no-action Brier; not a pooled player-accuracy claim',
        **{f'{label}_joint':node['comparisons'][label]['joint'] for label in ('legacy','bridge')}}
    report['method']['coverage']='expected randomised PIT; legacy single-random-PIT retained separately'
    report['input_sha256']={str(p.relative_to(ROOT)):sha256_file(p) for p in
        (Path(__file__),ROOT/'analysis/rule3_scores.py',ROOT/'scripts/a1_compare.py',ROOT/'scripts/release_gate.py',
         ROOT/f'analysis/experiments/{args.run}.json',path,ROOT/'docs/protocols/a2_clock_v3_development_20261123.md',
         *(ROOT/f'data/derived/experiments/{args.run}_{side}{tail}.parquet' for side in ('control','candidate') for tail in ('','_players')))}
    write_json(args.output,report,pretty=True)
    gate=release_gate.assess(report,'learned','clock_node_primary/legacy_joint',policy='v3')
    gate['primary']['also_beats_clean_bridge']=report['clock_node_primary']['bridge_joint']['ci_95'][1]<0
    gate['comparison_sha256']=sha256_file(args.output)
    if fold in ('F1','F2','F3'):
        supported=[r for r in gate['core']['details'] if r['status']!='unsupported']
        gate['supported_fold_compatibility']=all(r['status']=='established' for r in supported) and not any(r['status']=='material_harm' for r in gate['coverage']['details'])
        gate['unsupported_fold_bounds']=[r for r in gate['core']['details'] if r['status']=='unsupported']
    write_json(gate_path,gate,pretty=True)
    print(gate['decision'],gate['core']['established'],'/',gate['core']['checks'],flush=True)


if __name__=='__main__':main()
