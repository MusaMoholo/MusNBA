#!/usr/bin/env python3
"""Screen incoming-player rankings without treating unknown eligibility as a negative label."""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Mapping
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, atomic_bytes, sha256_file, write_json  # noqa: E402
from scripts import a1_minutes_fold_eval, a1_substitution_in_coverage, a1_substitution_out_screen  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS  # noqa: E402

TIERS = ('star', 'starter', 'bench', 'unknown')
POSITIONS = ('G', 'F', 'C', 'unknown')
NUMERIC = ('period', 'clock', 'margin', 'fouls_before', 'seconds_before', 'rest_before',
           'target_mean_proxy', 'target_deficit')
FEATURES = (*NUMERIC, *(f'tier_{tier}' for tier in TIERS), *(f'pos_{pos}' for pos in POSITIONS),
            *(f'remaining_{pos}' for pos in POSITIONS))
PARAMS = {'objective': 'binary', 'num_leaves': 15, 'learning_rate': 0.05, 'min_data_in_leaf': 80,
          'lambda_l2': 1.0, 'seed': 20261122, 'num_threads': 1, 'deterministic': True,
          'force_col_wise': True, 'verbosity': -1}
ROUNDS = 120
KEYS = ['window_id', 'team']
SEED = 20261122
REPLICATES = 10_000


def conditional_population(rows: pd.DataFrame) -> pd.DataFrame:
    outgoing = rows.loc[rows['decision'].eq('out')].copy()
    if outgoing['label'].isna().any() or outgoing.duplicated([*KEYS, 'player']).any():
        raise ValueError('observed fives contain missing labels or duplicate players')
    counts = outgoing.groupby(KEYS)['player'].size()
    if not counts.eq(5).all():
        raise ValueError('each observed team lineup must contain five distinct players')
    outgoing['exits'] = outgoing['label'].astype(int)
    exit_counts = outgoing.groupby(KEYS)['exits'].sum().rename('exit_count')
    remaining = outgoing.loc[outgoing['exits'].eq(0)].copy()
    remaining['position'] = remaining['prior_position'].fillna('unknown')
    if not remaining['position'].isin(POSITIONS).all():
        raise ValueError('unknown remaining-lineup position code')
    position_counts = remaining.groupby([*KEYS, 'position']).size().unstack(fill_value=0)
    position_counts = position_counts.reindex(columns=list(POSITIONS), fill_value=0)
    position_counts.columns = [f'remaining_{position}' for position in POSITIONS]
    contexts = exit_counts.to_frame().join(position_counts, how='left')
    contexts[list(position_counts.columns)] = contexts[list(position_counts.columns)].fillna(0).astype(int)
    if not contexts[list(position_counts.columns)].sum(axis=1).eq(5 - contexts['exit_count']).all():
        raise ValueError('remaining-lineup positions do not sum to the observed survivors')
    incoming = rows.loc[rows['decision'].eq('in') & rows['eligibility'].ne('known_ineligible')].copy()
    incoming = incoming.join(contexts, on=KEYS, validate='many_to_one')
    if incoming['exit_count'].isna().any():
        raise ValueError('incoming candidate has no observed team lineup')
    incoming = incoming.loc[incoming['exit_count'].gt(0)].copy()
    incoming['entry_count'] = incoming.groupby(KEYS)['label'].transform(lambda x: x.fillna(False).sum())
    incoming = incoming.loc[incoming['entry_count'].gt(0)].copy()
    incoming['pool_count'] = incoming.groupby(KEYS)['player'].transform('size')
    if (incoming['entry_count'] > incoming['exit_count']).any():
        raise ValueError('more observed entrants than observed exits')
    if incoming.duplicated([*KEYS, 'player']).any() or incoming.empty:
        raise ValueError('conditional incoming pool is empty or duplicated')
    if not incoming['prior_tier'].isin(TIERS).all():
        raise ValueError('incoming candidate has an invalid prior tier')
    return incoming.reset_index(drop=True)


def matrix(rows: pd.DataFrame) -> pd.DataFrame:
    values = {name: pd.to_numeric(rows[name], errors='raise').astype(float) for name in NUMERIC}
    values.update({f'tier_{tier}': rows['prior_tier'].eq(tier).astype(float) for tier in TIERS})
    pos = rows['prior_position'].fillna('unknown')
    values.update({f'pos_{position}': pos.eq(position).astype(float) for position in POSITIONS})
    values.update({f'remaining_{position}': rows[f'remaining_{position}'].astype(float) for position in POSITIONS})
    result = pd.DataFrame(values, index=rows.index)
    if np.isinf(result.to_numpy()).any() or not np.isfinite(result[list(NUMERIC[:5])].to_numpy()).all():
        raise ValueError('incoming features contain infinite values or missing observed game state')
    return result.loc[:, list(FEATURES)]


def fit_score(train: pd.DataFrame, valid: pd.DataFrame) -> tuple[np.ndarray, dict]:
    cases = train.loc[train['label'].fillna(False)].copy()
    if cases.empty or train.empty:
        raise ValueError('incoming case or reference mixture is empty')
    X = pd.concat([matrix(cases), matrix(train)], ignore_index=True)
    labels = np.concatenate([np.ones(len(cases)), np.zeros(len(train))])
    weights = np.concatenate([1 / cases['entry_count'].to_numpy(dtype=float),
                              1 / train['pool_count'].to_numpy(dtype=float)])
    if not np.isclose(weights[:len(cases)].sum(), weights[len(cases):].sum(), rtol=0, atol=1e-8):
        raise ValueError('case/reference team-window weights differ')
    model = lgb.train(PARAMS, lgb.Dataset(X, label=labels, weight=weights), num_boost_round=ROUNDS)
    scores = model.predict(matrix(valid), raw_score=True, num_threads=1)
    if not isinstance(scores, np.ndarray) or scores.shape != (len(valid),) or not np.isfinite(scores).all():
        raise ValueError('incoming model did not return one finite ranking score per candidate')
    details = {'case_rows': len(cases), 'reference_rows': len(train), 'weighted_team_windows': float(weights.sum() / 2),
               'feature_split_counts': {name: int(value) for name, value in zip(FEATURES, model.feature_importance())}}
    return scores, details


def select_lineup(five: list[str], exits: list[str], active: set[str], disqualified: set[str],
                  scores: Mapping[str, float | None]) -> tuple[list[str], list[str]]:
    if len(five) != 5 or len(set(five)) != 5 or len(exits) != len(set(exits)) or not set(exits).issubset(five):
        raise ValueError('selection requires five distinct players and distinct on-court exits')
    remaining = set(five) - set(exits)
    if not remaining.issubset(active - disqualified):
        raise ValueError('remaining lineup contains an unavailable or disqualified player')
    candidates = []
    for player, score in scores.items():
        if player in active and player not in disqualified and player not in five:
            if score is not None and not np.isfinite(score):
                raise ValueError('lineup score is non-finite')
            candidates.append((player, score))
    candidates.sort(key=lambda item: (item[1] is None, -(item[1] if item[1] is not None else 0), item[0]))
    if len(candidates) < len(exits):
        raise ValueError('insufficient scoreable active replacements')
    entrants = [player for player, _ in candidates[:len(exits)]]
    result = sorted(remaining | set(entrants))
    if len(result) != 5:
        raise ValueError('joint selection did not preserve five distinct players')
    return result, entrants


def score_groups(valid: pd.DataFrame, windows: pd.DataFrame, all_rows: pd.DataFrame, fold: str) -> pd.DataFrame:
    result = valid.copy()
    deficit = pd.to_numeric(result['target_deficit'], errors='raise')
    target = pd.to_numeric(result['target_mean_proxy'], errors='raise')
    result['baseline_score'] = deficit.where(deficit.notna(), target)
    result['baseline_used_target_fallback'] = deficit.isna() & target.notna()
    result['baseline_missing'] = result['baseline_score'].isna()
    for column in ('baseline_selected', 'candidate_selected', 'oracle_baseline_selected', 'oracle_candidate_selected',
                   'oracle_scored'):
        result[column] = False
    participants = {}
    for window in windows.to_dict('records'):
        for side in ('home', 'away'):
            participants[(window['window_id'], window[side])] = set(map(str, window[f'{side}_players']))
    out = all_rows.loc[all_rows['decision'].eq('out')]
    fives = {(window, team): group for (window, team), group in out.groupby(KEYS, sort=False)}
    disqualified_rows = all_rows.loc[all_rows['fouls_before'].ge(6) | all_rows['ejected_before']]
    disqualified_by_team_window = disqualified_rows.groupby(KEYS)['player'].agg(set).to_dict()
    total = len(result[KEYS].drop_duplicates())
    started, next_mark = time.monotonic(), 1
    for index, ((window, team), group) in enumerate(result.groupby(KEYS, sort=False), 1):
        key = (window, team)
        five_rows = fives[key]
        five = five_rows['player'].tolist()
        exits = five_rows.loc[five_rows['label'].astype(bool), 'player'].tolist()
        entries = int(group['entry_count'].iloc[0])
        if entries > len(exits):
            raise ValueError(f'{key}: incoming entry count exceeds outgoing count')
        for name, score_col in (('baseline', 'baseline_score'), ('candidate', 'candidate_score')):
            ordered = group.sort_values([score_col, 'player'], ascending=[False, True], na_position='last')
            result.loc[ordered.index[:entries], f'{name}_selected'] = True
        active = participants[key]
        oracle = group.loc[group['player'].isin(active)].copy()
        known_entries = oracle['label'].fillna(False).astype(bool)
        if int(known_entries.sum()) != entries:
            raise ValueError(f'{key}: in-pool entrant is absent from the participant oracle')
        disqualified = disqualified_by_team_window.get(key, set())
        # A partial in-pool evaluation cannot infer replacements outside the prospective pool.
        if entries == len(exits):
            for name, score_col in (('baseline', 'baseline_score'), ('candidate', 'candidate_score')):
                scores = {str(row.player): None if pd.isna(getattr(row, score_col)) else float(getattr(row, score_col))
                          for row in oracle.itertuples(index=False)}
                _, chosen = select_lineup(five, exits, active, disqualified, scores)
                result.loc[group.index[group['player'].isin(chosen)], f'oracle_{name}_selected'] = True
            result.loc[group.index, 'oracle_scored'] = True
        while next_mark <= 10 and index >= int(np.ceil(total * next_mark / 10)):
            print(f'{fold} ranked {index}/{total} team-windows {time.monotonic() - started:.1f}s', flush=True)
            next_mark += 1
    return result


def summary(cases: pd.DataFrame, prefix: str = '') -> dict:
    n = len(cases)
    if not n:
        raise ValueError('cannot summarize an empty entry population')
    games, inverse = np.unique(cases['game_id'].to_numpy(), return_inverse=True)
    player_games = len(cases[['game_id', 'player']].drop_duplicates())
    supported = len(games) >= 30 and player_games >= 100
    baseline = cases[f'{prefix}baseline_selected'].to_numpy(dtype=float)
    candidate = cases[f'{prefix}candidate_selected'].to_numpy(dtype=float)
    interval = None
    if supported:
        count = np.bincount(inverse)
        delta = np.bincount(inverse, weights=candidate - baseline)
        draws = np.random.default_rng(SEED).integers(0, len(games), (REPLICATES, len(games)))
        interval = [float(x) for x in np.quantile(delta[draws].sum(axis=1) / count[draws].sum(axis=1),
                                                  [0.025, 0.975])]
    return {'entries': n, 'games': len(games), 'player_games': player_games,
            'status': 'ok' if supported else 'insufficient_sample',
            'baseline_recall': float(baseline.mean()), 'candidate_recall': float(candidate.mean()),
            'change': float((candidate - baseline).mean()), 'ci_95': interval}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=EXPERIMENTS / '20261122_a1_s06_in_screen.json')
    parser.add_argument('--rows-output', type=Path, default=DERIVED / 'experiments/20261122_a1_s06_in_screen.parquet')
    args = parser.parse_args()
    if args.output.exists() or args.rows_output.exists():
        raise FileExistsError('refusing to overwrite an existing incoming screen')
    coverage_path = EXPERIMENTS / '20261122_a1_s06_in_coverage_audit.json'
    coverage = json.loads(coverage_path.read_text())
    for path, digest in coverage['input_sha256'].items():
        if sha256_file(ROOT / path) != digest:
            raise ValueError(f'coverage audit input changed: {path}')
    profiles = pd.read_parquet(a1_minutes_fold_eval.CAUSAL_PROFILES, columns=['date_et', 'player', 'pos'])
    populations, all_populations, windows_by_fold = {}, {}, {}
    paths = [Path(__file__), Path(a1_substitution_in_coverage.__file__), Path(a1_substitution_out_screen.__file__),
             coverage_path, a1_minutes_fold_eval.CAUSAL_PROFILES]
    for name in ('seed', *FOLDS):
        stem = f'20261122_a1_s06_fold_{name}_v3'
        report_path = EXPERIMENTS / f'{stem}.json'
        row_path = DERIVED / 'experiments' / f'{stem}.parquet'
        window_path = DERIVED / 'experiments' / f'{stem}_windows.parquet'
        report = json.loads(report_path.read_text())
        for path in (row_path, window_path):
            if report['output_sha256'][str(path.relative_to(ROOT))] != sha256_file(path):
                raise ValueError(f'{name}: saved candidate inputs changed')
        all_populations[name] = a1_substitution_in_coverage.attach_positions(pd.read_parquet(row_path), profiles)
        populations[name] = conditional_population(all_populations[name])
        windows_by_fold[name] = pd.read_parquet(window_path)
        paths.extend([report_path, row_path, window_path])
    results, frames = {}, []
    started = time.monotonic()
    for fold in FOLDS:
        train = a1_substitution_out_screen.training_rows(populations, fold)
        valid = populations[fold].copy()
        valid['candidate_score'], model_details = fit_score(train, valid)
        scored = score_groups(valid, windows_by_fold[fold], all_populations[fold], fold)
        scored['fold'] = fold
        cases = scored.loc[scored['label'].fillna(False)]
        oracle_cases = cases.loc[cases['oracle_scored']]
        results[fold] = {
            'training_through': str(train['date_et'].max()),
            'training_games': int(train['game_id'].nunique()),
            'validation_candidates': len(scored),
            'validation_team_windows': len(scored[KEYS].drop_duplicates()),
            'baseline_target_fallback_rows': int(scored['baseline_used_target_fallback'].sum()),
            'baseline_missing_rows': int(scored['baseline_missing'].sum()),
            'population_pool': summary(cases),
            'participant_oracle': summary(oracle_cases, 'oracle_'),
            'tiers': {tier: summary(cases.loc[cases['prior_tier'].eq(tier)])
                      for tier in TIERS if cases['prior_tier'].eq(tier).any()},
            **model_details,
        }
        frames.append(scored)
        print(f'{fold}: {len(scored)} potential candidates, {len(cases)} observed entrants, '
              f'{time.monotonic() - started:.1f}s', flush=True)
    saved = pd.concat(frames, ignore_index=True)
    cases = saved.loc[saved['label'].fillna(False)]
    oracle_cases = cases.loc[cases['oracle_scored']]
    pooled, oracle = summary(cases), summary(oracle_cases, 'oracle_')
    lower = pooled['ci_95'][0] if pooled['ci_95'] is not None else None
    favourable = sum(results[fold]['population_pool']['change'] > 0 for fold in FOLDS)
    report = {
        'experiment': 'a1_s06_incoming_positive_vs_unlabelled_mixture_screen',
        'model_params': PARAMS, 'num_boost_round': ROUNDS, 'features': list(FEATURES),
        'folds': results, 'pooled': pooled, 'participant_oracle_pooled': oracle,
        'favourable_fold_points': favourable,
        'diagnostic_screen_pass': lower is not None and lower > 0 and favourable >= 3,
        'limitations': 'Selected timeouts and observed outgoing sets/counts are conditioned on future events. '
                       'Unknown candidate eligibility is not a negative label; model scores are relative ranks, '
                       'not entry probabilities. The participant oracle uses future appearances and assumes, '
                       'rather than proves, current physical eligibility.',
        'input_sha256': {str(path.relative_to(ROOT)): sha256_file(path) for path in paths},
    }
    atomic_bytes(args.rows_output, saved.to_parquet(index=False))
    report['output_sha256'] = {str(args.rows_output.resolve().relative_to(ROOT)): sha256_file(args.rows_output)}
    write_json(args.output, report, pretty=True)
    print(f"pooled {pooled['entries']} entrants, paired recall change {pooled['change']:.6f}; "
          f"diagnostic screen passed: {report['diagnostic_screen_pass']}", flush=True)


if __name__ == '__main__':
    main()
