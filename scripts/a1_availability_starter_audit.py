#!/usr/bin/env python3
"""Independently replay and reconcile the inferred-roster starter simulation."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, sha256_file, write_json  # noqa: E402
from scripts import a1_availability_baseline, a1_minutes_fold_eval, a1_minutes_unconditional, minutes  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS  # noqa: E402

WORLDS, BOOTSTRAPS, BOOTSTRAP_SEED = 10_000, 10_000, 20261122


def independent_worlds(states: list[dict], positions: list[str | None], probability: np.ndarray,
                       seed: int, worlds: int = WORLDS) -> tuple[dict, np.ndarray, dict[tuple[int, ...], int]]:
    n = len(states)
    if len(positions) != n or probability.shape != (n,) or n > 63 or worlds <= 0:
        raise ValueError('invalid independent starter roster')
    if not np.isfinite(probability).all() or ((probability < 0) | (probability > 1)).any():
        raise ValueError('invalid independent fallback probability')
    active = np.random.default_rng(seed).random((worlds, n)) < probability
    enough = active.sum(axis=1) >= 5
    unknown = np.array([position not in ('G', 'F', 'C') for position in positions], dtype=bool)
    unknown_active = (active & unknown).any(axis=1)
    supported = enough & ~unknown_active
    rank = sorted(range(n), key=lambda i: (-round(states[i]['start_share'], 3), -states[i]['priority'], i))
    selected = np.zeros((worlds, n), dtype=bool)
    slots = np.zeros(worlds, dtype=int)
    counts = {key: np.zeros(worlds, dtype=int) for key in ('G', 'F', 'C')}
    limits = {'G': 3, 'F': 3, 'C': 2}
    for i in rank:
        position = positions[i]
        if position not in limits:
            continue
        take = supported & active[:, i] & (slots < 5) & (counts[position] < limits[position])
        selected[take, i] = True
        slots += take
        counts[position] += take
    for i in rank:
        take = supported & active[:, i] & ~selected[:, i] & (slots < 5)
        selected[take, i] = True
        slots += take
    if not np.all(slots[supported] == 5) or (selected & ~active).any():
        raise ValueError('independent selected fives are invalid')
    bit_values = np.left_shift(np.uint64(1), np.arange(n, dtype=np.uint64))
    masks, values = np.unique(selected[supported].astype(np.uint64) @ bit_values, return_counts=True)
    lineups = {tuple(i for i in range(n) if mask & bit_values[i]): int(count)
               for mask, count in zip(masks, values)}
    details = {'worlds': worlds, 'supported_worlds': int(supported.sum()),
               'fewer_than_five_active': int((~enough).sum()),
               'unknown_active_position': int((enough & unknown_active).sum())}
    return details, selected[supported].sum(axis=0), lineups


def mean_check(rows: pd.DataFrame, column: str, ids: list[str], weights: np.ndarray, result: dict) -> None:
    values = rows[['game_id', column]].copy()
    values['n'] = 1
    grouped = values.groupby('game_id').sum().reindex(ids, fill_value=0)
    n, games = len(rows), int(grouped['n'].gt(0).sum())
    supported = n >= 100 and games >= 30
    if (result['observations'] != n or result['games'] != games or result['missing'] != 0
            or result['status'] != ('ok' if supported else 'insufficient_sample')):
        raise ValueError(f'{column}: player summary support differs')
    expected_mean = float(rows[column].mean()) if n else None
    if expected_mean is None:
        if result['mean'] is not None:
            raise ValueError(f'{column}: empty-group mean is not missing')
    elif not np.isclose(result['mean'], expected_mean, rtol=0, atol=1e-12):
        raise ValueError(f'{column}: player summary mean differs')
    if supported:
        totals = weights @ grouped[[column, 'n']].to_numpy(dtype=float)
        if (totals[:, 1] == 0).any():
            raise ValueError(f'{column}: supported game bootstrap is empty')
        expected_ci = np.quantile(totals[:, 0] / totals[:, 1], [0.025, 0.975])
        if not np.allclose(result['ci_95'], expected_ci, atol=1e-12, rtol=0):
            raise ValueError(f'{column}: player summary interval differs')
    elif result['ci_95'] is not None:
        raise ValueError(f'{column}: unsupported interval was reported')


def audit(fold: str) -> dict:
    started = time.monotonic()
    report_path = EXPERIMENTS / f'20261122_a1_s07_starter_sim_{fold}.json'
    base_path = DERIVED / f'experiments/20261122_a1_s07_baseline_{fold}.parquet'
    players_path = DERIVED / f'experiments/20261122_a1_s07_starter_sim_{fold}.parquet'
    teams_path = DERIVED / f'experiments/20261122_a1_s07_starter_sim_{fold}_teams.parquet'
    lineups_path = DERIVED / f'experiments/20261122_a1_s07_starter_sim_{fold}_lineups.parquet'
    report = json.loads(report_path.read_text())
    for name, digest in {**report['input_sha256'], **report['output_sha256']}.items():
        if sha256_file(ROOT / name) != digest:
            raise ValueError(f'{fold}: starter experiment fingerprint differs: {name}')
    if (report['fold'], report['worlds_per_team_game'], report['bootstrap_replicates'],
            report['bootstrap_seed']) != (fold, WORLDS, BOOTSTRAPS, BOOTSTRAP_SEED):
        raise ValueError(f'{fold}: starter experiment settings differ')
    games, _ = a1_minutes_unconditional.fixed_games(json.loads(a1_minutes_fold_eval.PREREG.read_text()), fold)
    ids = sorted(games['game_id'].tolist())
    baseline, players, teams, lineups = (pd.read_parquet(path) for path in
                                        (base_path, players_path, teams_path, lineups_path))
    keys, team_keys = ['game_id', 'team', 'player'], ['game_id', 'team']
    if baseline.duplicated(keys).any() or players.duplicated(keys).any() or teams.duplicated(team_keys).any():
        raise ValueError(f'{fold}: repeated roster, player or team keys')
    if lineups.duplicated(team_keys + ['players']).any():
        raise ValueError(f'{fold}: repeated five-player identity')
    actual, coverage, _ = a1_availability_baseline.raw_starters(fold, games)
    expected_teams = {(str(row.game_id), str(team)) for row in games.itertuples(index=False)
                      for team in (row.home, row.away)}
    baseline_teams = set(map(tuple, baseline[team_keys].drop_duplicates().to_numpy()))
    if (report['expected_team_games'] != len(expected_teams)
            or report['no_prior_roster'] != len(expected_teams - baseline_teams)
            or report['observed_starter_label_coverage'] != coverage):
        raise ValueError(f'{fold}: starter roster/label coverage differs')
    if set(map(tuple, teams[team_keys].to_numpy())) != baseline_teams:
        raise ValueError(f'{fold}: team outputs differ from inferred rosters')
    model = minutes.build(FOLDS[fold][1], include_current=False)
    coach = minutes.coach_dnps(include_current=False)
    team_index = {(row['game_id'], row['team']): row for row in teams.to_dict('records')}
    player_index = {(row['game_id'], row['team'], row['player']): row for row in players.to_dict('records')}
    lineups_by_team = {key: part for key, part in lineups.groupby(team_keys)}
    checked_players = checked_lineups = supported_worlds = done = 0
    next_report = 20
    for day, date_rows in baseline.groupby('date_et', sort=True):
        dated = a1_minutes_unconditional.as_of_model(model, str(day), coach)
        for (gid, team), part in date_rows.groupby(team_keys, sort=True):
            part = part.sort_values('player', kind='stable')
            key = (str(gid), str(team))
            stored = team_index[key]
            truth = actual.get(key)
            if truth is None:
                if stored['status'] != 'incomplete_observed_starters' or stored['worlds'] != 0:
                    raise ValueError(f'{fold}: incomplete starter label was scored')
                if key in lineups_by_team:
                    raise ValueError(f'{fold}: incomplete starter label has saved lineups')
                continue
            source_states = [minutes.player_state(dated, str(team), str(player), str(day))
                             for player in part['player']]
            seed_bytes = f'a1_s07_starter_frequencies|{fold}|{gid}|{team}'.encode()
            seed = int.from_bytes(hashlib.sha256(seed_bytes).digest()[:8], 'little')
            detail, frequencies, expected_lineups = independent_worlds(
                source_states, part['prior_position'].tolist(), part['availability_fallback'].to_numpy(dtype=float),
                seed)
            for name, value in detail.items():
                if stored[name] != value:
                    raise ValueError(f'{fold}: independent world count differs: {name}')
            if stored['seed'] != str(seed):
                raise ValueError(f'{fold}: starter seed differs')
            names = part['player'].astype(str).tolist()
            if stored['actual_starters_outside_candidates'] != len(truth - set(names)):
                raise ValueError(f'{fold}: observed outside-roster starter count differs')
            count = detail['supported_worlds']
            if stored['status'] != ('ok' if count else 'no_supported_worlds'):
                raise ValueError(f'{fold}: team support status differs')
            actual_lineups = lineups_by_team.get(key)
            if count == 0:
                if actual_lineups is not None:
                    raise ValueError(f'{fold}: unsupported worlds have saved lineups')
                continue
            if actual_lineups is None or len(actual_lineups) != len(expected_lineups):
                raise ValueError(f'{fold}: five-player identity coverage differs')
            expected_by_names = {tuple(names[i] for i in selection): value
                                 for selection, value in expected_lineups.items()}
            for item in actual_lineups.itertuples(index=False):
                if not isinstance(item.players, str):
                    raise ValueError(f'{fold}: five-player identity is not a JSON string')
                selected = tuple(json.loads(item.players))
                if (expected_by_names.get(selected) != item.worlds
                        or bool(item.is_actual_five) != (set(selected) == truth)):
                    raise ValueError(f'{fold}: independently selected five differs')
                checked_lineups += 1
            for index, person in enumerate(names):
                if (key[0], key[1], person) not in player_index:
                    raise ValueError(f'{fold}: supported starter player is missing')
                output = player_index[(key[0], key[1], person)]
                predicted = frequencies[index] / count
                observed = int(person in truth)
                if (not np.isclose(output['starter_probability'], predicted, atol=1e-12, rtol=0)
                        or output['actual_starter'] != observed
                        or not np.isclose(output['starter_brier'], (predicted - observed) ** 2, atol=1e-12, rtol=0)
                        or output['team_supported_worlds'] != count
                        or output['tier'] != part.iloc[index]['tier']):
                    raise ValueError(f'{fold}: independently reconstructed player starter result differs')
                checked_players += 1
            supported_worlds += count
        done += int(date_rows['game_id'].nunique())
        if done >= next_report or done == baseline['game_id'].nunique():
            print(f'{fold}: audited {done}/{len(games)} games in {time.monotonic() - started:.1f}s', flush=True)
            while next_report <= done:
                next_report += 20
    if checked_players != len(players) or checked_lineups != len(lineups):
        raise ValueError(f'{fold}: saved player/lineup coverage differs')
    fields = ('worlds', 'supported_worlds', 'fewer_than_five_active', 'unknown_active_position')
    report_fields = ('worlds', 'supported_worlds', 'fewer_than_five_active_worlds', 'unknown_active_position_worlds')
    if any(int(teams[field].sum()) != report[name] for field, name in zip(fields, report_fields)):
        raise ValueError(f'{fold}: report world accounting differs')
    if report['observed_starters_outside_inferred_rosters'] != int(
            teams['actual_starters_outside_candidates'].sum()):
        raise ValueError(f'{fold}: report outside-roster starter count differs')
    if report['team_status'] != {str(k): int(v) for k, v in teams['status'].value_counts().items()}:
        raise ValueError(f'{fold}: report team status differs')
    draws = np.random.default_rng(BOOTSTRAP_SEED).integers(0, len(ids), (BOOTSTRAPS, len(ids)))
    weights = np.zeros(draws.shape, dtype=np.int16)
    np.add.at(weights, (np.arange(len(draws))[:, None], draws), 1)
    for role in ('all', 'star', 'starter', 'bench', 'unknown'):
        part = players if role == 'all' else players.loc[players['tier'].eq(role)]
        for metric in ('starter_probability', 'actual_starter', 'starter_brier'):
            mean_check(part, metric, ids, weights, report['player_summaries'][role][metric])
    return {
        'experiment': 'a1_s07_starter_frequency_independent_accounting', 'fold': fold,
        'games': len(games), 'player_games': checked_players, 'distinct_fives': checked_lineups,
        'supported_worlds': supported_worlds, 'bootstrap_replicates': BOOTSTRAPS,
        'seconds': round(time.monotonic() - started, 1),
        'limitations': 'Replays independent fallback draws and as-of selection on inferred rosters; '
                       'this does not validate physical availability, independence or pre-tip report coverage.',
        'input_sha256': {str(path.relative_to(ROOT)): sha256_file(path)
                         for path in (Path(__file__), report_path, base_path, players_path, teams_path, lineups_path)},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fold', choices=list(FOLDS), required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f'refusing to overwrite {args.output}')
    result = audit(args.fold)
    write_json(args.output, result, pretty=True)
    print(json.dumps({key: value for key, value in result.items() if key != 'input_sha256'}, indent=2))


if __name__ == '__main__':
    main()
