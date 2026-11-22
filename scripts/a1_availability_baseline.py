#!/usr/bin/env python3
"""Score frozen development-only no-report and projected-starter baselines."""
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
from scripts import (a1_compare, a1_flow_compare, a1_minutes_fold_eval, a1_minutes_unconditional,
                     a1_substitution_in_coverage, minutes)  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS  # noqa: E402

ACCOUNTING = EXPERIMENTS / '20261122_a1_s05_minutes_screen_accounting_corrected.json'
KEYS = ['game_id', 'team', 'player']


def choose_starters(states: list[dict], positions: list[str | None],
                    probability: np.ndarray) -> tuple[list[int], str | None]:
    if len(states) != len(positions) or probability.shape != (len(states),):
        raise ValueError('starter candidate states, positions and probabilities have different lengths')
    if not np.isfinite(probability).all() or ((probability < 0) | (probability > 1)).any():
        raise ValueError('starter candidate availability probabilities are invalid')
    sure = np.flatnonzero(probability >= 0.9).tolist()
    pool = sure if sure else list(range(len(states)))
    if len(pool) < 5:
        return [], 'fewer_than_five_sure_candidates'
    if any(positions[i] not in ('G', 'F', 'C') for i in pool):
        return [], 'unknown_prior_position'
    groups = [str(positions[i]) for i in pool]
    chosen = minutes.projected_starters([states[i] for i in pool], groups)
    if len(chosen) != 5 or len(set(chosen)) != 5:
        raise ValueError('starter selector did not return five distinct candidates')
    return [pool[i] for i in chosen], None


def log_loss(probability: np.ndarray, outcome: np.ndarray) -> dict:
    p, y = np.asarray(probability, dtype=float), np.asarray(outcome, dtype=float)
    if p.shape != y.shape or not np.isfinite(p).all() or not np.isin(y, (0, 1)).all() or ((p < 0) | (p > 1)).any():
        raise ValueError('log loss requires finite probabilities and binary outcomes')
    impossible = ((p == 0) & (y == 1)) | ((p == 1) & (y == 0))
    if impossible.any():
        return {'status': 'infinite', 'value': None, 'impossible_outcomes': int(impossible.sum())}
    assigned = np.where(y == 1, p, 1 - p)
    return {'status': 'ok', 'value': float(-np.log(assigned).mean()) if len(p) else None,
            'impossible_outcomes': 0}


def score_probabilities(rows: pd.DataFrame, ids: list[str], weights: np.ndarray) -> dict:
    known = rows['played'].notna() & ~rows['source_conflict']
    scored = rows.loc[known].copy()
    if scored.empty:
        raise ValueError('no known play labels are available for the frozen baseline')
    y = scored['played'].to_numpy(dtype=float)
    result = {}
    for label, column in (('no_report_availability_fallback', 'availability_fallback'),
                          ('target_positive_frequency', 'control_play_probability')):
        p = scored[column].to_numpy(dtype=float)
        if not np.isfinite(p).all() or ((p < 0) | (p > 1)).any() or not np.isin(y, (0, 1)).all():
            raise ValueError(f'{label} has invalid probabilities or play labels')
        scored['brier'] = (p - y) ** 2
        summary = a1_flow_compare.mean_report(scored, ['brier'], ids, weights, player=True)['brier']
        bins = np.minimum((p * 5).astype(int), 4)
        calibration = []
        for index in range(5):
            mask = bins == index
            subset = scored.loc[mask]
            calibration.append({
                'lower': index / 5, 'upper': (index + 1) / 5,
                'players': int(mask.sum()), 'games': int(subset['game_id'].nunique()),
                'mean_prediction': float(p[mask].mean()) if mask.any() else None,
                'observed_play_rate': float(y[mask].mean()) if mask.any() else None,
            })
        result[label] = {'brier': summary, 'log_loss': log_loss(p, y), 'calibration': calibration}
    return result


def raw_starters(fold: str, games: pd.DataFrame) -> tuple[dict[tuple[str, str], set[str]], dict, Path]:
    end = FOLDS[fold][2]
    season = int(end[:4]) + int(end[5:7] > '06')
    path = ROOT / f'data/raw/hoopr/player_box_{season}.parquet'
    box = pd.read_parquet(path, columns=['game_id', 'athlete_id', 'team_id', 'starter', 'did_not_play',
                                         'minutes', 'season_type'])
    box = box.loc[box['season_type'].eq(2) & box['game_id'].notna()].copy()
    box['game_id'] = box['game_id'].astype('int64').astype(str)
    box = box.loc[box['game_id'].isin(games['game_id'])].copy()
    missing_player = int(box['athlete_id'].isna().sum())
    box = box.dropna(subset=['athlete_id', 'team_id']).copy()
    box['player'] = box['athlete_id'].astype('int64').astype(str)
    box['team'] = box['team_id'].astype('int64').astype(str)
    if box.duplicated(['game_id', 'player']).any():
        raise ValueError(f'{fold}: raw starter labels contain duplicate game/player keys')
    box['starter'] = box['starter'].astype('boolean')
    box['did_not_play'] = box['did_not_play'].astype('boolean')
    box['minutes'] = pd.to_numeric(box['minutes'], errors='raise')
    starts = box.loc[box['starter'].eq(True).fillna(False)].copy()
    invalid = starts['did_not_play'].ne(False).fillna(True) | starts['minutes'].isna() | starts['minutes'].le(0)
    valid: dict[tuple[str, str], set[str]] = {}
    invalid_teams = set(zip(starts.loc[invalid, 'game_id'], starts.loc[invalid, 'team']))
    for (game_id, team), part in starts.groupby(['game_id', 'team'], sort=True):
        key = (str(game_id), str(team))
        names = set(part['player'])
        if len(names) == 5 and key not in invalid_teams:
            valid[key] = names
    expected = {(str(row.game_id), str(team)) for row in games.itertuples(index=False)
                for team in (row.home, row.away)}
    if not set(valid).issubset(expected):
        raise ValueError(f'{fold}: raw starter labels contain a non-scheduled team')
    return valid, {'raw_rows_missing_player_id': missing_player,
                   'team_games_without_complete_valid_starters': len(expected - set(valid))}, path


def evaluate(fold: str) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    started = time.monotonic()
    screen_path = DERIVED / f'experiments/20261122_a1_s05_no_report_{fold}_corrected.parquet'
    accounting = json.loads(ACCOUNTING.read_text())
    if accounting['output_sha256'].get(str(screen_path.relative_to(ROOT))) != sha256_file(screen_path):
        raise ValueError(f'{fold}: corrected no-report cohort differs from its independent audit')
    manifest = json.loads(a1_minutes_fold_eval.PREREG.read_text())
    games, segments = a1_minutes_unconditional.fixed_games(manifest, fold)
    rows = pd.read_parquet(screen_path)
    if rows.duplicated(KEYS).any() or not rows['fold'].eq(fold).all():
        raise ValueError(f'{fold}: no-report candidate keys or fold are invalid')
    rows['prior_profile_date'] = pd.to_datetime(rows['prior_profile_date'], errors='raise').dt.strftime('%Y-%m-%d')
    rows['date_et'] = pd.to_datetime(rows['date_et'], errors='raise').dt.strftime('%Y-%m-%d')
    rows['prior_day'] = pd.to_datetime(rows['prior_day'], errors='raise').dt.strftime('%Y-%m-%d')
    if not rows['prior_day'].lt(rows['date_et']).all():
        raise ValueError(f'{fold}: inferred membership is not prior to origin')
    profiles = pd.read_parquet(a1_minutes_fold_eval.CAUSAL_PROFILES, columns=['date_et', 'player', 'pos'])
    rows = a1_substitution_in_coverage.attach_positions(rows, profiles)
    actual, coverage, box_path = raw_starters(fold, games)
    expected_teams = {(str(game.game_id), str(team)) for game in games.itertuples(index=False)
                      for team in (game.home, game.away)}
    ids = sorted(games['game_id'].tolist())
    sample = np.random.default_rng(a1_compare.BOOTSTRAP_SEED).integers(
        0, len(ids), (a1_compare.BOOTSTRAP_REPLICATES, len(ids)))
    weights = np.zeros(sample.shape, dtype=np.int16)
    np.add.at(weights, (np.arange(len(sample))[:, None], sample), 1)
    probabilities = score_probabilities(rows, ids, weights)

    print(f'{fold}: building cutoff-specific D29 history', flush=True)
    model = minutes.build(FOLDS[fold][1], include_current=False)
    coach = minutes.coach_dnps(include_current=False)
    row_outputs, team_outputs = [], []
    done, next_report = 0, 20
    for day, date_rows in rows.groupby('date_et', sort=True):
        dated = a1_minutes_unconditional.as_of_model(model, str(day), coach)
        for (gid, team), part in date_rows.groupby(['game_id', 'team'], sort=True):
            part = part.sort_values('player', kind='stable').copy()
            states = [minutes.player_state(dated, str(team), str(player), str(day)) for player in part['player']]
            chosen, unsupported = choose_starters(states, part['prior_position'].tolist(),
                                                  part['availability_fallback'].to_numpy(dtype=float))
            prediction = {str(part.iloc[i]['player']) for i in chosen}
            truth = actual.get((str(gid), str(team)))
            if unsupported is None and truth is None:
                unsupported = 'incomplete_observed_starters'
            result = {'game_id': str(gid), 'team': str(team), 'date_et': str(day), 'status': unsupported or 'ok',
                      'candidate_count': len(part), 'unknown_prior_positions': int(part['prior_position'].isna().sum()),
                      'actual_starters_outside_candidates': len(truth - set(part['player'])) if truth is not None else None,
                      'slot_accuracy': len(prediction & truth) / 5 if unsupported is None and truth is not None else None,
                      'exact_five': int(prediction == truth) if unsupported is None and truth is not None else None}
            part['projected_starter'] = part['player'].isin(prediction) if chosen else pd.NA
            part['starter_scored_team'] = unsupported is None
            row_outputs.append(part)
            team_outputs.append(result)
        done += int(date_rows['game_id'].nunique())
        if done >= next_report or done == rows['game_id'].nunique():
            print(f'{fold}: {done}/{len(games)} games in {time.monotonic() - started:.1f}s', flush=True)
            while next_report <= done:
                next_report += 20
    candidate_rows = pd.concat(row_outputs, ignore_index=True)
    team_rows = pd.DataFrame(team_outputs)
    seen_teams = set(map(tuple, team_rows[['game_id', 'team']].to_numpy()))
    if not seen_teams.issubset(expected_teams):
        raise ValueError(f'{fold}: inferred roster includes an unscheduled team')
    status_counts = {str(k): int(v) for k, v in team_rows['status'].value_counts().items()}
    status_counts['no_prior_roster'] = len(expected_teams - seen_teams)
    team_summary = a1_flow_compare.mean_report(team_rows, ['slot_accuracy', 'exact_five'], ids, weights)
    known = rows['played'].notna() & ~rows['source_conflict']
    paths = [Path(__file__), ACCOUNTING, screen_path, a1_minutes_fold_eval.PREREG,
             a1_minutes_fold_eval.CAUSAL_PROFILES, segments, box_path, DERIVED / 'teams.json',
             ROOT / 'scripts/minutes.py', ROOT / 'scripts/a1_minutes_unconditional.py',
             ROOT / 'scripts/a1_substitution_in_coverage.py']
    paths += sorted((DERIVED / 'history').glob('*/on_court.parquet'))
    paths += sorted((ROOT / 'data/raw/hoopr').glob('player_box_*.parquet'))
    report = {
        'experiment': 'a1_s07_no_report_and_projected_starter_baselines',
        'fold': fold, 'games': len(games), 'fitted_before': FOLDS[fold][1],
        'candidate_player_games': len(rows), 'known_play_labels_scored': int(known.sum()),
        'unknown_play_labels': int(rows['played'].isna().sum()),
        'source_conflicts_excluded': int(rows['source_conflict'].sum()),
        'play_proxies': probabilities,
        'starter_team_status': status_counts,
        'starter_label_coverage': coverage,
        'starter_team_results': team_summary,
        'observed_starters_outside_inferred_rosters': int(team_rows['actual_starters_outside_candidates'].sum()),
        'seconds': round(time.monotonic() - started, 1),
        'limitations': 'No historical dated injury reports or official rosters are retained. The physical-availability '
                       'fallback and target-positive frequencies are not calibrated physical status; both are scored '
                       'against play/DNP labels only as proxies. Unknown labels remain excluded. Starter predictions '
                       'use prior-box membership and strictly prior positions; unsupported teams are reported, not '
                       'imputed. Raw boxes lack historical publication/correction timestamps.',
        'input_sha256': {str(p.relative_to(ROOT)): sha256_file(p) for p in dict.fromkeys(paths)},
    }
    return report, candidate_rows, team_rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fold', choices=list(FOLDS), required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--rows-output', type=Path, required=True)
    parser.add_argument('--teams-output', type=Path, required=True)
    args = parser.parse_args()
    paths = (args.output, args.rows_output, args.teams_output)
    if len({path.resolve() for path in paths}) != 3 or any(path.exists() for path in paths):
        raise FileExistsError('baseline output paths must be distinct and must not already exist')
    report, rows, teams = evaluate(args.fold)
    atomic_bytes(args.rows_output, rows.to_parquet(index=False))
    atomic_bytes(args.teams_output, teams.to_parquet(index=False))
    report['output_sha256'] = {str(path.resolve().relative_to(ROOT)): sha256_file(path)
                               for path in (args.rows_output, args.teams_output)}
    write_json(args.output, report, pretty=True)
    print(f"{args.fold}: saved {len(rows)} candidates and {len(teams)} team-games", flush=True)


if __name__ == '__main__':
    main()
