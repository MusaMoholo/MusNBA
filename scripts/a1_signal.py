#!/usr/bin/env python3
"""Reproduce the fixed A1 game-level component loadings with paired game uncertainty."""
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
from scripts import a1_compare, backtest, train  # noqa: E402
from scripts.evaluate import EXPERIMENTS  # noqa: E402

MANIFEST = EXPERIMENTS / '20261122_a1_manifest.json'
CONTROL = '20261120T162930Z_v1.3_pool_per_world_F4'
COMPONENTS = ('fg_pct', 'fg3_pct', 'fg3a_share', 'fga_100', 'fta_100', 'tov_100', 'oreb_100')
OUTCOMES = ('points_100', *COMPONENTS)
COEFFICIENTS = ('intercept', 'offence', 'opp_defence')


def fixed_games(games: pd.DataFrame, manifest: dict) -> pd.DataFrame:
    ids = [g['game_id'] for g in manifest['control']['games']]
    if len(ids) != 200 or len(set(ids)) != len(ids):
        raise ValueError('the S01 manifest must contain exactly 200 unique control games')
    if games['game_id'].isna().any() or games['game_id'].duplicated().any():
        raise ValueError('control games have missing or duplicate IDs')
    if set(games['game_id']) != set(ids):
        raise ValueError('control game IDs do not exactly match the S01 manifest')
    if (games['home'] == games['away']).any():
        raise ValueError('a game cannot have the same home and away team')
    return games.sort_values('game_id').reset_index(drop=True)


def component_sides(games: pd.DataFrame, ratings: pd.DataFrame) -> pd.DataFrame:
    if ratings['game_id'].isna().any() or ratings['game_id'].duplicated().any():
        raise ValueError('rating inputs have missing or duplicate game IDs')
    if set(games['game_id']) != set(ratings['game_id']):
        raise ValueError('rating inputs do not cover the same games')
    g = games.merge(ratings, on='game_id', validate='one_to_one')
    sides = []
    for side, other, label, opponent in (('home', 'away', 'h', 'a'), ('away', 'home', 'a', 'h')):
        out = pd.DataFrame({
            'game_id': g['game_id'], 'date_et': g['date_et'], 'side': side, 'team': g[side],
            'opponent': g[other], 'offence': g[f'off_{label}'], 'opp_defence': g[f'def_{opponent}'],
        })
        for prefix in ('sim', 'real'):
            for name in ('poss', 'fga', 'fgm', 'fg3a', 'fg3m', 'fta', 'tov', 'oreb'):
                out[f'{prefix}_{name}'] = g[f'{prefix}_{name}_{side}']
            out[f'{prefix}_points'] = g[f'{side}_sim'] if prefix == 'sim' else g[f'real_{side}']
            if (out[[f'{prefix}_{name}' for name in
                     ('poss', 'fga', 'fgm', 'fg3a', 'fg3m', 'fta', 'tov', 'oreb', 'points')]] < 0).any().any():
                raise ValueError(f'{prefix} component counts cannot be negative')
            for denominator in ('poss', 'fga', 'fg3a'):
                if (out[f'{prefix}_{denominator}'] <= 0).any():
                    raise ValueError(f'{prefix} {denominator} must be positive for every side')
            poss, fga, fg3a = (out[f'{prefix}_{name}'] for name in ('poss', 'fga', 'fg3a'))
            out[f'{prefix}_points_100'] = 100 * out[f'{prefix}_points'] / poss
            out[f'{prefix}_fg_pct'] = out[f'{prefix}_fgm'] / fga
            out[f'{prefix}_fg3_pct'] = out[f'{prefix}_fg3m'] / fg3a
            out[f'{prefix}_fg3a_share'] = fg3a / fga
            for name in ('fga', 'fta', 'tov', 'oreb'):
                out[f'{prefix}_{name}_100'] = 100 * out[f'{prefix}_{name}'] / poss
        sides.append(out)
    result = pd.concat(sides, ignore_index=True).sort_values(['game_id', 'side']).reset_index(drop=True)
    if result[['game_id', 'side', 'team', 'opponent']].isna().any().any():
        raise ValueError('team-side identifiers cannot be missing')
    numeric = result.select_dtypes(include='number').to_numpy(dtype=float)
    if not np.isfinite(numeric).all():
        raise ValueError('component dataset contains missing or non-finite numeric values')
    if not result.groupby('game_id')['side'].agg(set).eq({'home', 'away'}).all():
        raise ValueError('every game must contain exactly one home and away side')
    return result


def loading_report(sides: pd.DataFrame, replicates: int = a1_compare.BOOTSTRAP_REPLICATES,
                   seed: int = a1_compare.BOOTSTRAP_SEED) -> dict:
    if replicates < 1:
        raise ValueError('bootstrap replicates must be positive')
    sides = sides.sort_values(['game_id', 'side']).reset_index(drop=True)
    sizes = sides.groupby('game_id', sort=True).size()
    if len(sizes) < 2 or not sizes.eq(2).all() or sides.duplicated(['game_id', 'side']).any():
        raise ValueError('bootstrap requires exactly two distinct team sides per game')
    n = len(sizes)
    X = np.column_stack([np.ones(len(sides)), sides['offence'], sides['opp_defence']]).astype(float)
    Y = sides[[f'{prefix}_{outcome}' for prefix in ('sim', 'real') for outcome in OUTCOMES]].to_numpy(dtype=float)
    if not np.isfinite(X).all() or not np.isfinite(Y).all() or np.linalg.matrix_rank(X) != 3:
        raise ValueError('regression inputs must be finite and full rank')
    coeff = np.linalg.lstsq(X, Y, rcond=None)[0]
    means = Y.mean(axis=0)

    x = X.reshape(n, 2, 3)
    y = Y.reshape(n, 2, len(OUTCOMES) * 2)
    xx = np.einsum('gsi,gsj->gij', x, x).reshape(n, 9)
    xy = np.einsum('gsi,gsk->gik', x, y).reshape(n, -1)
    draws = np.random.default_rng(seed).integers(0, n, (replicates, n))
    weights = np.zeros(draws.shape, dtype=np.int16)
    np.add.at(weights, (np.arange(replicates)[:, None], draws), 1)
    try:
        boot = np.linalg.solve((weights @ xx).reshape(replicates, 3, 3),
                               (weights @ xy).reshape(replicates, 3, -1))
    except np.linalg.LinAlgError as exc:
        raise ValueError('a game-bootstrap sample has singular rating inputs') from exc
    boot_means = (weights @ y.sum(axis=1)) / (2 * n)

    def value(estimate, samples):
        return {'estimate': float(estimate), 'ci_95': [float(v) for v in np.quantile(samples, [0.025, 0.975])]}

    result = {}
    offset = len(OUTCOMES)
    for j, name in enumerate(OUTCOMES):
        per_outcome = {}
        for label, col in (('sim', j), ('real', j + offset)):
            per_outcome[label] = {'mean': value(means[col], boot_means[:, col])}
            per_outcome[label].update({
                key: value(coeff[k, col], boot[:, k, col]) for k, key in enumerate(COEFFICIENTS)
            })
        per_outcome['sim_minus_real'] = {
            'mean': value(means[j] - means[j + offset], boot_means[:, j] - boot_means[:, j + offset]),
            **{key: value(coeff[k, j] - coeff[k, j + offset], boot[:, k, j] - boot[:, k, j + offset])
               for k, key in enumerate(COEFFICIENTS)},
        }
        result[name] = per_outcome
    return result


def check_archived_loadings(report: dict, baseline: dict) -> None:
    for prefix in ('sim', 'real'):
        for key in COEFFICIENTS:
            found = report['points_100'][prefix][key]['estimate']
            archived = baseline['strength_loading'][prefix][key]
            if not np.isclose(found, archived, atol=0.000501, rtol=0):
                raise ValueError(f'archived strength loading differs: {prefix} {key}')
        for outcome in COMPONENTS:
            for key in ('offence', 'opp_defence'):
                found = report[outcome][prefix][key]['estimate']
                archived = baseline['component_loadings'][prefix][outcome][key]
                if not np.isclose(found, archived, atol=0.00000501, rtol=0):
                    raise ValueError(f'archived component loading differs: {prefix} {outcome} {key}')
            found = report[outcome][prefix]['mean']['estimate']
            archived = baseline['component_loadings'][prefix]['means'][outcome]
            if not np.isclose(found, archived, atol=0.000051, rtol=0):
                raise ValueError(f'archived component mean differs: {prefix} {outcome}')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, default=DERIVED / 'experiments' / '20261122_a1_s03_component_sides.parquet')
    parser.add_argument('--output', type=Path, default=EXPERIMENTS / '20261122_a1_s03_components.json')
    args = parser.parse_args()
    for path in (args.dataset, args.output):
        if path.exists():
            raise FileExistsError(f'refusing to overwrite {path}')
    control = DERIVED / 'experiments' / f'{CONTROL}.parquet'
    archived = EXPERIMENTS / f'{CONTROL}.json'
    manifest = json.loads(MANIFEST.read_text())
    games = fixed_games(pd.read_parquet(control), manifest)
    ratings = backtest.rating_baseline_inputs(games)
    sides = component_sides(games, ratings)
    report = loading_report(sides)
    original = json.loads(archived.read_text())['summary']['team_rating_baseline']
    if backtest.rating_baseline(games) != original:
        raise ValueError('the complete archived team-rating baseline did not reproduce')
    check_archived_loadings(report, original)
    args.dataset.parent.mkdir(parents=True, exist_ok=True)
    sides.to_parquet(args.dataset, index=False)
    paths = [MANIFEST, control, archived, ROOT / 'data' / 'raw' / 'hoopr' / 'player_box_2026.parquet',
             ROOT / 'scripts' / 'backtest.py', ROOT / 'scripts' / 'season_backtest.py',
             ROOT / 'scripts' / 'pathway.py', Path(__file__), args.dataset]
    def label(path: Path) -> str:
        path = path.resolve()
        return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)

    write_json(args.output, {
        'experiment': 'a1_s03_matched_component_loadings', 'commit': train.git_commit(),
        'control': CONTROL, 'games': len(games), 'team_sides': len(sides),
        'method': {'unit': 'team-game side; resample both sides of each complete game',
                   'bootstrap_replicates': a1_compare.BOOTSTRAP_REPLICATES, 'bootstrap_seed': a1_compare.BOOTSTRAP_SEED,
                   'regression': 'outcome = intercept + own offence + opponent defence; ratings are before game date',
                   'denominators': 'sim and actual each use their own possessions, attempts and makes',
                   'availability': 'actual participants; this is not an end-to-end availability forecast',
                   'limitations': 'observational loadings are not causal; real score and player-box totals may differ'},
        'archived_baseline_and_loadings_reproduced': True, 'outcomes': report,
        'sha256': {label(p): sha256_file(p) for p in paths},
    }, pretty=True)
    print(f'{len(games)} matched games, {len(sides)} team sides; archived loadings reproduced')
    print(f'saved {args.dataset} and {args.output}')


if __name__ == '__main__':
    main()
