#!/usr/bin/env python3
"""Screen the isolated rim-expression candidate on one guarded historical fold."""
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
from scripts import a1_compare, a1_minutes_fold_eval, a1_rim_calibration, compare, nodes, train  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS, TEST_FROM  # noqa: E402


def training_tail_masks(dates: np.ndarray, cutoff: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, str]:
    values = np.asarray(dates)
    if values.ndim != 1:
        raise ValueError('training dates must be a one-dimensional array')
    parsed = pd.to_datetime(pd.Series(values), errors='raise')
    if parsed.isna().any():
        raise ValueError('training dates cannot be missing')
    all_train = (values >= train.BURN_IN) & (values <= cutoff)
    if not all_train.any():
        raise ValueError('the training window is empty')
    integer_dates = parsed.astype('int64').to_numpy()
    tail_threshold = np.quantile(integer_dates[all_train], 0.9)
    tail = all_train & (integer_dates >= tail_threshold)
    return all_train, tail, all_train & ~tail, str(parsed[tail].min().date())


def summary(rows: pd.DataFrame) -> dict:
    if rows.empty:
        return {'observations': 0, 'games': 0, 'status': 'insufficient_sample'}
    base = rows['control_loss'].to_numpy(dtype=float)
    candidate = rows['candidate_loss'].to_numpy(dtype=float)
    games = rows['game_id'].to_numpy()
    delta, se, _ = compare.paired(base, candidate, games)
    grouped = rows.assign(delta=candidate - base).groupby('game_id')['delta'].agg(['sum', 'size'])
    enough = len(grouped) >= a1_compare.MIN_GAMES
    interval = None
    if enough:
        count = len(grouped)
        draws = np.random.default_rng(a1_compare.BOOTSTRAP_SEED).integers(
            0, count, (a1_compare.BOOTSTRAP_REPLICATES, count))
        sums = grouped['sum'].to_numpy()[draws].sum(axis=1)
        sizes = grouped['size'].to_numpy()[draws].sum(axis=1)
        interval = [float(v) for v in np.quantile(sums / sizes, [0.025, 0.975])]
    actual = rows['made'].to_numpy(dtype=float)
    control = rows['control_make'].to_numpy(dtype=float)
    adjusted = rows['candidate_make'].to_numpy(dtype=float)
    return {'observations': len(rows), 'games': len(grouped), 'status': 'ok' if enough else 'insufficient_sample',
            'control_log_loss': float(base.mean()), 'candidate_log_loss': float(candidate.mean()),
            'log_loss_delta': delta, 'game_cluster_se': se, 'z': float(delta / se) if se > 0 else None,
            'game_cluster_bootstrap_ci_95': interval,
            'actual_make': float(actual.mean()), 'control_make': float(control.mean()),
            'candidate_make': float(adjusted.mean()),
            'control_brier': float(np.mean((control - actual) ** 2)),
            'candidate_brier': float(np.mean((adjusted - actual) ** 2))}


def population_report(rows: pd.DataFrame, cuts: np.ndarray) -> dict:
    rim = rows.loc[rows['zone'].eq('rim')].copy()
    known = rim['matchup'].notna()
    matchup_bins = np.select([~known, rim['matchup'].le(cuts[0]), rim['matchup'].le(cuts[1]),
                              rim['matchup'].le(cuts[2])], ['unknown', 'Q1', 'Q2', 'Q3'], default='Q4')
    effective = rim['shooter_effective']
    reliability = np.select([effective.isna(), effective.lt(250), effective.le(750)],
                            ['unknown', '<250', '250–750'], default='>750')
    return {'all_shots': summary(rows), 'rim': summary(rim),
            'rim_matchup_training_quartiles': {name: summary(rim.loc[matchup_bins == name])
                                               for name in ('Q1', 'Q2', 'Q3', 'Q4', 'unknown')},
            'rim_shooter_reliability': {name: summary(rim.loc[reliability == name])
                                        for name in ('<250', '250–750', '>750', 'unknown')}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fold', choices=list(FOLDS), required=True)
    parser.add_argument('--threads', type=int, default=8)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--rows-output', type=Path, required=True)
    parser.add_argument('--model-output', type=Path, required=True)
    parser.add_argument('--reuse-model-dir', type=Path, help='reuse an independently audited fold-model directory')
    args = parser.parse_args()
    if args.threads < 1:
        raise ValueError('threads must be positive')
    if any(path.exists() for path in (args.output, args.rows_output, args.model_output)):
        raise FileExistsError('refusing to overwrite an existing rim-screen output or model')
    if len({path.resolve() for path in (args.output, args.rows_output, args.model_output)}) != 3:
        raise ValueError('report, rows and model outputs must be distinct')
    if not args.rows_output.resolve().is_relative_to((DERIVED / 'experiments').resolve()):
        raise ValueError('per-row predictions must remain under ignored data/derived/experiments')
    if not args.model_output.resolve().is_relative_to((ROOT / 'data/models').resolve()):
        raise ValueError('fitted candidate models must remain under ignored data/models')
    if Path.cwd().resolve() != ROOT:
        raise ValueError('run the fold screen from the repository root to preserve cached input signatures')

    started = time.monotonic()
    fold = args.fold
    cutoff, validation_from, validation_to = FOLDS[fold]
    feature_dir = Path(f'data/derived/variants/a1_scheduled_{fold}_20261122_v3/features')
    feature_path, feature_report = feature_dir / 'pregame.parquet', feature_dir / 'features_report.json'
    feature_meta = json.loads(feature_report.read_text())
    schedule = Path(f'data/derived/variants/a1_assignment_schedule_20261122_v3/{fold}.json')
    if (feature_meta.get('matchup') != str(schedule) or
            not all(feature_meta.get(k) is True for k in ('history_only', 'causal_first_priors', 'causal_positions'))):
        raise ValueError('fold features do not identify the guarded, dated assignment and causal settings')
    config_path = ROOT / 'models/v1.3.json'
    config = json.loads(config_path.read_text())
    settings = {**config['default'], **config['nodes']['shot_result'], 'seed': 7, 'threads': args.threads,
                'features': str(feature_path)}
    print(f'{fold}: loading/building guarded shot-result cache', flush=True)
    data = next(nodes.datasets(['shot_result'], pregame=feature_path))
    cache = nodes.cache_dir(feature_path)
    if json.loads((cache / 'signature.json').read_text()) != nodes.signature(feature_path):
        raise ValueError('shot node cache signature differs from its guarded inputs')
    if data['kind'] != 'multiclass' or data['classes'] != 3:
        raise ValueError('shot-result cache is not the expected three-class node')
    dates = data['date']
    if (dates >= TEST_FROM).any():
        raise ValueError('protected final-season rows entered the node cache')
    all_train, tail, fit_rows, tail_from = training_tail_masks(dates, cutoff)
    validation = (dates >= validation_from) & (dates <= validation_to)
    if not all_train.any() or not validation.any():
        raise ValueError(f'{fold}: empty training or validation set')
    reuse_paths = []
    model_bytes = None
    if args.reuse_model_dir:
        model_dir = args.reuse_model_dir
        meta_path, saved_config_path, model_path = (model_dir / name for name in ('meta.json', 'config.json', 'shot_result.txt'))
        meta, saved_config = json.loads(meta_path.read_text()), json.loads(saved_config_path.read_text())
        key = json.loads(meta['key'])
        saved_settings = {**key['spec']['default'], **key['spec']['nodes']['shot_result']}
        fields = ('features', 'segments', 'half_life', 'playoff_weight', 'drop', 'banded', 'recalibrate')
        if (key['signature'] != nodes.signature(feature_path) or key['training_code_sha256'] != sha256_file(Path(train.__file__))
                or saved_config.get('train_through') != cutoff
                or any(saved_settings.get(name) != settings.get(name) for name in fields)):
            raise ValueError('saved fold model provenance or training recipe differs from this guarded screen')
        if fold != 'F4':
            raise ValueError('only the independently accounted guarded F4 model is eligible for reuse')
        audit_path = EXPERIMENTS / '20261122_a1_s02_wiring_accounting_guarded.json'
        audited = json.loads(audit_path.read_text())['input_fingerprints']
        model_name = str(model_path.resolve().relative_to(ROOT))
        hashes = [entry['sha256'] for entry in audited if entry['path'] == model_name]
        if len(hashes) != 1 or hashes[0] != sha256_file(model_path):
            raise ValueError('saved F4 shot model does not match its independently audited fingerprint')
        columns = meta['fitted']['shot_result']['columns']
        if meta['fitted']['shot_result']['intercepts'] is not None:
            raise ValueError('reused shot model unexpectedly has fitted intercepts')
        model = lgb.Booster(model_file=str(model_path))
        node_report = meta['metrics']['shot_result']
        model_bytes = model_path.read_bytes()
        reuse_paths = [meta_path, saved_config_path, model_path, audit_path]
        print(f'{fold}: reusing independently audited guarded shot model; '
              f'{int(tail.sum()):,} training-tail rows', flush=True)
    else:
        print(f'{fold}: fitting baseline node on {int(fit_rows.sum()):,} earlier rows; '
              f'{int(tail.sum()):,} training-tail rows', flush=True)
        node_report, _, fitted = train.run_node(data, fold, FOLDS[fold], settings)
        model = fitted['model']
        columns = fitted['columns']
    if model.feature_name() != columns:
        raise ValueError('fitted shot node feature order differs from metadata')
    X = train.band_distances(data['X'][columns], fit_rows) if settings['banded'] else data['X'][columns]
    tail_probabilities = model.predict(X[tail], num_iteration=model.best_iteration, num_threads=args.threads)
    if not isinstance(tail_probabilities, np.ndarray):
        raise TypeError('shot node returned non-array training probabilities')
    calibration = a1_rim_calibration.fit(tail_probabilities, data['X']['mu_fg_shot'].to_numpy()[tail],
                                         data['zone'][tail], data['y'][tail], dates[tail], cutoff)
    print(f'{fold}: calibration fitted on {calibration["known_rim_rows"]:,} known rim shots; '
          f'scoring {int(validation.sum()):,} held-out shots', flush=True)
    control = model.predict(X[validation], num_iteration=model.best_iteration, num_threads=args.threads)
    if not isinstance(control, np.ndarray):
        raise TypeError('shot node returned non-array held-out probabilities')
    matchup = data['X']['mu_fg_shot'].to_numpy()[validation]
    zone = data['zone'][validation]
    candidate = a1_rim_calibration.apply(control, matchup, zone, calibration)
    if not np.array_equal(control[zone != 'rim'], candidate[zone != 'rim']):
        raise ValueError('rim-only candidate changed a non-rim shot')
    y = data['y'][validation].astype(int)
    n = len(y)
    control_loss = -np.log(control[np.arange(n), y])
    candidate_loss = -np.log(candidate[np.arange(n), y])
    if not np.isfinite(control_loss).all() or not np.isfinite(candidate_loss).all():
        raise ValueError('held-out shot loss is not finite')
    rows = pd.DataFrame({'game_id': data['game'][validation], 'date_et': dates[validation], 'zone': zone,
                         'outcome': y, 'made': (y != 0).astype(float), 'matchup': matchup,
                         'shooter_effective': data['X']['actor_shots_eff'].to_numpy()[validation],
                         'control_make': control[:, 1:].sum(axis=1), 'candidate_make': candidate[:, 1:].sum(axis=1),
                         'control_loss': control_loss, 'candidate_loss': candidate_loss})
    manifest = json.loads(a1_minutes_fold_eval.PREREG.read_text())
    fixed_games = a1_minutes_fold_eval.fold_games(manifest, fold)
    fixed_ids = set(fixed_games['game_id'])
    fixed = rows.loc[rows['game_id'].isin(fixed_ids)]
    if set(fixed['game_id']) != fixed_ids:
        raise ValueError(f'{fold}: fixed 200-game set differs from node validation rows')
    tail_values = data['X']['mu_fg_shot'].to_numpy()[tail]
    tail_zones = data['zone'][tail]
    cuts = np.quantile(tail_values[(tail_zones == 'rim') & np.isfinite(tail_values)], [0.25, 0.5, 0.75])
    reports = {'complete_validation': population_report(rows, cuts),
               'fixed_200_games': population_report(fixed, cuts)}
    paths = [config_path, a1_minutes_fold_eval.PREREG, feature_path, feature_report, schedule,
             cache / 'signature.json', cache / 'shot_result.npz', Path(__file__),
             Path(a1_rim_calibration.__file__), Path(train.__file__), Path(nodes.__file__), *reuse_paths]
    atomic_bytes(args.model_output, model_bytes if model_bytes is not None else model.model_to_string().encode())
    atomic_bytes(args.rows_output, rows.to_parquet(index=False))
    report = {'experiment': 'a1_s04_rim_expression_guarded_fold_screen', 'fold': fold,
              'method': 'Paired existing v1.3 shot-node recipe with/without a training-tail-fitted, '
                        'mean-preserving rim matchup log-odds response on guarded dated-assignment inputs.',
              'limitations': 'These corrected historical inputs differ from the accepted v1.3 static-input control; '
                             'actual shots and zones are teacher-forced. This is not a forecast or promotion.',
              'training_cutoff': cutoff, 'validation_from': validation_from, 'validation_to': validation_to,
              'training_tail_from': tail_from, 'settings': settings,
              'training_node': node_report, 'calibration': calibration,
              'training_rim_quartile_cutpoints': [float(v) for v in cuts], 'populations': reports,
              'baseline_model_reused': bool(args.reuse_model_dir),
              'input_sha256': {str(p.resolve().relative_to(ROOT)): sha256_file(p) for p in paths},
              'model_sha256': sha256_file(args.model_output), 'rows_sha256': sha256_file(args.rows_output),
              'elapsed_seconds': round(time.monotonic() - started, 1)}
    write_json(args.output, report, pretty=True)
    print(f'{fold}: saved {len(rows):,} held-out shots and report {args.output} in '
          f'{report["elapsed_seconds"]:.1f}s', flush=True)


if __name__ == '__main__':
    main()
