#!/usr/bin/env python3
"""Prepare one isolated S02-style dated fold engine for branch diagnostics."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import read_json, sha256_file, write_json  # noqa: E402
from scripts import backtest, evaluate, nodes, train  # noqa: E402

TEMPLATE = ROOT / 'models/a1_s02_f4_causal_guarded.json'
MANIFEST = ROOT / 'analysis/experiments/20261122_a1_pre_candidate_manifest.json'


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fold', choices=('F1', 'F2', 'F3'), required=True)
    parser.add_argument('--name', required=True, help='fresh ASCII alphanumeric/underscore experiment suffix')
    args = parser.parse_args()
    if not args.name or not args.name.isascii() or not all(c.isalnum() or c == '_' for c in args.name):
        raise ValueError('name must contain only ASCII letters, numbers and underscores')
    if os.environ.get('OPENBLAS_NUM_THREADS') != '1' or os.environ.get('OMP_NUM_THREADS') != '8':
        raise ValueError('set OPENBLAS_NUM_THREADS=1 and OMP_NUM_THREADS=8')
    fold = args.fold
    version = f'a1_dated_{fold.lower()}_{args.name}'
    work = ROOT / 'data/derived/experiments' / version
    output = ROOT / 'analysis/experiments' / f'20261122_{version}.json'
    audit_path = ROOT / 'analysis/experiments' / f'20261122_{version}_nodes_audit.json'
    model_dir = ROOT / 'data/models/folds' / f'{version}_{fold}_all'
    if work.exists() or output.exists() or audit_path.exists() or model_dir.exists():
        raise FileExistsError('refusing existing experiment, node audit or model namespace')
    features = Path(f'data/derived/variants/a1_scheduled_{fold}_20261122_v3/features/pregame.parquet')
    feature_report_path = ROOT / features.parent / 'features_report.json'
    feature_report = read_json(feature_report_path)
    schedule_path = ROOT / feature_report['matchup']
    schedule = read_json(schedule_path)
    if (schedule['kind'] != 'dated_implicit_schedule'
            or schedule['training_through'] != evaluate.FOLDS[fold][0]
            or feature_report['input_sha256'][feature_report['matchup']] != sha256_file(schedule_path)):
        raise ValueError('dated schedule does not match the fold cutoff and feature provenance')
    declared = read_json(MANIFEST)['confirmation'][fold]
    if len(declared['games']) != 200:
        raise ValueError('fixed earlier-fold confirmation panel is not 200 games')
    paths = (TEMPLATE, MANIFEST, ROOT / features, feature_report_path, schedule_path,
             ROOT / 'scripts/nodes.py', ROOT / 'scripts/train.py', ROOT / 'scripts/aggregate.py',
             ROOT / 'scripts/backtest.py', ROOT / 'scripts/engine.py',
             ROOT / 'scripts/a1_node_cache_audit.py', Path(__file__))
    fingerprints = {str(path.relative_to(ROOT)): sha256_file(path) for path in paths}

    def verify_inputs() -> None:
        if any(sha256_file(ROOT / name) != digest for name, digest in fingerprints.items()):
            raise ValueError('source, fold feature or schedule changed')

    verify_inputs()
    spec = read_json(TEMPLATE)
    spec['version'] = version
    spec['status'] = 'isolated dated-fold branch diagnostic; not promoted'
    spec['default']['features'] = str(features)
    work.mkdir(parents=True)
    config = work / 'config.json'
    write_json(config, spec, pretty=True)
    started = time.monotonic()
    subprocess.run([sys.executable, '-u', 'scripts/nodes.py', '--features', str(features)], cwd=ROOT, check=True)
    subprocess.run([sys.executable, '-u', '-m', 'scripts.a1_node_cache_audit', '--features', str(features),
                    '--fold', fold, '--output', str(audit_path)], cwd=ROOT, check=True)
    verify_inputs()
    model_version = backtest.fold_engine_version(fold, config, threads=8)
    model_config = read_json(ROOT / 'data/models' / model_version / 'config.json')
    if (model_config['train_through'] != evaluate.FOLDS[fold][0]
            or model_config['features'] != str(features)
            or model_config['matchup'] != feature_report['matchup']
            or set(model_config['nodes']) != set(train.NODES)):
        raise ValueError('fitted engine config differs from dated fold')
    model_files = [model_dir / name for name in ('config.json', 'meta.json')]
    model_files += [model_dir / f'{node}.txt' for node in train.NODES]
    if any(not path.is_file() for path in model_files):
        raise ValueError('fitted engine artifacts are incomplete')
    cache = nodes.cache_dir(features)
    node_audit = read_json(audit_path)
    for node in train.NODES:
        if sha256_file(cache / f'{node}.npz') != node_audit['nodes'][node]['sha256']:
            raise ValueError(f'{node}: cached dataset changed after independent audit')
    verify_inputs()
    write_json(output, {
        'kind': 'isolated dated-fold engine preparation; not a promotion or predictive gate',
        'fold': fold, 'training_through': evaluate.FOLDS[fold][0],
        'validation_from': evaluate.FOLDS[fold][1], 'validation_to': evaluate.FOLDS[fold][2],
        'config': str(config.relative_to(ROOT)), 'config_sha256': sha256_file(config),
        'model_version': model_version, 'model_files': {str(p.relative_to(ROOT)): sha256_file(p) for p in model_files},
        'node_audit': str(audit_path.relative_to(ROOT)), 'node_audit_sha256': sha256_file(audit_path),
        'input_sha256': fingerprints, 'threads': 8, 'blas_threads': 1,
        'elapsed_seconds': round(time.monotonic() - started, 3),
        'limitations': ['Dated body-free S02 diagnostic differs from accepted production engine.',
                        'Inputs lack verified original publication timestamps and dated injury reports.',
                        'Preparation only: no branch screen, accuracy comparison or promotion.'],
    }, pretty=True)
    print(f'{fold}: prepared {model_version}; report {output.relative_to(ROOT)}', flush=True)


if __name__ == '__main__':
    main()
