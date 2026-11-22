#!/usr/bin/env python3
"""Screen the frozen, prior-only tracking-defence increment on one guarded fold."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, atomic_bytes, sha256_file, write_json  # noqa: E402
from scripts import a1_minutes_fold_eval, a1_rim_calibration, a1_rim_screen, nodes, train  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS, TEST_FROM  # noqa: E402

TRACKING_ROWS = DERIVED / 'experiments/20261122_a1_s04_tracking_features.parquet'
TRACKING_REPORT = EXPERIMENTS / '20261122_a1_s04_tracking_features.json'
BUCKET_ZONES = {'rim': ('rim',), 'three': ('corner3', 'above3')}


def source_zone(zones: np.ndarray, bucket: str) -> np.ndarray:
    if bucket not in BUCKET_ZONES:
        raise ValueError(f'unknown tracking bucket {bucket!r}')
    return np.where(np.isin(zones, BUCKET_ZONES[bucket]), 'rim', 'paint')


def bucket_population(rows: pd.DataFrame, bucket: str, cuts: np.ndarray) -> dict:
    subset = rows[rows['zone'].isin(BUCKET_ZONES[bucket])]
    known = subset['tracking'].notna()
    values = subset['tracking']
    labels = np.select([~known, values.le(cuts[0]), values.le(cuts[1]), values.le(cuts[2])],
                       ['unknown', 'Q1', 'Q2', 'Q3'], default='Q4')
    return {'all': a1_rim_screen.summary(subset),
            'training_tracking_quartiles': {name: a1_rim_screen.summary(subset.loc[labels == name])
                                            for name in ('Q1', 'Q2', 'Q3', 'Q4', 'unknown')}}


def population(rows: pd.DataFrame, cuts: dict[str, np.ndarray]) -> dict:
    other = rows.loc[~rows['zone'].isin(sum(BUCKET_ZONES.values(), ()))]
    return {'all_shots': a1_rim_screen.summary(rows),
            'rim': bucket_population(rows, 'rim', cuts['rim']),
            'three': bucket_population(rows, 'three', cuts['three']),
            'other_zones': a1_rim_screen.summary(other)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fold', choices=list(FOLDS), required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--rows-output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.rows_output.exists():
        raise FileExistsError('refusing to overwrite an existing tracking-screen output')
    if not args.rows_output.resolve().is_relative_to((DERIVED / 'experiments').resolve()):
        raise ValueError('tracking-screen rows must remain under ignored data/derived/experiments')
    started = time.monotonic()
    fold = args.fold
    baseline_path = EXPERIMENTS / f'20261122_a1_s04_rim_{fold}_v2.json'
    baseline_rows = DERIVED / 'experiments' / f'20261122_a1_s04_rim_{fold}_v2.parquet'
    model_path = ROOT / 'data/models/folds' / f'a1_s04_rim_{fold}_v2/shot_result.txt'
    baseline = json.loads(baseline_path.read_text())
    tracking_report = json.loads(TRACKING_REPORT.read_text())
    if (baseline['fold'] != fold or sha256_file(model_path) != baseline['model_sha256']
            or sha256_file(baseline_rows) != baseline['rows_sha256']
            or sha256_file(TRACKING_ROWS) != tracking_report['rows_sha256']):
        raise ValueError(f'{fold}: guarded baseline or tracking outputs do not match their recorded fingerprints')
    for source in (baseline['input_sha256'], tracking_report['input_sha256']):
        for path, digest in source.items():
            if sha256_file(ROOT / path) != digest:
                raise ValueError(f'{fold}: changed tracking-screen input {path}')
    data = next(nodes.datasets(['shot_result'], pregame=Path(baseline['settings']['features'])))
    tracking = pd.read_parquet(TRACKING_ROWS)
    if len(tracking) != len(data['y']) or (data['date'] >= TEST_FROM).any():
        raise ValueError(f'{fold}: tracking rows differ in size or include the protected final season')
    for key, actual in (('game_id', data['game']), ('date_et', data['date']),
                        ('zone', data['zone']), ('outcome', data['y'])):
        if not np.array_equal(tracking[key].to_numpy(), actual):
            raise ValueError(f'{fold}: tracking {key} does not align with cached shot rows')
    cutoff, first, last = FOLDS[fold]
    all_train, tail, fit, tail_from = a1_rim_screen.training_tail_masks(data['date'], cutoff)
    valid = (data['date'] >= first) & (data['date'] <= last)
    if not all_train.any() or not valid.any():
        raise ValueError(f'{fold}: empty training or validation set')
    model = lgb.Booster(model_file=str(model_path))
    X = data['X'][model.feature_name()]
    X = train.band_distances(X, fit) if baseline['settings']['banded'] else X
    tail_prob = model.predict(X[tail], num_threads=6)
    control = model.predict(X[valid], num_threads=6)
    if not isinstance(tail_prob, np.ndarray) or not isinstance(control, np.ndarray):
        raise TypeError(f'{fold}: shot model returned non-array predictions')
    tail_zones, val_zones = data['zone'][tail], data['zone'][valid]
    calibrated = {}
    cuts = {}
    candidate = control.copy()
    for bucket in BUCKET_ZONES:
        values = tracking[f'{bucket}_five_mean'].to_numpy(dtype=float)
        fitted = a1_rim_calibration.fit(tail_prob, values[tail], source_zone(tail_zones, bucket),
                                        data['y'][tail], data['date'][tail], cutoff)
        eligible_tail = np.isin(tail_zones, BUCKET_ZONES[bucket]) & np.isfinite(values[tail])
        cuts[bucket] = np.quantile(values[tail][eligible_tail], [0.25, 0.5, 0.75])
        calibrated[bucket] = fitted
        candidate = a1_rim_calibration.apply(candidate, values[valid], source_zone(val_zones, bucket), fitted)
    y = data['y'][valid].astype(int)
    n = len(y)
    original_rows = pd.read_parquet(baseline_rows)
    control_loss = -np.log(control[np.arange(n), y])
    if (not np.array_equal(original_rows['game_id'].to_numpy(), data['game'][valid])
            or not np.allclose(original_rows['control_loss'], control_loss, rtol=0, atol=1e-12)):
        raise ValueError(f'{fold}: tracking control does not reproduce the saved guarded baseline')
    features = tracking.loc[valid].reset_index(drop=True)
    tracking_value = np.where(np.isin(val_zones, BUCKET_ZONES['rim']), features['rim_five_mean'],
                              np.where(np.isin(val_zones, BUCKET_ZONES['three']), features['three_five_mean'], np.nan))
    rows = pd.DataFrame({'game_id': data['game'][valid], 'date_et': data['date'][valid], 'zone': val_zones,
                         'outcome': y, 'made': (y != 0).astype(float), 'tracking': tracking_value,
                         'control_make': control[:, 1:].sum(axis=1), 'candidate_make': candidate[:, 1:].sum(axis=1),
                         'control_loss': control_loss, 'candidate_loss': -np.log(candidate[np.arange(n), y])})
    unchanged = ~np.isfinite(tracking_value)
    if not np.array_equal(control[unchanged], candidate[unchanged]):
        raise ValueError(f'{fold}: absent tracking inputs or other zones changed')
    manifest = json.loads(a1_minutes_fold_eval.PREREG.read_text())
    fixed_ids = set(a1_minutes_fold_eval.fold_games(manifest, fold)['game_id'])
    fixed = rows.loc[rows['game_id'].isin(fixed_ids)]
    if len(fixed_ids) != 200 or set(fixed['game_id']) != fixed_ids:
        raise ValueError(f'{fold}: fixed 200-game population differs from the preregistration')
    atomic_bytes(args.rows_output, rows.to_parquet(index=False))
    paths = (Path(__file__), Path(a1_rim_calibration.__file__), Path(a1_rim_screen.__file__), TRACKING_ROWS,
             TRACKING_REPORT, baseline_path, baseline_rows, model_path, a1_minutes_fold_eval.PREREG)
    report = {'experiment': 'a1_s04_tracking_defence_guarded_fold_screen', 'fold': fold,
              'method': 'training-tail level-preserving tracking-five increment over the identical guarded shot node',
              'limitations': 'retrospective source/crosswalk timing is unproven; actual shots/fives are conditioned on; '
                             'tracking buckets are not on-ball matchup labels; not a v1.3 engine comparison',
              'training_cutoff': cutoff, 'validation_from': first, 'validation_to': last, 'training_tail_from': tail_from,
              'calibration': calibrated,
              'training_quartile_cutpoints': {key: value.tolist() for key, value in cuts.items()},
              'populations': {'complete_validation': population(rows, cuts), 'fixed_200_games': population(fixed, cuts)},
              'input_sha256': {str(p.resolve().relative_to(ROOT)): sha256_file(p) for p in paths},
              'rows_sha256': sha256_file(args.rows_output), 'elapsed_seconds': round(time.monotonic() - started, 1)}
    write_json(args.output, report, pretty=True)
    print(f'{fold}: saved {n:,} paired shots in {report["elapsed_seconds"]:.1f}s', flush=True)


if __name__ == '__main__':
    main()
