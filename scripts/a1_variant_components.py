#!/usr/bin/env python3
"""Account for the rejected matchup variants' matched-game scoring changes."""
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
from scripts import a1_compare, a1_signal  # noqa: E402
from scripts.evaluate import EXPERIMENTS  # noqa: E402

CONTROL = '20261120T133953Z_v1.3_components_F4'
VARIANTS = {
    'v1.4c': '20261120T153853Z_v1.4c_F4',
    'v1.4e': '20261120T153837Z_v1.4e_F4',
    'v1.4f': '20261120T160608Z_v1.4f_F4',
}
COUNTS = ('poss', 'fga', 'fgm', 'fg3a', 'fg3m', 'fta', 'tov', 'oreb')


def paired_components(control: pd.DataFrame, candidate: pd.DataFrame) -> pd.DataFrame:
    for label, frame in (('control', control), ('candidate', candidate)):
        if frame['game_id'].isna().any() or frame['game_id'].duplicated().any():
            raise ValueError(f'{label} has missing or duplicate game IDs')
    if set(control['game_id']) != set(candidate['game_id']):
        raise ValueError('control and variant game IDs differ')
    a = control.sort_values('game_id').reset_index(drop=True)
    b = candidate.sort_values('game_id').reset_index(drop=True)
    for column in ('game_id', 'date_et', 'home', 'away', 'real_home', 'real_away'):
        if not a[column].equals(b[column]):
            raise ValueError(f'control and variant {column} differ')

    def totals(frame):
        out = {k: frame[f'sim_{k}_home'].to_numpy(dtype=float) + frame[f'sim_{k}_away'].to_numpy(dtype=float)
               for k in COUNTS}
        out['points'] = frame['total_sim'].to_numpy(dtype=float)
        out['two_point_points'] = 2 * (out['fgm'] - out['fg3m'])
        out['three_point_points'] = 3 * out['fg3m']
        out['free_throw_residual'] = out['points'] - out['two_point_points'] - out['three_point_points']
        if any(not np.isfinite(v).all() for v in out.values()) or (out['poss'] <= 0).any():
            raise ValueError('component counts must be finite and possessions positive')
        if (out['free_throw_residual'] < -1e-8).any() or (out['free_throw_residual'] > out['fta'] + 1e-8).any():
            raise ValueError('reconstructed scoring residual is outside free-throw-attempt bounds')
        return out

    x, y = totals(a), totals(b)
    rows = pd.DataFrame({'game_id': a['game_id']})
    for key in (*COUNTS, 'points', 'two_point_points', 'three_point_points', 'free_throw_residual'):
        rows[key] = y[key] - x[key]
    rate_x, rate_y = x['points'] / x['poss'], y['points'] / y['poss']
    rows['pace_term'] = (rate_x + rate_y) / 2 * (y['poss'] - x['poss'])
    rows['efficiency_term'] = (x['poss'] + y['poss']) / 2 * (rate_y - rate_x)
    if not np.allclose(rows['points'], rows['two_point_points'] + rows['three_point_points'] + rows['free_throw_residual'],
                       rtol=0, atol=1e-9):
        raise ValueError('field-goal and residual scoring changes do not reconcile')
    if not np.allclose(rows['points'], rows['pace_term'] + rows['efficiency_term'], rtol=0, atol=1e-9):
        raise ValueError('pace and efficiency terms do not reconcile')
    return rows


def intervals(rows: pd.DataFrame) -> dict:
    n = len(rows)
    draws = np.random.default_rng(a1_compare.BOOTSTRAP_SEED).integers(
        0, n, (a1_compare.BOOTSTRAP_REPLICATES, n))
    weights = np.zeros(draws.shape, dtype=np.int16)
    np.add.at(weights, (np.arange(len(draws))[:, None], draws), 1)
    result = {}
    for col in rows.columns.drop('game_id'):
        values = rows[col].to_numpy(dtype=float)
        samples = weights @ values / n
        result[col] = {'mean_per_game': float(values.mean()),
                       'ci_95': [float(v) for v in np.quantile(samples, [0.025, 0.975])]}
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=EXPERIMENTS / '20261122_a1_s03_variant_components.json')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f'refusing to overwrite {args.output}')
    manifest = json.loads(a1_signal.MANIFEST.read_text())
    paths = [a1_signal.MANIFEST, Path(__file__)]

    def load(run):
        data = DERIVED / 'experiments' / f'{run}.parquet'
        log = EXPERIMENTS / f'{run}.json'
        paths.extend([data, log])
        info = json.loads(log.read_text())
        if info['fold'] != 'F4' or info['worlds'] != 1000 or info['rotation'] != 'targets' or info['commit'] != '6d156a4':
            raise ValueError(f'{run} does not match the recorded shared-pool comparison')
        return a1_signal.fixed_games(pd.read_parquet(data), manifest)

    control = load(CONTROL)
    results = {}
    for label, run in VARIANTS.items():
        changes = paired_components(control, load(run))
        results[label] = {'run': run, 'games': len(changes), 'changes': intervals(changes)}
    write_json(args.output, {
        'experiment': 'a1_s03_rejected_variant_components', 'control': CONTROL,
        'method': {'unit': 'game; both teams summed',
                   'bootstrap_replicates': a1_compare.BOOTSTRAP_REPLICATES, 'bootstrap_seed': a1_compare.BOOTSTRAP_SEED,
                   'score_terms': '2*(FGM-3PM), 3*3PM, and points-2*FGM-3PM',
                   'pace_terms': 'symmetric exact decomposition of mean points = mean possessions * points per possession',
                   'limitations': 'shared-pool comparisons, not pool-0; random streams depend on model version; '
                                  'residual is reconstructed from engine scoring identity, not saved FTM; '
                                  'decompositions are descriptive, not causal'},
        'variants': results, 'sha256': {str(p): sha256_file(p) for p in paths},
    }, pretty=True)
    for name, result in results.items():
        x = result['changes']['points']
        print(f"{name}: total change {x['mean_per_game']:+.3f}, 95% {x['ci_95']}")
    print(f'saved {args.output}')


if __name__ == '__main__':
    main()
