#!/usr/bin/env python3
"""Independently reconcile a fixed-panel vector foul-penalty backtest."""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import read_json, sha256_file, write_json  # noqa: E402
from scripts import a1_compare, a1_substitution_world_audit, backtest  # noqa: E402


def crps(values, actual):
    values = np.sort(np.asarray(values, dtype=float))
    n = len(values)
    weights = 2 * np.arange(1, n + 1) - n - 1
    return float(np.abs(values - actual).mean() - (weights @ values) / (n * n))


def close(actual, expected, label):
    if not np.isfinite(actual) or not np.isclose(actual, expected, rtol=0, atol=1e-10):
        raise ValueError(f'{label}: score or sample statistic differs')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an audit')
    report = read_json(args.report)
    derived = ROOT / 'data/derived/experiments'
    name, control = report['run'], report['control']
    if args.report.name != f'{name}.json' or report['fold'] != 'F4' or report['worlds'] != 1000:
        raise ValueError('report name, fold or world count differs')
    if len(report['game_ids']) != (3 if report['pilot'] else 200) or len(report['captures']) != report['games']:
        raise ValueError('panel population differs')

    def verify():
        if any(sha256_file(ROOT / name) != digest for name, digest in report['fingerprints'].items()):
            raise ValueError('source, control, model or input changed')

    verify()
    game_path, player_path = derived / f'{name}.parquet', derived / f'{name}_players.parquet'
    if sha256_file(game_path) != report['game_rows_sha256'] or sha256_file(player_path) != report['player_rows_sha256']:
        raise ValueError('backtest output hash differs')
    games, players = pd.read_parquet(game_path), pd.read_parquet(player_path)
    baseline = pd.read_parquet(derived / f'{control}.parquet')
    baseline_players = pd.read_parquet(derived / f'{control}_players.parquet')
    ids = set(report['game_ids'])
    baseline = baseline[baseline['game_id'].isin(ids)]
    baseline_players = baseline_players[baseline_players['game_id'].isin(ids)]
    a1_compare._same_keys(baseline, games, ['game_id'], 'games')
    a1_compare._same_keys(baseline_players, players, ['game_id', 'player'], 'players')
    paired_games = a1_compare._pair(baseline, games, ['game_id'])
    a1_compare._same_values(paired_games, ('date_et', 'home', 'away', 'real_home', 'real_away',
                                           'real_ot', 'simulation_seed'), 'game facts')
    paired_players = a1_compare._pair(baseline_players, players, ['game_id', 'player'])
    a1_compare._same_values(paired_players, tuple(f'{stat}_actual' for stat in backtest.PLAYER_STATS), 'player facts')
    game_rows = games.set_index('game_id')
    player_rows = players.set_index(['game_id', 'player'])
    started = time.monotonic()
    fives = technicals = player_metrics = 0
    if {entry['game'] for entry in report['captures']} != ids:
        raise ValueError('capture game IDs differ')
    for index, entry in enumerate(report['captures'], 1):
        gid = entry['game']
        path = ROOT / entry['capture']
        if path != derived / f'{name}_worlds' / f'{gid}.npz' or sha256_file(path) != entry['sha256']:
            raise ValueError('capture path or hash differs')
        with np.load(path, allow_pickle=False) as data:
            capture = dict(data)
        if str(capture['game_id']) != gid:
            raise ValueError('capture game ID differs')
        accounting = a1_substitution_world_audit.audit_worlds(capture, foul_penalty=True)
        if accounting['worlds'] != 1000 or accounting['foul_penalty_events'] != entry['technical_events']:
            raise ValueError('capture world or technical count differs')
        fives += accounting['lineup_fives_checked']
        technicals += accounting['foul_penalty_events']
        game_row = game_rows.loc[gid]
        score = capture['final_score']
        for label, values, actual in (
                ('home', score[:, 0], game_row['real_home']),
                ('away', score[:, 1], game_row['real_away']),
                ('total', score.sum(axis=1), game_row['real_home'] + game_row['real_away']),
                ('margin', score[:, 0] - score[:, 1], game_row['real_home'] - game_row['real_away'])):
            close(game_row[f'{label}_sim'], values.mean(), f'{gid} {label} mean')
            close(game_row[f'{label}_crps'], crps(values, actual), f'{gid} {label} CRPS')
        close(game_row['p_home'], (score[:, 0] > score[:, 1]).mean(), f'{gid} win probability')
        player_ids = capture['player_ids'].tolist()
        if len(set(player_ids)) != len(player_ids):
            raise ValueError('capture contains duplicate players')
        for player in players.loc[players['game_id'] == gid, 'player']:
            if player not in player_ids:
                raise ValueError('scored player absent from capture')
            i = player_ids.index(player)
            row = player_rows.loc[(gid, player)]
            samples = {'min': capture['minutes'][:, i].sum(axis=1),
                       'pts': capture['player_points'][:, i].sum(axis=1),
                       'reb': (capture['player_oreb'][:, i] + capture['player_dreb'][:, i]).sum(axis=1),
                       'ast': capture['player_ast'][:, i].sum(axis=1),
                       'fg3m': capture['player_fg3m'][:, i].sum(axis=1)}
            for stat, values in samples.items():
                actual = row[f'{stat}_actual']
                if pd.isna(actual):
                    continue
                close(row[f'{stat}_sim'], values.mean(), f'{gid} {player} {stat} mean')
                close(row[f'{stat}_crps'], crps(values, actual), f'{gid} {player} {stat} CRPS')
                if not 0 <= row[f'{stat}_pit'] <= 1:
                    raise ValueError('player PIT outside [0, 1]')
                player_metrics += 1
        if index % (1 if report['pilot'] else 20) == 0:
            print(f'{index}/{report["games"]} games independently reconciled in '
                  f'{time.monotonic() - started:.1f}s', flush=True)
    verify()
    write_json(args.output, {
        'kind': 'independent fixed-panel vector-penalty accounting; not a promotion',
        'report': str(args.report), 'report_sha256': sha256_file(args.report),
        'games': report['games'], 'worlds_per_game': 1000, 'players': len(players),
        'player_metrics_checked': player_metrics, 'lineup_fives_checked': fives,
        'technical_events': technicals, 'elapsed_seconds': round(time.monotonic() - started, 3),
        'limitations': report['limitations'],
    }, pretty=True)


if __name__ == '__main__':
    main()
