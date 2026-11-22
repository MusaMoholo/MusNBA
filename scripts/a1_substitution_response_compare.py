#!/usr/bin/env python3
"""Compare saved Q4 player-minute errors by retrospective realised game state."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, atomic_bytes, sha256_file, write_json  # noqa: E402
from scripts import a1_compare, a1_flow_compare, pbp  # noqa: E402
from scripts.evaluate import EXPERIMENTS  # noqa: E402

CONTROL = '20261122T061053Z_a1_s03_flow_fixed200'


def historical_fouls(raw: pd.DataFrame, box: pd.DataFrame, player_keys: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    if player_keys.duplicated(['game_id', 'player']).any():
        raise ValueError('duplicate historical player-game keys')
    game_ids = set(player_keys['game_id'])
    events = raw.loc[raw['game_id'].isin(game_ids) & raw['period_number'].between(1, 3)].copy()
    period_coverage = events.groupby('game_id')['period_number'].nunique()
    covered_games = set(period_coverage[period_coverage.eq(3)].index)
    personal = events['type_text'].fillna('').map(lambda kind: pbp.is_personal_foul({'type_text': str(kind)}))
    foul_events = events.loc[personal].copy()
    bad_games = set(foul_events.loc[foul_events['athlete_id_1'].isna(), 'game_id'])
    foul_events = foul_events.dropna(subset=['athlete_id_1'])
    foul_events['player'] = foul_events['athlete_id_1'].astype('int64').astype(str)
    counted = foul_events.groupby(['game_id', 'player']).size().rename('q3_fouls').reset_index()
    if box.duplicated(['game_id', 'player']).any():
        raise ValueError('duplicate recorded box foul totals')
    rows = (player_keys.merge(counted, on=['game_id', 'player'], how='left', validate='one_to_one')
            .merge(box[['game_id', 'player', 'fouls']], on=['game_id', 'player'], how='left',
                   validate='one_to_one'))
    rows['q3_fouls'] = rows['q3_fouls'].fillna(0).astype(int)
    final = pd.to_numeric(rows['fouls'], errors='raise')
    if final.lt(0).any():
        raise ValueError('recorded box foul total is negative')
    exceeds = final.notna() & final.lt(rows['q3_fouls'])
    known = (rows['game_id'].isin(covered_games) & ~rows['game_id'].isin(bad_games)
             & final.notna() & ~exceeds)
    rows['foul_state'] = np.select([~known, rows['q3_fouls'].ge(4)],
                                   ['unknown', 'four_plus'], default='under_four')
    rows.loc[~known, 'q3_fouls'] = pd.NA
    coverage = {'games_without_all_q1_q3_periods': sorted(game_ids - covered_games),
                'games_with_unidentified_personal_fouler': sorted(bad_games),
                'unknown_player_foul_states': int((~known).sum()),
                'partial_count_exceeds_final_box': int(exceeds.sum())}
    return rows[['game_id', 'player', 'q3_fouls', 'foul_state']], coverage


def compare(candidate: str) -> tuple[dict, pd.DataFrame, list[Path]]:
    data = DERIVED / 'experiments'
    names = (CONTROL, candidate)
    logs = [json.loads((EXPERIMENTS / f'{name}.json').read_text()) for name in names]
    if any(log['fold'] != 'F4' or log['worlds'] != 1000 or not log.get('flow_diagnostics') for log in logs):
        raise ValueError('state comparison requires matched F4 1,000-world flow outputs')
    games = [pd.read_parquet(data / f'{name}.parquet') for name in names]
    players = [pd.read_parquet(data / f'{name}_players.parquet') for name in names]
    a1_compare._same_keys(games[0], games[1], ['game_id'], 'state comparison games')
    a1_compare._same_keys(players[0], players[1], ['game_id', 'player'], 'state comparison players')
    if len(games[0]) != 200:
        raise ValueError('state comparison requires the complete fixed 200-game panel')
    game_rows = a1_compare._pair(games[0], games[1], ['game_id'])
    a1_compare._same_values(game_rows, ('date_et', 'home', 'away', 'q1_margin_actual',
                                        'q2_margin_actual', 'q3_margin_actual'), 'recorded game state')
    paired = a1_compare._pair(players[0], players[1], ['game_id', 'player'])
    a1_compare._same_values(paired, ('q4_min_actual', 'min_actual'), 'recorded player minutes')
    ids = sorted(game_rows['game_id'].tolist())
    config_path = ROOT / logs[0]['config']
    spec = json.loads(config_path.read_text())
    feature_path = Path(spec.get('default', {}).get('features') or DERIVED / 'features/pregame.parquet')
    feature_path = feature_path if feature_path.is_absolute() else ROOT / feature_path
    profiles = pd.read_parquet(feature_path, columns=['game_id', 'player', 'team', 'date_et', 'usage', 'start_share'])
    roles = a1_compare.roles(paired[['game_id', 'player']], profiles, games[0])
    teams = profiles.loc[profiles['game_id'].isin(ids), ['game_id', 'player', 'team']]
    if teams.duplicated(['game_id', 'player']).any():
        raise ValueError('pregame profile team keys are duplicated')
    paired = paired.merge(roles, on=['game_id', 'player'], validate='one_to_one')
    paired = paired.merge(teams, on=['game_id', 'player'], validate='one_to_one')
    score = game_rows[['game_id', 'home_control', 'away_control']].copy()
    score['home_margin_q4_start'] = sum(game_rows[f'q{q}_margin_actual_control'] for q in range(1, 4))
    paired = paired.merge(score, on='game_id', validate='many_to_one')
    if (~paired['team'].isin(pd.concat([score['home_control'], score['away_control']]).unique())).any():
        raise ValueError('player team is absent from the saved games')
    if (~(paired['team'].eq(paired['home_control']) | paired['team'].eq(paired['away_control']))).any():
        raise ValueError('player team is not in its own game')
    signed_margin = paired['home_margin_q4_start'].where(paired['team'].eq(paired['home_control']),
                                                         -paired['home_margin_q4_start'])
    paired['margin_state'] = np.select([signed_margin.le(-15), signed_margin.ge(15), signed_margin.abs().le(5)],
                                       ['behind_15_plus', 'ahead_15_plus', 'close_5_or_less'],
                                       default='intermediate')

    raw_path = ROOT / 'data/raw/hoopr/play_by_play_2026.parquet'
    box_path = ROOT / 'data/raw/hoopr/player_box_2026.parquet'
    raw = pd.read_parquet(raw_path, columns=['game_id', 'period_number', 'type_text', 'athlete_id_1'])
    raw = raw.dropna(subset=['game_id'])
    raw['game_id'] = raw['game_id'].astype('int64').astype(str)
    box = pd.read_parquet(box_path, columns=['game_id', 'athlete_id', 'fouls']).dropna(
        subset=['game_id', 'athlete_id'])
    box['game_id'] = box['game_id'].astype('int64').astype(str)
    box['player'] = box['athlete_id'].astype('int64').astype(str)
    box = box.loc[box['game_id'].isin(ids)]
    fouls, coverage = historical_fouls(raw, box, paired[['game_id', 'player']])
    paired = paired.merge(fouls, on=['game_id', 'player'], validate='one_to_one')
    actual = paired['q4_min_actual_control']
    if actual.isna().any():
        raise ValueError('Q4 actual minutes are missing')
    for label in ('control', 'candidate'):
        paired[f'q4_{label}_bias'] = paired[f'q4_min_sim_{label}'] - actual
        paired[f'q4_{label}_absolute_error'] = paired[f'q4_{label}_bias'].abs()
    paired['q4_bias_change'] = paired['q4_candidate_bias'] - paired['q4_control_bias']
    paired['q4_absolute_error_change'] = (paired['q4_candidate_absolute_error']
                                           - paired['q4_control_absolute_error'])
    paired['minute_crps_change'] = paired['min_crps_candidate'] - paired['min_crps_control']
    metrics = ['q4_control_bias', 'q4_candidate_bias', 'q4_bias_change',
               'q4_control_absolute_error', 'q4_candidate_absolute_error', 'q4_absolute_error_change',
               'minute_crps_change']
    draws = np.random.default_rng(a1_compare.BOOTSTRAP_SEED).integers(
        0, len(ids), (a1_compare.BOOTSTRAP_REPLICATES, len(ids)))
    weights = np.zeros(draws.shape, dtype=np.int16)
    np.add.at(weights, (np.arange(len(draws))[:, None], draws), 1)
    groups = {}
    for tier in ('all', *a1_compare.ROLE_TIERS):
        base = paired if tier == 'all' else paired.loc[paired['tier'].eq(tier)]
        for dimension, labels in (('margin_state', ('all', 'behind_15_plus', 'ahead_15_plus',
                                                     'close_5_or_less', 'intermediate')),
                                  ('foul_state', ('four_plus', 'under_four', 'unknown'))):
            for label in labels:
                subset = base if label == 'all' else base.loc[base[dimension].eq(label)]
                groups[f'{tier}/{dimension}/{label}'] = a1_flow_compare.mean_report(
                    subset, metrics, ids, weights, player=True)
    paths = [ROOT / 'scripts/a1_substitution_response_compare.py', ROOT / 'scripts/a1_compare.py',
             ROOT / 'scripts/a1_flow_compare.py', ROOT / 'scripts/pbp.py', raw_path, box_path, config_path,
             feature_path,
             *(EXPERIMENTS / f'{name}.json' for name in names),
             *(data / f'{name}{suffix}.parquet' for name in names for suffix in ('', '_players'))]
    result = {
        'experiment': 'a1_s06_realised_state_subgroup_comparison',
        'control': CONTROL, 'candidate': candidate, 'games': len(ids), 'player_games': len(paired),
        'foul_state_coverage': coverage, 'groups': groups,
        'bootstrap_replicates': a1_compare.BOOTSTRAP_REPLICATES, 'bootstrap_seed': a1_compare.BOOTSTRAP_SEED,
        'limitations': 'Conditions on actual Q4-start score and recognised through-Q3 personal fouls after the '
                       'game. Saved simulated Q4 player means are unconditional across simulated states; '
                       'these subgroups do not directly measure the policy response inside simulated worlds. '
                       'Actual participants are supplied, not predicted availability.',
        'input_sha256': {str(path.relative_to(ROOT)): sha256_file(path) for path in paths},
    }
    columns = ['game_id', 'player', 'team', 'tier', 'home_margin_q4_start', 'margin_state',
               'q3_fouls', 'foul_state', *metrics]
    return result, paired[columns], paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--rows-output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.rows_output.exists() or args.output.resolve() == args.rows_output.resolve():
        raise FileExistsError('state comparison outputs must be distinct and new')
    result, rows, _ = compare(args.candidate)
    atomic_bytes(args.rows_output, rows.to_parquet(index=False))
    result['output_sha256'] = {str(args.rows_output.resolve().relative_to(ROOT)): sha256_file(args.rows_output)}
    write_json(args.output, result, pretty=True)
    print(f"compared {result['player_games']} player-games across {result['games']} games", flush=True)


if __name__ == '__main__':
    main()
