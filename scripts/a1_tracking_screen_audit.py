#!/usr/bin/env python3
"""Independently reconstruct tracking-fold predictions, metrics and the frozen node gate."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, sha256_file, write_json  # noqa: E402
from scripts import a1_minutes_fold_eval, a1_rim_audit, nodes, train  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS, TEST_FROM  # noqa: E402

BUCKETS = {'rim': ('rim',), 'three': ('corner3', 'above3')}


def audit_population(rows: pd.DataFrame, report: dict, cuts: dict, label: str) -> int:
    count = a1_rim_audit.audit_metrics(rows, report['all_shots'], f'{label} all')
    relevant = set(sum(BUCKETS.values(), ()))
    count += a1_rim_audit.audit_metrics(rows.loc[~rows['zone'].isin(relevant)],
                                       report['other_zones'], f'{label} other')
    for bucket, zones in BUCKETS.items():
        subset = rows.loc[rows['zone'].isin(zones)]
        count += a1_rim_audit.audit_metrics(subset, report[bucket]['all'], f'{label} {bucket}')
        values = subset['tracking']
        boundaries = cuts[bucket]
        bins = np.select([values.isna(), values.le(boundaries[0]), values.le(boundaries[1]), values.le(boundaries[2])],
                         ['unknown', 'Q1', 'Q2', 'Q3'], default='Q4')
        for group in ('Q1', 'Q2', 'Q3', 'Q4', 'unknown'):
            count += a1_rim_audit.audit_metrics(subset.loc[bins == group],
                                                report[bucket]['training_tracking_quartiles'][group],
                                                f'{label} {bucket} {group}')
    return count


def audit_fold(fold: str, manifest: dict) -> dict:
    report_path = EXPERIMENTS / f'20261122_a1_s04_tracking_{fold}.json'
    row_path = DERIVED / 'experiments' / f'20261122_a1_s04_tracking_{fold}.parquet'
    feature_path = DERIVED / 'experiments/20261122_a1_s04_tracking_features.parquet'
    baseline_path = EXPERIMENTS / f'20261122_a1_s04_rim_{fold}_v2.json'
    model_path = ROOT / 'data/models/folds' / f'a1_s04_rim_{fold}_v2/shot_result.txt'
    report = json.loads(report_path.read_text())
    baseline = json.loads(baseline_path.read_text())
    cutoff, first, last = FOLDS[fold]
    if (report['fold'], report['training_cutoff'], report['validation_from'], report['validation_to']) != (fold, cutoff, first, last):
        raise ValueError(f'{fold}: screen dates differ from registered fold dates')
    for path, digest in report['input_sha256'].items():
        if sha256_file(ROOT / path) != digest:
            raise ValueError(f'{fold}: input fingerprint mismatch for {path}')
    if sha256_file(row_path) != report['rows_sha256']:
        raise ValueError(f'{fold}: tracking-screen output fingerprint mismatch')
    data = next(nodes.datasets(['shot_result'], pregame=Path(baseline['settings']['features'])))
    features = pd.read_parquet(feature_path)
    if len(features) != len(data['y']) or (data['date'] >= TEST_FROM).any():
        raise ValueError(f'{fold}: feature population or protected cutoff differs')
    for name, actual in (('game_id', data['game']), ('date_et', data['date']),
                         ('zone', data['zone']), ('outcome', data['y'])):
        if not np.array_equal(features[name].to_numpy(), actual):
            raise ValueError(f'{fold}: tracking features do not align on {name}')
    dates = pd.to_datetime(pd.Series(data['date']), errors='raise')
    training = (dates >= pd.Timestamp(train.BURN_IN)) & (dates <= pd.Timestamp(cutoff))
    threshold = np.quantile(dates[training].astype('int64'), 0.9)
    tail = training & (dates.astype('int64') >= threshold)
    fit = training & ~tail
    valid = (dates >= pd.Timestamp(first)) & (dates <= pd.Timestamp(last))
    if str(dates[tail].min().date()) != report['training_tail_from']:
        raise ValueError(f'{fold}: training-tail start label differs')
    model = lgb.Booster(model_file=str(model_path))
    X = data['X'][model.feature_name()]
    X = train.band_distances(X, fit.to_numpy()) if baseline['settings']['banded'] else X
    tail_prob = model.predict(X[tail], num_threads=6)
    control = model.predict(X[valid], num_threads=6)
    if not isinstance(tail_prob, np.ndarray) or not isinstance(control, np.ndarray):
        raise TypeError(f'{fold}: saved shot model returned non-array predictions')
    tail_mask, val_mask = tail.to_numpy(), valid.to_numpy()
    candidate = control.copy()
    tracking = np.full(len(control), np.nan)
    cuts = {}
    for bucket, zones in BUCKETS.items():
        values = features[f'{bucket}_five_mean'].to_numpy(dtype=float)
        tail_values = values[tail_mask]
        eligible_tail = np.isin(data['zone'][tail_mask], zones) & np.isfinite(tail_values)
        cal = report['calibration'][bucket]
        if (cal['training_rows'] != int(tail.sum()) or cal['known_rim_rows'] != int(eligible_tail.sum())
                or cal['train_through'] != cutoff or cal['latest_training_date'] != str(dates[tail].max().date())):
            raise ValueError(f'{fold} {bucket}: training-cutoff or eligible sample differs')
        base_tail = tail_prob[eligible_tail, 1:].sum(axis=1)
        adjusted_tail = expit(logit(base_tail) + cal['intercept']
                              + cal['slope'] * (tail_values[eligible_tail] - cal['center']))
        for label, measured in (('center', tail_values[eligible_tail].mean()), ('baseline_mean', base_tail.mean()),
                                ('calibrated_mean', adjusted_tail.mean())):
            a1_rim_audit.equal(cal[label], measured, f'{fold} {bucket} {label}')
        a1_rim_audit.equal(adjusted_tail.mean(), base_tail.mean(), f'{fold} {bucket} training mean')
        cuts[bucket] = np.quantile(tail_values[eligible_tail], [0.25, 0.5, 0.75])
        a1_rim_audit.equal(cuts[bucket], report['training_quartile_cutpoints'][bucket], f'{fold} {bucket} cutpoints')
        val_values = values[val_mask]
        bucket_zone = np.isin(data['zone'][val_mask], zones)
        tracking[bucket_zone] = val_values[bucket_zone]
        eligible = bucket_zone & np.isfinite(val_values)
        base = candidate[eligible, 1:].sum(axis=1)
        adjusted = expit(logit(base) + cal['intercept'] + cal['slope'] * (val_values[eligible] - cal['center']))
        candidate[eligible, 0] = 1 - adjusted
        candidate[eligible, 1:] *= (adjusted / base)[:, None]
    rows = pd.read_parquet(row_path)
    y = data['y'][val_mask].astype(int)
    for name, actual in (('game_id', data['game'][val_mask]), ('date_et', data['date'][val_mask]),
                         ('zone', data['zone'][val_mask]), ('outcome', y)):
        if not np.array_equal(rows[name].to_numpy(), actual):
            raise ValueError(f'{fold}: saved screen {name} differs')
    for name, actual in (('tracking', tracking), ('made', (y != 0).astype(float)),
                         ('control_make', control[:, 1:].sum(axis=1)),
                         ('candidate_make', candidate[:, 1:].sum(axis=1)),
                         ('control_loss', -np.log(control[np.arange(len(y)), y])),
                         ('candidate_loss', -np.log(candidate[np.arange(len(y)), y]))):
        a1_rim_audit.equal(rows[name].to_numpy(), actual, f'{fold} {name}')
    fixed_ids = set(a1_minutes_fold_eval.fold_games(manifest, fold)['game_id'])
    fixed = rows.loc[rows['game_id'].isin(fixed_ids)]
    if len(fixed_ids) != 200 or set(fixed['game_id']) != fixed_ids:
        raise ValueError(f'{fold}: fixed 200 game IDs differ')
    populations = audit_population(rows, report['populations']['complete_validation'], cuts, f'{fold} full')
    populations += audit_population(fixed, report['populations']['fixed_200_games'], cuts, f'{fold} fixed')
    metric = report['populations']['complete_validation']['all_shots']
    return {'shots': len(rows), 'games': rows['game_id'].nunique(), 'fixed_shots': len(fixed),
            'metric_populations_audited': populations, 'control_log_loss': metric['control_log_loss'],
            'candidate_delta': metric['log_loss_delta'], 'candidate_relative': metric['log_loss_delta'] / metric['control_log_loss'],
            'candidate_se': metric['game_cluster_se'], 'candidate_z': metric['z']}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f'refusing to overwrite {args.output}')
    manifest = json.loads(a1_minutes_fold_eval.PREREG.read_text())
    folds = {}
    for fold in ('F1', 'F2', 'F3', 'F4'):
        print(f'{fold}: independently checking tracking predictions and paired populations', flush=True)
        folds[fold] = audit_fold(fold, manifest)
    noise_path = EXPERIMENTS / '20261122_a1_s04_rim_node_gate.json'
    noise = json.loads(noise_path.read_text())['training_seed_relative_rms']
    rows = list(folds.values())
    relative = float(np.mean([row['candidate_relative'] for row in rows]))
    mean_delta = float(np.mean([row['candidate_delta'] for row in rows]))
    pooled_se = float(np.sqrt(np.sum([row['candidate_se'] ** 2 for row in rows])) / len(rows))
    pooled_z = mean_delta / pooled_se if pooled_se > 0 else 0.0
    bad_fold = any(row['candidate_z'] > 2 and row['candidate_relative'] > 2 * noise for row in rows)
    verdict = ('better' if relative < -noise and pooled_z <= -2 and not bad_fold else
               'worse' if (relative > noise and pooled_z >= 2) or bad_fold else 'neutral')
    result = {'experiment': 'a1_s04_tracking_fold_independent_accounting_and_node_gate', 'folds': folds,
              'training_seed_relative_rms': noise, 'noise_report_sha256': sha256_file(noise_path),
              'candidate_mean_relative': relative, 'candidate_mean_delta': mean_delta, 'candidate_pooled_se': pooled_se,
              'candidate_pooled_z': pooled_z, 'candidate_bad_fold': bad_fold, 'node_gate_verdict': verdict,
              'limitations': 'retrospective source/crosswalk revision timing unproven; actual shots/fives supplied; '
                             'not the unchanged v1.3 engine control',
              'auditor_sha256': sha256_file(Path(__file__))}
    write_json(args.output, result, pretty=True)
    print(json.dumps(result, indent=1), flush=True)


if __name__ == '__main__':
    main()
