#!/usr/bin/env python3
"""Audit a saved single-game foul-penalty probe whose summary write failed."""
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
from scripts import a1_substitution_world_audit  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run')
    parser.add_argument('--log', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f'refusing to overwrite {args.output}')
    log = args.log.read_text()
    if 'game 1/1' not in log or 'Out of range float values are not JSON compliant: nan' not in log:
        raise ValueError('single-game log does not show both a completed simulation and the summary failure')
    games_path = DERIVED / 'experiments' / f'{args.run}.parquet'
    players_path = DERIVED / 'experiments' / f'{args.run}_players.parquet'
    manifest_path = ROOT / 'analysis/experiments/20261122_a1_s06_recovery_probe_games.json'
    game_ids = json.loads(manifest_path.read_text())
    if game_ids != ['401810472']:
        raise ValueError('the precommitted probe game manifest differs')
    world_path = DERIVED / 'experiments' / f'{args.run}_worlds/{game_ids[0]}.npz'
    games, players = pd.read_parquet(games_path), pd.read_parquet(players_path)
    if len(games) != 1 or str(games.iloc[0]['game_id']) != game_ids[0]:
        raise ValueError('saved game output differs from the frozen probe')
    if players.duplicated(['game_id', 'player']).any() or set(players['game_id'].astype(str)) != set(game_ids):
        raise ValueError('saved player output keys differ from the frozen probe')
    with np.load(world_path, allow_pickle=False) as data:
        result = a1_substitution_world_audit.audit_worlds(data, foul_penalty=True)
        if result['game_id'] != game_ids[0] or result['worlds'] != 1000:
            raise ValueError('world capture has an unexpected game or world count')
        game = games.iloc[0]
        for side, index in (('home', 0), ('away', 1)):
            if not np.isclose(data['final_score'][:, index].mean(), float(game[f'{side}_sim']),
                              rtol=0, atol=1e-10):
                raise ValueError(f'{side} captured scores differ from the saved game')
        indices = {player: index for index, player in enumerate(data['player_ids'].tolist())}
        for row in players.itertuples(index=False):
            if row.player not in indices:
                raise ValueError(f'player {row.player} is missing from captured worlds')
            player = indices[row.player]
            for label, field in (('pts', 'player_points'), ('min', 'minutes')):
                actual = float(data[field][:, player].sum(axis=1).mean())
                if not np.isclose(actual, getattr(row, f'{label}_sim'), rtol=0, atol=1e-10):
                    raise ValueError(f'player {row.player}: captured {label} differs from the saved output')
        trace = np.flatnonzero(data['technical_world'] == 563)
        if len(trace) != 1 or not np.isclose(data['technical_clock'][trace[0]], 4.4, rtol=0, atol=1e-5):
            raise ValueError('the previously failing world did not record its expected technical event')
        event = {
            'world': 563, 'period': int(data['technical_period'][trace[0]]),
            'clock_seconds_remaining': float(data['technical_clock'][trace[0]]),
            'fouler': str(data['player_ids'][data['technical_fouler'][trace[0]]]),
            'shooter': str(data['player_ids'][data['technical_shooter'][trace[0]]]),
            'made': int(data['technical_made'][trace[0]]),
        }
    inputs = [Path(__file__), ROOT / 'scripts/a1_substitution_world_audit.py', manifest_path,
              games_path, players_path, world_path]
    output = {
        'experiment': 'a1_s06_foul_penalty_single_game_probe_independent_audit',
        'run': args.run, 'simulation_process_status': 'failed_on_single_game_nonfinite_summary_serialization',
        'world_accounting': result, 'saved_player_means_checked': len(players), 'prior_failure_event': event,
        'limitations': 'The 1/1 simulation and saved worlds are audited; the one-game backtest process exited 1 '
                       'while serializing unsupported summary statistics, so this is not a successful complete '
                       'backtest or a paired accuracy result.',
        'input_sha256': {str(path.relative_to(ROOT)): sha256_file(path) for path in inputs},
        'log': str(args.log), 'log_sha256': sha256_file(args.log),
    }
    write_json(args.output, output, pretty=True)
    print(f"audited {result['worlds']} saved worlds, {result['foul_penalty_events']} technical events", flush=True)


if __name__ == '__main__':
    main()
