#!/usr/bin/env python3
"""Screen the existing no-injury-report fallback on prior-box historical rosters."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, atomic_bytes, sha256_file, write_json  # noqa: E402
from scripts import (a1_availability_cohort, a1_compare, a1_flow_compare, a1_minutes_audit,
                     a1_minutes_candidate, a1_minutes_fold_eval, a1_minutes_unconditional,
                     a1_rotation_diagnose, aggregate, minutes, projection)  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS  # noqa: E402


def prior_fallback(cohort: pd.DataFrame, season: int) -> tuple[pd.DataFrame, Path]:
    path = ROOT / f'data/raw/hoopr/player_box_{season}.parquet'
    raw = pd.read_parquet(path, columns=['game_id', 'game_date', 'team_id', 'athlete_id', 'season_type',
                                        'did_not_play', 'minutes', 'reason'])
    raw = raw.loc[raw['season_type'].eq(2)].dropna(subset=['game_id', 'game_date', 'team_id', 'athlete_id']).copy()
    for source, target in (('game_id', 'game_id'), ('team_id', 'team'), ('athlete_id', 'player')):
        raw[target] = raw[source].astype('int64').astype(str)
    raw['day'] = pd.to_datetime(raw['game_date'], errors='raise').dt.normalize()
    raw['minutes'] = pd.to_numeric(raw['minutes'], errors='raise')
    raw, _ = a1_availability_cohort.nba_team_records(raw, set(json.loads((DERIVED / 'teams.json').read_text())))
    a1_compare._unique(raw, ['game_id', 'player'], 'no-report prior boxes')
    raw['played'] = a1_availability_cohort.participation(raw)
    appearances = raw.loc[raw['played'].eq(1), ['day', 'player', 'minutes']].sort_values(
        ['player', 'day'], kind='stable').copy()
    if appearances.duplicated(['day', 'player']).any():
        raise ValueError('prior appearances have duplicate player dates')
    appearances['min_ewma'] = appearances.groupby('player')['minutes'].transform(
        lambda value: value.ewm(halflife=4, adjust=True).mean().round(2))
    raw['did_not_play'] = raw['did_not_play'].astype('boolean')
    raw.loc[raw['played'].isna(), 'did_not_play'] = pd.NA
    with_recent = a1_rotation_diagnose.recent_flags(cohort, raw)
    out = a1_minutes_audit.prior_join(with_recent, appearances, ['min_ewma']).rename(
        columns={'day': 'prior_minutes_date'})
    if (out['prior_minutes_date'].notna() & out['prior_minutes_date'].ge(out['date_et'])).any():
        raise ValueError('same-day appearance entered the no-report fallback')
    recent_missing = out['recent_window'].ge(3) & out['recent_played'].eq(0)
    out['availability_fallback'] = np.where(
        recent_missing, np.where(out['min_ewma'].ge(20), 0.8, 0.5), 1.0)
    return out, path


def availability_patterns(probability: np.ndarray, worlds: int, seed: int) -> tuple[np.ndarray, int]:
    p = np.asarray(probability, dtype=float)
    if p.ndim != 1 or len(p) < 5 or not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError('availability probabilities require at least five finite values between zero and one')
    rng = np.random.default_rng(seed)
    available = rng.random((worlds, len(p))) < p
    rejected = 0
    for _ in range(100):
        invalid = available.sum(axis=1) < 5
        n = int(invalid.sum())
        if not n:
            return available, rejected
        rejected += n
        available[invalid] = rng.random((n, len(p))) < p
    raise ValueError('could not draw legal five-player availability patterns in 100 attempts')


def target_draws(states: list[dict], sd_table: dict, available: np.ndarray, seed_parts: tuple[str, ...],
                 strict: bool) -> np.ndarray:
    solver = a1_minutes_candidate if strict else minutes
    patterns, inverse = np.unique(available, axis=0, return_inverse=True)
    result = np.zeros(available.shape, dtype=float)
    for index, pattern in enumerate(patterns):
        players = np.flatnonzero(pattern)
        worlds = np.flatnonzero(inverse == index)
        if len(players) < 5:
            raise ValueError('illegal availability pattern entered target draws')
        selected = [states[i] for i in players]
        mu = solver.game_targets(selected)
        cap = [state['cap'] for state in selected]
        spread = minutes.sd_for(sd_table, mu)
        if not np.isfinite(mu).all() or not np.isfinite(spread).all() or mu.sum() <= 0:
            raise ValueError('minute targets or spreads are missing, invalid or empty')
        key = ''.join('1' if flag else '0' for flag in pattern)
        seed = projection.seed_for(*seed_parts, key)
        result[np.ix_(worlds, players)] = solver.redraw(mu, cap, spread, len(worlds), np.random.default_rng(seed))
    if not np.isfinite(result).all() or (result < 0).any():
        raise ValueError('minute draws contain invalid values')
    return result


def summarise_draws(draws: np.ndarray, actual: np.ndarray, played: np.ndarray) -> dict[str, np.ndarray]:
    if np.isinf(actual).any() or np.isinf(played).any():
        raise ValueError('observed outcomes cannot be infinite')
    known = np.isfinite(actual)
    crps, covered = np.full(len(actual), np.nan), np.full(len(actual), np.nan)
    lo, hi = np.quantile(draws, (0.1, 0.9), axis=0)
    if known.any():
        crps[known] = aggregate.crps_samples(draws[:, known], actual[known])
        covered[known] = ((actual[known] >= lo[known]) & (actual[known] <= hi[known])).astype(float)
    probability = (draws > 0).mean(axis=0)
    return {'mean': draws.mean(axis=0), 'crps': crps, 'covered': covered,
            'play_probability': probability, 'play_brier': (probability - played) ** 2}


def evaluate(fold: str, worlds: int) -> tuple[dict, pd.DataFrame, list[Path]]:
    manifest = json.loads(a1_minutes_fold_eval.PREREG.read_text())
    games, segments = a1_minutes_unconditional.fixed_games(manifest, fold)
    coverage, cohort = a1_availability_cohort.build_for_games(games, fold, 'A1 preregistered fixed games')
    original = minutes.build(FOLDS[fold][1], include_current=False)
    clean = a1_minutes_candidate.build(FOLDS[fold][1], include_current=False)
    coach = minutes.coach_dnps(include_current=False)
    rows = a1_minutes_unconditional.attach_actuals(cohort, original['pg'])
    pre = pd.read_parquet(a1_minutes_fold_eval.CAUSAL_PROFILES, columns=['date_et', 'player', 'usage', 'start_share'])
    rows = a1_minutes_unconditional.attach_prior_roles(rows, pre)
    rows, box_path = prior_fallback(rows, coverage['season'])
    rows['date_et'] = pd.to_datetime(rows['date_et'], errors='raise').dt.strftime('%Y-%m-%d')

    start, results, done, next_report, rejected = time.monotonic(), [], 0, 20, 0
    errors = {name: 0.0 for name in a1_minutes_fold_eval.VARIANTS}
    peaks = {name: 0.0 for name in a1_minutes_fold_eval.VARIANTS}
    for day_value, date_rows in rows.groupby('date_et', sort=True):
        if not isinstance(day_value, str):
            raise TypeError('minute-state origin dates must be ISO strings')
        day = day_value
        models = {'control': a1_minutes_unconditional.as_of_model(original, day, coach),
                  'nba': a1_minutes_unconditional.as_of_model(clean, day, coach)}
        for (game_id, team), part in date_rows.groupby(['game_id', 'team'], sort=True):
            part = part.sort_values('player', kind='stable')
            states = {name: [minutes.player_state(model, str(team), str(pid), day) for pid in part['player']]
                      for name, model in models.items()}
            parts = ('a1_s05_no_report', fold, str(game_id), str(team))
            available, n = availability_patterns(part['availability_fallback'].to_numpy(dtype=float), worlds,
                                                 projection.seed_for(*parts, 'availability'))
            rejected += n
            actual = part['actual_reg'].to_numpy(dtype=float)
            played = part['played'].where(~part['source_conflict']).to_numpy(dtype=float)
            sources = {'control': (states['control'], original['sd'], False),
                       'nba_only': (states['nba'], clean['sd'], False),
                       'strict': (states['control'], original['sd'], True),
                       'combined': (states['nba'], clean['sd'], True)}
            out = part[['game_id', 'team', 'player', 'date_et', 'prior_day', 'prior_profile_date',
                        'prior_minutes_date', 'played', 'reg', 'actual_reg', 'source_conflict', 'listed_in_box',
                        'tier', 'recent_window', 'recent_played', 'recent_unknown', 'min_ewma',
                        'availability_fallback']].copy()
            out['fold'] = fold
            for name, (variant_states, spread, strict) in sources.items():
                draws = target_draws(variant_states, spread, available, parts, strict)
                errors[name] = max(errors[name], float(np.max(np.abs(draws.sum(axis=1) - 240))))
                peaks[name] = max(peaks[name], float(draws.max()))
                for metric, value in summarise_draws(draws, actual, played).items():
                    out[f'{name}_{metric}'] = value
            results.append(out)
        done += int(date_rows['game_id'].nunique())
        if done >= next_report or done == len(games):
            print(f'{fold}: {done}/{len(games)} games in {time.monotonic() - start:.1f}s', flush=True)
            while next_report <= done:
                next_report += 20
    result = pd.concat(results, ignore_index=True).rename(columns={'reg': 'on_court_reg', 'actual_reg': 'reg'})
    ids = sorted(games['game_id'].tolist())
    summaries = a1_minutes_fold_eval.summaries(result, ids)
    sample = np.random.default_rng(a1_compare.BOOTSTRAP_SEED).integers(
        0, len(ids), (a1_compare.BOOTSTRAP_REPLICATES, len(ids)))
    weights = np.zeros(sample.shape, dtype=np.int16)
    np.add.at(weights, (np.arange(len(sample))[:, None], sample), 1)
    names = []
    for variant in a1_minutes_fold_eval.VARIANTS:
        names.append(f'{variant}_play_brier')
        if variant != 'control':
            name = f'{variant}_minus_control_play_brier'
            result[name] = result[f'{variant}_play_brier'] - result['control_play_brier']
            names.append(name)
    probabilities = {
        tier: a1_flow_compare.mean_report(result if tier == 'all' else result.loc[result['tier'].eq(tier)],
                                          names, ids, weights, player=True)
        for tier in ('all', *a1_compare.ROLE_TIERS)
    }
    counts = {'candidates': len(result), 'labelled_plays': int(result['played'].eq(1).sum()),
              'labelled_dnps': int(result['played'].eq(0).sum()),
              'unknown_play': int(result['played'].isna().sum()),
              'unlisted': int((~result['listed_in_box']).sum()),
              'known_regulation_actual': int(result['reg'].notna().sum()),
              'source_conflicts': int(result['source_conflict'].sum()),
              'fallback_0_5': int(result['availability_fallback'].eq(0.5).sum()),
              'fallback_0_8': int(result['availability_fallback'].eq(0.8).sum()),
              'fallback_1_0': int(result['availability_fallback'].eq(1.0).sum()),
              'recent_windows_with_unknown_box_status': int(result['recent_unknown'].gt(0).sum()),
              'availability_resampled_worlds': rejected}
    paths = [a1_minutes_fold_eval.PREREG, a1_minutes_fold_eval.CAUSAL_PROFILES, segments, box_path,
             DERIVED / 'teams.json', ROOT / 'scripts/minutes.py', Path(a1_minutes_candidate.__file__),
             Path(a1_availability_cohort.__file__), Path(a1_minutes_unconditional.__file__),
             Path(a1_rotation_diagnose.__file__), Path(a1_minutes_fold_eval.__file__), Path(__file__)]
    paths += sorted((DERIVED / 'history').glob('*/on_court.parquet'))
    paths += sorted((ROOT / 'data/raw/hoopr').glob('player_box_*.parquet'))
    report = {
        'experiment': 'a1_s05_no_report_unconditional_minutes_screen', 'fold': fold,
        'games': len(games), 'worlds': worlds, 'fold_cutoff': FOLDS[fold][1],
        'method': 'Evaluate the fixed no-report availability fallback from strictly earlier prior boxes and a '
                  'four-game appearance-minute EWMA. Draw the same legal availability patterns for all four '
                  'candidate variants and re-solve targets per pattern; known zeros and positive regulation minutes '
                  'are scored, while unknown statuses remain unscored and in the candidate allocation.',
        'limitations': 'Historical injury reports and official dated rosters are unavailable; missing reports are '
                       'modelled as a named fallback, not known-active status. Recent unknown boxes are counted. '
                       'Unseen arrivals and source conflicts remain unscored; no-report probabilities and target '
                       'play are not complete end-to-end availability or actual engine rotation predictions. '
                       'Fewer-than-five patterns are conditionally resampled, unlike the legacy engine fallback. '
                       'Current-day boxes are outcomes only; retained boxes lack publication timestamps.',
        'candidate_coverage': {key: value for key, value in coverage.items() if key != 'per_game'},
        'labels_and_fallback': counts, 'maximum_team_minute_error': errors,
        'maximum_player_regulation_target': peaks, 'minute_results_by_prior_profile_tier': summaries,
        'target_play_brier_by_prior_profile_tier': probabilities,
    }
    return report, result, list(dict.fromkeys(paths))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fold', choices=list(FOLDS), required=True)
    parser.add_argument('--worlds', type=int, default=1000)
    args = parser.parse_args()
    if args.worlds != 1000:
        raise ValueError('the fixed screen uses 1,000 draws')
    output = EXPERIMENTS / f'20261122_a1_s05_no_report_{args.fold}.json'
    rows_output = DERIVED / 'experiments' / f'20261122_a1_s05_no_report_{args.fold}.parquet'
    if output.exists() or rows_output.exists():
        raise FileExistsError(f'refusing to overwrite {output} or {rows_output}')
    report, rows, paths = evaluate(args.fold, args.worlds)
    report['input_sha256'] = {str(path.relative_to(ROOT)): sha256_file(path) for path in paths}
    atomic_bytes(rows_output, rows.to_parquet(index=False))
    write_json(output, report, pretty=True)
    print(f'{args.fold}: saved {len(rows)} no-report candidate distributions and {output}', flush=True)


if __name__ == '__main__':
    main()
