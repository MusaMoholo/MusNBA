#!/usr/bin/env python3
"""Independently verify the frozen recorded-DNP return/rest proxy screen."""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, sha256_file, write_json  # noqa: E402
from scripts.a1_availability_baseline_audit import check_mean, check_number  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS, TEST_FROM  # noqa: E402

REPORT = EXPERIMENTS / '20261122_a1_s07_sequence_screen.json'
PREDICTIONS = DERIVED / 'experiments/20261122_a1_s07_sequence_screen.parquet'
SEQUENCES = DERIVED / 'experiments/20261122_a1_s07_sequences.parquet'
MANIFEST = EXPERIMENTS / '20261122_a1_pre_candidate_manifest.json'
REPLICATES, SEED = 10_000, 20261122


def independent_probabilities(train: pd.DataFrame, valid: pd.DataFrame,
                              fields: list[str]) -> tuple[np.ndarray, np.ndarray]:
    totals: dict[tuple, list[float]] = defaultdict(lambda: [0., 0.])
    for row in train.to_dict('records'):
        key = tuple(row[field] for field in fields)
        totals[key][0] += float(row['outcome'])
        totals[key][1] += 1
    probs, counts = [], []
    for row in valid.to_dict('records'):
        key = tuple(row[field] for field in fields)
        successes, count = totals[key]
        probs.append((successes + 1) / (count + 2))
        counts.append(int(count))
    return np.asarray(probs), np.asarray(counts)


def check_summary(summary: dict, rows: pd.DataFrame, ids: list[str], draws: np.ndarray) -> None:
    games = int(rows['game_id'].nunique())
    if not len(rows):
        if summary != {'observations': 0, 'games': 0, 'status': 'insufficient_sample', 'metrics': {}}:
            raise ValueError('empty population summary differs')
        return
    expected_status = 'ok' if len(rows) >= 100 and games >= 30 else 'insufficient_sample'
    if (summary['observations'], summary['games'], summary['status']) != (len(rows), games, expected_status):
        raise ValueError('population size or support status differs')
    if (summary['baseline_unseen_group_observations'] != int(rows['baseline_train_count'].eq(0).sum())
            or summary['candidate_unseen_group_observations'] != int(rows['candidate_train_count'].eq(0).sum())):
        raise ValueError('unseen training-group counts differ')
    scored = rows.copy()
    y = scored['outcome'].to_numpy(dtype=float)
    for label in ('baseline', 'candidate'):
        p = scored[label].to_numpy(dtype=float)
        if not np.isfinite(p).all() or ((p <= 0) | (p >= 1)).any():
            raise ValueError('smoothed prediction is invalid')
        scored[f'{label}_brier'] = (p - y) ** 2
        scored[f'{label}_log_loss'] = -np.log(np.where(y == 1, p, 1 - p))
    for metric in ('brier', 'log_loss'):
        scored[f'{metric}_change'] = scored[f'candidate_{metric}'] - scored[f'baseline_{metric}']
    for name in ('baseline_brier', 'candidate_brier', 'brier_change',
                 'baseline_log_loss', 'candidate_log_loss', 'log_loss_change'):
        check_mean(summary['metrics'][name], scored, name, ids, draws, player=True)


def check_calibration(cells: list[dict], rows: pd.DataFrame, name: str) -> None:
    if len(cells) != 5:
        raise ValueError('expected five fixed calibration cells')
    p = rows[name].to_numpy(dtype=float)
    y = rows['outcome'].to_numpy(dtype=float)
    bins = np.minimum((p * 5).astype(int), 4)
    for index, cell in enumerate(cells):
        mask = bins == index
        if (cell['lower'], cell['upper'], cell['observations'], cell['games']) != (
                index / 5, (index + 1) / 5, int(mask.sum()), rows.loc[mask, 'game_id'].nunique()):
            raise ValueError(f'{name} calibration cell {index} coverage differs')
        check_number(cell['mean_prediction'], float(p[mask].mean()) if mask.any() else None,
                     f'{name} calibration prediction')
        check_number(cell['observed_rate'], float(y[mask].mean()) if mask.any() else None,
                     f'{name} calibration outcome')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f'refusing to overwrite {args.output}')
    report = json.loads(REPORT.read_text())
    for section in ('input_sha256', 'output_sha256'):
        for path, digest in report[section].items():
            if sha256_file(ROOT / path) != digest:
                raise ValueError(f'screen input or output fingerprint differs: {path}')
    rows, predicted = pd.read_parquet(SEQUENCES), pd.read_parquet(PREDICTIONS)
    if len(predicted) != report['predicted_rows'] or predicted.duplicated(
            ['fold', 'cohort', 'game_id', 'team', 'player']).any():
        raise ValueError('prediction count or keys differ')
    manifest = json.loads(MANIFEST.read_text())
    fold_reports = {entry['fold']: entry for entry in report['folds']}
    if set(fold_reports) != set(FOLDS):
        raise ValueError('screen fold set differs')
    checked = 0
    populations = []
    for fold, (train_end, first, last) in FOLDS.items():
        result = fold_reports[fold]
        if (result['training_through'], result['validation_from'], result['validation_through']) != (
                train_end, first, last):
            raise ValueError(f'{fold}: stored cutoff differs')
        source = manifest['control']['games'] if fold == 'F4' else manifest['confirmation'][fold]['games']
        game_dates = pd.DataFrame(source)[['game_id', 'date_et']]
        ids = sorted(game_dates['game_id'].tolist())
        if len(ids) != 200 or len(set(ids)) != 200 or not game_dates['date_et'].between(first, last).all():
            raise ValueError(f'{fold}: fixed validation games differ')
        draws = np.random.default_rng(SEED).integers(0, len(ids), (REPLICATES, len(ids)))
        for cohort, baseline_fields, candidate_fields in (
                ('return', ['prior_reason'], ['prior_reason', 'duration_bin']),
                ('rest', [], ['prior_role'])):
            known = rows.loc[rows['cohort'].eq(cohort) & rows['outcome'].notna()].copy()
            if (not known['outcome'].isin([0, 1]).all() or known['prior_day'].ge(known['date_et']).any()
                    or known['date_et'].ge(TEST_FROM).any()):
                raise ValueError(f'{fold} {cohort}: outcome or prior-date cutoff is invalid')
            train = known.loc[known['date_et'].le(train_end)]
            valid = known.loc[known['date_et'].between(first, last) & known['game_id'].isin(ids)]
            got = predicted.loc[predicted['fold'].eq(fold) & predicted['cohort'].eq(cohort)].copy()
            keys = ['game_id', 'team', 'player']
            fields = ['date_et', 'prior_game_id', 'prior_day', 'prior_role', 'prior_reason',
                      'duration_bin', 'outcome']
            joined = got.merge(valid[keys + fields], on=keys, how='outer', suffixes=('_saved', '_source'),
                               indicator=True, validate='one_to_one')
            if joined['_merge'].ne('both').any():
                raise ValueError(f'{fold} {cohort}: validation player-game keys differ')
            for field in fields:
                left, right = joined[f'{field}_saved'], joined[f'{field}_source']
                if not (left.eq(right) | (left.isna() & right.isna())).fillna(False).all():
                    raise ValueError(f'{fold} {cohort}: {field} differs from the audited sequence population')
            if set(train['game_id']) & set(ids) or train['date_et'].ge(first).any():
                raise ValueError(f'{fold} {cohort}: training contains validation or future games')
            summary = result['populations'][cohort]
            if (summary['training_observations'], summary['training_games'], summary['training_last_outcome_date']) != (
                    len(train), train['game_id'].nunique(), str(train['date_et'].max())):
                raise ValueError(f'{fold} {cohort}: earlier training coverage differs')
            for label, fields in (('baseline', baseline_fields), ('candidate', candidate_fields)):
                p, counts = independent_probabilities(train, got, fields)
                if (not np.allclose(p, got[label].to_numpy(dtype=float), rtol=0, atol=1e-12)
                        or not np.array_equal(counts, got[f'{label}_train_count'].to_numpy(dtype=int))):
                    raise ValueError(f'{fold} {cohort}: {label} probabilities or training counts differ')
            check_summary(summary['validation'], got, ids, draws)
            expected_groups = {}
            for field in ('prior_role', 'prior_reason') if cohort == 'return' else ('prior_role',):
                for value, part in got.groupby(field, dropna=False, sort=True):
                    expected_groups[f'{field}:{value}'] = part
            if set(expected_groups) != set(summary['subgroups']):
                raise ValueError(f'{fold} {cohort}: subgroup identities differ')
            for name, part in expected_groups.items():
                check_summary(summary['subgroups'][name], part, ids, draws)
            for name in ('baseline', 'candidate'):
                check_calibration(summary['calibration'][name], got, name)
            checked += len(got)
            populations.append({'fold': fold, 'cohort': cohort, 'training': len(train), 'validation': len(got)})
            print(f'{fold} {cohort}: checked {len(got)} predictions and bootstrap groups', flush=True)
    if checked != len(predicted):
        raise ValueError('not all saved predictions were checked')
    paths = [Path(__file__), ROOT / 'scripts/a1_availability_baseline_audit.py',
             REPORT, PREDICTIONS, SEQUENCES, MANIFEST]
    output = {
        'experiment': 'a1_s07_recorded_dnp_return_and_rest_proxy_screen_independent_audit',
        'predictions_checked': checked, 'bootstrap_replicates': REPLICATES, 'populations': populations,
        'limitations': 'Scores condition on known next box listings and retrospective reason text. They cannot '
                       'validate physical availability, recovery, or pre-tip report calibration.',
        'input_sha256': {str(p.relative_to(ROOT)): sha256_file(p) for p in paths},
    }
    write_json(args.output, output, pretty=True)
    print(f'independently checked {checked} predictions across eight fold/cohort populations', flush=True)


if __name__ == '__main__':
    main()
