#!/usr/bin/env python3
"""Independently audit the earlier-year substitution seed targets and dated fits."""
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
from scripts import a1_minutes_fold_eval, a1_substitution_fold_data, minutes, projection  # noqa: E402
from scripts.evaluate import EXPERIMENTS  # noqa: E402


def audit_membership(targets: pd.DataFrame, box: pd.DataFrame) -> dict:
    if targets.duplicated(['game_id', 'player']).any() or targets['prior_day'].ge(targets['date_et']).any():
        raise ValueError('seed targets contain duplicate or non-prior roster entries')
    checked = 0
    for day, day_targets in targets.groupby('date_et', sort=True):
        past = box.loc[box['day'] < day, ['day', 'player', 'team']].drop_duplicates()
        last_day = past.groupby('player')['day'].transform('max')
        latest = past.loc[past['day'].eq(last_day)].copy()
        unique_team = latest.groupby('player')['team'].nunique()
        latest = latest.loc[latest['player'].isin(unique_team[unique_team.eq(1)].index)]
        if latest.duplicated('player').any():
            raise ValueError('independent latest-team reconstruction has duplicate players')
        for (_, team), group in day_targets.groupby(['game_id', 'team']):
            expected = latest.loc[latest['team'].eq(str(team)), ['player', 'day']].set_index('player')['day']
            actual = group.set_index('player')['prior_day']
            if set(expected.index) != set(actual.index) or not expected.sort_index().equals(actual.sort_index()):
                raise ValueError(f'{day} {team}: seed roster or prior box date differs')
            checked += len(group)
    if checked != len(targets):
        raise ValueError('not all seed roster rows were independently checked')
    return {'candidate_rows': checked, 'games': int(targets['game_id'].nunique()),
            'team_games': int(targets[['game_id', 'team']].drop_duplicates().shape[0])}


def audit_profiles(targets: pd.DataFrame, profiles: pd.DataFrame) -> int:
    events = profiles[['date_et', 'player', 'usage', 'start_share']].copy()
    events['day'] = pd.to_datetime(events.pop('date_et'), errors='raise').astype('datetime64[ns]')
    if events.duplicated(['day', 'player']).any():
        raise ValueError('independent profile history has ambiguous player-days')
    left = targets[['date_et', 'player', 'prior_profile_date', 'tier']].copy()
    left['origin'] = pd.to_datetime(left.pop('date_et'), errors='raise').astype('datetime64[ns]')
    joined = pd.merge_asof(left.sort_values(['origin', 'player']), events.sort_values(['day', 'player']),
                           left_on='origin', right_on='day', by='player',
                           direction='backward', allow_exact_matches=False)
    actual = pd.to_datetime(joined['prior_profile_date'], errors='raise')
    if not (actual.eq(joined['day']) | (actual.isna() & joined['day'].isna())).all():
        raise ValueError('seed prior profile dates differ from earlier player histories')
    usage = pd.to_numeric(joined['usage'], errors='raise').to_numpy(dtype=float)
    start = pd.to_numeric(joined['start_share'], errors='raise').to_numpy(dtype=float)
    known = np.isfinite(usage) & np.isfinite(start)
    tier = np.select([~known, usage >= .25, start >= .5], ['unknown', 'star', 'starter'], default='bench')
    if not np.array_equal(joined['tier'].to_numpy(), tier):
        raise ValueError('seed prior role tiers differ from earlier player profiles')
    return len(joined)


def same_tables(a: dict, b: dict) -> bool:
    if a.keys() != b.keys():
        return False
    return all(np.allclose(np.asarray(a[key], dtype=float), np.asarray(b[key], dtype=float),
                           rtol=0, atol=1e-12, equal_nan=True) for key in a)


def audit_dated_draws(targets: pd.DataFrame) -> dict:
    fit_before = a1_substitution_fold_data.SEED_FIT_BEFORE
    seed_start = a1_substitution_fold_data.SEED_START
    model = minutes.build(fit_before, include_current=False, upto=seed_start)
    coach = minutes.coach_dnps(include_current=False)
    modified = model['pg'].copy()
    changed = modified['date_et'].ge(fit_before)
    modified.loc[changed, 'reg'] = 0.0
    original_rows, _, _ = minutes.state_pass(model['pg'], model['params'], None, seed_start)
    changed_rows, _, _ = minutes.state_pass(modified, model['params'], None, seed_start)
    original_ramp = minutes.learn_ramp(model['pg'], original_rows, fit_before)
    changed_ramp = minutes.learn_ramp(modified, changed_rows, fit_before)
    if not same_tables(original_ramp, changed_ramp) or not same_tables(original_ramp, model['ramp']):
        raise ValueError('post-cutoff minute outcomes altered the fitted seed ramp')
    original_states, _, _ = minutes.state_pass(model['pg'], model['params'], original_ramp, seed_start, coach)
    changed_states, _, _ = minutes.state_pass(modified, model['params'], changed_ramp, seed_start, coach)
    original_sd = minutes.residual_sd(model['pg'], original_states, fit_before)
    changed_sd = minutes.residual_sd(modified, changed_states, fit_before)
    if original_sd['edges'] != changed_sd['edges'] or any(
            not same_tables(original_sd[key], changed_sd[key]) or not same_tables(original_sd[key], model['sd'][key])
            for key in ('sd', 'mean', 'n')):
        raise ValueError('post-cutoff minute outcomes altered the fitted seed residual spread')
    games = targets[['game_id', 'date_et']].drop_duplicates().sort_values(['date_et', 'game_id'])
    sample_ids = list(dict.fromkeys([games.iloc[0]['game_id'], games.iloc[-1]['game_id']]))
    maximum_error, rows_checked = 0.0, 0
    for (day, game_id, team), part in targets.loc[targets['game_id'].isin(sample_ids)].groupby(
            ['date_et', 'game_id', 'team'], sort=True):
        _, latest, team_dates = minutes.state_pass(model['pg'], model['params'], original_ramp, str(day), coach)
        if any(value >= day for dates in team_dates.values() for value in dates):
            raise ValueError('sampled seed states include a same-day or future team game')
        dated = {**model, 'latest': latest, 'team_dates': team_dates}
        part = part.sort_values('player', kind='stable')
        states = [minutes.player_state(dated, str(team), str(player), str(day)) for player in part['player']]
        mean = minutes.game_targets(states)
        sd = minutes.sd_for(original_sd, mean)
        seed = projection.seed_for('a1_s06_seed_targets', str(game_id), str(team))
        draws = minutes.redraw(mean, [state['cap'] for state in states], sd, 1000, np.random.default_rng(seed))
        error = np.abs(draws.mean(axis=0) - part['control_mean'].to_numpy(dtype=float))
        maximum_error = max(maximum_error, float(error.max()))
        rows_checked += len(part)
    if maximum_error > 1e-12:
        raise ValueError('recomputed seed target draws differ from the saved targets')
    return {'fit_before': fit_before, 'post_cutoff_player_games_perturbed': int(changed.sum()),
            'sample_game_ids': sample_ids, 'sample_target_rows': rows_checked,
            'maximum_reproduction_error': maximum_error}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=EXPERIMENTS / '20261122_a1_s06_seed_v3_audit.json')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an existing seed audit')
    report_path, rows_path, _, target_path = a1_substitution_fold_data.paths_for('seed')
    if target_path is None:
        raise ValueError('seed target output is not configured')
    source = json.loads(report_path.read_text())
    for path, digest in source['input_sha256'].items():
        if sha256_file(ROOT / path) != digest:
            raise ValueError(f'seed source changed: {path}')
    for path in (rows_path, target_path):
        if source['output_sha256'].get(str(path.relative_to(ROOT))) != sha256_file(path):
            raise ValueError(f'seed output changed: {path}')
    targets = pd.read_parquet(target_path)
    if (targets.empty or not targets['date_et'].between(a1_substitution_fold_data.SEED_START,
                                                         a1_substitution_fold_data.SEED_END).all()
            or targets['date_et'].le(source['seed_fit_before']).any()):
        raise ValueError('seed target dates differ from the fixed pre-origin training window')
    columns = ['game_id', 'game_date', 'athlete_id', 'team_id', 'season_type']
    raw = pd.read_parquet(ROOT / 'data/raw/hoopr/player_box_2023.parquet', columns=columns)
    raw = raw.loc[raw['season_type'].eq(2)].dropna(subset=['game_date', 'athlete_id', 'team_id']).copy()
    raw['day'] = pd.to_datetime(raw['game_date'], errors='raise').dt.strftime('%Y-%m-%d')
    raw['player'] = raw['athlete_id'].astype('int64').astype(str)
    raw['team'] = raw['team_id'].astype('int64').astype(str)
    teams = set(json.loads((DERIVED / 'teams.json').read_text()))
    raw = raw.loc[raw['team'].isin(teams)]
    membership = audit_membership(targets, raw)
    profiles = pd.read_parquet(a1_minutes_fold_eval.CAUSAL_PROFILES,
                               columns=['date_et', 'player', 'usage', 'start_share'])
    profile_rows = audit_profiles(targets, profiles)
    means = targets.groupby(['game_id', 'team'])['control_mean'].sum()
    maximum_team_error = float((means - 240).abs().max())
    if maximum_team_error > .001:
        raise ValueError('seed mean regulation targets do not reconcile to 240 minutes')
    dated = audit_dated_draws(targets)
    segments = pd.read_parquet(DERIVED / 'history/2023/segments.parquet',
                               columns=['game_id', 'date_et', 'game_ok', 'season_type',
                                        'offense', 'defense', 'off_home'])
    selected = a1_substitution_fold_data.seed_games(segments)
    if sorted(selected['game_id'].tolist()) != source['requested_game_ids']:
        raise ValueError('seed game selection differs from the frozen deterministic sample')
    inputs = [report_path, rows_path, target_path, Path(__file__)]
    report = {'experiment': 'a1_s06_seed_target_independent_audit', 'membership': membership,
              'profile_rows_checked': profile_rows, 'maximum_team_mean_minute_error': maximum_team_error,
              'dated_draws_and_future_injection': dated, 'fixed_selected_games': len(selected),
              'input_sha256': {str(path.relative_to(ROOT)): sha256_file(path) for path in inputs}}
    write_json(args.output, report, pretty=True)
    print(f"audited {membership['candidate_rows']} seed targets across {membership['games']} games; "
          f"sample reproduction max error {dated['maximum_reproduction_error']:.3g}", flush=True)


if __name__ == '__main__':
    main()
