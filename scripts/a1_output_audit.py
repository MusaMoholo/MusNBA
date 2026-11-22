#!/usr/bin/env python3
"""Independently audit new A1 backtest outputs and legacy-stream reproduction.

  .venv/bin/python scripts/a1_output_audit.py RUN --reference ORIGINAL --output new-report.json
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
from scripts import a1_compare, a1_manifest, backtest, train  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS  # noqa: E402


def _equal(left: pd.Series, right: pd.Series, label: str) -> None:
    if pd.api.types.is_numeric_dtype(left) and pd.api.types.is_numeric_dtype(right):
        equal = np.isclose(left.to_numpy(dtype=float), right.to_numpy(dtype=float), rtol=0, atol=1e-12, equal_nan=True)
    else:
        equal = (left.eq(right) | (left.isna() & right.isna())).to_numpy()
    if not equal.all():
        raise ValueError(f'{label} differs on {int((~equal).sum())} rows')


def legacy_check(new: pd.DataFrame, old: pd.DataFrame, keys: list[str], label: str) -> dict:
    old = old[old['game_id'].isin(new['game_id'])]
    a1_compare._same_keys(old, new, keys, label)
    old = old.set_index(keys).sort_index()
    new = new.set_index(keys).sort_index()
    missing = old.columns.difference(new.columns)
    if len(missing):
        raise ValueError(f'{label}: missing legacy columns {missing.tolist()}')
    for column in old.columns:
        _equal(old[column], new[column], f'{label} {column}')
    return {'rows': len(old), 'columns': len(old.columns), 'absolute_tolerance': 1e-12}


def audit(run: str, reference: str | None = None, pin_current_inputs: bool = False) -> dict:
    log = json.loads((EXPERIMENTS / f'{run}.json').read_text())
    frame = pd.read_parquet(DERIVED / 'experiments' / f'{run}.parquet')
    players = pd.read_parquet(DERIVED / 'experiments' / f'{run}_players.parquet')
    a1_compare._unique(frame, ['game_id'], 'games')
    a1_compare._unique(players, ['game_id', 'player'], 'players')
    if set(frame['game_id']) != set(players['game_id']):
        raise ValueError('games and player outputs do not have the same game IDs')
    _, _, val_to = FOLDS[log['fold']]
    season = int(val_to[:4]) if val_to[5:7] <= '06' else int(val_to[:4]) + 1
    columns = ['game_id', 'period_number', 'sequence_number', 'home_score', 'away_score',
               'home_team_id', 'away_team_id', 'type_text']
    raw = pd.read_parquet(ROOT / f'data/raw/hoopr/play_by_play_{season}.parquet', columns=columns)
    raw['game_id'] = raw['game_id'].astype('int64').astype(str)
    ends = raw[raw['game_id'].isin(frame['game_id']) & raw['type_text'].str.contains('End Period|End Game', case=False, na=False)]
    ends = (ends.sort_values(['game_id', 'period_number', 'sequence_number'])
            .groupby(['game_id', 'period_number'], as_index=False).tail(1)
            .sort_values(['game_id', 'period_number']).copy())
    for side in ('home', 'away'):
        score = f'{side}_score'
        ends[f'{side}_period'] = ends.groupby('game_id')[score].diff().fillna(ends[score])
    for q in range(1, 5):
        end = ends[ends['period_number'] == q]
        joined = frame.merge(end, on='game_id', how='left', validate='one_to_one')
        if joined[['home_period', 'away_period']].isna().any().any():
            raise ValueError(f'quarter {q}: missing scoreboard period end')
        for side in ('home', 'away'):
            _equal(joined[side].astype(str), joined[f'{side}_team_id'].astype('int64').astype(str), f'quarter {q} {side} team')
        for label, actual in (('total', joined['home_period'] + joined['away_period']),
                              ('margin', joined['home_period'] - joined['away_period'])):
            _equal(joined[f'q{q}_{label}_actual'], actual, f'quarter {q} {label} actual')
            for suffix in ('sim', 'crps', 'pit'):
                values = joined[f'q{q}_{label}_{suffix}'].to_numpy(dtype=float)
                if not np.isfinite(values).all() or (suffix == 'crps' and (values < -1e-9).any()) \
                   or (suffix == 'pit' and ((values < 0) | (values > 1)).any()):
                    raise ValueError(f'quarter {q} {label} has invalid {suffix}')
        if (joined[f'q{q}_total_sim'] + 1e-9 < joined[f'q{q}_margin_sim'].abs()).any():
            raise ValueError(f'quarter {q} simulated total is below the absolute margin')
    for side, sign in (('home', 1), ('away', -1)):
        regulation = (frame['q1_total_sim'] + sign * frame['q1_margin_sim']) / 2
        for q in range(2, 5):
            regulation = regulation + (frame[f'q{q}_total_sim'] + sign * frame[f'q{q}_margin_sim']) / 2
        if (regulation > frame[f'{side}_sim'] + 1e-9).any():
            raise ValueError(f'{side} regulation simulated points exceed full-game points')
        no_overtime = frame['sim_ot'].eq(0)
        _equal(regulation[no_overtime], frame.loc[no_overtime, f'{side}_sim'], f'{side} regulation without simulated OT')
    box = pd.read_parquet(ROOT / f'data/raw/hoopr/player_box_{season}.parquet',
                          columns=['game_id', 'athlete_id', 'team_id', 'three_point_field_goals_made'])
    box = box.dropna(subset=['athlete_id', 'team_id'])
    box['game_id'] = box['game_id'].astype('int64').astype(str)
    box['player'] = box['athlete_id'].astype('int64').astype(str)
    box['team'] = box['team_id'].astype('int64').astype(str)
    box = box[box['game_id'].isin(frame['game_id'])]
    joined = players.merge(box[['game_id', 'player', 'team', 'three_point_field_goals_made']], on=['game_id', 'player'],
                           how='left', validate='one_to_one', indicator=True)
    if joined['_merge'].ne('both').any():
        raise ValueError('player outputs include IDs missing from the raw box')
    _equal(joined['fg3m_actual'], joined['three_point_field_goals_made'], '3PM actual')
    spec = json.loads((ROOT / log['config']).read_text())
    pre, *_ = backtest.load_inputs(spec, log['fold'])
    expected = pre.loc[pre['game_id'].isin(frame['game_id']), ['game_id', 'player', 'team']]
    gaps = a1_compare.roster_gaps(expected, joined)
    gap_teams = pd.MultiIndex.from_frame(gaps[['game_id', 'team']])
    known = joined['fg3m_actual'].notna()
    for suffix in ('sim', 'crps', 'pit'):
        values = joined.loc[known, f'fg3m_{suffix}'].to_numpy(dtype=float)
        if not np.isfinite(values).all() or (suffix == 'crps' and (values < -1e-9).any()) \
           or (suffix == 'pit' and ((values < 0) | (values > 1)).any()):
            raise ValueError(f'3PM has invalid {suffix}')
    team = joined.groupby(['game_id', 'team'])['fg3m_sim'].agg(['sum', 'count', 'size']).reset_index()
    incomplete_teams = 0
    incomplete_rosters = 0
    for side in ('home', 'away'):
        values = frame[['game_id', side, f'sim_fg3m_{side}']].merge(
            team, left_on=['game_id', side], right_on=['game_id', 'team'], how='left', validate='one_to_one')
        if values['size'].isna().any():
            raise ValueError(f'{side} has no matched player 3PM outputs')
        roster_missing = pd.MultiIndex.from_arrays([values['game_id'], values[side]]).isin(gap_teams)
        incomplete_rosters += int(roster_missing.sum())
        incomplete = values['count'].ne(values['size']) | roster_missing
        incomplete_teams += int(incomplete.sum())
        _equal(values.loc[~incomplete, f'sim_fg3m_{side}'], values.loc[~incomplete, 'sum'], f'{side} player/team 3PM means')
    report = {'experiment': 'a1_output_accounting', 'run': run, 'games': len(frame), 'player_games': len(players),
              'expected_simulated_player_games': len(expected), 'player_games_without_output': len(gaps),
              'missing_player_outputs': gaps.to_dict(orient='records'),
              'quarter_scoreboard_comparisons': 8 * len(frame), 'quarter_mismatches': 0,
              'player_3pm_box_comparisons': int(known.sum()), 'player_3pm_missing_actuals': int((~known).sum()),
              'player_3pm_mismatches': 0, 'team_3pm_mean_comparisons': 2 * len(frame) - incomplete_teams,
              'team_3pm_incomplete': incomplete_teams, 'team_3pm_incomplete_rosters': incomplete_rosters,
              'team_3pm_mean_mismatches': 0}
    if reference:
        old = pd.read_parquet(DERIVED / 'experiments' / f'{reference}.parquet')
        old_players = pd.read_parquet(DERIVED / 'experiments' / f'{reference}_players.parquet')
        report['legacy_reproduction'] = {'reference': reference,
                                         'games': legacy_check(frame, old, ['game_id'], 'game'),
                                         'players': legacy_check(players, old_players, ['game_id', 'player'], 'player')}
    if pin_current_inputs:
        feature_path = Path(spec.get('default', {}).get('features') or DERIVED / 'features' / 'pregame.parquet')
        feature_path = feature_path if feature_path.is_absolute() else ROOT / feature_path
        folder = train.MODELS / log['models']
        config = json.loads((folder / 'config.json').read_text())
        paths = [ROOT / 'basketball_common.py', ROOT / log['config'], feature_path,
                 feature_path.parent / 'team_pregame.parquet', feature_path.parent / 'features_report.json',
                 DERIVED / 'experiments' / f'{run}.parquet', DERIVED / 'experiments' / f'{run}_players.parquet',
                 EXPERIMENTS / f'{run}.json', DERIVED / 'teams.json', DERIVED / 'athletes.parquet',
                 DERIVED / 'history' / str(season) / 'stints.parquet',
                 DERIVED / 'history' / str(season) / 'player_periods.csv.gz',
                 ROOT / 'data' / 'raw' / 'hoopr' / f'play_by_play_{season}.parquet']
        paths += [ROOT / 'scripts' / f'{name}.py' for name in (
            'a1_manifest', 'a1_output_audit', 'aggregate', 'backtest', 'engine', 'evaluate', 'features', 'matchups', 'minutes', 'nodes',
            'pbp', 'plays', 'projection', 'rotations', 'train')]
        paths += a1_manifest.model_paths(folder)
        if (folder / 'meta.json').exists():
            paths.append(folder / 'meta.json')
        for history in sorted((DERIVED / 'history').glob('*/')):
            paths += [history / 'segments.parquet', history / 'on_court.parquet']
        paths += sorted((ROOT / 'data' / 'raw' / 'hoopr').glob('player_box_*.parquet'))
        if config.get('matchup'):
            matchup = Path(config['matchup'])
            paths.append(matchup if matchup.is_absolute() else ROOT / matchup)
        report['input_fingerprints'] = [a1_manifest.fingerprint(p) for p in paths]
        report['fingerprint_scope'] = ('Files hashed at audit time; verify they did not change since the run. '
                                       'The log commit is only Git HEAD when the worktree is dirty.')
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('run')
    ap.add_argument('--reference', help='legacy run to reproduce on this run’s exact games')
    ap.add_argument('--pin-current-inputs', action='store_true',
                    help='hash current source, model and feature files; only meaningful if unchanged since the run')
    ap.add_argument('--output', type=Path, required=True, help='new report path; existing reports are never overwritten')
    args = ap.parse_args()
    if args.output.exists():
        raise FileExistsError(f'refusing to overwrite {args.output}')
    report = audit(args.run, args.reference, args.pin_current_inputs)
    write_json(args.output, report, pretty=True)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
