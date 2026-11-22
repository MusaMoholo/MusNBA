#!/usr/bin/env python3
"""Independently reconcile the four guarded rim-expression screen reports."""
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
from scripts import a1_minutes_fold_eval, nodes, train  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS, TEST_FROM  # noqa: E402


def equal(actual, expected, label: str, tolerance: float = 1e-12) -> None:
    if not np.allclose(actual, expected, rtol=0, atol=tolerance, equal_nan=True):
        raise ValueError(f'{label} differs from independently reconstructed values')


def audit_metrics(rows: pd.DataFrame, report: dict, label: str) -> int:
    if len(rows) != report['observations'] or rows['game_id'].nunique() != report['games']:
        raise ValueError(f'{label}: population size differs')
    if rows.empty:
        if report['status'] != 'insufficient_sample':
            raise ValueError(f'{label}: empty population was reported as supported')
        return 0
    control = rows['control_loss'].to_numpy()
    candidate = rows['candidate_loss'].to_numpy()
    delta = candidate - control
    groups = pd.DataFrame({'game_id': rows['game_id'], 'delta': delta}).groupby('game_id')['delta'].agg(['sum', 'size'])
    counts = groups['size'].to_numpy()
    totals = groups['sum'].to_numpy()
    mean = float(delta.mean())
    residual = totals - counts * mean
    games = len(groups)
    se = float(np.sqrt(games / max(games - 1, 1) * np.dot(residual, residual)) / len(rows))
    expected = {'control_log_loss': control.mean(), 'candidate_log_loss': candidate.mean(),
                'log_loss_delta': mean, 'game_cluster_se': se,
                'actual_make': rows['made'].mean(), 'control_make': rows['control_make'].mean(),
                'candidate_make': rows['candidate_make'].mean(),
                'control_brier': np.mean((rows['control_make'] - rows['made']) ** 2),
                'candidate_brier': np.mean((rows['candidate_make'] - rows['made']) ** 2)}
    for metric, value in expected.items():
        equal(report[metric], value, f'{label} {metric}')
    if se > 0:
        equal(report['z'], mean / se, f'{label} z')
    elif report['z'] is not None:
        raise ValueError(f'{label}: z is defined for a zero standard error')
    if games >= 30:
        indices = np.random.default_rng(20261122).integers(0, games, (10000, games))
        samples = totals[indices].sum(axis=1) / counts[indices].sum(axis=1)
        equal(report['game_cluster_bootstrap_ci_95'], np.quantile(samples, [0.025, 0.975]), f'{label} interval')
        if report['status'] != 'ok':
            raise ValueError(f'{label}: supported population not marked ok')
    elif report['status'] != 'insufficient_sample' or report['game_cluster_bootstrap_ci_95'] is not None:
        raise ValueError(f'{label}: unsupported population not labelled')
    return 1


def audit_population(rows: pd.DataFrame, report: dict, cuts: np.ndarray, label: str) -> int:
    rim = rows.loc[rows['zone'].eq('rim')]
    matchup = rim['matchup']
    reliability = rim['shooter_effective']
    bins = np.select([matchup.isna(), matchup.le(cuts[0]), matchup.le(cuts[1]), matchup.le(cuts[2])],
                     ['unknown', 'Q1', 'Q2', 'Q3'], default='Q4')
    roles = np.select([reliability.isna(), reliability.lt(250), reliability.le(750)],
                      ['unknown', '<250', '250–750'], default='>750')
    count = audit_metrics(rows, report['all_shots'], f'{label} all')
    count += audit_metrics(rim, report['rim'], f'{label} rim')
    for group in ('Q1', 'Q2', 'Q3', 'Q4', 'unknown'):
        count += audit_metrics(rim.loc[bins == group], report['rim_matchup_training_quartiles'][group],
                               f'{label} matchup {group}')
    for group in ('<250', '250–750', '>750', 'unknown'):
        count += audit_metrics(rim.loc[roles == group], report['rim_shooter_reliability'][group],
                               f'{label} reliability {group}')
    return count


def audit_fold(fold: str, manifest: dict) -> dict:
    stem = f'20261122_a1_s04_rim_{fold}_v2'
    report_path = EXPERIMENTS / f'{stem}.json'
    row_path = DERIVED / 'experiments' / f'{stem}.parquet'
    model_path = ROOT / 'data/models/folds' / f'a1_s04_rim_{fold}_v2' / 'shot_result.txt'
    report = json.loads(report_path.read_text())
    cutoff, first, last = FOLDS[fold]
    if (report['fold'], report['training_cutoff'], report['validation_from'], report['validation_to']) != (fold, cutoff, first, last):
        raise ValueError(f'{fold}: fold labels do not match the fixed contract')
    for path, digest in report['input_sha256'].items():
        if sha256_file(ROOT / path) != digest:
            raise ValueError(f'{fold}: input fingerprint mismatch for {path}')
    if sha256_file(row_path) != report['rows_sha256'] or sha256_file(model_path) != report['model_sha256']:
        raise ValueError(f'{fold}: saved output fingerprint mismatch')

    feature = Path(report['settings']['features'])
    data = next(nodes.datasets(['shot_result'], pregame=feature))
    dates = pd.to_datetime(pd.Series(data['date']), errors='raise')
    if dates.isna().any() or (dates >= pd.Timestamp(TEST_FROM)).any():
        raise ValueError(f'{fold}: missing or protected dates in cached inputs')
    training = (dates >= pd.Timestamp(train.BURN_IN)) & (dates <= pd.Timestamp(cutoff))
    threshold = np.quantile(dates[training].astype('int64'), 0.9)
    tail = training & (dates.astype('int64') >= threshold)
    fit = training & ~tail
    validation = (dates >= pd.Timestamp(first)) & (dates <= pd.Timestamp(last))
    calibration = report['calibration']
    fitted_rows = report['training_node'].get('rows_train')
    if (str(dates[tail].min().date()) != report['training_tail_from']
            or str(dates[tail].max().date()) != calibration['latest_training_date']
            or calibration['train_through'] != cutoff or int(tail.sum()) != calibration['training_rows']
            or (fitted_rows is not None and int(fit.sum()) != fitted_rows)):
        raise ValueError(f'{fold}: fitted-window accounting or date labels differ')
    model = lgb.Booster(model_file=str(model_path))
    X = data['X'][model.feature_name()]
    X = train.band_distances(X, fit.to_numpy()) if report['settings']['banded'] else X
    train_p = model.predict(X[tail], num_threads=6)
    val_p = model.predict(X[validation], num_threads=6)
    if not isinstance(train_p, np.ndarray) or not isinstance(val_p, np.ndarray):
        raise TypeError(f'{fold}: shot model returned non-array predictions')
    tail_values = data['X']['mu_fg_shot'].to_numpy(dtype=float)[tail]
    tail_zones = data['zone'][tail]
    known_tail = (tail_zones == 'rim') & np.isfinite(tail_values)
    if int(known_tail.sum()) != calibration['known_rim_rows']:
        raise ValueError(f'{fold}: known training rim count differs')
    base = train_p[known_tail, 1:].sum(axis=1)
    adjusted = expit(logit(base) + calibration['intercept']
                     + calibration['slope'] * (tail_values[known_tail] - calibration['center']))
    equal(calibration['center'], tail_values[known_tail].mean(), f'{fold} center')
    equal(calibration['baseline_mean'], base.mean(), f'{fold} baseline mean')
    equal(calibration['calibrated_mean'], adjusted.mean(), f'{fold} calibrated mean')
    equal(adjusted.mean(), base.mean(), f'{fold} mean preservation')
    cuts = np.quantile(tail_values[known_tail], [0.25, 0.5, 0.75])
    equal(report['training_rim_quartile_cutpoints'], cuts, f'{fold} training quantiles')

    rows = pd.read_parquet(row_path)
    v = validation.to_numpy()
    for column, expected in (('game_id', data['game'][v]), ('date_et', data['date'][v]),
                             ('zone', data['zone'][v]), ('outcome', data['y'][v])):
        if not np.array_equal(rows[column].to_numpy(), expected):
            raise ValueError(f'{fold}: saved {column} differs from validation inputs')
    for column, source in (('matchup', 'mu_fg_shot'), ('shooter_effective', 'actor_shots_eff')):
        equal(rows[column].to_numpy(), data['X'][source].to_numpy()[v], f'{fold} {column}')
    outcome = rows['outcome'].to_numpy(dtype=int)
    made = (outcome != 0).astype(float)
    equal(rows['made'].to_numpy(), made, f'{fold} outcomes')
    control_make = val_p[:, 1:].sum(axis=1)
    candidate_make = control_make.copy()
    eligible = rows['zone'].eq('rim').to_numpy() & rows['matchup'].notna().to_numpy()
    candidate_make[eligible] = expit(logit(control_make[eligible]) + calibration['intercept']
                                     + calibration['slope'] * (rows['matchup'].to_numpy(dtype=float)[eligible]
                                                                - calibration['center']))
    candidate = val_p.copy()
    candidate[eligible, 0] = 1 - candidate_make[eligible]
    candidate[eligible, 1:] *= (candidate_make[eligible] / control_make[eligible])[:, None]
    equal(rows['control_make'].to_numpy(), control_make, f'{fold} control make')
    equal(rows['candidate_make'].to_numpy(), candidate_make, f'{fold} candidate make')
    equal(rows['control_loss'].to_numpy(), -np.log(val_p[np.arange(len(rows)), outcome]), f'{fold} control loss')
    equal(rows['candidate_loss'].to_numpy(), -np.log(candidate[np.arange(len(rows)), outcome]), f'{fold} candidate loss')
    fixed_ids = set(a1_minutes_fold_eval.fold_games(manifest, fold)['game_id'])
    fixed = rows.loc[rows['game_id'].isin(fixed_ids)]
    if len(fixed_ids) != 200 or set(fixed['game_id']) != fixed_ids:
        raise ValueError(f'{fold}: fixed game IDs do not match the preregistration')
    count = audit_population(rows, report['populations']['complete_validation'], cuts, f'{fold} full')
    count += audit_population(fixed, report['populations']['fixed_200_games'], cuts, f'{fold} fixed')
    return {'shots': len(rows), 'games': rows['game_id'].nunique(), 'fixed_shots': len(fixed),
            'training_tail_rows': int(tail.sum()), 'known_rim_training_rows': int(known_tail.sum()),
            'metric_populations_audited': count, 'input_hashes': len(report['input_sha256']),
            'slope': calibration['slope'],
            'all_shot_log_loss_delta': report['populations']['complete_validation']['all_shots']['log_loss_delta'],
            'fixed_log_loss_delta': report['populations']['fixed_200_games']['all_shots']['log_loss_delta']}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f'refusing to overwrite {args.output}')
    manifest = json.loads(a1_minutes_fold_eval.PREREG.read_text())
    folds = {}
    for fold in ('F1', 'F2', 'F3', 'F4'):
        print(f'{fold}: independently checking fingerprints, predictions and paired populations', flush=True)
        folds[fold] = audit_fold(fold, manifest)
    original = pd.read_parquet(DERIVED / 'experiments/20261122_a1_s04_rim_F4.parquet')
    corrected = pd.read_parquet(DERIVED / 'experiments/20261122_a1_s04_rim_F4_v2.parquet')
    if not original.equals(corrected):
        raise ValueError('original and corrected F4 prediction rows differ')
    result = {'experiment': 'a1_s04_rim_independent_accounting', 'folds': folds,
              'original_corrected_f4_rows_identical': len(original),
              'auditor_sha256': sha256_file(Path(__file__))}
    write_json(args.output, result, pretty=True)
    print(json.dumps(result, indent=1), flush=True)


if __name__ == '__main__':
    main()
