#!/usr/bin/env python3
"""Reconcile the descriptive S04 interaction against both original prediction rows."""
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
from scripts import a1_minutes_fold_eval, a1_rim_audit, compare  # noqa: E402
from scripts.evaluate import EXPERIMENTS  # noqa: E402


def interaction_check(rows: pd.DataFrame, report: dict, label: str) -> None:
    if len(rows) != report['observations'] or rows['game_id'].nunique() != report['games']:
        raise ValueError(f'{label}: interaction population differs')
    if rows.empty:
        return
    cross = rows['candidate_loss'] - rows['rim_loss'] - rows['tracking_loss'] + rows['control_loss']
    mean, se, _ = compare.paired(np.zeros(len(rows)), cross.to_numpy(), rows['game_id'].to_numpy())
    a1_rim_audit.equal(report['mean'], mean, f'{label} interaction mean')
    a1_rim_audit.equal(report['game_cluster_se'], se, f'{label} interaction se')
    groups = pd.DataFrame({'game_id': rows['game_id'], 'cross': cross}).groupby('game_id')['cross'].agg(['sum', 'size'])
    if len(groups) >= 30:
        indices = np.random.default_rng(20261122).integers(0, len(groups), (10000, len(groups)))
        samples = groups['sum'].to_numpy()[indices].sum(axis=1) / groups['size'].to_numpy()[indices].sum(axis=1)
        a1_rim_audit.equal(report['game_cluster_bootstrap_ci_95'], np.quantile(samples, [0.025, 0.975]),
                           f'{label} interaction interval')
    elif report['game_cluster_bootstrap_ci_95'] is not None:
        raise ValueError(f'{label}: sparse interaction has an interval')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f'refusing to overwrite {args.output}')
    report_path = EXPERIMENTS / '20261122_a1_s04_defence_interactions.json'
    row_path = DERIVED / 'experiments/20261122_a1_s04_defence_interactions.parquet'
    report = json.loads(report_path.read_text())
    if sha256_file(row_path) != report['rows_sha256']:
        raise ValueError('interaction rows do not match report hash')
    for path, digest in report['input_sha256'].items():
        if sha256_file(ROOT / path) != digest:
            raise ValueError(f'interaction source changed: {path}')
    saved = pd.read_parquet(row_path)
    manifest = json.loads(a1_minutes_fold_eval.PREREG.read_text())
    counts = {}
    for fold in ('F1', 'F2', 'F3', 'F4'):
        rows = saved.loc[saved['fold'].eq(fold)].reset_index(drop=True)
        rim = pd.read_parquet(DERIVED / 'experiments' / f'20261122_a1_s04_rim_{fold}_v2.parquet')
        tracking = pd.read_parquet(DERIVED / 'experiments' / f'20261122_a1_s04_tracking_{fold}.parquet')
        if len(rows) != len(rim) or len(rows) != len(tracking):
            raise ValueError(f'{fold}: source row count differs')
        for column in ('game_id', 'zone', 'made'):
            if not np.array_equal(rows[column], rim[column]):
                raise ValueError(f'{fold}: source {column} differs')
        for name, value in (('control_loss', rim['control_loss']), ('rim_loss', rim['candidate_loss']),
                            ('tracking_loss', tracking['candidate_loss'])):
            a1_rim_audit.equal(rows[name], value, f'{fold} {name}')
        odds = lambda p: p / (1 - p)
        base = rim['control_make'].to_numpy(dtype=float)
        combined_odds = odds(rim['candidate_make'].to_numpy(dtype=float)) * odds(tracking['candidate_make'].to_numpy(dtype=float)) / odds(base)
        combined = combined_odds / (1 + combined_odds)
        a1_rim_audit.equal(rows['candidate_make'], combined, f'{fold} combined make')
        outcome = rim['made'].to_numpy(dtype=float)
        loss = np.where(outcome == 0, -np.log(1 - combined),
                        rim['control_loss'].to_numpy(dtype=float) - np.log(combined / base))
        a1_rim_audit.equal(rows['candidate_loss'], loss, f'{fold} combined loss')
        ids = set(a1_minutes_fold_eval.fold_games(manifest, fold)['game_id'])
        fixed = rows.loc[rows['game_id'].isin(ids)]
        if len(ids) != 200 or set(fixed['game_id']) != ids:
            raise ValueError(f'{fold}: fixed game IDs differ')
        for name, part in (('complete_validation', rows), ('fixed_200_games', fixed)):
            metrics = report['folds'][fold][name]
            a1_rim_audit.audit_metrics(part, metrics['combined'], f'{fold} {name} combined')
            interaction_check(part, metrics['interaction'], f'{fold} {name} all')
            interaction_check(part.loc[part['zone'].eq('rim')], metrics['rim_interaction'], f'{fold} {name} rim')
        counts[fold] = len(rows)
    result = {'experiment': 'a1_s04_defence_interaction_independent_accounting', 'fold_shots': counts,
              'report_sha256': sha256_file(report_path), 'rows_sha256': sha256_file(row_path),
              'auditor_sha256': sha256_file(Path(__file__))}
    write_json(args.output, result, pretty=True)
    print(json.dumps(result, indent=1), flush=True)


if __name__ == '__main__':
    main()
