#!/usr/bin/env python3
"""Reconcile and compare captured simulated versus recorded timeout-state exits."""
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
from scripts import a1_compare, a1_substitution_response_capture as capture  # noqa: E402
from scripts.evaluate import EXPERIMENTS  # noqa: E402

HISTORICAL = EXPERIMENTS / '20261122_a1_s06_timeout_states.json'
HISTORICAL_ROWS = DERIVED / 'experiments/20261122_a1_s06_timeout_states.parquet'


def rate_comparison(real: pd.DataFrame, simulated: pd.DataFrame, ids: list[str], weights: np.ndarray) -> dict:
    observed = real.assign(n=1, exits=real['changed'].astype(int)).groupby('game_id')[['n', 'exits']].sum()
    generated = simulated.groupby('game_id')[['decisions', 'exits']].sum()
    observed = observed.reindex(ids, fill_value=0)
    generated = generated.reindex(ids, fill_value=0)
    n_real, n_sim = int(observed['n'].sum()), int(generated['decisions'].sum())
    real_games, sim_games = int(observed['n'].gt(0).sum()), int(generated['decisions'].gt(0).sum())
    real_players = len(real[['game_id', 'player']].drop_duplicates())
    sim_players = len(simulated[['game_id', 'player']].drop_duplicates())
    supported = min(real_players, sim_players) >= 100 and min(real_games, sim_games) >= 30
    result = {
        'status': 'ok' if supported else 'insufficient_sample',
        'recorded_decisions': n_real, 'recorded_player_games': real_players, 'recorded_games': real_games,
        'simulated_decisions': n_sim, 'simulated_player_games': sim_players, 'simulated_games': sim_games,
        'recorded_exit_rate': float(observed['exits'].sum() / n_real) if n_real else None,
        'simulated_exit_rate': float(generated['exits'].sum() / n_sim) if n_sim else None,
        'simulated_minus_recorded_ci_95': None,
    }
    if supported:
        real_sample = weights @ observed[['exits', 'n']].to_numpy(dtype=float)
        sim_sample = weights @ generated[['exits', 'decisions']].to_numpy(dtype=float)
        if (real_sample[:, 1] == 0).any() or (sim_sample[:, 1] == 0).any():
            raise ValueError('supported timeout-state bootstrap has an empty denominator')
        delta = sim_sample[:, 0] / sim_sample[:, 1] - real_sample[:, 0] / real_sample[:, 1]
        result['simulated_minus_recorded_ci_95'] = np.quantile(delta, [0.025, 0.975]).tolist()
    return result


def audit(report_path: Path, rows_path: Path) -> dict:
    saved, historic_report = json.loads(report_path.read_text()), json.loads(HISTORICAL.read_text())
    for path, digest in {**saved['input_sha256'], **saved['output_sha256']}.items():
        if sha256_file(ROOT / path) != digest:
            raise ValueError(f'captured source differs: {path}')
    if saved['output_sha256'].get(str(rows_path.resolve().relative_to(ROOT))) != sha256_file(rows_path):
        raise ValueError('captured rows differ from their report')
    if historic_report['output_sha256'].get(str(HISTORICAL_ROWS.relative_to(ROOT))) != sha256_file(HISTORICAL_ROWS):
        raise ValueError('audited historical timeout-state rows changed')
    cells = pd.read_parquet(rows_path)
    historical = pd.read_parquet(HISTORICAL_ROWS)
    historical = historical.loc[historical['decision'].eq('out')].copy()
    if (cells.duplicated(['game_id', 'player', 'dimension', 'value']).any()
            or historical.duplicated(['window_id', 'player']).any()):
        raise ValueError('timeout state output contains duplicated decisions')
    if ((cells['decisions'] <= 0) | (cells['exits'] < 0) | (cells['exits'] > cells['decisions'])).any():
        raise ValueError('captured exit counts are invalid')
    reference = saved['reference']
    games_path = DERIVED / 'experiments' / f'{reference}.parquet'
    games = pd.read_parquet(games_path, columns=['game_id', 's06_timeout_team_windows', 's06_timeout_outgoing'])
    if games['game_id'].duplicated().any() or set(cells['game_id']) != set(games['game_id']):
        raise ValueError('capture games differ from the reference')
    totals = cells.groupby(['game_id', 'dimension'], as_index=False)[['decisions', 'exits']].sum()
    by_game = {(row['game_id'], row['dimension']): row for row in totals.to_dict('records')}
    checks = 0
    for game in games.itertuples(index=False):
        if not isinstance(game.s06_timeout_team_windows, (int, np.integer)):
            raise ValueError('reference timeout-window count is not an integer')
        expected_decisions = 5 * int(game.s06_timeout_team_windows)
        for dimension in capture.DIMENSIONS:
            key = (game.game_id, dimension)
            if key not in by_game:
                raise ValueError('capture omits a game/state dimension')
            observed = by_game[key]
            if (observed['decisions'] != expected_decisions
                    or observed['exits'] != game.s06_timeout_outgoing):
                raise ValueError('captured game/state totals differ from the reference policy counters')
            checks += 1
    common = sorted(set(games['game_id']) & set(historical['game_id']))
    if saved['games'] != 200 or not common:
        raise ValueError('full fixed candidate or common historical games are absent')
    real = historical.loc[historical['game_id'].isin(common)].copy()
    sim = cells.loc[cells['game_id'].isin(common)].copy()
    real_roles = real[['game_id', 'player', 'tier']].drop_duplicates()
    sim_roles = sim[['game_id', 'player', 'tier']].drop_duplicates()
    if real_roles.duplicated(['game_id', 'player']).any() or sim_roles.duplicated(['game_id', 'player']).any():
        raise ValueError('pregame role changes within a player-game')
    roles = real_roles.merge(sim_roles, on=['game_id', 'player'], how='outer', suffixes=('_real', '_sim'),
                             indicator=True, validate='one_to_one')
    both = roles['_merge'].eq('both')
    if not roles.loc[both, 'tier_real'].eq(roles.loc[both, 'tier_sim']).all():
        raise ValueError('captured and historical pregame roles disagree')
    draws = np.random.default_rng(a1_compare.BOOTSTRAP_SEED).integers(
        0, len(common), (a1_compare.BOOTSTRAP_REPLICATES, len(common)))
    weights = np.zeros(draws.shape, dtype=np.int16)
    np.add.at(weights, (np.arange(len(draws))[:, None], draws), 1)
    groups = {}
    for tier in ('all', *a1_compare.ROLE_TIERS):
        real_role = real if tier == 'all' else real.loc[real['tier'].eq(tier)]
        sim_role = sim if tier == 'all' else sim.loc[sim['tier'].eq(tier)]
        for dimension, labels in capture.DIMENSIONS.items():
            for label in labels:
                selected_real = real_role.loc[real_role[dimension].eq(label)]
                selected_sim = sim_role.loc[sim_role['dimension'].eq(dimension) & sim_role['value'].eq(label)]
                groups[f'{tier}/{dimension}/{label}'] = rate_comparison(
                    selected_real, selected_sim, common, weights)
    return {
        'experiment': 'a1_s06_simulated_state_response_independent_accounting',
        'reference': reference, 'candidate_games': saved['games'], 'common_historical_games': len(common),
        'captured_game_dimension_checks': checks,
        'role_coverage': {str(key): int(value) for key, value in roles['_merge'].value_counts().items()},
        'bootstrap_replicates': a1_compare.BOOTSTRAP_REPLICATES, 'bootstrap_seed': a1_compare.BOOTSTRAP_SEED,
        'groups': groups,
        'limitations': 'Simulated and historical timeout opportunities have different, selected timing; rates '
                       'are descriptive and actual participants are supplied. Score/foul state and player '
                       'composition differ by world, so this is not a causal or pre-game availability test.',
        'input_sha256': {str(path.relative_to(ROOT)): sha256_file(path)
                         for path in (Path(__file__), report_path, rows_path, HISTORICAL, HISTORICAL_ROWS, games_path)},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture_report', type=Path)
    parser.add_argument('capture_rows', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f'refusing to overwrite {args.output}')
    result = audit(args.capture_report.resolve(), args.capture_rows.resolve())
    write_json(args.output, result, pretty=True)
    print(f"audited {result['captured_game_dimension_checks']} game/state totals and compared "
          f"{result['common_historical_games']} games")


if __name__ == '__main__':
    main()
