#!/usr/bin/env python3
"""Screen a fixed outgoing-substitution model on chronological A1 development folds."""
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
from scripts import a1_compare  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS, TEST_FROM  # noqa: E402

TIERS = ('star', 'starter', 'bench', 'unknown')
FEATURES = ('period', 'clock', 'margin', 'fouls_before', 'seconds_before', 'stint_before',
            'target_mean_proxy', 'target_deficit', *(f'tier_{tier}' for tier in TIERS))
ROUNDS = 120
PARAMS = {'objective': 'binary', 'num_leaves': 15, 'learning_rate': 0.05, 'min_data_in_leaf': 80,
          'lambda_l2': 1.0, 'seed': 20261122, 'num_threads': 1, 'deterministic': True,
          'force_col_wise': True, 'verbosity': -1}


def outgoing(frame: pd.DataFrame) -> pd.DataFrame:
    rows = frame.loc[frame['decision'].eq('out')].copy()
    keys = ['window_id', 'team', 'player']
    if rows.empty or rows.duplicated(keys).any() or rows[keys + ['game_id', 'date_et']].isna().any().any():
        raise ValueError('outgoing population is empty, duplicated or missing identifiers')
    if rows['label'].isna().any() or not rows['prior_tier'].isin(TIERS).all():
        raise ValueError('outgoing labels or prior tiers are invalid')
    if rows['date_et'].ge(TEST_FROM).any():
        raise ValueError('protected final-season games are not eligible')
    return rows


def training_rows(populations: dict[str, pd.DataFrame], fold: str) -> pd.DataFrame:
    earlier = ['seed'] + list(FOLDS)[:list(FOLDS).index(fold)]
    train = pd.concat([populations[name] for name in earlier], ignore_index=True)
    validation = populations[fold]
    if train.empty or validation.empty or train['date_et'].ge(FOLDS[fold][1]).any():
        raise ValueError(f'{fold}: training contains a validation-date or future observation')
    if not validation['date_et'].between(FOLDS[fold][1], FOLDS[fold][2]).all():
        raise ValueError(f'{fold}: validation origins are outside the fixed fold')
    if set(train['game_id']) & set(validation['game_id']):
        raise ValueError(f'{fold}: a validation game also appears in training')
    return train


def feature_matrix(rows: pd.DataFrame) -> pd.DataFrame:
    matrix = rows[list(FEATURES[:8])].apply(pd.to_numeric, errors='raise').astype(float)
    for tier in TIERS:
        matrix[f'tier_{tier}'] = rows['prior_tier'].eq(tier).astype(float)
    if (np.isinf(matrix.to_numpy()).any()
            or not np.isfinite(matrix[list(FEATURES[:6])].to_numpy()).all()):
        raise ValueError('model features contain infinite values or missing observed game state')
    return matrix.loc[:, list(FEATURES)]


def conditional_baseline(train: pd.DataFrame, validation: pd.DataFrame) -> tuple[np.ndarray, int]:
    labels = train['label'].astype(int)
    overall = float(labels.mean())
    if not 0 < overall < 1:
        raise ValueError('baseline training labels need both outgoing classes')
    groups = pd.DataFrame({'period': train['period'].clip(upper=5), 'tier': train['prior_tier'],
                           'label': labels}).groupby(['period', 'tier'])['label'].agg(['sum', 'count'])
    groups['probability'] = (groups['sum'] + 20 * overall) / (groups['count'] + 20)
    lookup = pd.MultiIndex.from_arrays([validation['period'].clip(upper=5), validation['prior_tier']])
    probabilities = groups['probability'].reindex(lookup)
    return probabilities.fillna(overall).to_numpy(dtype=float), int(probabilities.isna().sum())


def predictions(train: pd.DataFrame, validation: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    labels = train['label'].astype(int).to_numpy()
    if np.unique(labels).size != 2:
        raise ValueError('candidate training labels need both outgoing classes')
    classifier = lgb.train(PARAMS, lgb.Dataset(feature_matrix(train), label=labels), num_boost_round=ROUNDS)
    baseline, fallback_rows = conditional_baseline(train, validation)
    candidate = classifier.predict(feature_matrix(validation), num_threads=1)
    if not isinstance(candidate, np.ndarray) or candidate.shape != (len(validation),):
        raise ValueError('candidate did not return one dense binary probability per decision')
    for name, probability in (('baseline', baseline), ('candidate', candidate)):
        if not np.isfinite(probability).all() or ((probability < 0) | (probability > 1)).any():
            raise ValueError(f'{name} produced invalid outgoing probabilities')
    rows = validation[['window_id', 'game_id', 'date_et', 'team', 'player', 'prior_tier', 'period',
                       'label']].copy()
    rows['baseline_probability'] = baseline
    rows['candidate_probability'] = candidate
    return rows, {'baseline_overall_fallback_rows': fallback_rows,
                  'feature_split_counts': {name: int(value)
                                           for name, value in zip(FEATURES, classifier.feature_importance())}}


def summary(rows: pd.DataFrame) -> dict:
    ids = sorted(rows['game_id'].unique().tolist())
    count = len(rows)
    player_games = len(rows[['game_id', 'player']].drop_duplicates())
    supported = len(ids) >= a1_compare.MIN_GAMES and player_games >= a1_compare.MIN_PLAYER_GAMES
    y = rows['label'].astype(int).to_numpy(dtype=float)
    values = {}
    for name in ('baseline', 'candidate'):
        probability = rows[f'{name}_probability'].to_numpy(dtype=float)
        values[f'{name}_brier'] = (probability - y) ** 2
        with np.errstate(divide='ignore'):
            values[f'{name}_log_loss'] = -np.log(np.where(y == 1, probability, 1 - probability))
    data = pd.DataFrame({'game_id': rows['game_id'].to_numpy(), 'n': 1, **values})
    grouped = data.groupby('game_id').sum().reindex(ids, fill_value=0)
    result = {'observations': count, 'player_games': player_games, 'games': len(ids),
              'outgoing_count': int(y.sum()), 'status': 'ok' if supported else 'insufficient_sample'}
    weights = None
    if supported:
        draws = np.random.default_rng(a1_compare.BOOTSTRAP_SEED).integers(
            0, len(ids), (a1_compare.BOOTSTRAP_REPLICATES, len(ids)))
        weights = np.zeros(draws.shape, dtype=np.int16)
        np.add.at(weights, (np.arange(len(draws))[:, None], draws), 1)
    for metric in ('brier', 'log_loss'):
        a = grouped[f'baseline_{metric}'].to_numpy(dtype=float)
        b = grouped[f'candidate_{metric}'].to_numpy(dtype=float)
        if not np.isfinite(a).all() or not np.isfinite(b).all():
            result[metric] = {'status': 'infinite_log_loss', 'baseline': None, 'candidate': None,
                              'change': None, 'ci_95': None,
                              'baseline_infinite_games': int(np.isinf(a).sum()),
                              'candidate_infinite_games': int(np.isinf(b).sum())}
            continue
        interval = None
        if weights is not None:
            totals = weights @ grouped['n'].to_numpy(dtype=float)
            if (totals <= 0).any():
                raise ValueError('game bootstrap contains an empty replicate')
            difference = (weights @ (b - a)) / totals
            interval = [float(value) for value in np.quantile(difference, [0.025, 0.975])]
        result[metric] = {'baseline': float(a.sum() / count), 'candidate': float(b.sum() / count),
                          'change': float((b - a).sum() / count), 'ci_95': interval}
    return result


def load_population(name: str) -> tuple[pd.DataFrame, list[Path], dict]:
    stem = f'20261122_a1_s06_fold_{name}_v3'
    report_path = EXPERIMENTS / f'{stem}.json'
    rows_path = DERIVED / 'experiments' / f'{stem}.parquet'
    report = json.loads(report_path.read_text())
    if report['population'] != name:
        raise ValueError(f'{name}: dataset report population differs')
    for path, digest in report['input_sha256'].items():
        if sha256_file(ROOT / path) != digest:
            raise ValueError(f'{name}: recorded input changed: {path}')
    if report['output_sha256'].get(str(rows_path.relative_to(ROOT))) != sha256_file(rows_path):
        raise ValueError(f'{name}: candidate rows differ from their report')
    rows = outgoing(pd.read_parquet(rows_path))
    if len(rows) != report['candidate_counts']['out_rows']:
        raise ValueError(f'{name}: outgoing population differs from the independent accounting')
    return rows, [report_path, rows_path], report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=EXPERIMENTS / '20261122_a1_s06_out_screen.json')
    parser.add_argument('--rows-output', type=Path,
                        default=DERIVED / 'experiments/20261122_a1_s06_out_screen.parquet')
    args = parser.parse_args()
    if args.output.exists() or args.rows_output.exists():
        raise FileExistsError('refusing to overwrite an existing outgoing screen')
    populations, inputs, provenance = {}, [Path(__file__)], {}
    for name in ('seed', *FOLDS):
        populations[name], paths, provenance[name] = load_population(name)
        inputs.extend(paths)
    results, frames = {}, []
    started = time.monotonic()
    for fold in FOLDS:
        train = training_rows(populations, fold)
        validation = populations[fold]
        scored, model_details = predictions(train, validation)
        scored['fold'] = fold
        results[fold] = {
            'training_games': int(train['game_id'].nunique()), 'training_rows': len(train),
            'training_through': str(train['date_et'].max()),
            'validation_from': FOLDS[fold][1], 'validation_through': FOLDS[fold][2],
            'target_missing': int(validation['target_mean_proxy'].isna().sum()),
            'deficit_missing': int(validation['target_deficit'].isna().sum()),
            'all': summary(scored),
            'tiers': {tier: summary(scored.loc[scored['prior_tier'].eq(tier)])
                      for tier in TIERS if scored['prior_tier'].eq(tier).any()},
            **model_details,
        }
        frames.append(scored)
        print(f'{fold}: {len(scored)} outgoing decisions from {scored["game_id"].nunique()} games, '
              f'{time.monotonic() - started:.1f}s', flush=True)
    scores = pd.concat(frames, ignore_index=True)
    pooled = summary(scores)
    upper = pooled['brier']['ci_95'][1] if pooled['brier']['ci_95'] is not None else None
    favourable = sum(results[fold]['all']['brier']['change'] < 0 for fold in FOLDS)
    report = {
        'experiment': 'a1_s06_outgoing_selected_timeout_fold_screen',
        'model_params': PARAMS, 'num_boost_round': ROUNDS, 'features': list(FEATURES), 'baseline_prior_weight': 20,
        'folds': results, 'pooled': pooled, 'favourable_fold_points': favourable,
        'diagnostic_screen_pass': upper is not None and upper < 0 and favourable >= 3,
        'selection_rule': 'Pooled paired outgoing Brier 95% upper bound below zero and at least three of four '
                          'fold point differences below zero; this is only an event-level research screen.',
        'limitations': 'Outcome-selected timeouts, inferred lineups, prior-box rosters and mean target proxies do '
                       'not establish a deployable all-stoppage hazard, physical availability or an engine gain.',
        'populations': {name: {'games': report['candidate_counts']['games'],
                               'out_rows': report['candidate_counts']['out_rows']}
                        for name, report in provenance.items()},
        'input_sha256': {str(path.relative_to(ROOT)): sha256_file(path) for path in inputs},
    }
    atomic_bytes(args.rows_output, scores.to_parquet(index=False))
    report['output_sha256'] = {str(args.rows_output.resolve().relative_to(ROOT)): sha256_file(args.rows_output)}
    write_json(args.output, report, pretty=True)
    print(f"pooled {len(scores)} decisions, paired Brier change {pooled['brier']['change']:.6f}; "
          f"diagnostic screen passed: {report['diagnostic_screen_pass']}", flush=True)


if __name__ == '__main__':
    main()
