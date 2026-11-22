#!/usr/bin/env python3
"""Independently reconcile a frozen S07 availability and starter baseline."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import SupportsFloat

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, sha256_file, write_json  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS  # noqa: E402

MANIFEST = EXPERIMENTS / '20261122_a1_pre_candidate_manifest.json'
KEYS = ['game_id', 'team', 'player']
SEED = 20261122
REPLICATES = 10_000


def check_number(actual: SupportsFloat | None, expected: SupportsFloat | None, label: str) -> None:
    if actual is None or expected is None:
        if actual is not None or expected is not None:
            raise ValueError(f'{label}: one value is missing')
    elif not np.isclose(float(actual), float(expected), rtol=0, atol=1e-12):
        raise ValueError(f'{label}: {actual} differs from {expected}')


def check_mean(summary: dict, rows: pd.DataFrame, column: str, ids: list[str],
               draws: np.ndarray, player: bool = False) -> None:
    values = pd.to_numeric(rows[column], errors='raise')
    valid = values.notna()
    if not np.isfinite(values[valid]).all():
        raise ValueError(f'{column}: non-finite observed value')
    by_game = pd.DataFrame({'game_id': rows.loc[valid, 'game_id'], 'value': values[valid]})
    grouped = by_game.groupby('game_id')['value'].agg(['sum', 'count']).reindex(ids, fill_value=0)
    n, games = int(valid.sum()), int((grouped['count'] > 0).sum())
    status = 'ok' if games >= 30 and (not player or n >= 100) else 'insufficient_sample'
    if (summary['observations'], summary['games'], summary['missing'], summary['status']) != (
            n, games, int((~valid).sum()), status):
        raise ValueError(f'{column}: reported sample or support status differs')
    check_number(summary['mean'], float(values[valid].mean()) if n else None, f'{column} mean')
    if status == 'ok':
        totals = grouped['sum'].to_numpy()[draws].sum(axis=1)
        counts = grouped['count'].to_numpy()[draws].sum(axis=1)
        if (counts == 0).any():
            raise ValueError(f'{column}: empty bootstrap replicate')
        expected = np.quantile(totals / counts, [0.025, 0.975])
        for index in range(2):
            check_number(summary['ci_95'][index], expected[index], f'{column} CI {index}')
    elif summary['ci_95'] is not None:
        raise ValueError(f'{column}: interval reported below support threshold')


def check_probabilities(report: dict, rows: pd.DataFrame, ids: list[str], draws: np.ndarray) -> int:
    known = rows['played'].notna() & ~rows['source_conflict']
    scored = rows.loc[known].copy()
    if (int(known.sum()), int(rows['played'].isna().sum()), int(rows['source_conflict'].sum())) != (
            report['known_play_labels_scored'], report['unknown_play_labels'], report['source_conflicts_excluded']):
        raise ValueError('play-label coverage differs')
    y = scored['played'].to_numpy(dtype=float)
    if not np.isin(y, [0, 1]).all():
        raise ValueError('known play labels are not binary')
    for label, column in (('no_report_availability_fallback', 'availability_fallback'),
                          ('target_positive_frequency', 'control_play_probability')):
        p = scored[column].to_numpy(dtype=float)
        if not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
            raise ValueError(f'{label}: invalid probability')
        scored['audit_brier'] = (p - y) ** 2
        metric = report['play_proxies'][label]
        check_mean(metric['brier'], scored, 'audit_brier', ids, draws, player=True)
        impossible = ((p == 0) & (y == 1)) | ((p == 1) & (y == 0))
        loss = metric['log_loss']
        if loss['impossible_outcomes'] != int(impossible.sum()):
            raise ValueError(f'{label}: impossible prediction count differs')
        if impossible.any():
            if loss['status'] != 'infinite' or loss['value'] is not None:
                raise ValueError(f'{label}: impossible predictions must have infinite loss')
        else:
            if loss['status'] != 'ok':
                raise ValueError(f'{label}: finite loss has incorrect status')
            check_number(loss['value'], float(-np.log(np.where(y == 1, p, 1 - p)).mean()), f'{label} loss')
        for index, cell in enumerate(metric['calibration']):
            mask = (np.minimum((p * 5).astype(int), 4) == index)
            subset = scored.loc[mask]
            if (cell['lower'], cell['upper'], cell['players'], cell['games']) != (
                    index / 5, (index + 1) / 5, int(mask.sum()), subset['game_id'].nunique()):
                raise ValueError(f'{label}: calibration cell {index} counts differ')
            check_number(cell['mean_prediction'], float(p[mask].mean()) if mask.any() else None,
                         f'{label} calibration prediction {index}')
            check_number(cell['observed_play_rate'], float(y[mask].mean()) if mask.any() else None,
                         f'{label} calibration outcome {index}')
    return int(known.sum())


def audit(fold: str) -> dict:
    stem = f'20261122_a1_s07_baseline_{fold}'
    report_path = EXPERIMENTS / f'{stem}.json'
    row_path = DERIVED / f'experiments/{stem}.parquet'
    team_path = DERIVED / f'experiments/{stem}_teams.parquet'
    report = json.loads(report_path.read_text())
    if report['fold'] != fold or report['fitted_before'] != FOLDS[fold][1]:
        raise ValueError(f'{fold}: incorrect fold or fitting cutoff')
    for name in ('input_sha256', 'output_sha256'):
        for path, digest in report[name].items():
            if sha256_file(ROOT / path) != digest:
                raise ValueError(f'{fold}: {name} mismatch for {path}')
    if set(report['output_sha256']) != {str(p.relative_to(ROOT)) for p in (row_path, team_path)}:
        raise ValueError(f'{fold}: report does not fingerprint both outputs')

    manifest = json.loads(MANIFEST.read_text())
    fixed = manifest['control']['games'] if fold == 'F4' else manifest['confirmation'][fold]['games']
    games = pd.DataFrame(fixed)[['game_id', 'date_et']]
    if games['game_id'].duplicated().any() or len(games) != 200:
        raise ValueError(f'{fold}: preregistered game IDs are invalid')
    ids = sorted(games['game_id'].tolist())
    if not games['date_et'].between(FOLDS[fold][1], FOLDS[fold][2]).all():
        raise ValueError(f'{fold}: a game is outside the development fold')
    season = int(FOLDS[fold][2][:4]) + int(FOLDS[fold][2][5:7] > '06')
    segments_path = DERIVED / f'history/{season}/segments.parquet'
    segments = pd.read_parquet(segments_path, columns=['game_id', 'date_et', 'offense', 'defense', 'off_home'])
    segments['game_id'] = segments['game_id'].astype(str)
    segments = segments.loc[segments['game_id'].isin(ids)].copy()
    segments['home'] = np.where(segments['off_home'], segments['offense'], segments['defense']).astype(str)
    segments['away'] = np.where(segments['off_home'], segments['defense'], segments['offense']).astype(str)
    schedule = segments[['game_id', 'date_et', 'home', 'away']].drop_duplicates()
    schedule = games.merge(schedule, on=['game_id', 'date_et'], validate='one_to_one')
    if len(schedule) != 200 or schedule['home'].eq(schedule['away']).any():
        raise ValueError(f'{fold}: incomplete or invalid scheduled sides')
    expected_teams = {(str(row.game_id), str(team)) for row in schedule.itertuples(index=False)
                      for team in (row.home, row.away)}

    rows, teams = pd.read_parquet(row_path), pd.read_parquet(team_path)
    source_path = DERIVED / f'experiments/20261122_a1_s05_no_report_{fold}_corrected.parquet'
    source = pd.read_parquet(source_path)
    if rows.duplicated(KEYS).any() or source.duplicated(KEYS).any() or teams.duplicated(['game_id', 'team']).any():
        raise ValueError(f'{fold}: duplicate saved candidate or team')
    if len(rows) != report['candidate_player_games'] or not rows['fold'].eq(fold).all():
        raise ValueError(f'{fold}: candidate count or fold differs')
    columns = KEYS + ['played', 'source_conflict', 'availability_fallback', 'control_play_probability']
    joined = rows[columns].merge(source[columns], on=KEYS, how='outer', suffixes=('_saved', '_source'),
                                 indicator=True, validate='one_to_one')
    if joined['_merge'].ne('both').any():
        raise ValueError(f'{fold}: candidate keys differ from independently audited S05 cohort')
    for column in columns[len(KEYS):]:
        left, right = joined[f'{column}_saved'], joined[f'{column}_source']
        equal = left.eq(right) | (left.isna() & right.isna())
        if not equal.fillna(False).all():
            raise ValueError(f'{fold}: saved {column} differs from S05 cohort')
    if not (pd.to_datetime(rows['prior_day']) < pd.to_datetime(rows['date_et'])).all():
        raise ValueError(f'{fold}: membership is not strictly before the origin')
    profile_date = pd.to_datetime(rows['prior_profile_date'])
    if (profile_date.notna() & profile_date.ge(pd.to_datetime(rows['date_et']))).any():
        raise ValueError(f'{fold}: a player profile is not strictly before the origin')

    box_path = ROOT / f'data/raw/hoopr/player_box_{season}.parquet'
    box = pd.read_parquet(box_path, columns=['game_id', 'athlete_id', 'team_id', 'starter',
                                             'did_not_play', 'minutes', 'season_type'])
    box = box.loc[box['season_type'].eq(2) & box['game_id'].notna()].copy()
    box['game_id'] = box['game_id'].astype('int64').astype(str)
    box = box.loc[box['game_id'].isin(ids)].dropna(subset=['athlete_id', 'team_id']).copy()
    box['player'] = box['athlete_id'].astype('int64').astype(str)
    box['team'] = box['team_id'].astype('int64').astype(str)
    if box.duplicated(['game_id', 'player']).any():
        raise ValueError(f'{fold}: duplicate raw box player')
    starts = box.loc[box['starter'].astype('boolean').eq(True).fillna(False)].copy()
    dnp = starts['did_not_play'].astype('boolean')
    minutes = pd.to_numeric(starts['minutes'], errors='raise')
    starts['valid'] = dnp.eq(False).fillna(False) & minutes.notna() & minutes.gt(0)
    actual = {}
    for key, part in starts.groupby(['game_id', 'team']):
        if len(part) == 5 and part['valid'].all() and part['player'].nunique() == 5:
            actual[key] = set(part['player'])
    seen = set(map(tuple, teams[['game_id', 'team']].to_numpy()))
    if not seen.issubset(expected_teams):
        raise ValueError(f'{fold}: a scored team is not on the schedule')
    status_counts = {str(k): int(v) for k, v in teams['status'].value_counts().items()}
    status_counts['no_prior_roster'] = len(expected_teams - seen)
    if status_counts != report['starter_team_status']:
        raise ValueError(f'{fold}: team status counts differ')
    if len(expected_teams - set(actual)) != report['starter_label_coverage']['team_games_without_complete_valid_starters']:
        raise ValueError(f'{fold}: complete observed-starter coverage differs')

    groups = {(str(gid), str(team)): part for (gid, team), part in rows.groupby(['game_id', 'team'])}
    outside = 0
    for result in teams.itertuples(index=False):
        key = (str(result.game_id), str(result.team))
        part = groups[key]
        sure = part.loc[part['availability_fallback'].ge(0.9)]
        pool = sure if len(sure) else part
        truth = actual.get(key)
        predicted = set(part.loc[part['projected_starter'].fillna(False).astype(bool), 'player'])
        if len(pool) < 5:
            status = 'fewer_than_five_sure_candidates'
        elif not pool['prior_position'].isin(['G', 'F', 'C']).all():
            status = 'unknown_prior_position'
        elif truth is None:
            status = 'incomplete_observed_starters'
        else:
            status = 'ok'
        if result.status != status or bool(part['starter_scored_team'].all()) != (status == 'ok'):
            raise ValueError(f'{fold} {key}: unsupported status differs')
        if result.candidate_count != len(part) or result.unknown_prior_positions != int(part['prior_position'].isna().sum()):
            raise ValueError(f'{fold} {key}: candidate or position coverage differs')
        if status in ('ok', 'incomplete_observed_starters'):
            if len(predicted) != 5 or not predicted.issubset(set(pool['player'])):
                raise ValueError(f'{fold} {key}: projected five is invalid')
        elif predicted or part['projected_starter'].notna().any():
            raise ValueError(f'{fold} {key}: unsupported selection has predicted starters')
        count = len(truth - set(part['player'])) if truth is not None else None
        check_number(result.actual_starters_outside_candidates if pd.notna(result.actual_starters_outside_candidates)
                     else None, count, f'{fold} {key} outside roster')
        outside += count or 0
        check_number(result.slot_accuracy if pd.notna(result.slot_accuracy) else None,
                     len(predicted & truth) / 5 if status == 'ok' and truth is not None else None,
                     f'{fold} {key} slot accuracy')
        check_number(result.exact_five if pd.notna(result.exact_five) else None,
                     int(predicted == truth) if status == 'ok' and truth is not None else None,
                     f'{fold} {key} exact five')
    if outside != report['observed_starters_outside_inferred_rosters']:
        raise ValueError(f'{fold}: outside-roster starter count differs')

    draws = np.random.default_rng(SEED).integers(0, len(ids), (REPLICATES, len(ids)))
    known = check_probabilities(report, rows, ids, draws)
    for metric in ('slot_accuracy', 'exact_five'):
        check_mean(report['starter_team_results'][metric], teams, metric, ids, draws)
    return {
        'fold': fold, 'games': len(ids), 'candidate_player_games': len(rows),
        'known_play_labels': known, 'team_games': len(teams), 'starter_status': status_counts,
        'observed_starters_outside_roster': outside, 'bootstrap_replicates': REPLICATES,
        'fingerprints_checked': len(report['input_sha256']) + len(report['output_sha256']),
        'input_sha256': {str(p.relative_to(ROOT)): sha256_file(p)
                         for p in (report_path, row_path, team_path, source_path, MANIFEST,
                                   segments_path, box_path)},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fold', choices=list(FOLDS), required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f'refusing to overwrite {args.output}')
    result = audit(args.fold)
    result['experiment'] = 'a1_s07_baseline_independent_accounting'
    result['audit_source_sha256'] = sha256_file(Path(__file__))
    write_json(args.output, result, pretty=True)
    print(f"{result['fold']}: audited {result['candidate_player_games']} candidates, "
          f"{result['known_play_labels']} known labels and {result['team_games']} team-games", flush=True)


if __name__ == '__main__':
    main()
