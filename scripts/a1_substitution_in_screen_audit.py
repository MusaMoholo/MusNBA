#!/usr/bin/env python3
"""Independently reproduce incoming-screen features, selections, refits and paired intervals."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, sha256_file, write_json  # noqa: E402
from scripts.a1_minutes_fold_eval import CAUSAL_PROFILES  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS, TEST_FROM  # noqa: E402
from scripts.features import known_group  # noqa: E402

REPORT = EXPERIMENTS / '20261122_a1_s06_in_screen.json'
SCORES = DERIVED / 'experiments/20261122_a1_s06_in_screen.parquet'
TIERS = ('star', 'starter', 'bench', 'unknown')
POSITIONS = ('G', 'F', 'C', 'unknown')
NUMERIC = ('period', 'clock', 'margin', 'fouls_before', 'seconds_before', 'rest_before',
           'target_mean_proxy', 'target_deficit')
FEATURES = (*NUMERIC, *(f'tier_{tier}' for tier in TIERS), *(f'pos_{position}' for position in POSITIONS),
            *(f'remaining_{position}' for position in POSITIONS))
PARAMS = {'objective': 'binary', 'num_leaves': 15, 'learning_rate': 0.05, 'min_data_in_leaf': 80,
          'lambda_l2': 1.0, 'seed': 20261122, 'num_threads': 1, 'deterministic': True,
          'force_col_wise': True, 'verbosity': -1}
SEED = 20261122
REPLICATES = 10_000
KEYS = ['window_id', 'team']


def populations(raw: pd.DataFrame, position_lookup: dict[tuple[str, str], str | None]) -> pd.DataFrame:
    rows = raw.copy()
    position = []
    for row in rows[['player', 'date_et', 'prior_profile_date']].to_dict('records'):
        day = row['prior_profile_date']
        if day is None or pd.isna(day):
            position.append(None)
        else:
            if day >= row['date_et'] or (row['player'], day) not in position_lookup:
                raise ValueError('incoming position is not strictly prior or its profile is absent')
            position.append(position_lookup[(row['player'], day)])
    rows['prior_position'] = position
    outgoing = rows.loc[rows['decision'].eq('out')]
    states = {}
    for (window, team), group in outgoing.groupby(KEYS, sort=False):
        if len(group) != 5 or group['player'].nunique() != 5 or group['label'].isna().any():
            raise ValueError('independent source lineup is not five observed players')
        exit_count = int(group['label'].astype(int).sum())
        remaining = group.loc[~group['label'].astype(bool), 'prior_position'].fillna('unknown').value_counts()
        states[(window, team)] = (exit_count, {pos: int(remaining.get(pos, 0)) for pos in POSITIONS})
    incoming = rows.loc[rows['decision'].eq('in') & rows['eligibility'].ne('known_ineligible')].copy()
    keys = list(zip(incoming['window_id'], incoming['team']))
    incoming['exit_count'] = [states[key][0] for key in keys]
    for pos in POSITIONS:
        incoming[f'remaining_{pos}'] = [states[key][1][pos] for key in keys]
    incoming = incoming.loc[incoming['exit_count'].gt(0)].copy()
    labels = incoming['label'].fillna(False).astype(int)
    incoming['entry_count'] = labels.groupby([incoming[column] for column in KEYS]).transform('sum')
    incoming = incoming.loc[incoming['entry_count'].gt(0)].copy()
    incoming['pool_count'] = incoming.groupby(KEYS)['player'].transform('size')
    return incoming.reset_index(drop=True)


def matrix(rows: pd.DataFrame) -> pd.DataFrame:
    data = rows[list(NUMERIC)].apply(pd.to_numeric, errors='raise').astype(float)
    for tier in TIERS:
        data[f'tier_{tier}'] = (rows['prior_tier'] == tier).astype(float)
    for pos in POSITIONS:
        data[f'pos_{pos}'] = (rows['prior_position'].fillna('unknown') == pos).astype(float)
    for pos in POSITIONS:
        data[f'remaining_{pos}'] = rows[f'remaining_{pos}'].astype(float)
    return data.loc[:, list(FEATURES)]


def rank(group: pd.DataFrame, score: str, k: int) -> set[str]:
    values = []
    for row in group[['player', score]].to_dict('records'):
        value = row[score]
        missing = bool(pd.isna(value))
        values.append((missing, -float(value) if not missing else 0.0, row['player']))
    return {player for _, _, player in sorted(values)[:k]}


def audit_selections(scored: pd.DataFrame, raw: pd.DataFrame, windows: pd.DataFrame) -> dict:
    five = {(window, team): group for (window, team), group in
            raw.loc[raw['decision'].eq('out')].groupby(KEYS, sort=False)}
    roster = {}
    for row in windows.to_dict('records'):
        for side in ('home', 'away'):
            roster[(row['window_id'], row[side])] = set(map(str, row[f'{side}_players']))
    disqualified = raw.loc[raw['fouls_before'].ge(6) | raw['ejected_before']].groupby(KEYS)['player'].agg(set).to_dict()
    groups_checked = oracle_checked = 0
    for (window, team), group in scored.groupby(KEYS, sort=False):
        key = (window, team)
        outs = five[key]
        k = int(group['label'].fillna(False).sum())
        if k != int(group['entry_count'].iloc[0]) or k < 1:
            raise ValueError('incoming entry count does not match preserved positive labels')
        expected_baseline = pd.to_numeric(group['target_deficit'], errors='raise').where(
            group['target_deficit'].notna(), pd.to_numeric(group['target_mean_proxy'], errors='raise'))
        if not np.allclose(group['baseline_score'].to_numpy(dtype=float), expected_baseline.to_numpy(dtype=float),
                           rtol=0, atol=0, equal_nan=True):
            raise ValueError('incoming baseline fallback differs')
        for model in ('baseline', 'candidate'):
            expected = rank(group, f'{model}_score', k)
            actual = set(group.loc[group[f'{model}_selected'], 'player'])
            if actual != expected:
                raise ValueError(f'{key}: incoming pool selection differs')
        exits = set(outs.loc[outs['label'].astype(bool), 'player'])
        expected_oracle = k == len(exits)
        if not group['oracle_scored'].eq(expected_oracle).all():
            raise ValueError(f'{key}: participant-oracle inclusion differs')
        if expected_oracle:
            active = roster[key]
            remaining = set(outs['player']) - exits
            banned = disqualified.get(key, set())
            for model in ('baseline', 'candidate'):
                available = group.loc[group['player'].isin(active - banned)]
                expected = rank(available, f'{model}_score', k)
                actual = set(group.loc[group[f'oracle_{model}_selected'], 'player'])
                if actual != expected or len(remaining | actual) != 5 or not (remaining | actual).issubset(active - banned):
                    raise ValueError(f'{key}: participant-oracle lineup is not the expected active five')
            oracle_checked += 1
        groups_checked += 1
    return {'team_windows': groups_checked, 'oracle_team_windows': oracle_checked}


def audit_metric(cases: pd.DataFrame, report: dict, prefix: str = '') -> float:
    games = sorted(cases['game_id'].unique().tolist())
    player_games = len(cases[['game_id', 'player']].drop_duplicates())
    supported = len(games) >= 30 and player_games >= 100
    counts = {'entries': len(cases), 'games': len(games), 'player_games': player_games,
              'status': 'ok' if supported else 'insufficient_sample'}
    if any(report[key] != value for key, value in counts.items()):
        raise ValueError('incoming metric population or support differs')
    baseline = cases[f'{prefix}baseline_selected'].to_numpy(dtype=float)
    candidate = cases[f'{prefix}candidate_selected'].to_numpy(dtype=float)
    error = max(abs(float(report['baseline_recall']) - float(baseline.mean())),
                abs(float(report['candidate_recall']) - float(candidate.mean())),
                abs(float(report['change']) - float((candidate - baseline).mean())))
    if supported:
        per_game = pd.DataFrame({'game_id': cases['game_id'].to_numpy(), 'count': 1,
                                 'difference': candidate - baseline}).groupby('game_id').sum().reindex(games)
        draws = np.random.default_rng(SEED).integers(0, len(games), (REPLICATES, len(games)))
        weights = np.zeros(draws.shape, dtype=np.int16)
        np.add.at(weights, (np.arange(REPLICATES)[:, None], draws), 1)
        difference = (weights @ per_game['difference'].to_numpy(dtype=float)) / (weights @ per_game['count'].to_numpy())
        interval = np.quantile(difference, [0.025, 0.975])
        error = max(error, float(np.max(np.abs(interval - np.asarray(report['ci_95'])))))
    elif report['ci_95'] is not None:
        raise ValueError('unsupported incoming metric has a bootstrap interval')
    if error > 1e-12:
        raise ValueError(f'incoming metric or bootstrap differs by {error}')
    return error


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=EXPERIMENTS / '20261122_a1_s06_in_screen_audit.json')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite the incoming screen audit')
    report = json.loads(REPORT.read_text())
    if report['features'] != list(FEATURES) or report['model_params'] != PARAMS or report['num_boost_round'] != 120:
        raise ValueError('incoming screen differs from the frozen model protocol')
    for path, digest in report['input_sha256'].items():
        if sha256_file(ROOT / path) != digest:
            raise ValueError(f'incoming screen input changed: {path}')
    if sha256_file(SCORES) != report['output_sha256'][str(SCORES.relative_to(ROOT))]:
        raise ValueError('incoming scores differ from their saved fingerprint')
    profiles = pd.read_parquet(CAUSAL_PROFILES, columns=['date_et', 'player', 'pos'])
    position_lookup = {(row['player'], str(row['date_et'])[:10]): known_group(row['pos'])
                       for row in profiles.to_dict('records')}
    if len(position_lookup) != len(profiles):
        raise ValueError('incoming position lookup has duplicate player/dates')
    raw, windows, data = {}, {}, {}
    for name in ('seed', *FOLDS):
        stem = f'20261122_a1_s06_fold_{name}_v3'
        raw[name] = pd.read_parquet(DERIVED / 'experiments' / f'{stem}.parquet')
        windows[name] = pd.read_parquet(DERIVED / 'experiments' / f'{stem}_windows.parquet')
        data[name] = populations(raw[name], position_lookup)
    saved = pd.read_parquet(SCORES)
    score_error = metric_error = 0.0
    group_counts = {}
    for index, fold in enumerate(FOLDS):
        train = pd.concat([data[name] for name in ['seed', *list(FOLDS)[:index]]], ignore_index=True)
        valid = data[fold]
        scored = saved.loc[saved['fold'].eq(fold)].reset_index(drop=True)
        if (train['date_et'].max() >= FOLDS[fold][1] or valid['date_et'].ge(TEST_FROM).any()
                or not valid['date_et'].between(FOLDS[fold][1], FOLDS[fold][2]).all()
                or set(train['game_id']) & set(valid['game_id'])):
            raise ValueError(f'{fold}: incoming model cutoff differs')
        columns = list(valid.columns)
        pd.testing.assert_frame_equal(scored[columns], valid[columns], check_dtype=False)
        cases = train.loc[train['label'].fillna(False)]
        labels = np.r_[np.ones(len(cases)), np.zeros(len(train))]
        weights = np.r_[1 / cases['entry_count'].to_numpy(dtype=float),
                        1 / train['pool_count'].to_numpy(dtype=float)]
        model = lgb.train(PARAMS, lgb.Dataset(pd.concat([matrix(cases), matrix(train)], ignore_index=True),
                                          label=labels, weight=weights), num_boost_round=120)
        prediction = model.predict(matrix(valid), raw_score=True, num_threads=1)
        if not isinstance(prediction, np.ndarray):
            raise ValueError(f'{fold}: incoming refit returned a non-array')
        score_error = max(score_error, float(np.max(np.abs(prediction - scored['candidate_score'].to_numpy()))))
        if score_error > 1e-12:
            raise ValueError(f'{fold}: independently fitted incoming scores differ')
        if dict(zip(FEATURES, (int(x) for x in model.feature_importance()))) != report['folds'][fold]['feature_split_counts']:
            raise ValueError(f'{fold}: incoming feature splits differ')
        group_counts[fold] = audit_selections(scored, raw[fold], windows[fold])
        cases = scored.loc[scored['label'].fillna(False)]
        fold_report = report['folds'][fold]
        metric_error = max(metric_error, audit_metric(cases, fold_report['population_pool']),
                           audit_metric(cases.loc[cases['oracle_scored']], fold_report['participant_oracle'], 'oracle_'))
        for tier, tier_report in fold_report['tiers'].items():
            metric_error = max(metric_error, audit_metric(cases.loc[cases['prior_tier'].eq(tier)], tier_report))
        print(f'{fold}: {len(scored)} ranks and {group_counts[fold]["team_windows"]} team-windows verified', flush=True)
    cases = saved.loc[saved['label'].fillna(False)]
    metric_error = max(metric_error, audit_metric(cases, report['pooled']),
                       audit_metric(cases.loc[cases['oracle_scored']], report['participant_oracle_pooled'], 'oracle_'))
    favourable = sum(report['folds'][fold]['population_pool']['change'] > 0 for fold in FOLDS)
    if (favourable != report['favourable_fold_points']
            or report['diagnostic_screen_pass'] != (report['pooled']['ci_95'][0] > 0 and favourable >= 3)):
        raise ValueError('incoming frozen selection rule differs')
    result = {'experiment': 'a1_s06_incoming_screen_independent_audit',
              'candidate_rows': len(saved), 'observed_entries': len(cases), 'group_counts': group_counts,
              'bootstrap_replicates_per_supported_cell': REPLICATES, 'maximum_score_error': score_error,
              'maximum_metric_error': metric_error, 'diagnostic_screen_pass': report['diagnostic_screen_pass'],
              'input_sha256': {str(path.relative_to(ROOT)): sha256_file(path)
                               for path in (Path(__file__), REPORT, SCORES, CAUSAL_PROFILES)}}
    write_json(args.output, result, pretty=True)
    print(f'independently audited {len(saved)} candidate ranks and {len(cases)} observed entrants', flush=True)


if __name__ == '__main__':
    main()
