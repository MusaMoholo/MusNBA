#!/usr/bin/env python3
"""Historical S04 reproduction: preserve its frozen gate; new node work uses compare.py (MODEL.md)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, sha256_file, write_json  # noqa: E402
from scripts import a1_rim_audit, compare, nodes, train  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS, TEST_FROM  # noqa: E402


def audit_fold(fold: str) -> dict:
    baseline_path = EXPERIMENTS / f'20261122_a1_s04_rim_{fold}_v2.json'
    baseline_rows = DERIVED / 'experiments' / f'20261122_a1_s04_rim_{fold}_v2.parquet'
    noise_path = EXPERIMENTS / f'20261122_a1_s04_rim_noise_{fold}.json'
    noise_rows = DERIVED / 'experiments' / f'20261122_a1_s04_rim_noise_{fold}.parquet'
    noise_model = ROOT / 'data/models/folds' / f'a1_s04_rim_noise_{fold}' / 'shot_result.txt'
    baseline = json.loads(baseline_path.read_text())
    noise = json.loads(noise_path.read_text())
    if noise['fold'] != fold or noise['settings'] != {**baseline['settings'], 'seed': 8}:
        raise ValueError(f'{fold}: training-seed settings differ beyond the seed')
    if (noise['baseline_screen_sha256'] != sha256_file(baseline_path)
            or noise['baseline_rows_sha256'] != sha256_file(baseline_rows)
            or noise['rows_sha256'] != sha256_file(noise_rows)
            or noise['model_sha256'] != sha256_file(noise_model)
            or noise['noise_script_sha256'] != sha256_file(ROOT / 'scripts/a1_rim_noise.py')
            or noise['input_sha256'] != baseline['input_sha256']):
        raise ValueError(f'{fold}: noise input or output fingerprints differ')
    for path, digest in noise['input_sha256'].items():
        if sha256_file(ROOT / path) != digest:
            raise ValueError(f'{fold}: changed noise-screen input {path}')
    original = pd.read_parquet(baseline_rows)
    rows = pd.read_parquet(noise_rows)
    if (not rows['game_id'].equals(original['game_id'])
            or not np.array_equal(rows['control_loss'], original['control_loss'])
            or len(rows) != noise['rows'] or rows['game_id'].nunique() != noise['games']):
        raise ValueError(f'{fold}: paired seed rows do not match the baseline')
    data = next(nodes.datasets(['shot_result'], pregame=Path(noise['settings']['features'])))
    dates = pd.to_datetime(pd.Series(data['date']), errors='raise')
    if dates.isna().any() or (dates >= pd.Timestamp(TEST_FROM)).any():
        raise ValueError(f'{fold}: protected or missing dates entered the noise data')
    cutoff, first, last = FOLDS[fold]
    training = (dates >= pd.Timestamp(train.BURN_IN)) & (dates <= pd.Timestamp(cutoff))
    threshold = np.quantile(dates[training].astype('int64'), 0.9)
    fit = training & (dates.astype('int64') < threshold)
    valid = (dates >= pd.Timestamp(first)) & (dates <= pd.Timestamp(last))
    mask = valid.to_numpy()
    if (not np.array_equal(original['game_id'], data['game'][mask])
            or not np.array_equal(original['outcome'], data['y'][mask])):
        raise ValueError(f'{fold}: noise model is not scored on the frozen validation rows')
    model = lgb.Booster(model_file=str(noise_model))
    X = data['X'][model.feature_name()]
    X = train.band_distances(X, fit.to_numpy()) if noise['settings']['banded'] else X
    predicted = model.predict(X[mask], num_threads=6)
    if not isinstance(predicted, np.ndarray):
        raise TypeError(f'{fold}: second-seed model returned non-array predictions')
    outcome = original['outcome'].to_numpy(dtype=int)
    a1_rim_audit.equal(rows['second_loss'], -np.log(predicted[np.arange(len(rows)), outcome]), f'{fold} second loss')
    delta, se, _ = compare.paired(rows['control_loss'].to_numpy(), rows['second_loss'].to_numpy(),
                                  rows['game_id'].to_numpy())
    base = float(rows['control_loss'].mean())
    for label, measured in (('control_log_loss', base), ('second_log_loss', rows['second_loss'].mean()),
                            ('delta', delta), ('se', se), ('relative_delta', delta / base)):
        a1_rim_audit.equal(noise[label], measured, f'{fold} seed {label}')
    candidate = baseline['populations']['complete_validation']['all_shots']
    return {'noise_delta': delta, 'noise_relative': delta / base,
            'candidate_delta': candidate['log_loss_delta'],
            'candidate_relative': candidate['log_loss_delta'] / base,
            'candidate_se': candidate['game_cluster_se'], 'candidate_z': candidate['z'],
            'rows': len(rows), 'games': rows['game_id'].nunique()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f'refusing to overwrite {args.output}')
    folds = {}
    for fold in ('F1', 'F2', 'F3', 'F4'):
        print(f'{fold}: independently checking training-seed prediction rows', flush=True)
        folds[fold] = audit_fold(fold)
    results = list(folds.values())
    noise = float(np.sqrt(np.mean([row['noise_relative'] ** 2 for row in results])))
    candidate_relative = float(np.mean([row['candidate_relative'] for row in results]))
    mean_delta = float(np.mean([row['candidate_delta'] for row in results]))
    pooled_se = float(np.sqrt(np.sum([row['candidate_se'] ** 2 for row in results])) / len(results))
    pooled_z = mean_delta / pooled_se if pooled_se > 0 else 0.0
    bad_fold = any(row['candidate_z'] > 2 and row['candidate_relative'] > 2 * noise for row in results)
    verdict = ('better' if candidate_relative < -noise and pooled_z <= -2 and not bad_fold else
               'worse' if (candidate_relative > noise and pooled_z >= 2) or bad_fold else 'neutral')
    result = {'experiment': 'a1_s04_rim_training_noise_and_node_gate',
              'population': 'F1–F4 complete held-out shot rows, guarded causal-input diagnostics',
              'method': 'existing TRAINING_PLAN section 7 relative RMS seed-noise and pooled game-cluster z gate',
              'folds': folds, 'training_seed_relative_rms': noise, 'candidate_mean_relative': candidate_relative,
              'candidate_mean_delta': mean_delta, 'candidate_pooled_se': pooled_se, 'candidate_pooled_z': pooled_z,
              'candidate_bad_fold': bad_fold, 'node_gate_verdict': verdict,
              'limitations': 'not the unchanged v1.3 engine control; actual shots and lineups are conditioned on',
              'auditor_sha256': sha256_file(Path(__file__))}
    write_json(args.output, result, pretty=True)
    print(json.dumps(result, indent=1), flush=True)


if __name__ == '__main__':
    main()
