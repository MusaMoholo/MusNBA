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
from basketball_common import DERIVED, sha256_file, write_json  # noqa: E402
from scripts import a1_compare, a1_minutes_fold_eval, a1_minutes_unconditional  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS, TEST_FROM  # noqa: E402


def audit(folds: list[str]) -> dict:
    hashes: dict[str, str] = {}
    output_hashes: dict[str, str] = {}
    manifest = json.loads(a1_minutes_fold_eval.PREREG.read_text())
    report = {}
    for fold in folds:
        files = {kind: EXPERIMENTS / f'20261122_a1_s05_{kind}_{fold}.json'
                 for kind in ('unconditional', 'no_report')}
        row_files = {kind: DERIVED / 'experiments' / f'20261122_a1_s05_{kind}_{fold}.parquet'
                     for kind in files}
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
                             'maximum_team_mean_minute_error': maxima}
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folds', nargs='+', choices=list(FOLDS), default=list(FOLDS))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f'refusing to overwrite {args.output}')
    result = audit(args.folds)
    result['audit_source_sha256'] = sha256_file(Path(__file__))
    write_json(args.output, result, pretty=True)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
