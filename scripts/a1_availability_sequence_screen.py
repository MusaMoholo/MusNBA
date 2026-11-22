#!/usr/bin/env python3
"""Screen frozen, censored recorded-DNP return and rest play proxies."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, atomic_bytes, sha256_file, write_json  # noqa: E402
from scripts import a1_compare, a1_flow_compare  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS, TEST_FROM  # noqa: E402

MANIFEST = EXPERIMENTS / '20261122_a1_pre_candidate_manifest.json'
SEQUENCES = DERIVED / 'experiments/20261122_a1_s07_sequences.parquet'
SEQUENCE_REPORT = EXPERIMENTS / '20261122_a1_s07_sequences.json'
SEQUENCE_AUDIT = EXPERIMENTS / '20261122_a1_s07_sequences_accounting_v2.json'


def choose_population(rows: pd.DataFrame, fold: str, cohort: str,
                      game_ids: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    if fold not in FOLDS or cohort not in ('return', 'rest'):
        raise ValueError('unsupported fold or sequence population')
    train_end, first, last = FOLDS[fold]
    known = rows.loc[rows['cohort'].eq(cohort) & rows['outcome'].notna()].copy()
    if not known['outcome'].isin([0, 1]).all():
        raise ValueError('known sequence outcomes must be binary')
    if known[['game_id', 'date_et', 'prior_day']].isna().any().any():
        raise ValueError('known sequence outcomes need game, prior and target dates')
    if known['prior_day'].ge(known['date_et']).any() or known['date_et'].ge(TEST_FROM).any():
        raise ValueError('sequence features or outcomes violate the date cutoff')
    train = known.loc[known['date_et'].le(train_end)].copy()
    valid = known.loc[known['date_et'].between(first, last) & known['game_id'].isin(game_ids)].copy()
    if train.empty:
        raise ValueError(f'{fold} {cohort}: no earlier training observations')
    if set(train['game_id']) & set(game_ids) or train['date_et'].ge(first).any():
        raise ValueError(f'{fold} {cohort}: training overlaps validation or its cutoff')
    if valid.duplicated(['game_id', 'team', 'player']).any():
        raise ValueError(f'{fold} {cohort}: duplicate validation player-game')
    return train, valid


def probabilities(train: pd.DataFrame, valid: pd.DataFrame, keys: list[str]) -> tuple[np.ndarray, np.ndarray]:
    if not train['outcome'].isin([0, 1]).all():
        raise ValueError('training outcome must be binary')
    if keys and (train[keys].isna().any().any() or valid[keys].isna().any().any()):
        raise ValueError('a prespecified grouping feature is missing')
    if keys:
        groups = train.groupby(keys, dropna=False)['outcome'].agg(['sum', 'count']).reset_index()
        joined = valid[keys].merge(groups, on=keys, how='left', validate='many_to_one', sort=False)
        successes = joined['sum'].fillna(0).to_numpy(dtype=float)
        count = joined['count'].fillna(0).to_numpy(dtype=int)
    else:
        successes = np.full(len(valid), float(train['outcome'].sum()))
        count = np.full(len(valid), len(train), dtype=int)
    p = (successes + 1) / (count + 2)
    if not np.isfinite(p).all() or ((p <= 0) | (p >= 1)).any():
        raise ValueError('smoothed prediction is not strictly between zero and one')
    return p, count


def summaries(rows: pd.DataFrame, ids: list[str], weights: np.ndarray) -> dict:
    if rows.empty:
        return {'observations': 0, 'games': 0, 'status': 'insufficient_sample', 'metrics': {}}
    out = rows.copy()
    y = out['outcome'].to_numpy(dtype=float)
    for label in ('baseline', 'candidate'):
        p = out[label].to_numpy(dtype=float)
        out[f'{label}_brier'] = (p - y) ** 2
        out[f'{label}_log_loss'] = -np.log(np.where(y == 1, p, 1 - p))
    out['brier_change'] = out['candidate_brier'] - out['baseline_brier']
    out['log_loss_change'] = out['candidate_log_loss'] - out['baseline_log_loss']
    names = ['baseline_brier', 'candidate_brier', 'brier_change',
             'baseline_log_loss', 'candidate_log_loss', 'log_loss_change']
    metrics = a1_flow_compare.mean_report(out, names, ids, weights, player=True)
    return {
        'observations': len(out), 'games': int(out['game_id'].nunique()),
        'status': metrics['brier_change']['status'], 'metrics': metrics,
        'baseline_unseen_group_observations': int(out['baseline_train_count'].eq(0).sum()),
        'candidate_unseen_group_observations': int(out['candidate_train_count'].eq(0).sum()),
    }


def calibration(rows: pd.DataFrame, name: str) -> list[dict]:
    p = rows[name].to_numpy(dtype=float)
    y = rows['outcome'].to_numpy(dtype=float)
    bins = np.minimum((p * 5).astype(int), 4)
    cells = []
    for index in range(5):
        selected = bins == index
        subset = rows.loc[selected]
        cells.append({
            'lower': index / 5, 'upper': (index + 1) / 5,
            'observations': int(selected.sum()), 'games': int(subset['game_id'].nunique()),
            'mean_prediction': float(p[selected].mean()) if selected.any() else None,
            'observed_rate': float(y[selected].mean()) if selected.any() else None,
        })
    return cells


def fold_screen(rows: pd.DataFrame, fold: str, manifest: dict) -> tuple[dict, pd.DataFrame]:
    selection = manifest['control']['games'] if fold == 'F4' else manifest['confirmation'][fold]['games']
    game_dates = pd.DataFrame(selection)[['game_id', 'date_et']]
    if (len(game_dates) != 200 or game_dates['game_id'].duplicated().any()
            or not game_dates['date_et'].between(FOLDS[fold][1], FOLDS[fold][2]).all()):
        raise ValueError(f'{fold}: fixed validation game/date population differs')
    ids = sorted(game_dates['game_id'].tolist())
    draws = np.random.default_rng(a1_compare.BOOTSTRAP_SEED).integers(
        0, len(ids), (a1_compare.BOOTSTRAP_REPLICATES, len(ids)))
    weights = np.zeros(draws.shape, dtype=np.int16)
    np.add.at(weights, (np.arange(len(draws))[:, None], draws), 1)
    populations = {}
    predictions = []
    for cohort, baseline_keys, candidate_keys in (
            ('return', ['prior_reason'], ['prior_reason', 'duration_bin']),
            ('rest', [], ['prior_role'])):
        train, valid = choose_population(rows, fold, cohort, ids)
        if not valid.empty:
            dates = valid[['game_id', 'date_et']].drop_duplicates().merge(
                game_dates, on=['game_id', 'date_et'], how='left', indicator=True, validate='many_to_one')
            if dates['_merge'].ne('both').any():
                raise ValueError(f'{fold} {cohort}: validation game date differs from the fixed manifest')
        valid['baseline'], valid['baseline_train_count'] = probabilities(train, valid, baseline_keys)
        valid['candidate'], valid['candidate_train_count'] = probabilities(train, valid, candidate_keys)
        valid['fold'] = fold
        main = summaries(valid, ids, weights)
        groups = {}
        for field in ('prior_role', 'prior_reason') if cohort == 'return' else ('prior_role',):
            for value, part in valid.groupby(field, dropna=False, sort=True):
                groups[f'{field}:{value}'] = summaries(part, ids, weights)
        populations[cohort] = {
            'training_observations': len(train), 'training_games': int(train['game_id'].nunique()),
            'training_last_outcome_date': str(train['date_et'].max()),
            'validation': main, 'subgroups': groups,
            'calibration': {name: calibration(valid, name) for name in ('baseline', 'candidate')},
        }
        predictions.append(valid[['fold', 'cohort', 'game_id', 'date_et', 'team', 'player',
                                  'prior_game_id', 'prior_day', 'prior_role', 'prior_reason',
                                  'duration_bin', 'outcome', 'baseline', 'candidate',
                                  'baseline_train_count', 'candidate_train_count']])
    return {'fold': fold, 'training_through': FOLDS[fold][0], 'validation_from': FOLDS[fold][1],
            'validation_through': FOLDS[fold][2], 'fixed_games': len(ids), 'populations': populations}, \
        pd.concat(predictions, ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--rows-output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.rows_output.exists() or args.output.resolve() == args.rows_output.resolve():
        raise FileExistsError('screen output paths must be distinct and new')
    sequence_report = json.loads(SEQUENCE_REPORT.read_text())
    sequence_audit = json.loads(SEQUENCE_AUDIT.read_text())
    for report in (sequence_report, sequence_audit):
        for section in ('input_sha256', 'output_sha256'):
            for path, digest in report.get(section, {}).items():
                if sha256_file(ROOT / path) != digest:
                    raise ValueError(f'audited sequence input differs: {path}')
    rows = pd.read_parquet(SEQUENCES)
    if len(rows) != sequence_report['rows'] or len(rows) != sequence_audit['rows_checked']:
        raise ValueError('sequence population differs from its independent accounting')
    manifest = json.loads(MANIFEST.read_text())
    reports, predictions = [], []
    for fold in FOLDS:
        result, predicted = fold_screen(rows, fold, manifest)
        reports.append(result)
        predictions.append(predicted)
        print(f"{fold}: {len(predicted)} known-outcome exposures scored", flush=True)
    all_predictions = pd.concat(predictions, ignore_index=True)
    atomic_bytes(args.rows_output, all_predictions.to_parquet(index=False))
    paths = [Path(__file__), SEQUENCES, SEQUENCE_REPORT, SEQUENCE_AUDIT, MANIFEST,
             ROOT / 'scripts/a1_compare.py', ROOT / 'scripts/a1_flow_compare.py', ROOT / 'scripts/evaluate.py']
    result = {
        'experiment': 'a1_s07_recorded_dnp_return_and_rest_proxy_screen',
        'folds': reports, 'predicted_rows': len(all_predictions),
        'bootstrap': {'replicates': a1_compare.BOOTSTRAP_REPLICATES, 'seed': a1_compare.BOOTSTRAP_SEED,
                      'unit': 'complete game ID', 'minimum_player_games': a1_compare.MIN_PLAYER_GAMES,
                      'minimum_games': a1_compare.MIN_GAMES},
        'limitations': 'Conditional on a known next listed box outcome after a known prior listing; unlisted games, '
                       'team changes, ambiguous labels, season ends and left-censored returns are excluded. '
                       'Retrospective reason text lacks publication timestamps and is not physical recovery, '
                       'pre-tip availability, a future roster model or a deployable season-absence hazard.',
        'input_sha256': {str(p.relative_to(ROOT)): sha256_file(p) for p in paths},
        'output_sha256': {str(args.rows_output.resolve().relative_to(ROOT)): sha256_file(args.rows_output)},
    }
    write_json(args.output, result, pretty=True)
    print(f'saved {len(all_predictions)} predictions across four development folds', flush=True)


if __name__ == '__main__':
    main()
