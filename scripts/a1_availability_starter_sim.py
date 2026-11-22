#!/usr/bin/env python3
"""Explore no-report fallback starter frequencies on inferred historical rosters."""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, atomic_bytes, sha256_file, write_json  # noqa: E402
from scripts import (a1_availability_baseline, a1_compare, a1_flow_compare, a1_minutes_fold_eval,
                     a1_minutes_unconditional, minutes, projection)  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS  # noqa: E402

WORLDS = 10_000


def simulate(states: list[dict], positions: list[str | None], probability: np.ndarray,
             seed: int, worlds: int = WORLDS) -> tuple[dict, Counter[tuple[int, ...]]]:
    n = len(states)
    if (len(positions) != n or probability.shape != (n,) or n > 63 or worlds <= 0
            or not np.isfinite(probability).all() or ((probability < 0) | (probability > 1)).any()):
        raise ValueError('invalid starter-simulation roster, probabilities or world count')
    bit_values = np.left_shift(np.uint64(1), np.arange(n, dtype=np.uint64))
    active = np.random.default_rng(seed).random((worlds, n)) < probability
    masks, counts = np.unique(active.astype(np.uint64) @ bit_values, return_counts=True)
    lineups: Counter[tuple[int, ...]] = Counter()
    unsupported: Counter[str] = Counter()
    for mask, count in zip(masks, counts):
        indices = [i for i in range(n) if mask & bit_values[i]]
        if len(indices) < 5:
            unsupported['fewer_than_five_active'] += int(count)
            continue
        if any(positions[i] not in ('G', 'F', 'C') for i in indices):
            unsupported['unknown_active_position'] += int(count)
            continue
        picked = minutes.projected_starters([states[i] for i in indices], [str(positions[i]) for i in indices])
        selected = tuple(sorted(indices[i] for i in picked))
        if len(selected) != 5 or len(set(selected)) != 5:
            raise ValueError('starter selector did not produce five distinct active players')
        lineups[selected] += int(count)
    supported = sum(lineups.values())
    if supported + sum(unsupported.values()) != worlds:
        raise ValueError('starter simulation does not partition its worlds')
    return {'worlds': worlds, 'supported_worlds': supported,
            'fewer_than_five_active': unsupported['fewer_than_five_active'],
            'unknown_active_position': unsupported['unknown_active_position']}, lineups


def evaluate(fold: str) -> tuple[dict, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    started = time.monotonic()
    baseline = EXPERIMENTS / f'20261122_a1_s07_baseline_{fold}.json'
    accounting_path = EXPERIMENTS / f'20261122_a1_s07_baseline_{fold}_accounting_v2.json'
    rows_path = DERIVED / f'experiments/20261122_a1_s07_baseline_{fold}.parquet'
    teams_path = DERIVED / f'experiments/20261122_a1_s07_baseline_{fold}_teams.parquet'
    accounting = json.loads(accounting_path.read_text())
    for path in (baseline, rows_path, teams_path):
        if accounting['input_sha256'].get(str(path.relative_to(ROOT))) != sha256_file(path):
            raise ValueError(f'{fold}: audited starter input differs: {path}')
    for path, digest in json.loads(baseline.read_text())['input_sha256'].items():
        if sha256_file(ROOT / path) != digest:
            raise ValueError(f'{fold}: baseline source changed: {path}')
    manifest = json.loads(a1_minutes_fold_eval.PREREG.read_text())
    games, segments = a1_minutes_unconditional.fixed_games(manifest, fold)
    ids = sorted(games['game_id'].tolist())
    rows = pd.read_parquet(rows_path)
    if rows.duplicated(['game_id', 'team', 'player']).any() or not rows['fold'].eq(fold).all():
        raise ValueError(f'{fold}: inferred roster keys or fold are invalid')
    if not rows['prior_day'].lt(rows['date_et']).all():
        raise ValueError(f'{fold}: inferred roster uses a same-day or future listing')
    actual, coverage, box_path = a1_availability_baseline.raw_starters(fold, games)
    expected_teams = {(str(row.game_id), str(team)) for row in games.itertuples(index=False)
                      for team in (row.home, row.away)}
    seen_teams = set(map(tuple, rows[['game_id', 'team']].drop_duplicates().to_numpy()))
    if not seen_teams.issubset(expected_teams):
        raise ValueError(f'{fold}: an inferred roster is not in the fixed schedule')

    model = minutes.build(FOLDS[fold][1], include_current=False)
    coach = minutes.coach_dnps(include_current=False)
    player_rows, team_rows, lineup_rows = [], [], []
    done, next_report = 0, 20
    for day, date_rows in rows.groupby('date_et', sort=True):
        dated = a1_minutes_unconditional.as_of_model(model, str(day), coach)
        for (gid, team), part in date_rows.groupby(['game_id', 'team'], sort=True):
            part = part.sort_values('player', kind='stable').copy()
            truth = actual.get((str(gid), str(team)))
            if truth is None:
                team_rows.append({'game_id': str(gid), 'team': str(team), 'date_et': str(day),
                                  'status': 'incomplete_observed_starters', 'worlds': 0,
                                  'supported_worlds': 0, 'fewer_than_five_active': 0,
                                  'unknown_active_position': 0, 'actual_starters_outside_candidates': None})
                continue
            states = [minutes.player_state(dated, str(team), str(player), str(day)) for player in part['player']]
            seed = projection.seed_for('a1_s07_starter_frequencies', fold, str(gid), str(team))
            summary, lineups = simulate(states, part['prior_position'].tolist(),
                                        part['availability_fallback'].to_numpy(dtype=float), seed)
            players = part['player'].astype(str).tolist()
            frequencies = np.zeros(len(players), dtype=np.int64)
            for selection, count in lineups.items():
                frequencies[list(selection)] += count
                chosen = tuple(players[i] for i in selection)
                lineup_rows.append({'game_id': str(gid), 'team': str(team), 'players': json.dumps(chosen),
                                    'worlds': count, 'is_actual_five': set(chosen) == truth})
            supported = summary['supported_worlds']
            outside = len(truth - set(players))
            team_rows.append({'game_id': str(gid), 'team': str(team), 'date_et': str(day),
                              'status': 'ok' if supported else 'no_supported_worlds',
                              'actual_starters_outside_candidates': outside, 'seed': str(seed), **summary})
            if supported:
                part['starter_probability'] = frequencies / supported
                part['actual_starter'] = part['player'].astype(str).isin(truth).astype(int)
                part['starter_brier'] = (part['starter_probability'] - part['actual_starter']) ** 2
                part['team_supported_worlds'] = supported
                if not np.isclose(part['starter_probability'].sum(), 5, rtol=0, atol=1e-12):
                    raise ValueError('supported starter probabilities do not sum to five')
                player_rows.append(part[['game_id', 'team', 'player', 'tier', 'starter_probability',
                                         'actual_starter', 'starter_brier', 'team_supported_worlds']])
        done += int(date_rows['game_id'].nunique())
        if done >= next_report or done == rows['game_id'].nunique():
            print(f'{fold}: {done}/{len(games)} games in {time.monotonic() - started:.1f}s', flush=True)
            while next_report <= done:
                next_report += 20
    if not player_rows:
        raise ValueError(f'{fold}: no starter simulation has a supported world')
    players = pd.concat(player_rows, ignore_index=True)
    teams = pd.DataFrame(team_rows)
    lineups = pd.DataFrame(lineup_rows)
    draws = np.random.default_rng(a1_compare.BOOTSTRAP_SEED).integers(
        0, len(ids), (a1_compare.BOOTSTRAP_REPLICATES, len(ids)))
    weights = np.zeros(draws.shape, dtype=np.int16)
    np.add.at(weights, (np.arange(len(draws))[:, None], draws), 1)
    summaries = {
        role: a1_flow_compare.mean_report(players if role == 'all' else players.loc[players['tier'].eq(role)],
                                          ['starter_probability', 'actual_starter', 'starter_brier'],
                                          ids, weights, player=True)
        for role in ('all', *a1_compare.ROLE_TIERS)
    }
    inputs = [Path(__file__), baseline, accounting_path, rows_path, teams_path, a1_minutes_fold_eval.PREREG,
              segments, box_path, DERIVED / 'teams.json', ROOT / 'scripts/minutes.py',
              ROOT / 'scripts/a1_minutes_unconditional.py', ROOT / 'scripts/a1_availability_baseline.py',
              ROOT / 'scripts/projection.py', ROOT / 'scripts/a1_flow_compare.py', ROOT / 'scripts/a1_compare.py',
              ROOT / 'basketball_common.py']
    inputs += sorted((DERIVED / 'history').glob('*/on_court.parquet'))
    inputs += sorted((ROOT / 'data/raw/hoopr').glob('player_box_*.parquet'))
    report = {
        'experiment': 'a1_s07_inferred_roster_starter_frequency_simulation',
        'fold': fold, 'games': len(games), 'worlds_per_team_game': WORLDS,
        'bootstrap_replicates': a1_compare.BOOTSTRAP_REPLICATES, 'bootstrap_seed': a1_compare.BOOTSTRAP_SEED,
        'expected_team_games': len(expected_teams), 'no_prior_roster': len(expected_teams - seen_teams),
        'team_status': {str(k): int(v) for k, v in teams['status'].value_counts().items()},
        'observed_starter_label_coverage': coverage,
        'observed_starters_outside_inferred_rosters': int(teams['actual_starters_outside_candidates'].sum()),
        'worlds': int(teams['worlds'].sum()), 'supported_worlds': int(teams['supported_worlds'].sum()),
        'fewer_than_five_active_worlds': int(teams['fewer_than_five_active'].sum()),
        'unknown_active_position_worlds': int(teams['unknown_active_position'].sum()),
        'player_summaries': summaries, 'seconds': round(time.monotonic() - started, 1),
        'limitations': 'Independent fallback states and inferred prior-box membership are not a dated pre-tip '
                       'physical-availability forecast. Probabilities condition on supported worlds; active unknown '
                       'positions and fewer than five active players are excluded, not repaired. Complete raw '
                       'starter labels are retrospective and missing roster starters remain outside the player score.',
        'input_sha256': {str(path.relative_to(ROOT)): sha256_file(path) for path in dict.fromkeys(inputs)},
    }
    return report, players, teams, lineups


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fold', choices=list(FOLDS), required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--rows-output', type=Path, required=True)
    parser.add_argument('--teams-output', type=Path, required=True)
    parser.add_argument('--lineups-output', type=Path, required=True)
    args = parser.parse_args()
    paths = (args.output, args.rows_output, args.teams_output, args.lineups_output)
    if len({path.resolve() for path in paths}) != len(paths) or any(path.exists() for path in paths):
        raise FileExistsError('starter outputs must be distinct and new')
    report, players, teams, lineups = evaluate(args.fold)
    for path, frame in zip(paths[1:], (players, teams, lineups)):
        atomic_bytes(path, frame.to_parquet(index=False))
    report['output_sha256'] = {str(path.resolve().relative_to(ROOT)): sha256_file(path) for path in paths[1:]}
    write_json(args.output, report, pretty=True)
    print(f'{args.fold}: saved {len(players)} player-games and {len(lineups)} five-player identities', flush=True)


if __name__ == '__main__':
    main()
