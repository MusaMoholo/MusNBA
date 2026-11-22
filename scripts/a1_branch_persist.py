#!/usr/bin/env python3
"""Research-only conditional branch capture from an unchanged prospective snapshot's inputs."""
from __future__ import annotations

import argparse
import json
import sys
import time
from copy import deepcopy
from dataclasses import asdict
from datetime import date
from fractions import Fraction
from pathlib import Path

import lightgbm
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, MASTER_CSV, SNAPSHOTS, read_json, sha256_file, write_json  # noqa: E402
from scripts import (a1_branch_world_probe, a1_lineup_branches, a1_substitution_world_audit,  # noqa: E402
                     box_scores, engine, master_fixtures, minutes, nightly, projection)
from scripts.season_stats import period_profiles, player_table, team_table  # noqa: E402


def source_paths(model: str) -> list[Path]:
    folder = engine.MODELS / model
    config = read_json(folder / 'config.json')
    features = engine.features_dir(model)
    segments = Path(config['segments']) if config.get('segments') else DERIVED
    if not segments.is_absolute():
        segments = ROOT / segments
    paths = [
        MASTER_CSV, DERIVED / 'teams.json', DERIVED / 'players.json', DERIVED / 'athletes.parquet',
        *(DERIVED / name for name in ('player_games.csv', 'team_games.csv', 'player_periods.csv')),
        *(DERIVED / 'rotations' / name for name in ('on_court.parquet', 'stints.parquet')),
        *(features / name for name in ('latest.parquet', 'team_latest.parquet', 'pregame.parquet', 'features_report.json')),
        folder / 'config.json', *(folder / node['file'] for node in config['nodes'].values()),
        ROOT / 'basketball_common.py', *sorted((ROOT / 'scripts').glob('*.py')),
        *sorted((segments / 'history').glob('*/segments.parquet')),
        *sorted((DERIVED / 'history').glob('*/on_court.parquet')),
        *sorted((ROOT / 'data/raw/hoopr').glob('player_box_*.parquet')),
    ]
    if config.get('matchup'):
        matchup = Path(config['matchup'])
        paths.append(matchup if matchup.is_absolute() else ROOT / matchup)
    return sorted(set(paths))


def fingerprint(paths: list[Path]) -> dict[str, str]:
    if not paths or any(not path.is_file() for path in paths):
        raise FileNotFoundError('a required branch input or model artifact is missing')
    return {str(path.relative_to(ROOT)): sha256_file(path) for path in paths}


def check_median_cutoff(path: Path, origin: str) -> None:
    dates = pd.read_parquet(path, columns=['date_et'])['date_et']
    if dates.empty or dates.isna().any():
        raise ValueError('model median input has missing dates')
    parsed = pd.to_datetime(dates, format='%Y-%m-%d', errors='raise')
    if (parsed >= pd.Timestamp(origin)).any():
        raise ValueError('model median input contains games on or after the origin')


def quarter_availability(value: float) -> float:
    if not np.isfinite(value) or not 0 <= value <= 1:
        raise ValueError('availability must be finite and between zero and one')
    if value in (0, 1):
        return float(value)
    scaled = Fraction(str(value)) * 4 + Fraction(1, 2)
    return min(3, max(1, scaled.numerator // scaled.denominator)) / 4


def quarter_candidate(game: engine.Game, roster_inputs: dict) -> tuple[engine.Game, dict]:
    """Keep the original game untouched; apply D47 to every prospective roster probability."""
    candidate, inputs = deepcopy(game), deepcopy(roster_inputs)
    for row in inputs.values():
        original = row['availability']
        row['original_availability'] = original
        row['availability'] = quarter_availability(original)
    for index, player_id in enumerate(candidate.ids):
        player_id = str(player_id)
        side_index = int(candidate.side[index])
        side = candidate.sides[side_index]
        local_index = index - int(np.flatnonzero(candidate.side == side_index)[0])
        player = candidate.players[side][local_index]
        if (str(player['id']) != player_id
                or float(candidate.avail[index]) != float(inputs[player_id]['original_availability'])
                or float(player['availability']) != float(inputs[player_id]['original_availability'])):
            raise ValueError(f'player {player_id} availability differs from the original roster')
        player['availability'] = inputs[player_id]['availability']
        candidate.avail[index] = player['availability']
    return candidate, inputs


def checked_snapshot(day: str, game_id: str) -> tuple[dict, dict, dict]:
    if date.fromisoformat(day).isoformat() != day:
        raise ValueError('slate date must be ISO formatted')
    if not game_id.isascii() or not game_id.isdigit():
        raise ValueError('game ID must contain only ASCII digits')
    path = SNAPSHOTS / day
    meta = read_json(path / 'meta.json')
    if meta['slate_date'] != day or meta['kind'] != 'prospective' or meta['origin'] > day:
        raise ValueError('a matching prospective snapshot with a valid origin is required')
    if meta['model'].get('id') != engine.ENGINE['id'] or meta['model'].get('rotation') != 'targets':
        raise ValueError('snapshot does not use the current target-rotation engine')
    model = meta['model'].get('models')
    if model != engine.ENGINE['models'] or meta['model'].get('pool') != engine.ROTATION['pool']:
        raise ValueError('snapshot model or rotation pool does not match the research engine')
    game = next((g for g in master_fixtures.load() if g['game_id'] == game_id and g['date_et'] == day), None)
    saved = read_json(path / 'games.json').get(game_id)
    if game is None or saved is None:
        raise ValueError('game not found in both the master and snapshot')
    inputs = meta['inputs']
    checks = {
        'master_sha256': MASTER_CSV,
        'player_games_sha256': DERIVED / 'player_games.csv',
        'team_games_sha256': DERIVED / 'team_games.csv',
        'player_periods_sha256': DERIVED / 'player_periods.csv',
    }
    if any(inputs.get(key) != sha256_file(file) for key, file in checks.items()):
        raise ValueError('snapshot box-score or master inputs differ from retained files')
    features = engine.features_dir(model)
    paths = {'latest': features / 'latest.parquet', 'team_latest': features / 'team_latest.parquet',
             'stints': DERIVED / 'rotations/stints.parquet', 'on_court': DERIVED / 'rotations/on_court.parquet',
             'models': engine.MODELS / model / 'config.json'}
    if any(inputs['engine_inputs_sha256'].get(key) != sha256_file(file) for key, file in paths.items()):
        raise ValueError('snapshot engine inputs differ from retained files')
    registry_data = read_json(DERIVED / 'players.json')
    registry = registry_data['players']
    if (inputs.get('registry_run') != registry_data['run']
            or saved.get('availability_report') != nightly.forecast_availability_report(game, registry)):
        raise ValueError('snapshot availability report differs from the retained registry')
    config = read_json(engine.MODELS / model / 'config.json')
    if config['train_through'] >= meta['origin']:
        raise ValueError('model training must end before the forecast origin')
    return meta, game, registry


def run(day: str, game_id: str, worlds: int, output: Path, worlds_dir: Path) -> None:
    if worlds < 1:
        raise ValueError('world count must be positive')
    if output.exists() or worlds_dir.exists():
        raise FileExistsError('refusing to overwrite an existing report or capture directory')
    meta, fixture, registry = checked_snapshot(day, game_id)
    model, origin = meta['model']['models'], meta['origin']
    if origin in engine._MINUTES:
        raise ValueError('branch capture requires fresh, uncached origin minutes inputs')
    paths = source_paths(model)
    paths.extend([SNAPSHOTS / day / 'meta.json', SNAPSHOTS / day / 'games.json'])
    before = fingerprint(paths)
    check_median_cutoff(engine.features_dir(model) / 'pregame.parquet', origin)
    team_rows, player_rows = box_scores.load_csv('team_games.csv'), box_scores.load_csv('player_games.csv')
    period_rows = box_scores.load_csv('player_periods.csv')
    teams = read_json(DERIVED / 'teams.json')
    T, lg = team_table(team_rows, origin, teams)
    P = player_table(player_rows, origin)
    Q, priors = period_profiles(period_rows, player_rows, origin, team_rows, blowout=15)
    g = engine.inputs_for(fixture, day, T, lg, P, registry, Q, priors, origin=origin)
    minute_inputs = engine._MINUTES[origin]
    roster_inputs = {}
    for side in g.sides:
        team_id = str(fixture[f'{side}_id'])
        for player in projection.player_inputs(team_id, P, registry, lg, T, True, Q, priors):
            pid = str(player['id'])
            if pid in roster_inputs:
                raise ValueError('duplicate player in origin rosters')
            role = minutes.player_state(minute_inputs, team_id, pid, day)['healthy']
            roster_inputs[pid] = {**player, 'healthy_role': role}
    a1_lineup_branches.select_uncertain(g, registry, minute_inputs['latest'], roster_inputs)
    g, roster_inputs = quarter_candidate(g, roster_inputs)
    selected, rankings = a1_lineup_branches.select_uncertain(g, registry, minute_inputs['latest'], roster_inputs)
    branches = (a1_lineup_branches.enumerate_branches(g, [(p.team_id, p.player_id) for p in selected])
                if selected else ())
    eng = engine.Engine(model) if branches else None
    if branches:
        worlds_dir.mkdir(parents=True)
    records = []
    for number, branch in enumerate(branches):
        assert eng is not None
        start = time.monotonic()
        prepared = a1_lineup_branches.prepare_branch(g, branch.assignments)
        seed = projection.seed_for('lineup-v1', engine.ENGINE['id'], origin, day, game_id, branch.branch_id)
        policy = a1_branch_world_probe.RepairedTrace()
        eng.rotation_policy = policy
        eng.simulate(prepared, worlds, seed)
        st = eng.last
        data = policy.capture(prepared, st)
        data.update({f'box_{name}': values.copy() for name, values in st.box.items()})
        data['possessions'] = st.poss.copy()
        audit = a1_substitution_world_audit.audit_worlds(data)
        path = worlds_dir / f'branch-{number:03d}.npz'
        np.savez_compressed(path, **data)
        weight = None if branch.weight is None else {
            'numerator': str(branch.weight.numerator), 'denominator': str(branch.weight.denominator),
        }
        records.append({'branch_id': branch.branch_id, 'assignments': branch.assignments,
                        'weight': weight, 'seed': str(seed), 'worlds': worlds, 'capture': str(path),
                        'capture_sha256': sha256_file(path), 'audit': audit, 'policy_counts': dict(policy.counts)})
        print(f'branch {number + 1}/{len(branches)}: {worlds} worlds, {time.monotonic() - start:.1f}s', flush=True)
    if fingerprint(paths) != before:
        raise ValueError('an input or model artifact changed during branch capture; results are not valid')
    write_json(output, {
        'schema': 1, 'kind': 'research conditional branches; not a forecast or promotion',
        'game': game_id, 'slate_date': day, 'origin': origin, 'engine': engine.ENGINE['id'], 'model': model,
        'worlds_per_branch': worlds, 'selected': [asdict(player) for player in selected],
        'selection_policy': 'top3-offensive-proxy-one-per-team-v1', 'impact_ranking': rankings,
        'availability_policy': 'D47-nearest-quarter-preserve-uncertain-v1',
        'no_branch_reason': None if selected else "no uncertain player in either team's top three; retain unconditional forecast",
        'weight_assumptions': 'uncalibrated independent availability probabilities',
        'rotation_policy': 'isolated branch-only foul-out repair; short rosters fail',
        'numpy': np.__version__, 'lightgbm': lightgbm.__version__,
        'input_sha256': before, 'branches': records,
    }, pretty=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--day', required=True)
    parser.add_argument('--game', required=True)
    parser.add_argument('--worlds', type=int, default=10000)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--worlds-dir', type=Path, required=True)
    args = parser.parse_args()
    run(args.day, args.game, args.worlds, args.output, args.worlds_dir)


if __name__ == '__main__':
    main()
