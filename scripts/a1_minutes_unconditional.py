#!/usr/bin/env python3
"""Screen pre-origin prior-box roster minutes, including known zero-minute outcomes.

This is an all-candidates-active sensitivity analysis, not a historically available injury forecast.
"""
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
                     a1_minutes_candidate, a1_minutes_fold_eval, aggregate, minutes, projection)  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS  # noqa: E402


def fixed_games(manifest: dict, fold: str) -> tuple[pd.DataFrame, Path]:
    games = a1_minutes_fold_eval.fold_games(manifest, fold)
    end = FOLDS[fold][2]
    season = int(end[:4]) + int(end[5:7] > '06')
    source = DERIVED / f'history/{season}/segments.parquet'
    segments = pd.read_parquet(source, columns=['game_id', 'date_et', 'offense', 'defense', 'off_home'])
    segments['game_id'] = segments['game_id'].astype(str)
    segments = segments.loc[segments['game_id'].isin(games['game_id'])].copy()
    if segments[['date_et', 'offense', 'defense', 'off_home']].isna().any().any():
        raise ValueError(f'{fold}: schedule segments have missing team, home or date values')
    segments['home'] = np.where(segments['off_home'], segments['offense'], segments['defense']).astype(str)
    segments['away'] = np.where(segments['off_home'], segments['defense'], segments['offense']).astype(str)
    pairs = segments[['game_id', 'date_et', 'home', 'away']].drop_duplicates()
    a1_compare._unique(pairs, ['game_id'], f'{fold} recorded schedule sides')
    out = games.merge(pairs, on=['game_id', 'date_et'], validate='one_to_one')
    if len(out) != len(games) or out['home'].eq(out['away']).any():
        raise ValueError(f'{fold}: fixed games do not have distinct, recorded schedule sides')
    return out, source


def attach_actuals(cohort: pd.DataFrame, pg: pd.DataFrame) -> pd.DataFrame:
    observed = pg[['game_id', 'player', 'team', 'reg']].copy()
    a1_compare._unique(observed, ['game_id', 'player'], 'on-court regulation outcomes')
    rows = cohort.merge(observed, on=['game_id', 'player', 'team'], how='left', validate='one_to_one')
    if (rows['reg'].notna() & (~np.isfinite(rows['reg']) | rows['reg'].lt(0) | rows['reg'].gt(48))).any():
        raise ValueError('on-court regulation minutes must be finite and between 0 and 48')
    rows['source_conflict'] = rows['played'].eq(0) & rows['reg'].fillna(0).gt(0)
    rows['actual_reg'] = np.nan
    rows.loc[rows['played'].eq(0) & ~rows['source_conflict'], 'actual_reg'] = 0.0
    rows.loc[rows['played'].eq(1), 'actual_reg'] = rows.loc[rows['played'].eq(1), 'reg']
    return rows


def attach_prior_roles(cohort: pd.DataFrame, pre: pd.DataFrame) -> pd.DataFrame:
    events = pre[['date_et', 'player', 'usage', 'start_share']].rename(columns={'date_et': 'day'}).copy()
    events['day'] = pd.to_datetime(events['day'], errors='raise')
    rows = a1_minutes_audit.prior_join(cohort, events, ['usage', 'start_share']).rename(
        columns={'day': 'prior_profile_date'})
    usage = pd.to_numeric(rows['usage'], errors='raise').to_numpy(dtype=float)
    start = pd.to_numeric(rows['start_share'], errors='raise').to_numpy(dtype=float)
    for name, value in (('usage', usage), ('start share', start)):
        if (np.isinf(value) | (value < 0) | (value > 1)).any():
            raise ValueError(f'prior {name} must be between zero and one or missing')
    known = np.isfinite(usage) & np.isfinite(start)
    rows['tier'] = np.select([~known, usage >= 0.25, start >= 0.5],
                             ['unknown', 'star', 'starter'], default='bench')
    return rows


def as_of_model(model: dict, day: str, coach_dnps: dict) -> dict:
    _, latest, team_dates = minutes.state_pass(model['pg'], model['params'], model['ramp'], day, coach_dnps)
    if any(date >= day for dates in team_dates.values() for date in dates):
        raise ValueError('same-day or future team games entered minute states')
    if any(state['last_date'] is not None and state['last_date'] >= day for state in latest.values()):
        raise ValueError('same-day or future player appearances entered minute states')
    return {**model, 'latest': latest, 'team_dates': team_dates}


def distribution(states: list[dict], sd_table: dict, actual: np.ndarray, played: np.ndarray,
                 seed: int, strict: bool, worlds: int) -> dict[str, np.ndarray]:
    solver = a1_minutes_candidate if strict else minutes
    target = solver.game_targets(states)
    spread = minutes.sd_for(sd_table, target)
    if not np.isfinite(spread).all():
        raise ValueError('minute residual spread is not finite')
    draws = solver.redraw(target, [s['cap'] for s in states], spread, worlds, np.random.default_rng(seed))
    if not np.isfinite(draws).all() or np.isinf(actual).any() or np.isinf(played).any():
        raise ValueError('minute draws or observed values are invalid')
    known = np.isfinite(actual)
    lo, hi = np.quantile(draws, (0.1, 0.9), axis=0)
    crps, covered = np.full(len(actual), np.nan), np.full(len(actual), np.nan)
    if known.any():
        crps[known] = aggregate.crps_samples(draws[:, known], actual[known])
        covered[known] = ((actual[known] >= lo[known]) & (actual[known] <= hi[known])).astype(float)
    probability = (draws > 0).mean(axis=0)
    return {'mean': draws.mean(axis=0), 'crps': crps, 'covered': covered,
            'play_probability': probability, 'play_brier': (probability - played) ** 2}


def evaluate(fold: str, worlds: int) -> tuple[dict, pd.DataFrame, list[Path]]:
    manifest = json.loads(a1_minutes_fold_eval.PREREG.read_text())
    games, segments = fixed_games(manifest, fold)
    coverage, cohort = a1_availability_cohort.build_for_games(games, fold, 'A1 preregistered fixed games')
    original = minutes.build(FOLDS[fold][1], include_current=False)
    clean = a1_minutes_candidate.build(FOLDS[fold][1], include_current=False)
    coach = minutes.coach_dnps(include_current=False)
    rows = attach_actuals(cohort, original['pg'])
    pre = pd.read_parquet(a1_minutes_fold_eval.CAUSAL_PROFILES, columns=['date_et', 'player', 'usage', 'start_share'])
    rows = attach_prior_roles(rows, pre)
    dates = pd.to_datetime(rows['date_et'], errors='raise')
    rows['date_et'] = dates.dt.strftime('%Y-%m-%d')
    if rows['prior_day'].ge(rows['date_et']).any():
        raise ValueError('roster membership is not strictly pre-origin')

    start, results, done, next_report = time.monotonic(), [], 0, 20
    for day_value, date_rows in rows.groupby('date_et', sort=True):
        if not isinstance(day_value, str):
            raise TypeError('minute-state origin dates must be ISO strings')
        day = day_value
        models = {'control': as_of_model(original, day, coach), 'nba': as_of_model(clean, day, coach)}
        for (game_id, team), part in date_rows.groupby(['game_id', 'team'], sort=True):
            part = part.sort_values('player', kind='stable')
            if len(part) < 5:
                raise ValueError(f'{fold} {game_id} {team}: prior roster cannot cover a legal five')
            states = {name: [minutes.player_state(model, str(team), str(pid), day) for pid in part['player']]
                      for name, model in models.items()}
            actual = part['actual_reg'].to_numpy(dtype=float)
            played = part['played'].where(~part['source_conflict']).to_numpy(dtype=float)
            seed = projection.seed_for('a1_s05_unconditional', fold, str(game_id), str(team))
            outputs = {
                'control': distribution(states['control'], original['sd'], actual, played, seed, False, worlds),
                'nba_only': distribution(states['nba'], clean['sd'], actual, played, seed, False, worlds),
                'strict': distribution(states['control'], original['sd'], actual, played, seed, True, worlds),
                'combined': distribution(states['nba'], clean['sd'], actual, played, seed, True, worlds),
            }
            out = part[['game_id', 'team', 'player', 'date_et', 'prior_day', 'prior_profile_date',
                        'played', 'reg', 'actual_reg', 'source_conflict', 'listed_in_box', 'tier']].copy()
            out['fold'] = fold
            for name, values in outputs.items():
                for metric, value in values.items():
                    out[f'{name}_{metric}'] = value
            results.append(out)
        done += int(date_rows['game_id'].nunique())
        if done >= next_report or done == len(games):
            print(f'{fold}: {done}/{len(games)} games in {time.monotonic() - start:.1f}s', flush=True)
            while next_report <= done:
                next_report += 20
    result = pd.concat(results, ignore_index=True)
    result = result.rename(columns={'reg': 'on_court_reg', 'actual_reg': 'reg'})
    ids = sorted(games['game_id'].tolist())
    summaries = a1_minutes_fold_eval.summaries(result, ids)
    draws = np.random.default_rng(a1_compare.BOOTSTRAP_SEED).integers(
        0, len(ids), (a1_compare.BOOTSTRAP_REPLICATES, len(ids)))
    weights = np.zeros(draws.shape, dtype=np.int16)
    np.add.at(weights, (np.arange(len(draws))[:, None], draws), 1)
    probability_names = []
    for variant in a1_minutes_fold_eval.VARIANTS:
        probability_names.append(f'{variant}_play_brier')
        if variant != 'control':
            name = f'{variant}_minus_control_play_brier'
            result[name] = result[f'{variant}_play_brier'] - result['control_play_brier']
            probability_names.append(name)
    probabilities = {
        tier: a1_flow_compare.mean_report(result if tier == 'all' else result.loc[result['tier'].eq(tier)],
                                          probability_names, ids, weights, player=True)
        for tier in ('all', *a1_compare.ROLE_TIERS)
    }
    label_counts = {'candidates': len(result), 'labelled_plays': int(result['played'].eq(1).sum()),
                    'labelled_dnps': int(result['played'].eq(0).sum()),
                    'unknown_play': int(result['played'].isna().sum()),
                    'unlisted': int((~result['listed_in_box']).sum()),
                    'known_regulation_actual': int(result['reg'].notna().sum()),
                    'source_conflicts_excluded_from_minute_scores': int(result['source_conflict'].sum()),
                    'positive_box_minutes_without_on_court_regulation': int(
                        (result['played'].eq(1) & result['reg'].isna()).sum())}
    paths = [a1_minutes_fold_eval.PREREG, a1_minutes_fold_eval.CAUSAL_PROFILES, segments,
             ROOT / f'data/raw/hoopr/player_box_{coverage["season"]}.parquet',
             DERIVED / 'teams.json', ROOT / 'scripts/minutes.py', Path(a1_minutes_candidate.__file__),
             Path(a1_availability_cohort.__file__), Path(a1_minutes_fold_eval.__file__), Path(__file__)]
    paths += sorted((DERIVED / 'history').glob('*/on_court.parquet'))
    paths += sorted((ROOT / 'data/raw/hoopr').glob('player_box_*.parquet'))
    paths = list(dict.fromkeys(paths))
    report = {
        'experiment': 'a1_s05_prior_roster_unconditional_minutes_screen', 'fold': fold, 'games': len(games),
        'worlds': worlds, 'fold_cutoff': FOLDS[fold][1],
        'method': 'Construct each team roster only from its latest uniquely observed prior box team, treat every '
                  'candidate as physically available, and draw allocations from D29 latest states rebuilt strictly '
                  'before each origin. Score known zero-minute DNPs and known positive regulation minutes; unknown '
                  'statuses remain unscored but stay in the allocation. Previous pregame profile tiers are joined '
                  'strictly before the origin. Fold ramp and residual distributions use pre-validation fits.',
        'limitations': 'This is a no-injury-information all-candidates-active sensitivity, not the production '
                       'historical pregame forecast or a complete unconditional accuracy estimate. DNPs include '
                       'injuries; unlisted candidates, missing on-court minutes and new roster members are not '
                       'invented. Prior boxes lack publication timestamps. Tier definitions use the latest earlier '
                       'profile, not S01 same-game profiles. Targets are not the full engine.',
        'candidate_coverage': {k: v for k, v in coverage.items() if k != 'per_game'},
        'labels': label_counts, 'minute_results_by_prior_profile_tier': summaries,
        'play_brier_by_prior_profile_tier': probabilities,
    }
    return report, result, paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fold', choices=list(FOLDS), required=True)
    parser.add_argument('--worlds', type=int, default=1000)
    args = parser.parse_args()
    if args.worlds != 1000:
        raise ValueError('the fixed screen uses 1,000 draws')
    output = EXPERIMENTS / f'20261122_a1_s05_unconditional_{args.fold}.json'
    rows_output = DERIVED / 'experiments' / f'20261122_a1_s05_unconditional_{args.fold}.parquet'
    if output.exists() or rows_output.exists():
        raise FileExistsError(f'refusing to overwrite {output} or {rows_output}')
    report, rows, paths = evaluate(args.fold, args.worlds)
    report['input_sha256'] = {str(path.relative_to(ROOT)): sha256_file(path) for path in paths}
    atomic_bytes(rows_output, rows.to_parquet(index=False))
    write_json(output, report, pretty=True)
    print(f'{args.fold}: saved {len(rows)} roster-candidate distributions and {output}', flush=True)


if __name__ == '__main__':
    main()
