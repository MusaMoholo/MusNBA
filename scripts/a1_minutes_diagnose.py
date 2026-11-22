#!/usr/bin/env python3
"""Reproduce D29 rotation history and compare NBA-only minute-state inputs on A1's fixed panel."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, atomic_bytes, sha256_file, write_json  # noqa: E402
from scripts import a1_compare, a1_flow_compare, a1_minutes_audit, a1_signal, minutes  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS  # noqa: E402

CONTROL = a1_minutes_audit.CONTROL
POPULATION = DERIVED / 'experiments' / '20261122_a1_s05_minutes_population.parquet'


def rotation_events(pg: pd.DataFrame, coach_dnps: dict) -> pd.DataFrame:
    """Reconstruct the production rotation-share updates, retaining each day's final state."""
    team_games = pg[['date_et', 'game_id', 'team']].drop_duplicates()
    a1_compare._unique(team_games, ['game_id', 'team'], 'minutes team games')
    plays = pg[['date_et', 'game_id', 'team', 'player']].copy()
    plays['played'] = 1
    missed = []
    for row in team_games.itertuples(index=False):
        for player in coach_dnps.get((str(row.game_id), str(row.team)), ()):
            missed.append((row.date_et, row.game_id, row.team, str(player), 0))
    dnps = pd.DataFrame(missed, columns=['date_et', 'game_id', 'team', 'player', 'played'])
    events = pd.concat([plays, dnps], ignore_index=True).sort_values(
        ['date_et', 'game_id', 'team', 'played', 'player'], kind='stable')
    if events.duplicated(['game_id', 'player', 'played']).any():
        raise ValueError('rotation history has duplicate play or DNP events')
    conflicts = int(events.duplicated(['game_id', 'player']).sum())
    decay = 0.5 ** (1 / minutes.MINUTES['half_life'])
    states: dict[str, tuple[float, float]] = {}
    shares = []
    for player, played in zip(events['player'].astype(str), events['played'].astype(int)):
        old_s, old_w = states.get(player, (0.8, 1.0))
        new_s, new_w = old_s * decay + played, old_w * decay + 1.0
        states[player] = (new_s, new_w)
        shares.append(new_s / new_w)
    events['rotation_share'] = shares
    events['day'] = pd.to_datetime(events['date_et'], errors='raise')
    result = events.drop_duplicates(['day', 'player'], keep='last').copy()
    result.attrs['conflicting_play_and_coach_dnp'] = conflicts
    return result


def score_groups(rows: pd.DataFrame, ids: list[str], weights: np.ndarray) -> dict:
    entries = {
        'all': pd.Series(True, index=rows.index),
        **{tier: rows['tier'].eq(tier) for tier in a1_compare.ROLE_TIERS},
        'fringe_recent_lt_10': rows['prior_appearances'].ge(3) & rows['recent_five_minutes'].lt(10),
        'core_recent_ge_25': rows['prior_appearances'].ge(3) & rows['recent_five_minutes'].ge(25),
        'recent_team_change_30_days': rows['days_since_team_change'].between(0, 30),
        'core_first_return_after_5_team_games': (rows['prior_appearances'].ge(3) &
                                                rows['recent_five_minutes'].ge(25) &
                                                rows['team_games_since_appearance'].ge(5)),
    }
    names = ['min_actual', 'min_sim', 'min_crps', 'minute_error', 'minute_coverage',
             'target_actual_reg', 'target_control', 'target_clean', 'target_difference',
             'target_mae_difference', 'healthy_difference']
    return {name: a1_flow_compare.mean_report(rows.loc[mask], names, ids, weights, player=True)
            for name, mask in entries.items()}


def rotation_cohorts(rows: pd.DataFrame, ids: list[str], weights: np.ndarray) -> dict:
    labelled = rows.loc[rows['played'].eq(1) | rows['dnp_coach']].copy()
    labelled['rotation_actual'] = labelled['played'].eq(1).astype(float)
    labelled['rotation_error'] = labelled['rotation_share'] - labelled['rotation_actual']
    labelled['rotation_brier'] = (labelled['rotation_error']) ** 2
    labelled['low_share'] = labelled['rotation_share'].lt(0.5)
    masks = {
        'all': pd.Series(True, index=labelled.index),
        'fringe_recent_lt_10': labelled['prior_appearances'].ge(3) & labelled['recent_five_minutes'].lt(10),
        'core_recent_ge_25': labelled['prior_appearances'].ge(3) & labelled['recent_five_minutes'].ge(25),
        'recent_role_ge_15_low_rotation_share': labelled['prior_appearances'].ge(3) &
                                                labelled['recent_five_minutes'].ge(15) & labelled['low_share'],
    }
    names = ['rotation_share', 'rotation_actual', 'rotation_error', 'rotation_brier']
    return {name: a1_flow_compare.mean_report(labelled.loc[mask], names, ids, weights, player=True)
            for name, mask in masks.items()}


def build() -> tuple[dict, pd.DataFrame]:
    manifest = json.loads(a1_signal.MANIFEST.read_text())
    data = DERIVED / 'experiments'
    games_path = data / f'{CONTROL}.parquet'
    players_path = data / f'{CONTROL}_players.parquet'
    games = a1_signal.fixed_games(pd.read_parquet(games_path), manifest)
    ids = sorted(games['game_id'].tolist())
    players = pd.read_parquet(players_path)
    population = pd.read_parquet(POPULATION)
    teams_path = DERIVED / 'teams.json'
    teams = set(json.loads(teams_path.read_text()))
    if len(teams) != 30:
        raise ValueError('canonical NBA team list is not complete')
    print('loading historical minutes and coaching DNPs', flush=True)
    pg = minutes.player_games(include_current=False)
    cd = minutes.coach_dnps(include_current=False)
    bad = pg.loc[~pg['team'].isin(teams)]
    clean = pg.loc[pg['team'].isin(teams)].copy()
    cutoff = FOLDS['F4'][1]
    print(f'building original D29 states ({len(pg)} player-games)', flush=True)
    with patch.object(minutes, 'player_games', return_value=pg):
        original = minutes.build(cutoff, include_current=False)
    print(f'building NBA-only candidate states ({len(clean)} player-games)', flush=True)
    with patch.object(minutes, 'player_games', return_value=clean):
        candidate = minutes.build(cutoff, include_current=False)
    print('replaying original rotation-share updates', flush=True)
    events = rotation_events(pg, cd)
    final = events.sort_values(['day', 'game_id', 'team', 'played'], kind='stable').drop_duplicates('player', keep='last')
    expected = np.array([original['latest'][str(player)]['rotation'] for player in final['player']])
    differences = np.abs(final['rotation_share'].to_numpy(dtype=float) - expected)
    if not len(differences) or differences.max() > 1e-12 or set(final['player']) != set(original['latest']):
        raise ValueError('independent rotation replay does not match the production final states')
    pop = a1_minutes_audit.prior_join(population, events, ['rotation_share']).rename(columns={'day': 'rotation_prior_day'})
    if pop['rotation_share'].isna().any():
        pop.loc[pop['rotation_share'].isna(), 'rotation_share'] = 0.5
    if ((pop['rotation_share'] < 0) | (pop['rotation_share'] > 1)).any():
        raise ValueError('rotation shares must be probabilities in [0,1]')

    cols = ['game_id', 'player', 'team', 'date_et', 'healthy', 'alloc', 'missed', 'k_back']
    orig_rows = original['rows'].loc[original['rows']['game_id'].isin(ids), cols]
    clean_rows = candidate['rows'].loc[candidate['rows']['game_id'].isin(ids), cols]
    a1_compare._same_keys(orig_rows, clean_rows, ['game_id', 'player'], 'minutes history variants')
    compared = orig_rows.merge(clean_rows, on=['game_id', 'player'], suffixes=('_control', '_clean'),
                               validate='one_to_one')
    for col in ('team', 'date_et'):
        if not compared[f'{col}_control'].equals(compared[f'{col}_clean']):
            raise ValueError(f'minutes history variants have different {col}')
    reg = pg[['game_id', 'player', 'reg']]
    a1_compare._unique(reg, ['game_id', 'player'], 'minutes actuals')
    compared = compared.merge(reg, on=['game_id', 'player'], validate='one_to_one')
    coverage = compared[['game_id', 'player']].merge(players[['game_id', 'player']], on=['game_id', 'player'],
                                                     how='outer', indicator=True, validate='one_to_one')
    if coverage['_merge'].eq('right_only').any():
        raise ValueError('fixed-player output lacks corresponding minute-state inputs')
    rows = players.merge(compared, on=['game_id', 'player'], validate='one_to_one')
    pop_fields = ['game_id', 'player', 'prior_appearances', 'recent_five_minutes', 'days_since_team_change',
                  'team_games_since_appearance', 'rotation_share']
    rows = rows.merge(pop[pop_fields], on=['game_id', 'player'], how='left', validate='one_to_one')
    pre = pd.read_parquet(ROOT / 'data/derived/variants/matchup/features/pregame.parquet')
    roles = a1_compare.roles(rows[['game_id', 'player']], pre, games)
    rows = rows.merge(roles, on=['game_id', 'player'], validate='one_to_one')
    if not np.isfinite(rows[['min_actual', 'min_sim', 'min_crps', 'min_pit']].to_numpy(dtype=float)).all():
        raise ValueError('the fixed-player minute outcomes contain missing or non-finite values')
    if not rows['min_pit'].between(0, 1).all():
        raise ValueError('a minute PIT value is outside [0,1]')
    rows['minute_error'] = rows['min_sim'] - rows['min_actual']
    rows['minute_coverage'] = rows['min_pit'].between(0.1, 0.9).astype(float)
    rows['target_actual_reg'] = rows['reg']
    rows['target_control'], rows['target_clean'] = rows['alloc_control'], rows['alloc_clean']
    rows['target_difference'] = rows['target_clean'] - rows['target_control']
    rows['target_mae_difference'] = (rows['target_clean'] - rows['reg']).abs() - (rows['target_control'] - rows['reg']).abs()
    rows['healthy_difference'] = rows['healthy_clean'] - rows['healthy_control']

    draws = np.random.default_rng(a1_compare.BOOTSTRAP_SEED).integers(
        0, len(ids), (a1_compare.BOOTSTRAP_REPLICATES, len(ids)))
    weights = np.zeros(draws.shape, dtype=np.int16)
    np.add.at(weights, (np.arange(len(draws))[:, None], draws), 1)
    source_paths = [a1_signal.MANIFEST, games_path, players_path, POPULATION, teams_path,
                    ROOT / 'scripts/minutes.py', Path(__file__)]
    source_paths += sorted((DERIVED / 'history').glob('*/on_court.parquet'))
    source_paths += sorted((ROOT / 'data/raw/hoopr').glob('player_box_*.parquet'))
    report = {
        'experiment': 'a1_s05_minutes_nba_only_diagnostic',
        'control': CONTROL,
        'method': 'Replay unmodified D29 historical inputs and a separate candidate excluding non-NBA team IDs; '
                  'both use the same fixed pre-validation cutoff, actual-participant team sets and game IDs. '
                  'Rotation share is reconstructed independently from the production play/coach-DNP update.',
        'limitations': 'Targets are conditional on actual participants and are not pre-game forecasts or full-engine '
                       'CRPS. Rotation is scored only on known positive-minute or DNP-coach labels; injury and '
                       'unlisted statuses stay unknown. NBA-only filtering is a candidate, not a promotion.',
        'games': len(ids), 'player_games': len(rows),
        'player_key_coverage': {str(k): int(v) for k, v in coverage['_merge'].value_counts().items()},
        'excluded_non_nba': {'player_games': len(bad), 'games': int(bad['game_id'].nunique()),
                             'by_season': bad.groupby('season').size().to_dict()},
        'rotation_replay': {'players': len(final), 'max_absolute_difference': float(differences.max()),
                            'prior_not_observed_candidates': int(pop['rotation_prior_day'].isna().sum()),
                            'unseen_player_live_prior': 0.5,
                            'conflicting_play_and_coach_dnp': events.attrs['conflicting_play_and_coach_dnp']},
        'baseline_and_target_comparison': score_groups(rows, ids, weights),
        'rotation_calibration': rotation_cohorts(pop, ids, weights),
        'input_sha256': {str(p.relative_to(ROOT)): sha256_file(p) for p in source_paths},
    }
    return report, rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=EXPERIMENTS / '20261122_a1_s05_minutes_diagnostic.json')
    parser.add_argument('--rows-output', type=Path, default=DERIVED / 'experiments' / '20261122_a1_s05_minutes_diagnostic.parquet')
    args = parser.parse_args()
    if args.output.exists() or args.rows_output.exists():
        raise FileExistsError('refusing to overwrite an existing minutes diagnostic')
    report, rows = build()
    atomic_bytes(args.rows_output, rows.to_parquet(index=False))
    write_json(args.output, report, pretty=True)
    print(f"audited {report['games']} games and {report['player_games']} player-games; saved {args.output}", flush=True)


if __name__ == '__main__':
    main()
