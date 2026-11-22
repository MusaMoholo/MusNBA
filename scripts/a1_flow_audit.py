#!/usr/bin/env python3
"""Independently account for the opt-in A1 clock, lineup and player-quarter capture."""
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
from scripts import a1_compare, a1_flow_compare  # noqa: E402
from scripts.evaluate import EXPERIMENTS  # noqa: E402


def assert_equal(actual: np.ndarray, expected: np.ndarray, name: str, tolerance: float = 1e-10) -> float:
    actual, expected = np.asarray(actual, dtype=float), np.asarray(expected, dtype=float)
    if actual.shape != expected.shape or np.isinf(actual).any() or np.isinf(expected).any():
        raise ValueError(f'{name}: invalid or differently shaped accounting values')
    if not np.isclose(actual, expected, rtol=0, atol=tolerance, equal_nan=True).all():
        raise ValueError(f'{name}: independent accounting mismatch')
    finite = np.isfinite(actual) & np.isfinite(expected)
    return float(np.max(np.abs(actual[finite] - expected[finite]))) if finite.any() else 0.0


def real_tick_counts(stints: pd.DataFrame, roster: set[str]) -> tuple[int, int, int]:
    ticks = np.arange(5, 2880, 10)
    bounds = stints[['start_t', 'end_t']].to_numpy(dtype=float)
    if not len(bounds) or not np.isfinite(bounds).all() or (bounds[:, 0] > bounds[:, 1]).any():
        raise ValueError('recorded regulation stints are absent or have invalid bounds')
    players = stints['player'].astype(str).to_numpy()
    occupied = (bounds[:, :1] <= ticks) & (ticks < bounds[:, 1:])
    known = np.isin(players, list(roster))
    count = occupied[known].sum(axis=0)
    unknown = occupied[~known].any(axis=0)
    duplicates = np.zeros(len(ticks), dtype=bool)
    for player in np.unique(players[known]):
        duplicates |= occupied[players == player].sum(axis=0) > 1
    valid = (count == 5) & ~unknown & ~duplicates
    return int(valid.sum()), int((~valid).sum()), int((~known).sum())


def audit(run: str, reference: str = a1_flow_compare.REFERENCE) -> tuple[dict, list[Path]]:
    data = DERIVED / 'experiments'
    log_path = EXPERIMENTS / f'{run}.json'
    log = json.loads(log_path.read_text())
    if not log.get('flow_diagnostics') or log.get('fold') != 'F4':
        raise ValueError('run is not an F4 flow-diagnostic capture')
    games_path, players_path = data / f'{run}.parquet', data / f'{run}_players.parquet'
    games, players = pd.read_parquet(games_path), pd.read_parquet(players_path)
    a1_compare._unique(games, ['game_id'], 'flow games')
    a1_compare._unique(players, ['game_id', 'player'], 'flow players')
    ids = set(games['game_id'])
    if len(ids) != log['games'] or set(players['game_id']) != ids:
        raise ValueError('flow games and player outputs do not match the run log')
    reference_games_path = data / f'{reference}.parquet'
    reference_players_path = data / f'{reference}_players.parquet'
    original_games = pd.read_parquet(reference_games_path)
    original_players = pd.read_parquet(reference_players_path)
    original_games = original_games.loc[original_games['game_id'].isin(ids)]
    original_players = original_players.loc[original_players['game_id'].isin(ids)]
    reproduced_games = a1_flow_compare.exact_reproduction(original_games, games, ['game_id'])
    reproduced_players = a1_flow_compare.exact_reproduction(original_players, players, ['game_id', 'player'])

    profile_path = DERIVED / 'variants/matchup/features/pregame.parquet'
    profile = pd.read_parquet(profile_path, columns=['game_id', 'player', 'team'])
    profile = profile.loc[profile['game_id'].isin(ids)]
    a1_compare._unique(profile, ['game_id', 'player'], 'flow roster')
    roster = profile.merge(players[['game_id', 'player']], on=['game_id', 'player'], how='outer',
                           validate='one_to_one', indicator=True)
    if roster['_merge'].eq('right_only').any():
        raise ValueError('flow player output has a player outside the simulated roster')
    missing = roster.loc[roster['_merge'].eq('left_only'), ['game_id', 'team', 'player']]
    complete = roster.groupby(['game_id', 'team'], observed=True)['_merge'].agg(lambda values: values.eq('both').all())
    annotated = players.merge(profile, on=['game_id', 'player'], validate='one_to_one')
    periods_path = DERIVED / 'history/2026/player_periods.csv.gz'
    periods = pd.read_csv(periods_path, usecols=['game_id', 'team_id', 'player_id', 'period', 'pts', 'sec',
                                                'fga', 'fta', 'tov'],
                          dtype={'game_id': str, 'team_id': str, 'player_id': str})
    periods = periods.loc[periods['game_id'].isin(ids)]
    a1_compare._unique(periods, ['game_id', 'team_id', 'player_id', 'period'], 'recorded player-periods')
    source_checks, max_difference = 0, 0.0
    for q in range(1, 5):
        source = periods.loc[periods['period'].eq(q)].rename(columns={'team_id': 'team', 'player_id': 'player'})
        joined = annotated.merge(source, on=['game_id', 'team', 'player'], how='left', validate='one_to_one')
        for stat in ('pts', 'fga', 'fta', 'tov', 'min'):
            expected = joined['sec'].to_numpy(dtype=float) / 60 if stat == 'min' else joined[stat].to_numpy(dtype=float)
            actual = joined[f'q{q}_{stat}_actual'].to_numpy(dtype=float)
            max_difference = max(max_difference, assert_equal(actual, expected, f'quarter {q} {stat} actuals'))
            source_checks += len(actual)

    game_index = games.set_index('game_id')
    sum_checks = 0
    for (game_value, team_value), part in annotated.groupby(['game_id', 'team'], sort=True):
        if not isinstance(game_value, str) or not isinstance(team_value, str):
            raise TypeError('simulated game and team identifiers must be strings')
        gid, team = game_value, team_value
        if not bool(complete.loc[(gid, team)]):
            continue
        game = game_index.loc[gid]
        if team == game['home']:
            side, sign = 'home', 1
        elif team == game['away']:
            side, sign = 'away', -1
        else:
            raise ValueError('simulated player has a team outside the recorded game')
        for q in range(1, 5):
            expected_points = (game[f'q{q}_total_sim'] + sign * game[f'q{q}_margin_sim']) / 2
            actual_points, actual_minutes = part[f'q{q}_pts_sim'].sum(), part[f'q{q}_min_sim'].sum()
            max_difference = max(max_difference, assert_equal(np.array([actual_points, actual_minutes]),
                                                               np.array([expected_points, 60.0]),
                                                               f'{gid} {team} quarter {q}'))
            sum_checks += 2
        for stat in ('pts', 'fga', 'fgm', 'fg3a', 'fg3m', 'fta', 'tov', 'oreb'):
            expected = game[f'{side}_sim'] if stat == 'pts' else game[f'sim_{stat}_{side}']
            value = part[f'{stat}_sim'].sum()
            max_difference = max(max_difference, assert_equal(np.array([value]), np.array([expected]),
                                                               f'{gid} {team} {stat}'))
            sum_checks += 1

    stints_path = DERIVED / 'history/2026/stints.parquet'
    stints = pd.read_parquet(stints_path)
    stints = stints.loc[stints['game_id'].isin(ids) & stints['period'].le(4)]
    segments_path = DERIVED / 'history/2026/segments.parquet'
    segments = pd.read_parquet(segments_path, columns=['game_id', 'duration', 'start_clock'])
    segments = segments.loc[segments['game_id'].isin(ids)]
    tick_checks, clock_checks = 0, 0
    for game in games.itertuples(index=False):
        if not isinstance(game.worlds, (int, np.integer)) or game.worlds <= 0:
            raise ValueError('flow games require a positive integer world count')
        worlds = int(game.worlds)
        source = segments.loc[segments['game_id'].eq(game.game_id)]
        duration = pd.to_numeric(source['duration'], errors='raise').to_numpy(dtype=float)
        clock = pd.to_numeric(source['start_clock'], errors='raise').to_numpy(dtype=float)
        valid = np.isfinite(duration) & np.isfinite(clock)
        if not valid.any() or (duration[valid] < 0).any():
            raise ValueError('recorded clock values are absent or negative')
        observed = np.array([len(source), (~valid).sum(), duration[valid].mean(), (clock[valid] <= 24).mean()])
        saved = np.array([game.flow_clock_recorded_segments, game.flow_clock_recorded_clock_missing,
                          game.flow_clock_recorded_mean_duration, game.flow_clock_recorded_start_at_or_below_24s])
        max_difference = max(max_difference, assert_equal(saved, observed, f'{game.game_id} recorded clock'))
        clock_checks += len(saved)
        for side in ('home', 'away'):
            team = str(getattr(game, side))
            people = set(profile.loc[profile['game_id'].eq(game.game_id) & profile['team'].eq(team), 'player'])
            real = stints.loc[stints['game_id'].eq(game.game_id) & stints['team'].eq(team)]
            expected = real_tick_counts(real, people)
            recorded = tuple(getattr(game, f'flow_rotation_{side}_{name}')
                             for name in ('valid_ticks', 'invalid_ticks', 'unknown_player_stints'))
            if expected != recorded or getattr(game, f'flow_rotation_{side}_ticks') != 288:
                raise ValueError(f'{game.game_id} {team}: recorded lineup ticks do not reconcile')
            valid_ticks = expected[0]
            for name in ('usage', 'fg_rim', 'd_fg_rim'):
                count = getattr(game, f'flow_rotation_{side}_{name}_known_world_ticks')
                if valid_ticks == 0 and pd.isna(count):
                    continue
                if not 0 <= count <= valid_ticks * worlds:
                    raise ValueError(f'{game.game_id} {team}: invalid known-profile world-tick count')
            for name, upper in (('scheduled_exact_five', 1), ('scheduled_matching_slots', 5)):
                value = getattr(game, f'flow_rotation_{side}_{name}')
                if pd.notna(value) and not 0 <= value <= upper:
                    raise ValueError(f'{game.game_id} {team}: invalid lineup overlap')
            tick_checks += 1
    paths = [log_path, games_path, players_path, reference_games_path, reference_players_path,
             profile_path, periods_path, stints_path, segments_path, Path(__file__)]
    report = {
        'experiment': 'a1_s03_flow_independent_accounting', 'run': run, 'reference': reference, 'games': len(games),
        'player_games': len(players), 'original_game_values_reproduced': reproduced_games,
        'original_player_values_reproduced': reproduced_players, 'recorded_player_period_values_checked': source_checks,
        'simulated_team_quarter_and_component_values_checked': sum_checks,
        'recorded_team_lineup_tick_sets_checked': tick_checks, 'recorded_clock_values_checked': clock_checks,
        'max_absolute_difference': max_difference,
        'simulated_roster_players_without_box_output': missing.to_dict(orient='records'),
        'incomplete_roster_team_games': int((~complete).sum()),
        'limitations': 'Team/quarter sums are checked only for sides whose entire simulated roster has player-box '
                       'output. Scheduled fives precede foul-outs and their overlap is not event-level validation.',
    }
    return report, paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run')
    parser.add_argument('--reference', default=a1_flow_compare.REFERENCE,
                        help='same-policy run to reproduce; defaults to the original S01 control')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f'refusing to overwrite {args.output}')
    report, paths = audit(args.run, args.reference)
    report['input_sha256'] = {str(path.relative_to(ROOT)): sha256_file(path) for path in paths}
    write_json(args.output, report, pretty=True)
    print(json.dumps({key: value for key, value in report.items() if key != 'input_sha256'}, indent=2))


if __name__ == '__main__':
    main()
