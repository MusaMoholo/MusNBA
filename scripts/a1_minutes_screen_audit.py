#!/usr/bin/env python3
"""Reconcile both A1 historical minute screens and their retained provenance."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import sha256_file, write_json  # noqa: E402
from scripts import a1_compare, a1_minutes_fold_eval, a1_minutes_unconditional  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS, TEST_FROM  # noqa: E402


def audit(folds: list[str], suffix: str = '') -> dict:
    hashes: dict[str, str] = {}
    output_hashes: dict[str, str] = {}
    manifest = json.loads(a1_minutes_fold_eval.PREREG.read_text())
    original_audit = (json.loads((EXPERIMENTS / '20261122_a1_s05_minutes_screen_accounting_uncorrected.json').read_text())
                      if suffix else None)
    report = {}
    for fold in folds:
        paths = {kind: a1_minutes_unconditional.output_paths(kind, fold, suffix)
                 for kind in ('unconditional', 'no_report')}
        files = {kind: pair[0] for kind, pair in paths.items()}
        row_files = {kind: pair[1] for kind, pair in paths.items()}
        for path in (*files.values(), *row_files.values()):
            output_hashes[str(path.relative_to(ROOT))] = sha256_file(path)
        logs = {kind: json.loads(path.read_text()) for kind, path in files.items()}
        for kind, log in logs.items():
            if log['fold'] != fold or log['worlds'] != 1000 or log['fold_cutoff'] != FOLDS[fold][1]:
                raise ValueError(f'{fold} {kind}: saved evaluation settings differ from the fixed contract')
            for name, digest in log['input_sha256'].items():
                if name not in hashes:
                    hashes[name] = sha256_file(ROOT / name)
                if hashes[name] != digest:
                    raise ValueError(f'{fold} {kind}: source fingerprint differs for {name}')
        rows = {kind: pd.read_parquet(path) for kind, path in row_files.items()}
        a1_compare._same_keys(rows['unconditional'], rows['no_report'], ['game_id', 'player'],
                              f'{fold} historical minute screens')
        games, _ = a1_minutes_unconditional.fixed_games(manifest, fold)
        expected_sides = {(str(row.game_id), str(team)) for row in games.itertuples()
                          for team in (row.home, row.away)}
        for kind, frame in rows.items():
            no_roster = {(item['game_id'], item['team'])
                         for item in logs[kind]['candidate_coverage']['team_games_without_prior_candidates']}
            observed = set(map(tuple, frame[['game_id', 'team']].drop_duplicates().to_numpy()))
            if not no_roster.issubset(expected_sides) or observed != expected_sides - no_roster:
                raise ValueError(f'{fold} {kind}: missing team rosters do not match reported coverage')
        paired = a1_compare._pair(rows['unconditional'], rows['no_report'], ['game_id', 'player'])
        a1_compare._same_values(paired, ('team', 'date_et', 'prior_day', 'played', 'reg', 'tier',
                                          'source_conflict', 'listed_in_box'), f'{fold} populations')
        details = {}
        for kind, frame in rows.items():
            unchanged = None
            if original_audit is not None:
                old_log, old_rows = a1_minutes_unconditional.output_paths(kind, fold)
                for path in (old_log, old_rows):
                    if original_audit['output_sha256'].get(str(path.relative_to(ROOT))) != sha256_file(path):
                        raise ValueError(f'{fold} {kind}: original audited output changed: {path}')
                original = pd.read_parquet(old_rows)
                a1_compare._same_keys(original, frame, ['game_id', 'player'], f'{fold} {kind} original screen')
                population = a1_compare._pair(original, frame, ['game_id', 'player'])
                a1_compare._same_values(population, ('team', 'date_et', 'prior_day', 'played', 'reg', 'tier',
                                                      'source_conflict', 'listed_in_box'),
                                        f'{fold} {kind} original screen population')
                original = original.sort_values(['game_id', 'player']).reset_index(drop=True)
                current = frame.sort_values(['game_id', 'player']).reset_index(drop=True)
                columns = [c for c in original if isinstance(c, str) and c.startswith(('control_', 'nba_only_'))]
                if not columns or not set(columns).issubset(current):
                    raise ValueError(f'{fold} {kind}: original control columns are missing')
                for column in columns:
                    old_values = original[column].to_numpy(dtype=float)
                    new_values = current[column].to_numpy(dtype=float)
                    if not np.allclose(old_values, new_values, rtol=0, atol=1e-12, equal_nan=True):
                        raise ValueError(f'{fold} {kind}: original {column} differs after strict repair')
                unchanged = {'rows': len(original), 'columns': len(columns), 'absolute_tolerance': 1e-12}
            if frame['date_et'].ge(TEST_FROM).any() or frame['prior_day'].ge(frame['date_et']).any():
                raise ValueError(f'{fold} {kind}: a final-season or non-prior roster date entered the screen')
            profile_day = pd.to_datetime(frame['prior_profile_date'], errors='raise')
            origin = pd.to_datetime(frame['date_et'], errors='raise')
            if (profile_day.notna() & profile_day.ge(origin)).any():
                raise ValueError(f'{fold} {kind}: a same-day or future profile entered role tiers')
            if (frame['played'].isna() & frame['reg'].notna()).any():
                raise ValueError(f'{fold} {kind}: an unknown play outcome received actual minutes')
            if (frame['played'].eq(0) & ~frame['source_conflict'] & frame['reg'].ne(0)).any():
                raise ValueError(f'{fold} {kind}: known DNPs must have zero regulation minutes')
            if (frame['source_conflict'] & frame['reg'].notna()).any():
                raise ValueError(f'{fold} {kind}: contradictory source actuals were scored')
            maxima = {}
            for variant in a1_minutes_fold_eval.VARIANTS:
                for name in ('crps', 'covered'):
                    valid = frame[f'{variant}_{name}'].notna()
                    if not valid.equals(frame['reg'].notna()):
                        raise ValueError(f'{fold} {kind}: {variant} {name} has inconsistent actual coverage')
                probs = frame[f'{variant}_play_probability'].to_numpy(dtype=float)
                if not np.isfinite(probs).all() or ((probs < 0) | (probs > 1)).any():
                    raise ValueError(f'{fold} {kind}: invalid {variant} play-target probabilities')
                metric = frame[f'{variant}_crps'].dropna()
                if (metric < -1e-10).any():
                    raise ValueError(f'{fold} {kind}: a CRPS is negative')
                recorded = logs[kind]['minute_results_by_prior_profile_tier']['all'][f'{variant}_crps']
                if recorded['observations'] != len(metric) or not np.isclose(recorded['mean'], metric.mean(), rtol=0, atol=1e-12):
                    raise ValueError(f'{fold} {kind}: reported {variant} minute CRPS does not match rows')
                team_sums = frame.groupby(['game_id', 'team'])[f'{variant}_mean'].sum()
                maxima[variant] = float(team_sums.sub(240).abs().max())
                if variant in ('strict', 'combined'):
                    if maxima[variant] > 1e-9 or frame[f'{variant}_mean'].gt(48 + 1e-10).any():
                        raise ValueError(f'{fold} {kind}: strict target means violate regulation limits')
            details[kind] = {'requested_games': len(games), 'evaluated_games': int(frame['game_id'].nunique()),
                             'games_without_a_candidate_roster': sorted(set(games['game_id']) - set(frame['game_id'])),
                             'requested_team_games': len(expected_sides),
                             'evaluated_team_games': int(frame[['game_id', 'team']].drop_duplicates().shape[0]),
                             'candidates': len(frame), 'known_regulation_actual': int(frame['reg'].notna().sum()),
                             'unknown_play': int(frame['played'].isna().sum()),
                             'maximum_team_mean_minute_error': maxima,
                             'original_control_and_nba_only_reproduced': unchanged}
        no_report = rows['no_report']
        prior_minute_day = pd.to_datetime(no_report['prior_minutes_date'], errors='raise')
        origins = pd.to_datetime(no_report['date_et'], errors='raise')
        if (prior_minute_day.notna() & prior_minute_day.ge(origins)).any():
            raise ValueError(f'{fold}: same-day or future minutes entered the no-report fallback')
        inactive_recent = no_report['recent_window'].ge(3) & no_report['recent_played'].eq(0)
        expected_p = np.where(inactive_recent, np.where(no_report['min_ewma'].ge(20), 0.8, 0.5), 1.0)
        if not np.array_equal(expected_p, no_report['availability_fallback'].to_numpy(dtype=float)):
            raise ValueError(f'{fold}: saved no-report probabilities differ from the fixed fallback rule')
        details['no_report']['fallback_without_prior_minute_ewma'] = int(
            (inactive_recent & no_report['min_ewma'].isna()).sum())
        report[fold] = details
    return {'experiment': 'a1_s05_historical_minutes_screen_accounting',
            'method': 'Check source hashes, fixed fold keys, common labels, strictly prior inputs, unknown/zero '
                      'outcomes, recorded CRPS and strict 240-minute target means independently for both screens.',
            'folds': report, 'unique_input_hashes_checked': len(hashes), 'output_sha256': output_hashes}


def audit_conditional(folds: list[str]) -> dict:
    original_log = EXPERIMENTS / '20261122_a1_s05_minutes_fold_screen.json'
    corrected_log = EXPERIMENTS / '20261122_a1_s05_minutes_fold_screen_corrected.json'
    original_rows = ROOT / 'data/derived/experiments/20261122_a1_s05_minutes_fold_screen.parquet'
    corrected_rows = ROOT / 'data/derived/experiments/20261122_a1_s05_minutes_fold_screen_corrected.parquet'
    expected_original = {
        original_log: 'd1cf7ee333a0fab025699a35248a9b0c22fb3f784860bf4d46fb8aefe81ca19b',
        original_rows: '9082ee7f42856202d1546c1300d28aab392c07c18b71c8bb9087c526b705eb6b',
    }
    for path, digest in expected_original.items():
        if sha256_file(path) != digest:
            raise ValueError(f'original conditional screen differs from recorded fingerprint: {path}')
    original_report = json.loads(original_log.read_text())
    corrected_report = json.loads(corrected_log.read_text())
    if original_report['input_sha256']['scripts/a1_minutes_candidate.py'] != (
            '3bd085968d6f1a9e08b1bf5f58aaa4af75f1d81d1261e858b291d5c069d416dc'):
        raise ValueError('original conditional screen candidate fingerprint differs from the pre-repair source')
    for name, digest in corrected_report['input_sha256'].items():
        if sha256_file(ROOT / name) != digest:
            raise ValueError(f'corrected conditional screen input differs: {name}')
    original, corrected = pd.read_parquet(original_rows), pd.read_parquet(corrected_rows)
    keys = ['fold', 'game_id', 'player']
    a1_compare._same_keys(original, corrected, keys, 'conditional screen')
    paired = a1_compare._pair(original, corrected, keys)
    a1_compare._same_values(paired, ('team', 'date_et', 'reg', 'tier'),
                            'original and corrected conditional populations')
    original = original.sort_values(keys).reset_index(drop=True)
    corrected = corrected.sort_values(keys).reset_index(drop=True)
    columns = [c for c in original if isinstance(c, str) and c.startswith(('control_', 'nba_only_'))]
    if not columns or not set(columns).issubset(corrected):
        raise ValueError('conditional screen original control columns are missing')
    for column in columns:
        if not np.allclose(original[column].to_numpy(dtype=float), corrected[column].to_numpy(dtype=float),
                           rtol=0, atol=1e-12, equal_nan=True):
            raise ValueError(f'conditional screen original {column} differs after strict repair')
    manifest = json.loads(a1_minutes_fold_eval.PREREG.read_text())
    results = {}
    for fold in folds:
        frame = corrected.loc[corrected['fold'].eq(fold)]
        games = a1_minutes_fold_eval.fold_games(manifest, fold)
        if set(frame['game_id']) != set(games['game_id']):
            raise ValueError(f'{fold}: conditional screen games differ from the fixed population')
        mapped_dates = frame['game_id'].map(games.set_index('game_id')['date_et'])
        if frame['date_et'].ne(mapped_dates).any() or frame['date_et'].ge(TEST_FROM).any():
            raise ValueError(f'{fold}: invalid or final-season conditional screen date')
        if not np.isfinite(frame['reg']).all() or not frame['reg'].between(0, 48).all():
            raise ValueError(f'{fold}: invalid participant regulation minutes')
        team_count = frame.groupby(['game_id', 'team']).size()
        if len(team_count) != 400 or team_count.lt(5).any():
            raise ValueError(f'{fold}: invalid conditional team-game population')
        maxima = {}
        for variant in a1_minutes_fold_eval.VARIANTS:
            for name in ('mean', 'crps', 'covered'):
                values = frame[f'{variant}_{name}']
                if not np.isfinite(values).all():
                    raise ValueError(f'{fold}: {variant} {name} has missing or infinite values')
            if frame[f'{variant}_crps'].lt(-1e-10).any():
                raise ValueError(f'{fold}: {variant} CRPS is negative')
            if not frame[f'{variant}_covered'].isin([0, 1]).all():
                raise ValueError(f'{fold}: {variant} coverage is not binary')
            team_means = frame.groupby(['game_id', 'team'])[f'{variant}_mean'].sum()
            maxima[variant] = float(team_means.sub(240).abs().max())
            if variant in ('strict', 'combined'):
                if maxima[variant] > 1e-9 or not frame[f'{variant}_mean'].between(0, 48 + 1e-10).all():
                    raise ValueError(f'{fold}: {variant} mean targets violate regulation limits')
        for tier in ('all', *a1_compare.ROLE_TIERS):
            part = frame if tier == 'all' else frame.loc[frame['tier'].eq(tier)]
            for column in columns + [c for c in frame if isinstance(c, str) and c.startswith(('strict_', 'combined_'))]:
                recorded = corrected_report['folds'][fold][tier].get(column)
                if recorded is None:
                    continue
                valid = part[column].dropna()
                if recorded['observations'] != len(valid):
                    raise ValueError(f'{fold} {tier}: {column} count differs from saved rows')
                if len(valid) and not np.isclose(recorded['mean'], valid.mean(), rtol=0, atol=1e-12):
                    raise ValueError(f'{fold} {tier}: {column} mean differs from saved rows')
        results[fold] = {'games': len(games), 'team_games': len(team_count), 'player_games': len(frame),
                         'original_control_and_nba_only_reproduced': {'rows': len(frame), 'columns': len(columns),
                                                                       'absolute_tolerance': 1e-12},
                         'maximum_team_mean_minute_error': maxima}
    paths = (original_log, original_rows, corrected_log, corrected_rows)
    return {'experiment': 'a1_s05_conditional_minutes_screen_accounting',
            'method': 'Check fixed keys and dates, original fingerprints, corrected input hashes, unchanged '
                      'control/NBA-only values, legal strict means and reported fold/tier metrics.',
            'folds': results, 'input_hashes_checked': len(corrected_report['input_sha256']),
            'output_sha256': {str(p.relative_to(ROOT)): sha256_file(p) for p in paths}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folds', nargs='+', choices=list(FOLDS), default=list(FOLDS))
    parser.add_argument('--suffix', default='', help='identifier appended to the screen output names')
    parser.add_argument('--conditional', action='store_true', help='audit the corrected conditional screen')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f'refusing to overwrite {args.output}')
    if args.conditional and args.suffix:
        parser.error('--suffix does not apply to the conditional screen')
    result = audit_conditional(args.folds) if args.conditional else audit(args.folds, args.suffix)
    result['audit_source_sha256'] = sha256_file(Path(__file__))
    write_json(args.output, result, pretty=True)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
