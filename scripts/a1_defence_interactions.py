#!/usr/bin/env python3
"""Explore interaction of the already-rejected S04 rim and tracking adjustments."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, atomic_bytes, sha256_file, write_json  # noqa: E402
from scripts import a1_minutes_fold_eval, a1_rim_screen, compare  # noqa: E402
from scripts.evaluate import EXPERIMENTS  # noqa: E402


def interaction_summary(rows: pd.DataFrame) -> dict:
    if rows.empty:
        return {'observations': 0, 'games': 0}
    interaction = rows['candidate_loss'] - rows['rim_loss'] - rows['tracking_loss'] + rows['control_loss']
    delta, se, _ = compare.paired(np.zeros(len(rows)), interaction.to_numpy(), rows['game_id'].to_numpy())
    grouped = pd.DataFrame({'game_id': rows['game_id'], 'value': interaction}).groupby('game_id')['value'].agg(['sum', 'size'])
    interval = None
    if len(grouped) >= 30:
        indices = np.random.default_rng(20261122).integers(0, len(grouped), (10000, len(grouped)))
        samples = grouped['sum'].to_numpy()[indices].sum(axis=1) / grouped['size'].to_numpy()[indices].sum(axis=1)
        interval = [float(v) for v in np.quantile(samples, [0.025, 0.975])]
    return {'observations': len(rows), 'games': len(grouped), 'mean': delta, 'game_cluster_se': se,
            'game_cluster_bootstrap_ci_95': interval}


def fold_result(fold: str, manifest: dict) -> tuple[pd.DataFrame, dict, list[Path]]:
    rim_path = DERIVED / 'experiments' / f'20261122_a1_s04_rim_{fold}_v2.parquet'
    tracking_path = DERIVED / 'experiments' / f'20261122_a1_s04_tracking_{fold}.parquet'
    rim_report = EXPERIMENTS / f'20261122_a1_s04_rim_{fold}_v2.json'
    tracking_report = EXPERIMENTS / f'20261122_a1_s04_tracking_{fold}.json'
    rim_meta, tracking_meta = json.loads(rim_report.read_text()), json.loads(tracking_report.read_text())
    if sha256_file(rim_path) != rim_meta['rows_sha256'] or sha256_file(tracking_path) != tracking_meta['rows_sha256']:
        raise ValueError(f'{fold}: source prediction rows do not match their recorded fingerprints')
    rim, tracking = pd.read_parquet(rim_path), pd.read_parquet(tracking_path)
    if len(rim) != len(tracking):
        raise ValueError(f'{fold}: single-family populations differ')
    for column in ('game_id', 'date_et', 'zone', 'outcome'):
        if not np.array_equal(rim[column], tracking[column]):
            raise ValueError(f'{fold}: single-family {column} differs')
    for column in ('control_make', 'control_loss'):
        if not np.allclose(rim[column], tracking[column], rtol=0, atol=1e-12):
            raise ValueError(f'{fold}: single-family baseline {column} differs')
    baseline = rim['control_make'].to_numpy(dtype=float)
    combined = expit(logit(rim['candidate_make'].to_numpy(dtype=float))
                     + logit(tracking['candidate_make'].to_numpy(dtype=float)) - logit(baseline))
    made = rim['made'].to_numpy(dtype=float)
    control_loss = rim['control_loss'].to_numpy(dtype=float)
    loss = np.where(made == 0, -np.log1p(-combined),
                    control_loss - np.log(combined / baseline))
    rows = pd.DataFrame({'fold': fold, 'game_id': rim['game_id'], 'zone': rim['zone'], 'made': made,
                         'control_make': baseline, 'candidate_make': combined,
                         'control_loss': control_loss, 'candidate_loss': loss,
                         'rim_loss': rim['candidate_loss'], 'tracking_loss': tracking['candidate_loss']})
    fixed_ids = set(a1_minutes_fold_eval.fold_games(manifest, fold)['game_id'])
    fixed = rows.loc[rows['game_id'].isin(fixed_ids)]
    if len(fixed_ids) != 200 or set(fixed['game_id']) != fixed_ids:
        raise ValueError(f'{fold}: fixed 200 game IDs differ')
    result = {}
    for label, subset in (('complete_validation', rows), ('fixed_200_games', fixed)):
        result[label] = {'combined': a1_rim_screen.summary(subset), 'interaction': interaction_summary(subset),
                         'rim_interaction': interaction_summary(subset.loc[subset['zone'].eq('rim')])}
    return rows, result, [rim_path, tracking_path, rim_report, tracking_report]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--rows-output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.rows_output.exists():
        raise FileExistsError('refusing to overwrite an interaction result')
    if not args.rows_output.resolve().is_relative_to((DERIVED / 'experiments').resolve()):
        raise ValueError('interaction rows must remain under ignored data/derived/experiments')
    manifest = json.loads(a1_minutes_fold_eval.PREREG.read_text())
    results, parts, inputs = {}, [], [a1_minutes_fold_eval.PREREG, Path(__file__)]
    for fold in ('F1', 'F2', 'F3', 'F4'):
        rows, results[fold], paths = fold_result(fold, manifest)
        parts.append(rows)
        inputs.extend(paths)
        print(f'{fold}: composed {len(rows):,} existing held-out predictions', flush=True)
    atomic_bytes(args.rows_output, pd.concat(parts, ignore_index=True).to_parquet(index=False))
    report = {'experiment': 'a1_s04_posthoc_defence_interaction', 'folds': results,
              'method': 'sum already-fitted rim and tracking log-odds adjustments; no coefficients refitted',
              'limitations': 'post hoc, descriptive actual-shot diagnostic; neither rejected family may be promoted '
                             'from this interaction; guarded input is not the unchanged v1.3 engine control',
              'input_sha256': {str(p.resolve().relative_to(ROOT)): sha256_file(p) for p in inputs},
              'rows_sha256': sha256_file(args.rows_output)}
    write_json(args.output, report, pretty=True)
    print(f'saved {args.output}', flush=True)


if __name__ == '__main__':
    main()
