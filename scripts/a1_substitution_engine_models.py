#!/usr/bin/env python3
"""Reproduce the frozen S06 node screens and save an earlier-fold engine candidate."""
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
from scripts import (a1_minutes_fold_eval, a1_substitution_in_coverage, a1_substitution_in_screen,
                     a1_substitution_out_screen)  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS  # noqa: E402


def verify_report(path: Path) -> dict:
    report = json.loads(path.read_text())
    for group in ('input_sha256', 'output_sha256'):
        for name, digest in report.get(group, {}).items():
            if sha256_file(ROOT / name) != digest:
                raise ValueError(f'{path.name}: {group} fingerprint differs for {name}')
    return report


def reproduce(rows: pd.DataFrame, prediction: np.ndarray, saved: pd.DataFrame, column: str) -> float:
    keys = ['window_id', 'team', 'player']
    if len(prediction) != len(rows) or not np.isfinite(prediction).all():
        raise ValueError(f'{column}: invalid candidate predictions')
    current = rows[keys].copy()
    current['reproduced'] = prediction
    expected = saved[keys + [column]]
    paired = current.merge(expected, on=keys, how='outer', validate='one_to_one', indicator=True)
    if len(paired) != len(rows) or not paired['_merge'].eq('both').all():
        raise ValueError(f'{column}: saved screen population differs')
    maximum = float(np.max(np.abs(paired['reproduced'] - paired[column])))
    if maximum > 1e-12:
        raise ValueError(f'{column}: screen reproduction differs by {maximum}')
    return maximum


def templates(windows: pd.DataFrame, cutoff: str) -> tuple[dict, list[Path]]:
    if windows.empty or windows['date_et'].ge(cutoff).any() or windows['window_id'].duplicated().any():
        raise ValueError('timeout templates must be unique and strictly before validation')
    if not windows['kind'].eq('timeout').all():
        raise ValueError('template population contains non-timeout windows')
    period = windows['period'].to_numpy(dtype=int)
    clock = windows['clock'].to_numpy(dtype=float)
    length = np.where(period <= 4, 720, 300)
    if (period < 1).any() or not np.isfinite(clock).all() or ((clock < 0) | (clock > length)).any():
        raise ValueError('template clocks are outside their periods')
    max_periods, paths = {}, []
    for season in sorted(windows['season'].unique()):
        path = DERIVED / f'history/{int(season)}/segments.parquet'
        segment = pd.read_parquet(path, columns=['game_id', 'period'])
        maxima = segment.groupby('game_id')['period'].max()
        max_periods.update({str(gid): int(value) for gid, value in maxima.items()})
        paths.append(path)
    regulation, overtime = [], []
    for gid, group in windows.groupby('game_id', sort=True):
        if str(gid) not in max_periods:
            raise ValueError(f'{gid}: no earlier-game period inventory for timeout template')
        if int(group['period'].max()) > max_periods[str(gid)]:
            raise ValueError(f'{gid}: timeout period exceeds the recorded game')
        reg = group.loc[group['period'].le(4), ['period', 'clock']].sort_values(
            ['period', 'clock'], ascending=[True, False], kind='stable')
        regulation.append([[int(period_value), float(720 - clock_value)]
                           for period_value, clock_value in reg.to_numpy(dtype=float)])
        for p in range(5, max_periods[str(gid)] + 1):
            overtime.append(sorted((300 - group.loc[group['period'].eq(p), 'clock']).astype(float).tolist()))
    if not regulation or not overtime:
        raise ValueError('training games lack regulation or observed overtime templates')
    return {'regulation': regulation, 'overtime': overtime,
            'training_games': int(windows['game_id'].nunique()),
            'training_through': str(windows['date_et'].max()),
            'timeout_windows': len(windows)}, paths


def build(fold: str, folder: Path, output: Path) -> None:
    if fold not in FOLDS:
        raise ValueError('unsupported validation fold')
    targets = [folder / 'outgoing.txt', folder / 'incoming.txt', folder / 'templates.json', output]
    if any(path.exists() for path in targets):
        raise FileExistsError('refusing to overwrite an existing substitution-model artifact')
    out_report_path = EXPERIMENTS / '20261122_a1_s06_out_screen.json'
    in_report_path = EXPERIMENTS / '20261122_a1_s06_in_screen.json'
    out_report, in_report = verify_report(out_report_path), verify_report(in_report_path)
    profiles_path = a1_minutes_fold_eval.CAUSAL_PROFILES
    profiles = pd.read_parquet(profiles_path, columns=['date_et', 'player', 'pos'])
    names = ['seed'] + list(FOLDS)[:list(FOLDS).index(fold) + 1]
    out_rows, in_rows, windows, paths = {}, {}, {}, [Path(__file__), out_report_path, in_report_path, profiles_path]
    for name in names:
        report_path = EXPERIMENTS / f'20261122_a1_s06_fold_{name}_v3.json'
        report = verify_report(report_path)
        row_path = DERIVED / 'experiments' / f'20261122_a1_s06_fold_{name}_v3.parquet'
        window_path = DERIVED / 'experiments' / f'20261122_a1_s06_fold_{name}_v3_windows.parquet'
        if report['population'] != name:
            raise ValueError(f'{name}: population mismatch')
        raw = pd.read_parquet(row_path)
        out_rows[name] = a1_substitution_out_screen.outgoing(raw)
        enriched = a1_substitution_in_coverage.attach_positions(raw, profiles)
        in_rows[name] = a1_substitution_in_screen.conditional_population(enriched)
        windows[name] = pd.read_parquet(window_path)
        paths.extend([report_path, row_path, window_path])
    out_train = a1_substitution_out_screen.training_rows(out_rows, fold)
    in_train = a1_substitution_out_screen.training_rows(in_rows, fold)
    labels = out_train['label'].astype(int).to_numpy()
    out_model = lgb.train(a1_substitution_out_screen.PARAMS,
                          lgb.Dataset(a1_substitution_out_screen.feature_matrix(out_train), label=labels),
                          num_boost_round=a1_substitution_out_screen.ROUNDS)
    cases = in_train.loc[in_train['label'].fillna(False)]
    X = pd.concat([a1_substitution_in_screen.matrix(cases), a1_substitution_in_screen.matrix(in_train)],
                  ignore_index=True)
    y = np.concatenate([np.ones(len(cases)), np.zeros(len(in_train))])
    weights = np.concatenate([1 / cases['entry_count'].to_numpy(dtype=float),
                              1 / in_train['pool_count'].to_numpy(dtype=float)])
    if not np.isclose(weights[:len(cases)].sum(), weights[len(cases):].sum(), rtol=0, atol=1e-8):
        raise ValueError('incoming case/reference weights differ')
    in_model = lgb.train(a1_substitution_in_screen.PARAMS, lgb.Dataset(X, label=y, weight=weights),
                         num_boost_round=a1_substitution_in_screen.ROUNDS)
    out_scores_path = ROOT / next(iter(out_report['output_sha256']))
    in_scores_path = ROOT / next(iter(in_report['output_sha256']))
    out_saved = pd.read_parquet(out_scores_path)
    in_saved = pd.read_parquet(in_scores_path)
    out_prediction = np.asarray(out_model.predict(a1_substitution_out_screen.feature_matrix(out_rows[fold]),
                                                   num_threads=1))
    in_prediction = np.asarray(in_model.predict(a1_substitution_in_screen.matrix(in_rows[fold]),
                                                 raw_score=True, num_threads=1))
    errors = {
        'outgoing': reproduce(out_rows[fold], out_prediction, out_saved.loc[out_saved['fold'].eq(fold)],
                              'candidate_probability'),
        'incoming': reproduce(in_rows[fold], in_prediction, in_saved.loc[in_saved['fold'].eq(fold)],
                              'candidate_score'),
    }
    earlier = names[:-1]
    timing, timing_paths = templates(pd.concat([windows[name] for name in earlier], ignore_index=True),
                                     FOLDS[fold][1])
    folder.mkdir(parents=True, exist_ok=True)
    out_model.save_model(str(targets[0]))
    in_model.save_model(str(targets[1]))
    write_json(targets[2], timing, pretty=True)
    paths.extend([out_scores_path, in_scores_path, *timing_paths])
    paths = list(dict.fromkeys(paths))
    record = {
        'experiment': 'a1_s06_frozen_selected_timeout_models', 'fold': fold,
        'validation_from': FOLDS[fold][1], 'training_through': timing['training_through'],
        'training_games': timing['training_games'], 'training_timeout_windows': timing['timeout_windows'],
        'regulation_templates': len(timing['regulation']), 'overtime_templates': len(timing['overtime']),
        'outgoing_training_rows': len(out_train), 'incoming_training_rows': len(in_train),
        'screen_max_absolute_error': errors,
        'input_sha256': {str(path.resolve().relative_to(ROOT)): sha256_file(path) for path in paths},
        'output_sha256': {str(path.resolve().relative_to(ROOT)): sha256_file(path) for path in targets[:3]},
        'limitation': 'Training-selected timeout templates and relative incoming scores are research-only; '
                      'historical participant rosters are not pre-game availability forecasts.',
    }
    write_json(output, record, pretty=True)
    print(f"{fold}: {timing['training_games']} earlier games, {timing['timeout_windows']} selected timeouts; "
          f"screen maximum errors {errors}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fold', choices=list(FOLDS), required=True)
    parser.add_argument('--folder', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.fold, args.folder, args.output)


if __name__ == '__main__':
    main()
