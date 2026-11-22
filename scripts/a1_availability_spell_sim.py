#!/usr/bin/env python3
"""Explore censored recorded-DNP spell lengths with earlier-fold play proxies."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, atomic_bytes, sha256_file, write_json  # noqa: E402
from scripts import a1_availability_sequence_screen, projection  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS, TEST_FROM  # noqa: E402

SEQUENCES = DERIVED / 'experiments/20261122_a1_s07_sequences.parquet'
SCREEN = EXPERIMENTS / '20261122_a1_s07_sequence_screen.json'
SCREEN_AUDIT = EXPERIMENTS / '20261122_a1_s07_sequence_screen_accounting.json'
MANIFEST = EXPERIMENTS / '20261122_a1_pre_candidate_manifest.json'
HORIZON, WORLDS, BOOTSTRAPS, BOOTSTRAP_SEED = 5, 10_000, 10_000, 20261122


def build_episodes(rows: pd.DataFrame, fold: str, game_dates: pd.DataFrame) -> pd.DataFrame:
    _, first, last = FOLDS[fold]
    required = ['season', 'team', 'player', 'prior_game_id', 'prior_day', 'game_id', 'date_et',
                'cohort', 'prior_role', 'prior_reason', 'prior_duration', 'next_status', 'outcome']
    if set(required) - set(rows):
        raise ValueError('recorded-spell sequence columns are missing')
    returns = rows.loc[rows['cohort'].eq('return'), required].copy()
    keys = ['season', 'team', 'player', 'prior_game_id']
    if returns.duplicated(keys).any():
        raise ValueError('duplicate recorded-spell prior listing')
    records = returns.to_dict('records')
    by_prior = {tuple(record[k] for k in keys): record for record in records}
    fixed = game_dates[['game_id', 'date_et']].copy()
    if len(fixed) != 200 or fixed['game_id'].duplicated().any() or not fixed['date_et'].between(first, last).all():
        raise ValueError(f'{fold}: fixed validation game/date panel differs')
    date_by_game = dict(zip(fixed['game_id'], fixed['date_et']))
    starts = [record for record in records if record['prior_duration'] == 1
              and record['game_id'] in date_by_game and first <= record['date_et'] <= last]
    episodes = []
    for initial in starts:
        if initial['date_et'] != date_by_game[initial['game_id']]:
            raise ValueError('spell anchor date differs from the fixed game panel')
        current = initial
        observed, event, censor = 0, 0, None
        for step in range(1, HORIZON + 1):
            date = current['date_et']
            if date is None or pd.isna(date) or date > last:
                censor = 'fold_end_or_season_end'
                break
            if date < first or date >= TEST_FROM or current['prior_day'] >= date:
                raise ValueError('spell follows a game outside its date-safe validation window')
            state = current['next_status']
            if state not in ('play', 'dnp'):
                censor = str(state)
                break
            observed = step
            if state == 'play':
                if current['outcome'] != 1:
                    raise ValueError('recorded return has an inconsistent outcome')
                event = step
                break
            if current['outcome'] != 0:
                raise ValueError('recorded continued DNP has an inconsistent outcome')
            if step == HORIZON:
                censor = 'horizon'
                break
            key = (current['season'], current['team'], current['player'], current['game_id'])
            if key not in by_prior:
                raise ValueError('a known continued DNP has no subsequent sequence row')
            following = by_prior[key]
            if (following['prior_duration'] != step + 1 or following['prior_day'] != current['date_et']
                    or following['prior_reason'] != initial['prior_reason']
                    or following['prior_role'] != initial['prior_role']):
                raise ValueError('consecutive recorded DNP spell state is inconsistent')
            current = following
        if event == 0 and censor is None:
            raise ValueError('recorded spell ended without a return or explicit censor')
        episodes.append({
            'fold': fold, 'game_id': initial['game_id'], 'date_et': initial['date_et'],
            'season': initial['season'], 'team': initial['team'], 'player': initial['player'],
            'prior_game_id': initial['prior_game_id'], 'prior_day': initial['prior_day'],
            'prior_role': initial['prior_role'], 'prior_reason': initial['prior_reason'],
            'observed_steps': observed, 'return_step': event, 'censor_reason': censor,
        })
    return pd.DataFrame(episodes)


def add_predictions(train: pd.DataFrame, episodes: pd.DataFrame, fold: str) -> pd.DataFrame:
    if episodes.empty:
        raise ValueError(f'{fold}: no first-DNP anchors in the fixed panel')
    out = episodes.copy()
    reasons = out[['prior_reason']].copy()
    baseline, _ = a1_availability_sequence_screen.probabilities(train, reasons, ['prior_reason'])
    survival = {'baseline': np.ones(len(out)), 'candidate': np.ones(len(out))}
    uniforms = np.random.default_rng(projection.seed_for('a1_s07_recorded_spell', fold)).random((len(out), WORLDS))
    for step in range(1, HORIZON + 1):
        features = reasons.copy()
        features['duration_bin'] = '1' if step == 1 else '2-3' if step <= 3 else '4+'
        candidate, _ = a1_availability_sequence_screen.probabilities(
            train, features, ['prior_reason', 'duration_bin'])
        for name, hazard in (('baseline', baseline), ('candidate', candidate)):
            survival[name] = survival[name] * (1 - hazard)
            out[f'{name}_survival_{step}'] = survival[name]
            out[f'{name}_sim_survival_{step}'] = (uniforms < survival[name][:, None]).mean(axis=1)
    return out


def summarize(rows: pd.DataFrame, ids: list[str], weights: np.ndarray) -> dict:
    if rows.empty:
        return {'anchors': 0, 'games': 0, 'status': 'insufficient_sample', 'horizons': []}
    grouped = rows.assign(anchors=1).groupby('game_id').sum(numeric_only=True).reindex(ids, fill_value=0)
    starts = grouped['anchors'].to_numpy(dtype=float)
    start_draws = weights @ starts
    group_supported = len(rows) >= 100 and rows['game_id'].nunique() >= 30
    if group_supported and (start_draws == 0).any():
        raise ValueError('an anchor-game bootstrap has no sampled spells')
    start_draws = np.where(start_draws == 0, np.nan, start_draws)
    observed_survival = 1.
    bootstrap_survival = np.ones(len(weights))
    horizons = []
    for step in range(1, HORIZON + 1):
        risk = rows['observed_steps'].ge(step)
        events = rows['return_step'].eq(step)
        if (events & ~risk).any():
            raise ValueError('a recorded return is not in its risk set')
        counts = rows.assign(risk=risk.astype(int), event=events.astype(int)).groupby('game_id')[
            ['risk', 'event']].sum().reindex(ids, fill_value=0)
        n_risk, n_event = int(risk.sum()), int(events.sum())
        games_at_risk = int(rows.loc[risk, 'game_id'].nunique())
        supported = n_risk >= 100 and games_at_risk >= 30
        observed_survival = observed_survival * (1 - n_event / n_risk) if n_risk else np.nan
        risk_draws = weights @ counts['risk'].to_numpy(dtype=float)
        event_draws = weights @ counts['event'].to_numpy(dtype=float)
        if supported and (risk_draws == 0).any():
            raise ValueError('a supported risk-set bootstrap has zero risk')
        if (risk_draws == 0).any():
            bootstrap_survival[:] = np.nan
        else:
            bootstrap_survival *= 1 - event_draws / risk_draws
        entry = {
            'step': step, 'recorded_games_missed_at_least': step + 1,
            'at_risk': n_risk, 'games_at_risk': games_at_risk, 'returns': n_event,
            'censored_before_step': int((rows['return_step'].eq(0) & rows['observed_steps'].eq(step - 1)).sum()),
            'status': 'ok' if supported else 'insufficient_sample',
            'observed_survival': float(observed_survival) if n_risk else None,
            'observed_survival_ci_95': np.quantile(bootstrap_survival, [0.025, 0.975]).tolist()
            if supported else None,
        }
        for name in ('baseline', 'candidate'):
            column = f'{name}_survival_{step}'
            sums = grouped[column].to_numpy(dtype=float)
            analytic = float(rows[column].mean())
            simulated = float(rows[f'{name}_sim_survival_{step}'].mean())
            tolerance = 6 * np.sqrt(0.25 / (len(rows) * WORLDS))
            if abs(analytic - simulated) > tolerance:
                raise ValueError(f'{name} simulated survival differs from its analytic expectation')
            estimates = weights @ sums / start_draws
            entry[name] = {
                'analytic_survival': analytic, 'simulated_survival': simulated,
                'survival_ci_95': np.quantile(estimates, [0.025, 0.975]).tolist() if supported else None,
                'minus_observed': analytic - observed_survival if n_risk else None,
                'minus_observed_ci_95': np.quantile(estimates - bootstrap_survival, [0.025, 0.975]).tolist()
                if supported else None,
            }
        horizons.append(entry)
    return {
        'anchors': len(rows), 'games': int(rows['game_id'].nunique()),
        'status': 'ok' if group_supported else 'insufficient_sample',
        'observed_returns': int(rows['return_step'].gt(0).sum()),
        'censor_reasons': {str(k): int(v) for k, v in rows['censor_reason'].value_counts().items()},
        'horizons': horizons,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--rows-output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.rows_output.exists() or args.output.resolve() == args.rows_output.resolve():
        raise FileExistsError('spell output paths must be distinct and new')
    screen, audit = json.loads(SCREEN.read_text()), json.loads(SCREEN_AUDIT.read_text())
    if audit['input_sha256'].get(str(SCREEN.relative_to(ROOT))) != sha256_file(SCREEN):
        raise ValueError('sequence screen differs from its independent accounting')
    if audit['input_sha256'].get(str(SEQUENCES.relative_to(ROOT))) != sha256_file(SEQUENCES):
        raise ValueError('sequence rows differ from their independent accounting')
    for path, digest in screen['input_sha256'].items():
        if sha256_file(ROOT / path) != digest:
            raise ValueError(f'precommitted screen input differs: {path}')
    rows = pd.read_parquet(SEQUENCES)
    manifest = json.loads(MANIFEST.read_text())
    reports, all_episodes = [], []
    for fold, (train_end, _, _) in FOLDS.items():
        selection = manifest['control']['games'] if fold == 'F4' else manifest['confirmation'][fold]['games']
        game_dates = pd.DataFrame(selection)[['game_id', 'date_et']]
        ids = sorted(game_dates['game_id'].tolist())
        train = rows.loc[rows['cohort'].eq('return') & rows['outcome'].notna()
                         & rows['date_et'].le(train_end)].copy()
        if train.empty or train['date_et'].ge(FOLDS[fold][1]).any():
            raise ValueError(f'{fold}: earlier-fold return training is absent or not chronological')
        episodes = add_predictions(train, build_episodes(rows, fold, game_dates), fold)
        draws = np.random.default_rng(BOOTSTRAP_SEED).integers(0, len(ids), (BOOTSTRAPS, len(ids)))
        weights = np.zeros(draws.shape, dtype=np.int16)
        np.add.at(weights, (np.arange(len(draws))[:, None], draws), 1)
        groups = {'all': summarize(episodes, ids, weights)}
        for role in ('star', 'starter', 'bench', 'unknown'):
            groups[role] = summarize(episodes.loc[episodes['prior_role'].eq(role)], ids, weights)
        reports.append({'fold': fold, 'training_through': train_end, 'groups': groups})
        all_episodes.append(episodes)
        print(f'{fold}: simulated {len(episodes)} recorded-spell anchors × {WORLDS} worlds', flush=True)
    combined = pd.concat(all_episodes, ignore_index=True)
    atomic_bytes(args.rows_output, combined.to_parquet(index=False))
    inputs = [Path(__file__), SEQUENCES, SCREEN, SCREEN_AUDIT, MANIFEST,
              ROOT / 'scripts/a1_availability_sequence_screen.py', ROOT / 'scripts/projection.py',
              ROOT / 'scripts/evaluate.py']
    output = {
        'experiment': 'a1_s07_censored_recorded_spell_simulation',
        'horizon_next_games': HORIZON, 'worlds_per_anchor': WORLDS, 'bootstrap_replicates': BOOTSTRAPS,
        'bootstrap_seed': BOOTSTRAP_SEED, 'folds': reports, 'anchors': len(combined),
        'limitations': 'Selected known prior DNPs, retrospective reason text and potentially informative right '
                       'censoring describe recorded listings, not physical absence or a pre-tip injury forecast. '
                       'Observed survival assumes non-informative censoring. Estimates after five next games '
                       'remain censored; unsupported role/horizon cells have no interval.',
        'input_sha256': {str(p.relative_to(ROOT)): sha256_file(p) for p in inputs},
        'output_sha256': {str(args.rows_output.resolve().relative_to(ROOT)): sha256_file(args.rows_output)},
    }
    write_json(args.output, output, pretty=True)
    print(f'saved {len(combined)} recorded-spell anchors', flush=True)


if __name__ == '__main__':
    main()
