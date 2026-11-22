#!/usr/bin/env python3
"""Fit the registered second training seed for one guarded rim-screen fold."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, atomic_bytes, sha256_file, write_json  # noqa: E402
from scripts import compare, nodes, train  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS, TEST_FROM  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fold', choices=list(FOLDS), required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--rows-output', type=Path, required=True)
    parser.add_argument('--model-output', type=Path, required=True)
    args = parser.parse_args()
    if any(path.exists() for path in (args.output, args.rows_output, args.model_output)):
        raise FileExistsError('refusing to overwrite an existing noise-screen output')
    if not args.rows_output.resolve().is_relative_to((DERIVED / 'experiments').resolve()):
        raise ValueError('row losses must remain under ignored data/derived/experiments')
    if not args.model_output.resolve().is_relative_to((ROOT / 'data/models').resolve()):
        raise ValueError('fitted models must remain under ignored data/models')
    start = time.monotonic()
    baseline_path = EXPERIMENTS / f'20261122_a1_s04_rim_{args.fold}_v2.json'
    baseline_rows = DERIVED / 'experiments' / f'20261122_a1_s04_rim_{args.fold}_v2.parquet'
    baseline = json.loads(baseline_path.read_text())
    if baseline['fold'] != args.fold or baseline['settings']['seed'] != 7:
        raise ValueError('the guarded baseline fold or first seed differs from the frozen contract')
    if sha256_file(baseline_rows) != baseline['rows_sha256']:
        raise ValueError('guarded baseline rows do not match their report')
    for path, digest in baseline['input_sha256'].items():
        if sha256_file(ROOT / path) != digest:
            raise ValueError(f'guarded baseline input fingerprint differs: {path}')
    settings = {**baseline['settings'], 'seed': 8}
    print(f'{args.fold}: fitting second training seed with otherwise identical settings', flush=True)
    data = next(nodes.datasets(['shot_result'], pregame=Path(settings['features'])))
    if (data['date'] >= TEST_FROM).any():
        raise ValueError('protected final-season rows entered the noise screen')
    metric, _, fitted = train.run_node(data, args.fold, FOLDS[args.fold], settings)
    cutoff, first, last = FOLDS[args.fold]
    dates = pd.to_datetime(pd.Series(data['date']), errors='raise')
    training = (dates >= pd.Timestamp(train.BURN_IN)) & (dates <= pd.Timestamp(cutoff))
    threshold = np.quantile(dates[training].astype('int64'), 0.9)
    fit = training & (dates.astype('int64') < threshold)
    valid = (dates >= pd.Timestamp(first)) & (dates <= pd.Timestamp(last))
    X = data['X'][fitted['columns']]
    X = train.band_distances(X, fit.to_numpy()) if settings['banded'] else X
    probs = fitted['model'].predict(X[valid], num_iteration=fitted['model'].best_iteration,
                                    num_threads=settings['threads'])
    if not isinstance(probs, np.ndarray):
        raise TypeError('second-seed model returned non-array predictions')
    heldout = pd.read_parquet(baseline_rows)
    mask = valid.to_numpy()
    if (not np.array_equal(heldout['game_id'].to_numpy(), data['game'][mask])
            or not np.array_equal(heldout['outcome'].to_numpy(), data['y'][mask])):
        raise ValueError('second training seed does not score the identical held-out rows')
    outcome = heldout['outcome'].to_numpy(dtype=int)
    second_loss = -np.log(probs[np.arange(len(outcome)), outcome])
    control_loss = heldout['control_loss'].to_numpy()
    delta, se, _ = compare.paired(control_loss, second_loss, heldout['game_id'].to_numpy())
    rows = pd.DataFrame({'game_id': heldout['game_id'], 'control_loss': control_loss, 'second_loss': second_loss})
    atomic_bytes(args.model_output, fitted['model'].model_to_string().encode())
    atomic_bytes(args.rows_output, rows.to_parquet(index=False))
    result = {'experiment': 'a1_s04_guarded_shot_training_seed_noise', 'fold': args.fold, 'settings': settings,
              'baseline_screen_sha256': sha256_file(baseline_path), 'baseline_rows_sha256': sha256_file(baseline_rows),
              'input_sha256': baseline['input_sha256'], 'noise_script_sha256': sha256_file(Path(__file__)),
              'rows': len(rows), 'games': rows['game_id'].nunique(), 'control_log_loss': float(control_loss.mean()),
              'second_log_loss': float(second_loss.mean()), 'delta': delta, 'se': se,
              'relative_delta': delta / float(control_loss.mean()), 'z': delta / se if se > 0 else None,
              'training_node': metric, 'model_sha256': sha256_file(args.model_output),
              'rows_sha256': sha256_file(args.rows_output), 'elapsed_seconds': round(time.monotonic() - start, 1)}
    write_json(args.output, result, pretty=True)
    print(f'{args.fold}: saved {len(rows):,} paired held-out shots in {result["elapsed_seconds"]:.1f}s', flush=True)


if __name__ == '__main__':
    main()
