#!/usr/bin/env python3
"""Compare matched real-state replay with an exactly reproduced free-running control."""
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
from scripts import a1_compare, a1_signal, backtest, train  # noqa: E402
from scripts.evaluate import EXPERIMENTS  # noqa: E402

REFERENCE = '20261122T022323Z_a1_s01_control'
TEACHER = '20261122T050308Z_a1_s03_m6a_fixed200'


def exact_reproduction(reference: pd.DataFrame, observed: pd.DataFrame, keys: list[str]) -> int:
    a1_compare._same_keys(reference, observed, keys, 'control reproduction')
    missing = set(reference.columns) - set(observed.columns)
    if missing:
        raise ValueError(f'expanded output lacks original columns: {sorted(missing)}')
    a = reference.sort_values(keys).reset_index(drop=True)
    b = observed.sort_values(keys).reset_index(drop=True)
    for column in reference.columns:
        if pd.api.types.is_numeric_dtype(a[column]):
            before, after = a[column].to_numpy(dtype=float), b[column].to_numpy(dtype=float)
            if np.isinf(before).any() or np.isinf(after).any():
                raise ValueError(f'control reproduction has an infinite value in {column}')
            equal = np.isclose(before, after, rtol=0, atol=1e-12, equal_nan=True)
        else:
            equal = (a[column].eq(b[column]) | (a[column].isna() & b[column].isna())).to_numpy()
        if not equal.all():
            raise ValueError(f'expanded control differs in {column}: {int((~equal).sum())} rows')
    return len(a) * len(reference.columns)


def mean_report(rows: pd.DataFrame, names: list[str], ids: list[str], weights: np.ndarray,
                player: bool = False) -> dict:
    out = {}
    for name in names:
        values = pd.to_numeric(rows[name], errors='raise').to_numpy(dtype=float)
        if np.isinf(values).any():
            raise ValueError(f'{name} has infinite values')
        good = np.isfinite(values)
        data = pd.DataFrame({'game_id': rows.loc[good, 'game_id'].to_numpy(), 'value': values[good], 'n': 1})
        group = data.groupby('game_id')[['value', 'n']].sum().reindex(ids, fill_value=0)
        n, games = int(good.sum()), int((group['n'] > 0).sum())
        result = {'observations': n, 'games': games, 'missing': int((~good).sum()),
                  'status': 'ok' if games >= a1_compare.MIN_GAMES and
                  (not player or n >= a1_compare.MIN_PLAYER_GAMES) else 'insufficient_sample',
                  'mean': None, 'ci_95': None}
        if n:
            result['mean'] = float(group['value'].sum() / n)
        if result['status'] == 'ok':
            totals = weights @ group.to_numpy(dtype=float)
            if (totals[:, 1] == 0).any():
                raise ValueError(f'{name} has an empty game-bootstrap sample')
            result['ci_95'] = [float(v) for v in np.quantile(totals[:, 0] / totals[:, 1], [0.025, 0.975])]
        out[name] = result
    return out


def teacher_sides(free: pd.DataFrame, components: pd.DataFrame) -> pd.DataFrame:
    keys = ['game_id', 'side']
    a1_compare._same_keys(free, components, keys, 'teacher team sides')
    rows = free[keys + ['team', 'offence', 'opp_defence']].merge(
        components, on=keys, suffixes=('_free', '_teacher'), validate='one_to_one')
    if not rows['team_free'].equals(rows['team_teacher']):
        raise ValueError('teacher and free-running team identities differ')
    poss = rows['eligible_possessions'].to_numpy(dtype=float)
    if (poss <= 0).any():
        raise ValueError('teacher replay has non-positive eligible possessions')
    for kind, prefix in (('actual', 'real'), ('sim', 'sim')):
        fga = rows[f'fga_{kind}'].to_numpy(dtype=float)
        fg3a = rows[f'fg3a_{kind}'].to_numpy(dtype=float)
        if (fga <= 0).any() or (fg3a <= 0).any():
            raise ValueError('teacher replay has a non-positive shot denominator')
        rows[f'{prefix}_points_100'] = 100 * rows[f'pts_{kind}'] / poss
        rows[f'{prefix}_fg_pct'] = rows[f'fgm_{kind}'] / fga
        rows[f'{prefix}_fg3_pct'] = rows[f'fg3m_{kind}'] / fg3a
        rows[f'{prefix}_fg3a_share'] = fg3a / fga
        for stat in ('fga', 'fta', 'tov', 'oreb'):
            rows[f'{prefix}_{stat}_100'] = 100 * rows[f'{stat}_{kind}'] / poss
    return rows


def component_comparison(free: pd.DataFrame, teacher: pd.DataFrame) -> dict:
    keys = ['game_id', 'side', 'offence', 'opp_defence']
    teacher = teacher.sort_values(['game_id', 'side']).reset_index(drop=True)
    free = free.sort_values(['game_id', 'side']).reset_index(drop=True)
    if not teacher[['game_id', 'side']].equals(free[['game_id', 'side']]):
        raise ValueError('teacher and free-running sides are not aligned')
    error_change = teacher[keys].copy()
    for outcome in a1_signal.OUTCOMES:
        error_change[f'sim_{outcome}'] = free[f'sim_{outcome}'] - free[f'real_{outcome}']
        error_change[f'real_{outcome}'] = teacher[f'sim_{outcome}'] - teacher[f'real_{outcome}']
    return {'teacher_vs_event_actual': a1_signal.loading_report(teacher),
            'free_vs_official_or_box_actual': a1_signal.loading_report(free),
            'free_error_minus_teacher_error': a1_signal.loading_report(error_change)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', help='expanded free-running control run name')
    parser.add_argument('--output', type=Path, default=EXPERIMENTS / '20261122_a1_s03_flow_comparison.json')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f'refusing to overwrite {args.output}')
    log_path = EXPERIMENTS / f'{args.run}.json'
    log = json.loads(log_path.read_text())
    if not log.get('flow_diagnostics') or log.get('worlds') != 1000 or log.get('fold') != 'F4':
        raise ValueError('run is not the fixed 1,000-world F4 flow diagnostic')
    for path, digest in log['flow_diagnostics']['sha256'].items():
        if sha256_file(ROOT / path) != digest:
            raise ValueError(f'flow diagnostic source changed after scoring: {path}')
    manifest = json.loads(a1_signal.MANIFEST.read_text())
    control = manifest['control']
    if (log.get('models') != control['fitted_models'] or log.get('config') != control['config'] or
            log.get('rotation') != control['rotation'] or log.get('pool') != control['pool'] or
            log.get('known_starters') is not False or log.get('simulation_stream') is not None or
            log.get('seed_key') is not None):
        raise ValueError('expanded control settings differ from the fixed control')
    model_dir = (train.MODELS / log['models']).resolve()
    model_hashes = {item['path']: item['sha256'] for item in manifest['input_fingerprints']
                    if (ROOT / item['path']).parent == model_dir}
    if len(model_hashes) != 17 or any(sha256_file(ROOT / path) != digest for path, digest in model_hashes.items()):
        raise ValueError('expanded control model files do not match the fixed manifest')
    ids = sorted(g['game_id'] for g in manifest['control']['games'])
    data = DERIVED / 'experiments'
    ref_games = a1_signal.fixed_games(pd.read_parquet(data / f'{REFERENCE}.parquet'), manifest)
    games = a1_signal.fixed_games(pd.read_parquet(data / f'{args.run}.parquet'), manifest)
    ref_players = pd.read_parquet(data / f'{REFERENCE}_players.parquet')
    players = pd.read_parquet(data / f'{args.run}_players.parquet')
    checked_games = exact_reproduction(ref_games, games, ['game_id'])
    checked_players = exact_reproduction(ref_players, players, ['game_id', 'player'])
    components = pd.read_parquet(data / f'{TEACHER}_components.parquet')
    replay_players = pd.read_parquet(data / f'{TEACHER}.parquet')
    rating = backtest.rating_baseline_inputs(games)
    free_sides = a1_signal.component_sides(games, rating)
    replay_sides = teacher_sides(free_sides, components)

    draws = np.random.default_rng(a1_compare.BOOTSTRAP_SEED).integers(
        0, len(ids), (a1_compare.BOOTSTRAP_REPLICATES, len(ids)))
    weights = np.zeros(draws.shape, dtype=np.int16)
    np.add.at(weights, (np.arange(len(draws))[:, None], draws), 1)

    paired = players.merge(replay_players, on=['game_id', 'player'], how='outer',
                           suffixes=('_free', '_teacher'), indicator=True, validate='one_to_one')
    coverage = {str(k): int(v) for k, v in paired['_merge'].value_counts().items()}
    paired = paired[paired['_merge'] == 'both'].copy()
    pre = pd.read_parquet(ROOT / 'data/derived/variants/matchup/features/pregame.parquet')
    roles = a1_compare.roles(paired[['game_id', 'player']], pre, games)
    paired = paired.drop(columns='tier').merge(roles, on=['game_id', 'player'], validate='one_to_one')
    for stat in ('pts', 'reb', 'ast', 'fg3m', 'fga', 'fta', 'tov'):
        paired[f'{stat}_teacher_error'] = paired[f'{stat}_sim_teacher'] - paired[f'{stat}_actual_teacher']
        paired[f'{stat}_free_error'] = paired[f'{stat}_sim_free'] - paired[f'{stat}_actual_free']
        paired[f'{stat}_flow_increment'] = paired[f'{stat}_free_error'] - paired[f'{stat}_teacher_error']
        paired[f'{stat}_actual_population_gap'] = paired[f'{stat}_actual_teacher'] - paired[f'{stat}_actual_free']
    paired['uses_teacher_sim'] = paired['fga_sim_teacher'] + 0.44 * paired['fta_sim_teacher'] + paired['tov_sim_teacher']
    paired['uses_teacher_actual'] = paired['fga_actual_teacher'] + 0.44 * paired['fta_actual_teacher'] + paired['tov_actual_teacher']
    paired['uses_free_sim'] = paired['fga_sim_free'] + 0.44 * paired['fta_sim_free'] + paired['tov_sim_free']
    paired['uses_free_actual'] = paired['fga_actual_free'] + 0.44 * paired['fta_actual_free'] + paired['tov_actual_free']
    paired['uses_teacher_error'] = paired['uses_teacher_sim'] - paired['uses_teacher_actual']
    paired['uses_free_error'] = paired['uses_free_sim'] - paired['uses_free_actual']
    paired['uses_flow_increment'] = paired['uses_free_error'] - paired['uses_teacher_error']
    paired['minute_error'] = paired['min_sim'] - paired['min_actual']
    paired['minute_absolute_error'] = paired['minute_error'].abs()
    for q in range(1, 5):
        for stat in ('min', 'pts', 'fga', 'fta', 'tov'):
            paired[f'q{q}_{stat}_error'] = paired[f'q{q}_{stat}_sim'] - paired[f'q{q}_{stat}_actual']
    player_names = [f'{stat}_{part}' for stat in ('pts', 'reb', 'ast', 'fg3m', 'fga', 'fta', 'tov')
                    for part in ('teacher_error', 'free_error', 'flow_increment', 'actual_population_gap')]
    player_names += ['uses_teacher_error', 'uses_free_error', 'uses_flow_increment', 'minute_error', 'minute_absolute_error']
    player_names += [f'q{q}_{stat}_error' for q in range(1, 5) for stat in ('min', 'pts', 'fga', 'fta', 'tov')]
    player_report = {tier: mean_report(paired if tier == 'all' else paired[paired['tier'] == tier],
                                       player_names, ids, weights, player=True)
                     for tier in ('all', *a1_compare.ROLE_TIERS)}

    clock = games[['game_id']].copy()
    for measure in ('segments_per_world', 'mean_duration', 'start_at_or_below_24s'):
        sim = f'flow_clock_simulated_{measure}'
        actual = f'flow_clock_recorded_{measure.replace("segments_per_world", "segments")}'
        clock[f'{measure}_difference'] = games[sim] - games[actual]
    clock['overtime_probability_error'] = games['sim_ot'] - games['real_ot']
    rotation_rows = []
    for side in ('home', 'away'):
        cols = {c.removeprefix(f'flow_rotation_{side}_'): c
                for c in games.columns if c.startswith(f'flow_rotation_{side}_')}
        frame = games[['game_id', *cols.values()]].rename(columns={v: k for k, v in cols.items()}).copy()
        for feature in ('usage', 'fg_rim', 'd_fg_rim'):
            frame[f'{feature}_difference'] = frame[f'{feature}_scheduled'] - frame[f'{feature}_actual']
        rotation_rows.append(frame)
    rotation = pd.concat(rotation_rows, ignore_index=True)
    rotation_names = ['valid_ticks', 'invalid_ticks', 'scheduled_exact_five', 'scheduled_matching_slots',
                      'usage_difference', 'fg_rim_difference', 'd_fg_rim_difference']
    paths = [a1_signal.MANIFEST, log_path, data / f'{REFERENCE}.parquet', data / f'{REFERENCE}_players.parquet',
             data / f'{args.run}.parquet', data / f'{args.run}_players.parquet',
             data / f'{TEACHER}_components.parquet', data / f'{TEACHER}.parquet', Path(__file__)]
    write_json(args.output, {
        'experiment': 'a1_s03_teacher_vs_free_flow', 'teacher': TEACHER, 'control': args.run,
        'method': {'games': len(ids), 'teacher_worlds': 10000, 'free_worlds': 1000,
                   'bootstrap': '10,000 paired complete-game clusters, seed 20261122',
                   'usage_proxy': 'FGA + 0.44*FTA + player turnovers; not the exact possession-use count',
                   'lineups': 'scheduled regulation fives at 10-second midpoints, before foul-out replacements',
                   'limitations': 'teacher actuals omit excluded events; free actuals use official/player-box data; '
                                  'game-state, minutes and lineups change together, so contrasts are not causal'},
        'reproduction': {'game_values_checked': checked_games, 'player_values_checked': checked_players,
                         'model_files_matching_manifest': len(model_hashes),
                         'player_key_coverage': coverage},
        'component_loadings': component_comparison(free_sides, replay_sides),
        'players_by_pregame_role': player_report,
        'clock': mean_report(clock, [c for c in clock.columns if c != 'game_id'], ids, weights),
        'rotation': mean_report(rotation, rotation_names, ids, weights),
        'sha256': {str(p.resolve().relative_to(ROOT)): sha256_file(p) for p in paths},
    }, pretty=True)
    print(f'{len(ids)} matched games; {checked_games} game and {checked_players} player control values reproduced')
    print(f'paired player-key coverage {coverage}; saved {args.output}')


if __name__ == '__main__':
    main()
