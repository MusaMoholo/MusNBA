#!/usr/bin/env python3
"""Independently reconcile the frozen censored recorded-spell experiment."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, sha256_file, write_json  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS, TEST_FROM  # noqa: E402

MANIFEST = EXPERIMENTS / '20261122_a1_pre_candidate_manifest.json'
SEQUENCES = DERIVED / 'experiments/20261122_a1_s07_sequences.parquet'
REPORT = EXPERIMENTS / '20261122_a1_s07_spell_sim.json'
ROWS = DERIVED / 'experiments/20261122_a1_s07_spell_sim.parquet'
HORIZON, WORLDS, BOOTSTRAPS, BOOTSTRAP_SEED = 5, 10_000, 10_000, 20261122


def close(actual: object, expected: object, label: str) -> None:
    if expected is None:
        if actual is not None:
            raise ValueError(f'{label}: expected an unsupported or missing value')
        return
    a, b = np.asarray(actual, dtype=float), np.asarray(expected, dtype=float)
    if a.shape != b.shape or not np.isfinite(a).all() or not np.allclose(a, b, atol=1e-12, rtol=0):
        raise ValueError(f'{label}: independent value differs')


def audit() -> dict:
    report, manifest = json.loads(REPORT.read_text()), json.loads(MANIFEST.read_text())
    for path, digest in {**report['input_sha256'], **report['output_sha256']}.items():
        if sha256_file(ROOT / path) != digest:
            raise ValueError(f'spell experiment fingerprint differs: {path}')
    if (report['horizon_next_games'], report['worlds_per_anchor'], report['bootstrap_replicates'],
            report['bootstrap_seed']) != (HORIZON, WORLDS, BOOTSTRAPS, BOOTSTRAP_SEED):
        raise ValueError('spell experiment settings differ from the frozen protocol')
    seq, saved = pd.read_parquet(SEQUENCES), pd.read_parquet(ROWS)
    returns = seq.loc[seq['cohort'].eq('return')].copy()
    keys = ['season', 'team', 'player', 'prior_game_id']
    if returns.duplicated(keys).any() or saved.duplicated(['fold', *keys]).any():
        raise ValueError('recorded spell keys are duplicated')
    by_prior = {tuple(row[k] for k in keys): row for row in returns.to_dict('records')}
    checked_anchors = checked_predictions = checked_horizons = 0
    for fold, (train_end, first, last) in FOLDS.items():
        selection = manifest['control']['games'] if fold == 'F4' else manifest['confirmation'][fold]['games']
        game_dates = {str(game['game_id']): str(game['date_et']) for game in selection}
        ids = sorted(game_dates)
        if len(ids) != 200 or any(day < first or day > last for day in game_dates.values()):
            raise ValueError(f'{fold}: invalid fixed game panel')
        anchors = returns.loc[returns['prior_duration'].eq(1) & returns['game_id'].isin(ids)
                              & returns['date_et'].between(first, last)].copy()
        observed = saved.loc[saved['fold'].eq(fold)].copy()
        if len(anchors) != len(observed):
            raise ValueError(f'{fold}: anchor count differs')
        original = anchors.set_index(keys)
        if set(original.index) != set(map(tuple, observed[keys].to_numpy())):
            raise ValueError(f'{fold}: anchor membership differs')
        for item in observed.to_dict('records'):
            key = tuple(item[k] for k in keys)
            anchor = original.loc[key]
            for col in ('game_id', 'date_et', 'prior_day', 'prior_role', 'prior_reason'):
                if item[col] != anchor[col]:
                    raise ValueError(f'{fold}: anchor field differs: {col}')
            if game_dates[str(anchor['game_id'])] != anchor['date_et']:
                raise ValueError(f'{fold}: anchor date differs from the panel')
            current, steps, event, censor = anchor.to_dict(), 0, 0, None
            for step in range(1, HORIZON + 1):
                day = current['date_et']
                if pd.isna(day) or day > last:
                    censor = 'fold_end_or_season_end'
                    break
                if day < first or day >= TEST_FROM or current['prior_day'] >= day:
                    raise ValueError(f'{fold}: invalid temporal ordering')
                state = current['next_status']
                if state not in ('play', 'dnp'):
                    censor = str(state)
                    break
                steps = step
                if state == 'play':
                    if current['outcome'] != 1:
                        raise ValueError(f'{fold}: inconsistent recorded return')
                    event = step
                    break
                if current['outcome'] != 0:
                    raise ValueError(f'{fold}: inconsistent recorded DNP')
                if step == HORIZON:
                    censor = 'horizon'
                    break
                next_key = (item['season'], item['team'], item['player'], current['game_id'])
                if next_key not in by_prior:
                    raise ValueError(f'{fold}: a listed DNP continuation is missing')
                following = by_prior[next_key]
                if (following['prior_duration'] != step + 1 or following['prior_day'] != day
                        or following['prior_reason'] != item['prior_reason']
                        or following['prior_role'] != item['prior_role']):
                    raise ValueError(f'{fold}: recorded spell chain differs')
                current = following
            saved_censor = None if pd.isna(item['censor_reason']) else item['censor_reason']
            if (item['observed_steps'], item['return_step'], saved_censor) != (steps, event, censor):
                raise ValueError(f'{fold}: return or right-censor outcome differs')
            checked_anchors += 1

        train = returns.loc[returns['outcome'].notna() & returns['date_et'].le(train_end)]
        if train.empty or not train['outcome'].isin([0, 1]).all() or train['date_et'].ge(first).any():
            raise ValueError(f'{fold}: return fitting inputs are not valid earlier observations')
        reason = train.groupby('prior_reason')['outcome'].agg(['sum', 'count'])
        duration = train.groupby(['prior_reason', 'duration_bin'])['outcome'].agg(['sum', 'count'])
        survival = {'baseline': np.ones(len(observed)), 'candidate': np.ones(len(observed))}
        seed = int.from_bytes(hashlib.sha256(f'a1_s07_recorded_spell|{fold}'.encode()).digest()[:8], 'little')
        uniforms = np.random.default_rng(seed).random((len(observed), WORLDS))
        for step in range(1, HORIZON + 1):
            interval = '1' if step == 1 else '2-3' if step <= 3 else '4+'
            hazards = {'baseline': [], 'candidate': []}
            for value in observed['prior_reason']:
                for name, table, key in (('baseline', reason, value), ('candidate', duration, (value, interval))):
                    if key in table.index:
                        row = table.loc[key]
                        hazard = (float(row['sum']) + 1) / (int(row['count']) + 2)
                    else:
                        hazard = 0.5
                    hazards[name].append(hazard)
            for name in ('baseline', 'candidate'):
                survival[name] *= 1 - np.asarray(hazards[name])
                simulated = np.mean(uniforms < survival[name][:, None], axis=1)
                close(observed[f'{name}_survival_{step}'].to_numpy(), survival[name], f'{fold} analytic {name}')
                close(observed[f'{name}_sim_survival_{step}'].to_numpy(), simulated, f'{fold} simulated {name}')
                checked_predictions += 2 * len(observed)

        draws = np.random.default_rng(BOOTSTRAP_SEED).integers(0, len(ids), (BOOTSTRAPS, len(ids)))
        weights = np.zeros(draws.shape, dtype=np.int16)
        np.add.at(weights, (np.arange(len(draws))[:, None], draws), 1)
        fold_report = next(part for part in report['folds'] if part['fold'] == fold)
        if fold_report['training_through'] != train_end:
            raise ValueError(f'{fold}: recorded training cutoff differs')
        for role in ('all', 'star', 'starter', 'bench', 'unknown'):
            part = observed if role == 'all' else observed.loc[observed['prior_role'].eq(role)]
            result = fold_report['groups'][role]
            if not len(part):
                if result != {'anchors': 0, 'games': 0, 'status': 'insufficient_sample', 'horizons': []}:
                    raise ValueError(f'{fold}/{role}: empty group is not explicitly unsupported')
                continue
            game_count = part['game_id'].nunique()
            status = 'ok' if len(part) >= 100 and game_count >= 30 else 'insufficient_sample'
            censor_counts = {str(k): int(v) for k, v in part['censor_reason'].value_counts().items()}
            if (result['anchors'] != len(part) or result['games'] != game_count or result['status'] != status
                    or result['observed_returns'] != int(part['return_step'].gt(0).sum())
                    or result['censor_reasons'] != censor_counts or len(result['horizons']) != HORIZON):
                raise ValueError(f'{fold}/{role}: group accounting differs')
            start_counts = part.groupby('game_id').size().reindex(ids, fill_value=0).to_numpy(dtype=float)
            start_draws = weights @ start_counts
            observed_survival = 1.
            boot_survival = np.ones(BOOTSTRAPS)
            for step, entry in enumerate(result['horizons'], 1):
                risk = part['observed_steps'].ge(step)
                events = part['return_step'].eq(step)
                n_risk, n_event = int(risk.sum()), int(events.sum())
                risk_games = int(part.loc[risk, 'game_id'].nunique())
                supported = n_risk >= 100 and risk_games >= 30
                counts = pd.DataFrame({'game_id': part['game_id'], 'risk': risk.astype(int),
                                       'event': events.astype(int)}).groupby('game_id').sum().reindex(ids, fill_value=0)
                risk_draws = weights @ counts['risk'].to_numpy(dtype=float)
                event_draws = weights @ counts['event'].to_numpy(dtype=float)
                if n_risk:
                    observed_survival *= 1 - n_event / n_risk
                if (risk_draws == 0).any():
                    if supported:
                        raise ValueError(f'{fold}/{role}: supported risk bootstrap is empty')
                    boot_survival[:] = np.nan
                else:
                    boot_survival *= 1 - event_draws / risk_draws
                if (entry['step'] != step or entry['recorded_games_missed_at_least'] != step + 1
                        or entry['at_risk'] != n_risk or entry['games_at_risk'] != risk_games
                        or entry['returns'] != n_event
                        or entry['censored_before_step'] != int(
                            (part['return_step'].eq(0) & part['observed_steps'].eq(step - 1)).sum())
                        or entry['status'] != ('ok' if supported else 'insufficient_sample')):
                    raise ValueError(f'{fold}/{role}: horizon count differs')
                close(entry['observed_survival'], observed_survival if n_risk else None, 'observed survival')
                close(entry['observed_survival_ci_95'],
                      np.quantile(boot_survival, [0.025, 0.975]) if supported else None, 'survival CI')
                for name in ('baseline', 'candidate'):
                    values = part[f'{name}_survival_{step}']
                    grouped = part.groupby('game_id')[f'{name}_survival_{step}'].sum().reindex(ids, fill_value=0)
                    prediction = float(values.mean())
                    cell = entry[name]
                    close(cell['analytic_survival'], prediction, 'analytic mean')
                    close(cell['simulated_survival'], float(part[f'{name}_sim_survival_{step}'].mean()),
                          'simulated mean')
                    if supported:
                        if (start_draws == 0).any():
                            raise ValueError(f'{fold}/{role}: supported anchor bootstrap is empty')
                        samples = weights @ grouped.to_numpy(dtype=float) / start_draws
                        ci = np.quantile(samples, [0.025, 0.975])
                        diff_ci = np.quantile(samples - boot_survival, [0.025, 0.975])
                    else:
                        ci = diff_ci = None
                    close(cell['survival_ci_95'], ci, 'analytic mean CI')
                    close(cell['minus_observed'], prediction - observed_survival if n_risk else None,
                          'analytic minus observed')
                    close(cell['minus_observed_ci_95'], diff_ci, 'analytic minus observed CI')
                checked_horizons += 1
    if checked_anchors != report['anchors'] or checked_anchors != len(saved):
        raise ValueError('total audited spell anchors differ')
    return {
        'experiment': 'a1_s07_recorded_spell_independent_accounting',
        'anchors': checked_anchors, 'predicted_survival_values': checked_predictions,
        'role_horizons': checked_horizons, 'bootstrap_replicates': BOOTSTRAPS,
        'limitations': 'Reconciles recorded-listing trajectories and frozen earlier-fold probabilities; '
                       'right-censoring can be informative, and historical status reports are not established.',
        'input_sha256': {str(path.relative_to(ROOT)): sha256_file(path)
                         for path in (Path(__file__), REPORT, ROWS, SEQUENCES, MANIFEST)},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f'refusing to overwrite {args.output}')
    result = audit()
    write_json(args.output, result, pretty=True)
    print(json.dumps({key: value for key, value in result.items() if key != 'input_sha256'}, indent=2))


if __name__ == '__main__':
    main()
