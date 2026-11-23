#!/usr/bin/env python3
"""Frozen pre-origin inferred-roster input census; no outcome reads or simulation."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
from pathlib import Path
import sys
import time

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from basketball_common import read_json, sha256_file, write_json  # noqa: E402
from scripts import a1_minutes_fold_eval, features  # noqa: E402

AUDIT = ROOT / 'analysis/experiments/20261122_a1_s05_minutes_screen_accounting_corrected.json'
PROTOCOL = ROOT / 'docs/protocols/a1_prior_roster_20261123.md'
INPUT_COLUMNS = ('game_id', 'team', 'player', 'date_et', 'prior_day', 'prior_profile_date',
                 'prior_minutes_date', 'availability_fallback')


def classify(rows: pd.DataFrame, profiles: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    rows = rows.copy()
    if rows.duplicated(['game_id', 'player']).any():
        raise ValueError('duplicate candidate game/player keys')
    for key in ('date_et', 'prior_day', 'prior_profile_date', 'prior_minutes_date'):
        rows[key] = pd.to_datetime(rows[key], errors='raise').dt.strftime('%Y-%m-%d')
    if rows['date_et'].isna().any() or rows['prior_day'].isna().any():
        raise ValueError('missing origin or prior membership date')
    for key in ('prior_day', 'prior_profile_date', 'prior_minutes_date'):
        if (rows[key].notna() & rows[key].ge(rows['date_et'])).any():
            raise ValueError(f'{key} must be strictly before origin')
    p = rows['availability_fallback'].to_numpy(dtype=float)
    if not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError('invalid prior availability assumption')
    source = profiles[['date_et', 'player', 'team', 'pos']].rename(columns={
        'date_et': 'prior_profile_date', 'team': 'profile_team', 'pos': 'prior_position'})
    if source.duplicated(['prior_profile_date', 'player']).any():
        raise ValueError('ambiguous prior profile snapshots')
    out = rows.merge(source, on=['prior_profile_date', 'player'], how='left', validate='many_to_one', indicator=True)
    out['profile_found'] = out.pop('_merge').eq('both')
    out['known_position'] = out['prior_position'].map(features.known_group).notna()
    out['starter_pool'] = False
    teams = []
    for (gid, tid), part in out.groupby(['game_id', 'team'], sort=True):
        possible = part['availability_fallback'].gt(0)
        sure = part['availability_fallback'].ge(0.9)
        pool = sure if sure.sum() >= 5 else possible
        out.loc[part.index, 'starter_pool'] = pool
        missing = part.loc[pool & ~part['known_position'], 'player'].tolist()
        teams.append({'game_id': str(gid), 'team': str(tid), 'candidates': len(part),
                      'possible': int(possible.sum()), 'starter_pool': int(pool.sum()),
                      'missing_profiles': int((~part['profile_found']).sum()),
                      'missing_positions': int((~part['known_position']).sum()),
                      'starter_pool_missing_positions': missing,
                      'supported_starter_pool': bool(pool.sum() >= 5 and not missing),
                      'all_profiles_positions_known': bool(part['profile_found'].all() and part['known_position'].all()),
                      'profile_team_differs': int((part['profile_found'] & part['profile_team'].ne(tid)).sum())})
    return out, teams


def fold_census(fold: str) -> tuple[dict, pd.DataFrame, dict]:
    path = ROOT / f'data/derived/experiments/20261122_a1_s05_no_report_{fold}_corrected.parquet'
    report_path = ROOT / f'analysis/experiments/20261122_a1_s05_no_report_{fold}_corrected.json'
    audit = read_json(AUDIT)
    report = read_json(report_path)
    profile_path = ROOT / a1_minutes_fold_eval.CAUSAL_PROFILES
    for item in (path, report_path):
        if sha256_file(item) != audit['output_sha256'][str(item.relative_to(ROOT))]:
            raise ValueError(f'{fold}: retained cohort differs from independent audit')
    if sha256_file(profile_path) != report['input_sha256'][str(profile_path.relative_to(ROOT))]:
        raise ValueError('prior profile source differs from retained cohort')
    profiles = pd.read_parquet(profile_path, columns=['date_et', 'player', 'team', 'pos'])
    source = pd.read_parquet(path, columns=list(INPUT_COLUMNS))
    manifest = read_json(a1_minutes_fold_eval.PREREG)
    games = a1_minutes_fold_eval.fold_games(manifest, fold)
    if not set(source['game_id']) <= set(games['game_id']):
        raise ValueError(f'{fold}: roster source contains games outside the fixed panel')
    missing_games = sorted(set(games['game_id']) - set(source['game_id']))
    joined = source.merge(games, on='game_id', suffixes=('', '_manifest'))
    if joined['date_et'].ne(joined['date_et_manifest']).any():
        raise ValueError('cohort origin differs from manifest')
    rows, teams = classify(source, profiles)
    rows['fold'] = fold
    team_table = pd.DataFrame(teams)
    if not team_table.groupby('game_id').size().eq(2).all():
        raise ValueError('candidate game does not have exactly two teams')
    supported = team_table.groupby('game_id')['supported_starter_pool'].all().reindex(games['game_id'], fill_value=False)
    all_known = team_table.groupby('game_id')['all_profiles_positions_known'].all().reindex(games['game_id'], fill_value=False)
    order = sorted(games['game_id'], key=lambda gid: hashlib.sha256(
        f'a1-prior-roster-20261123|{fold}|{gid}'.encode()).digest())
    selected = order[:32]
    result = {'fold': fold, 'games': len(games), 'games_with_roster_rows': len(games) - len(missing_games),
              'missing_roster_games': missing_games, 'team_games': len(teams), 'candidates': len(rows),
              'missing_profiles': int((~rows['profile_found']).sum()),
              'missing_positions': int((~rows['known_position']).sum()),
              'starter_pool_missing_positions': int((rows['starter_pool'] & ~rows['known_position']).sum()),
              'supported_starter_pool_games': int(supported.sum()),
              'all_profiles_positions_known_games': int(all_known.sum()),
              'selected_games': selected, 'selected_supported': int(supported.loc[selected].sum()),
              'selected_all_known': int(all_known.loc[selected].sum()), 'teams': teams}
    fingerprints = {str(p.relative_to(ROOT)): sha256_file(p) for p in
                    (path, report_path, profile_path, AUDIT, a1_minutes_fold_eval.PREREG)}
    return result, rows, fingerprints


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    args = parser.parse_args()
    if not args.name.isidentifier() or not args.name.isascii():
        raise ValueError('name must be an ASCII identifier')
    output = ROOT / f'analysis/experiments/{args.name}.json'
    row_path = ROOT / f'data/derived/experiments/{args.name}.parquet'
    if output.exists() or row_path.exists():
        raise FileExistsError('refusing to overwrite a census')
    started = time.monotonic()
    with ProcessPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(fold_census, ('F1', 'F2', 'F3', 'F4')))
    fingerprints = {str(p.relative_to(ROOT)): sha256_file(p) for p in (Path(__file__), PROTOCOL)}
    for _, _, values in results:
        fingerprints.update(values)
    rows = pd.concat([item[1] for item in results], ignore_index=True)
    rows.to_parquet(row_path, index=False)
    write_json(output, {'kind': 'prior-origin inferred-roster input coverage, no outcomes or simulations',
                       'folds': [item[0] for item in results], 'fingerprints': fingerprints,
                       'rows': str(row_path.relative_to(ROOT)), 'rows_sha256': sha256_file(row_path),
                       'outcome_columns_read': [], 'workers': 4, 'elapsed_seconds': time.monotonic() - started,
                       'limitations': ['Prior-box membership is inferred, not an official dated roster.',
                                       'Prior pregame profiles omit the most recent game update.',
                                       'No dated injury calibration or predictive promotion test.']}, pretty=True)
    for fold, _, _ in results:
        print(f"{fold['fold']}: {fold['supported_starter_pool_games']}/200 supported starter-pool contexts; "
              f"{fold['selected_supported']}/32 frozen probe games", flush=True)


if __name__ == '__main__':
    main()
