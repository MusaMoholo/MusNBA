#!/usr/bin/env python3
"""Strict, game-clustered comparisons for the preregistered A1 engine evaluation.

The first run is the control. Unlike the legacy scorecard, role tiers come from pre-game
usage and start share. This reports evidence, not an automatic promotion decision.

  .venv/bin/python scripts/a1_compare.py CONTROL CANDIDATE [--game-ids games.json] [--output report.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, write_json  # noqa: E402
from scripts import backtest  # noqa: E402
from scripts.evaluate import EXPERIMENTS  # noqa: E402

STATS = ('min', 'pts', 'reb', 'ast', 'fg3m')
ROLE_TIERS = ('star', 'starter', 'bench', 'unknown')
BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED = 20261122
MIN_PLAYER_GAMES = 100
MIN_GAMES = 30


def _unique(frame: pd.DataFrame, keys: list[str], label: str) -> None:
    if frame[keys].isna().any().any():
        raise ValueError(f'{label} has missing keys: {keys}')
    if frame.duplicated(keys).any():
        raise ValueError(f'{label} has duplicate keys: {keys}')


def _same_keys(left: pd.DataFrame, right: pd.DataFrame, keys: list[str], label: str) -> None:
    _unique(left, keys, f'{label} control')
    _unique(right, keys, f'{label} candidate')
    a = pd.MultiIndex.from_frame(left[keys])
    b = pd.MultiIndex.from_frame(right[keys])
    if not a.difference(b).empty or not b.difference(a).empty:
        raise ValueError(f'{label} keys differ: control-only={len(a.difference(b))}, candidate-only={len(b.difference(a))}')


def _pair(left: pd.DataFrame, right: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    def suffix(frame: pd.DataFrame, side: str) -> pd.DataFrame:
        return frame.rename(columns={c: f'{c}_{side}' for c in frame.columns if c not in keys})
    return suffix(left, 'control').merge(suffix(right, 'candidate'), on=keys, validate='one_to_one')


def _same_values(rows: pd.DataFrame, columns: tuple[str, ...], label: str) -> None:
    for column in columns:
        a, b = rows[f'{column}_control'], rows[f'{column}_candidate']
        if pd.api.types.is_numeric_dtype(a) and pd.api.types.is_numeric_dtype(b):
            equal = np.isclose(a.to_numpy(dtype=float), b.to_numpy(dtype=float), rtol=0, atol=1e-12, equal_nan=True)
        else:
            equal = (a.eq(b) | (a.isna() & b.isna())).to_numpy()
        if not equal.all():
            raise ValueError(f'{label} differs between runs: {column} ({int((~equal).sum())} rows)')


def roster_gaps(expected: pd.DataFrame, observed: pd.DataFrame) -> pd.DataFrame:
    keys = ['game_id', 'player']
    _unique(expected, keys, 'simulated roster')
    _unique(observed, keys, 'player output')
    if expected['team'].isna().any():
        raise ValueError('simulated roster has missing teams')
    rows = expected[keys + ['team']].merge(observed[keys + ['team']], on=keys, how='outer',
                                           suffixes=('_control', '_candidate'), validate='one_to_one', indicator=True)
    if rows['_merge'].eq('right_only').any():
        raise ValueError('player outputs include IDs absent from the simulated roster')
    matched = rows['_merge'].eq('both')
    _same_values(rows.loc[matched], ('team',), 'player roster teams')
    return rows.loc[rows['_merge'].eq('left_only'), keys + ['team_control']].rename(columns={'team_control': 'team'})


def roles(keys: pd.DataFrame, pre: pd.DataFrame, games: pd.DataFrame) -> pd.DataFrame:
    _unique(pre, ['game_id', 'player'], 'pre-game profiles')
    source = pre[['game_id', 'player', 'date_et', 'usage', 'start_share']]
    rows = keys.merge(source, on=['game_id', 'player'], how='left', validate='one_to_one')
    rows = rows.merge(games[['game_id', 'date_et']], on='game_id', how='left', suffixes=('_profile', '_game'),
                      validate='many_to_one')
    bad_date = rows['date_et_profile'].notna() & rows['date_et_profile'].ne(rows['date_et_game'])
    if bad_date.any():
        raise ValueError(f'pre-game profile date differs from game date on {int(bad_date.sum())} player-games')
    usage = pd.to_numeric(rows['usage'], errors='raise').astype(float)
    start = pd.to_numeric(rows['start_share'], errors='raise').astype(float)
    for name, values in (('usage', usage), ('start_share', start)):
        if (np.isinf(values) | (values < 0) | (values > 1)).any():
            raise ValueError(f'pre-game {name} must be between 0 and 1 or missing')
    known = np.isfinite(usage) & np.isfinite(start)
    rows['tier'] = np.select([~known, usage >= 0.25, start >= 0.5], ['unknown', 'star', 'starter'], default='bench')
    return rows[['game_id', 'player', 'tier']]


def _interval(values: np.ndarray) -> list[float]:
    return [float(x) for x in np.quantile(values, [0.025, 0.975])]


def _result(control: float, candidate: float, boot: np.ndarray | None, transform=None) -> dict:
    apply = transform if transform is not None else lambda x: x
    result: dict[str, float | list[float] | None] = {
        'control': float(control), 'candidate': float(candidate),
        'change': float(apply(candidate) - apply(control))}
    result['ci_95'] = _interval(boot) if boot is not None else None
    return result


def distribution(rows: pd.DataFrame, stat: str, game_ids: list[str], weights: np.ndarray, player: bool) -> dict:
    needed = [f'{stat}_{part}_{side}' for part in ('actual', 'sim', 'crps', 'pit') for side in ('control', 'candidate')]
    missing = [c for c in needed if c not in rows.columns]
    if missing:
        return {'status': 'unavailable', 'missing_columns': missing}
    _same_values(rows, (f'{stat}_actual',), f'{stat} actuals')
    actual = rows[f'{stat}_actual_control'].to_numpy(dtype=float)
    if np.isinf(actual).any():
        raise ValueError(f'{stat}: infinite actual is invalid')
    valid_actual = np.isfinite(actual)
    for col in needed:
        if not np.isfinite(rows.loc[valid_actual, col].to_numpy(dtype=float)).all():
            raise ValueError(f'{stat}: non-finite {col} for a player/game with a known actual')
    work = rows.loc[valid_actual, ['game_id']].copy()
    for side in ('control', 'candidate'):
        work[f'crps_{side}'] = rows.loc[valid_actual, f'{stat}_crps_{side}'].to_numpy(dtype=float)
        work[f'bias_{side}'] = rows.loc[valid_actual, f'{stat}_sim_{side}'].to_numpy(dtype=float) - actual[valid_actual]
        pit = rows.loc[valid_actual, f'{stat}_pit_{side}'].to_numpy(dtype=float)
        if ((pit < 0) | (pit > 1)).any():
            raise ValueError(f'{stat}: PIT outside [0, 1]')
        work[f'coverage_{side}'] = ((pit >= 0.1) & (pit <= 0.9)).astype(int)
    work['n'] = 1
    grouped = work.groupby('game_id').sum().reindex(game_ids, fill_value=0)
    n = len(work)
    n_games = int((grouped['n'] > 0).sum())
    reportable = n_games >= MIN_GAMES and (not player or n >= MIN_PLAYER_GAMES)
    result = {'status': 'ok' if reportable else 'insufficient_sample', 'observations': n, 'games': n_games,
              'missing_actuals': int((~valid_actual).sum())}
    if not n:
        return result
    totals = grouped.sum()
    boot = weights @ grouped.to_numpy(dtype=float) if reportable else None
    columns = {name: i for i, name in enumerate(grouped.columns)}
    if boot is not None and (boot[:, columns['n']] == 0).any():
        raise ValueError(f'{stat}: bootstrap contains an empty subgroup')
    for metric, target in (('crps', None), ('bias', 0.0), ('coverage', 0.8)):
        a, b = float(totals[f'{metric}_control'] / n), float(totals[f'{metric}_candidate'] / n)
        transform = (lambda x: abs(x - target)) if target is not None else None
        interval = None
        if boot is not None:
            aa = boot[:, columns[f'{metric}_control']] / boot[:, columns['n']]
            bb = boot[:, columns[f'{metric}_candidate']] / boot[:, columns['n']]
            interval = (np.abs(bb - target) - np.abs(aa - target)) if target is not None else bb - aa
        result[metric] = _result(a, b, interval, transform)
    return result


def _win_metrics(rows: pd.DataFrame, game_ids: list[str], weights: np.ndarray) -> dict:
    win = (rows['real_home_control'] > rows['real_away_control']).to_numpy(dtype=float)
    metrics = {}
    values = {}
    for side in ('control', 'candidate'):
        p = rows[f'p_home_{side}'].to_numpy(dtype=float)
        if not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
            raise ValueError(f'{side} home-win probabilities are invalid')
        observed_probability = np.where(win == 1, p, 1 - p)
        with np.errstate(divide='ignore'):
            loss = -np.log(observed_probability)
        values[side] = {'brier': (p - win) ** 2, 'log_loss': loss}
    for metric in ('brier', 'log_loss'):
        a, b = values['control'][metric], values['candidate'][metric]
        if not np.isfinite(a).all() or not np.isfinite(b).all():
            metrics[metric] = {'status': 'infinite_log_loss',
                               'control': float(a.mean()) if np.isfinite(a).all() else None,
                               'candidate': float(b.mean()) if np.isfinite(b).all() else None,
                               'change': None, 'ci_95': None,
                               'infinite_control_games': int(np.isinf(a).sum()),
                               'infinite_candidate_games': int(np.isinf(b).sum())}
            continue
        by_game = pd.DataFrame({'game_id': rows['game_id'], 'change': b - a}).set_index('game_id').reindex(game_ids)
        boot = weights @ by_game['change'].to_numpy(dtype=float) / len(game_ids) if len(game_ids) >= MIN_GAMES else None
        metrics[metric] = _result(float(a.mean()), float(b.mean()), boot)
    status = 'infinite_log_loss' if metrics['log_loss'].get('status') else (
        'ok' if len(game_ids) >= MIN_GAMES else 'insufficient_sample')
    return {'status': status, **metrics}


def compare(control: str, candidate: str, ids_path: Path | None = None) -> dict:
    names = (control, candidate)
    logs = [json.loads((EXPERIMENTS / f'{name}.json').read_text()) for name in names]
    if logs[0]['fold'] != logs[1]['fold'] or logs[0]['worlds'] != logs[1]['worlds']:
        raise ValueError('runs must use the same fold and number of worlds')
    games = [pd.read_parquet(DERIVED / 'experiments' / f'{name}.parquet') for name in names]
    players = [pd.read_parquet(DERIVED / 'experiments' / f'{name}_players.parquet') for name in names]
    for frame in games + players:
        if frame['game_id'].isna().any():
            raise ValueError('game IDs cannot be missing')
        frame['game_id'] = frame['game_id'].astype(str)
    for frame in players:
        if frame['player'].isna().any():
            raise ValueError('player IDs cannot be missing')
        frame['player'] = frame['player'].astype(str)
    if ids_path is not None:
        chosen = backtest.select_games(np.array(sorted(games[0]['game_id'].unique())), 0, 0, ids_path)
        backtest.select_games(np.array(sorted(games[1]['game_id'].unique())), 0, 0, ids_path)
        games = [frame[frame['game_id'].isin(chosen)] for frame in games]
        players = [frame[frame['game_id'].isin(chosen)] for frame in players]
    _same_keys(games[0], games[1], ['game_id'], 'games')
    _same_keys(players[0], players[1], ['game_id', 'player'], 'players')
    if games[0].empty:
        raise ValueError('the matched game population is empty')
    if set(players[0]['game_id']) != set(games[0]['game_id']):
        raise ValueError('every selected game must have at least one matched player')
    paired_games = _pair(games[0], games[1], ['game_id'])
    _same_values(paired_games, ('date_et', 'home', 'away', 'real_home', 'real_away', 'real_ot'), 'game facts')
    paired_players = _pair(players[0], players[1], ['game_id', 'player'])
    spec = json.loads((ROOT / logs[0]['config']).read_text())
    pre, *_ = backtest.load_inputs(spec, logs[0]['fold'])
    tiers = roles(paired_players[['game_id', 'player']], pre, games[0])
    paired_players = paired_players.merge(tiers, on=['game_id', 'player'], validate='one_to_one')
    game_ids = sorted(paired_games['game_id'].tolist())
    expected = pre.loc[pre['game_id'].isin(game_ids), ['game_id', 'player', 'team']]
    observed = paired_players[['game_id', 'player']].merge(expected, on=['game_id', 'player'], how='left',
                                                            validate='one_to_one')
    gaps = roster_gaps(expected, observed)
    draws = np.random.default_rng(BOOTSTRAP_SEED).integers(0, len(game_ids), (BOOTSTRAP_REPLICATES, len(game_ids)))
    weights = np.zeros(draws.shape, dtype=np.int16)
    np.add.at(weights, (np.arange(BOOTSTRAP_REPLICATES)[:, None], draws), 1)
    for side in ('control', 'candidate'):
        paired_games[f'total_actual_{side}'] = paired_games[f'real_home_{side}'] + paired_games[f'real_away_{side}']
        paired_games[f'margin_actual_{side}'] = paired_games[f'real_home_{side}'] - paired_games[f'real_away_{side}']
    player_results = {}
    for tier in ('all', *ROLE_TIERS):
        subset = paired_players if tier == 'all' else paired_players[paired_players['tier'] == tier]
        player_results[tier] = {stat: distribution(subset, stat, game_ids, weights, True) for stat in STATS}
    game_stats = ('total', 'margin', *(f'q{q}_{kind}' for q in range(1, 5) for kind in ('total', 'margin')))
    return {
        'experiment': 'a1_paired_comparison',
        'runs': {'control': control, 'candidate': candidate},
        'population': {'fold': logs[0]['fold'], 'games': len(game_ids), 'game_ids': game_ids,
                       'player_games': len(paired_players),
                       'expected_simulated_player_games': len(expected), 'unscored_simulated_players': gaps.to_dict(orient='records'),
                       'tiers': {tier: int((paired_players['tier'] == tier).sum()) for tier in ROLE_TIERS},
                       'selection': str(ids_path) if ids_path else 'exact equality of both complete runs',
                       'availability': 'conditional on actual participants; not an availability forecast'},
        'method': {'bootstrap': 'paired complete-game resampling; player games equally weighted',
                   'replicates': BOOTSTRAP_REPLICATES, 'seed': BOOTSTRAP_SEED, 'confidence': 0.95,
                   'coverage': 'randomised PIT in [0.1, 0.9]',
                   'win_scoring': 'Brier and log loss use empirical probabilities; zero probability on the outcome is infinite',
                   'bias_and_coverage_change': 'change in absolute deviation from 0 and 0.8, respectively',
                   'minimum_player_games': MIN_PLAYER_GAMES, 'minimum_games': MIN_GAMES,
                   'limitations': 'No Holm correction or promotion decision; cutoff safety depends on dated input provenance.'},
        'players': player_results,
        'games': {stat: distribution(paired_games, stat, game_ids, weights, False) for stat in game_stats},
        'win': _win_metrics(paired_games, game_ids, weights),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('control')
    ap.add_argument('candidate')
    ap.add_argument('--game-ids', type=Path, help='explicitly compare this exact subset in both runs')
    ap.add_argument('--output', type=Path, help='new report path; existing reports are never overwritten')
    args = ap.parse_args()
    report = compare(args.control, args.candidate, args.game_ids)
    if args.output:
        if args.output.exists():
            raise FileExistsError(f'refusing to overwrite {args.output}')
        write_json(args.output, report, pretty=True)
        print(f"saved {args.output}: {report['population']['games']} games, {report['population']['player_games']} player-games")
    else:
        print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
