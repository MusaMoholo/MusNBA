#!/usr/bin/env python3
"""Independently reproduce pooled player intervals by resampling complete games."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, sha256_file, write_json  # noqa: E402
from scripts import a1_compare, a1_minutes_gate  # noqa: E402


def audit_players(control: pd.DataFrame, candidate: pd.DataFrame, report: dict) -> dict:
    keys = ['game_id', 'player']
    for label, frame in (('control', control), ('candidate', candidate)):
        if frame[keys].isna().any().any() or frame.duplicated(keys).any():
            raise ValueError(f'{label} player-game keys are missing or duplicated')
    rows = control.merge(candidate, on=keys, suffixes=('_control', '_candidate'),
                         how='outer', validate='one_to_one', indicator=True)
    if rows['_merge'].ne('both').any() or len(rows) != report['population']['player_games']:
        raise ValueError('player-game populations do not match the paired report')
    ids = report['population']['game_ids']
    if not ids or ids != sorted(set(ids)) or set(rows['game_id']) != set(ids):
        raise ValueError('paired report and player rows do not share the same unique games')
    method = report['method']
    if (method['replicates'], method['seed']) != (a1_compare.BOOTSTRAP_REPLICATES, a1_compare.BOOTSTRAP_SEED):
        raise ValueError('paired bootstrap settings differ from the frozen contract')
    samples = np.random.default_rng(method['seed']).integers(0, len(ids), (method['replicates'], len(ids)))
    bounds = []
    max_error = 0.0
    for stat in a1_compare.STATS:
        actual = rows[f'{stat}_actual_control'].to_numpy(dtype=float)
        other_actual = rows[f'{stat}_actual_candidate'].to_numpy(dtype=float)
        if np.isinf(actual).any() or not np.allclose(actual, other_actual, rtol=0, atol=1e-12, equal_nan=True):
            raise ValueError(f'{stat}: actual outcomes do not match')
        known = np.isfinite(actual)
        part = rows.loc[known, ['game_id']].copy()
        if part.empty:
            raise ValueError(f'{stat}: no known actual outcomes')
        part['n'] = 1
        for side in ('control', 'candidate'):
            crps = rows.loc[known, f'{stat}_crps_{side}'].to_numpy(dtype=float)
            predicted = rows.loc[known, f'{stat}_sim_{side}'].to_numpy(dtype=float)
            pit = rows.loc[known, f'{stat}_pit_{side}'].to_numpy(dtype=float)
            if (not np.isfinite(crps).all() or (crps < -1e-9).any() or not np.isfinite(predicted).all()
                    or not np.isfinite(pit).all() or ((pit < 0) | (pit > 1)).any()):
                raise ValueError(f'{stat}: invalid {side} prediction, CRPS or PIT')
            part[f'crps_{side}'] = crps
            part[f'bias_{side}'] = predicted - actual[known]
            part[f'coverage_{side}'] = ((pit >= 0.1) & (pit <= 0.9)).astype(int)
        grouped = part.groupby('game_id').sum().reindex(ids, fill_value=0)
        denominator = grouped['n'].to_numpy()[samples].sum(axis=1)
        if (denominator == 0).any():
            raise ValueError(f'{stat}: bootstrap contains an empty sample')
        saved = report['players']['all'][stat]
        if saved['status'] != 'ok' or saved['observations'] != len(part):
            raise ValueError(f'{stat}: paired report has unsupported or mismatched observations')
        for metric, target in (('crps', None), ('bias', 0.0), ('coverage', 0.8)):
            values, bootstrap = {}, {}
            for side in ('control', 'candidate'):
                data = grouped[f'{metric}_{side}'].to_numpy(dtype=float)
                values[side] = float(data.sum() / len(part))
                bootstrap[side] = data[samples].sum(axis=1) / denominator
            if target is None:
                change = values['candidate'] - values['control']
                sampled_change = bootstrap['candidate'] - bootstrap['control']
            else:
                change = abs(values['candidate'] - target) - abs(values['control'] - target)
                sampled_change = np.abs(bootstrap['candidate'] - target) - np.abs(bootstrap['control'] - target)
            ci = np.quantile(sampled_change, [0.025, 0.975])
            expected = saved[metric]
            if expected.get('ci_95') is None or len(expected['ci_95']) != 2:
                raise ValueError(f'{stat} {metric}: paired report has no two-sided interval')
            check = np.array([values['control'], values['candidate'], change, *ci])
            reference = np.array([expected['control'], expected['candidate'], expected['change'], *expected['ci_95']])
            if not np.isfinite(reference).all():
                raise ValueError(f'{stat} {metric}: paired report contains invalid values')
            error = float(np.max(np.abs(check - reference)))
            max_error = max(max_error, error)
            if error > 1e-10:
                raise ValueError(f'{stat} {metric}: independent bootstrap differs by {error}')
            if metric != 'crps':
                bound = a1_minutes_gate.PLAYER_BIAS[stat] if metric == 'bias' else 0.03
                bounds.append({'stat': stat, 'metric': metric, 'bound': bound,
                               'change': float(change), 'ci_95': ci.tolist(), 'established': bool(ci[1] < bound)})
    return {'experiment': 'a1_pooled_player_bootstrap_accounting', 'runs': report['runs'],
            'games': len(ids), 'player_games': len(rows), 'metrics_checked': 3 * len(a1_compare.STATS),
            'max_absolute_difference': max_error,
            'pooled_bias_coverage': {'checks': len(bounds), 'established': sum(row['established'] for row in bounds),
                                     'bounds': bounds},
            'method': 'Directly sample game indices with replacement, independently of the paired report’s '
                      'game-weight multiplication; retain all player rows and weight player-games equally.',
            'limitations': 'Uncorrected 95% accounting and non-inferiority screens; not a promotion decision.'}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('comparison', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f'refusing to overwrite {args.output}')
    report = json.loads(args.comparison.read_text())
    paths = [DERIVED / 'experiments' / f"{report['runs'][side]}_players.parquet" for side in ('control', 'candidate')]
    control, candidate = (pd.read_parquet(path) for path in paths)
    result = audit_players(control, candidate, report)
    inputs = [path.resolve() for path in
              (args.comparison, *paths, Path(__file__), Path(a1_compare.__file__), Path(a1_minutes_gate.__file__))]
    if any(not path.is_relative_to(ROOT) for path in inputs):
        raise ValueError('audit inputs must be inside the repository')
    result['input_sha256'] = {str(path.relative_to(ROOT)): sha256_file(path) for path in inputs}
    write_json(args.output, result, pretty=True)
    print(f"checked {result['metrics_checked']} pooled metrics on {result['games']} games; "
          f"pooled bounds {result['pooled_bias_coverage']['established']}/{result['pooled_bias_coverage']['checks']}")


if __name__ == '__main__':
    main()
