#!/usr/bin/env python3
"""Screen conditional regulation-minute target distributions on A1's fixed development folds."""
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
from scripts import a1_compare, a1_flow_compare, a1_minutes_candidate, aggregate, minutes, projection  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS  # noqa: E402

PREREG = EXPERIMENTS / '20261122_a1_pre_candidate_manifest.json'
CAUSAL_PROFILES = DERIVED / 'variants/a1_causal_base_20261122_v2/features/pregame.parquet'
VARIANTS = ('control', 'nba_only', 'strict', 'combined')


def fold_games(manifest: dict, fold: str) -> pd.DataFrame:
    source = manifest['control']['games'] if fold == 'F4' else manifest['confirmation'][fold]['games']
    games = pd.DataFrame(source)[['game_id', 'date_et']]
    a1_compare._unique(games, ['game_id'], f'{fold} fixed games')
    if len(games) != 200 or not games['date_et'].between(FOLDS[fold][1], FOLDS[fold][2]).all():
        raise ValueError(f'{fold} fixed games do not match the preregistered 200-game dates')
    return games


def state_dicts(part: pd.DataFrame, suffix: str) -> list[dict]:
    fields = ['healthy', 'cap', 'ramp', 'priority']
    values = part[[f'{c}_{suffix}' for c in fields]].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError(f'{suffix} minute states contain missing or non-finite values')
    return [dict(zip(fields, row), rotation=1.0) for row in values]


def distribution(states: list[dict], sd_table: dict, actual: np.ndarray, seed: int,
                 strict: bool, worlds: int) -> dict[str, np.ndarray]:
    solver = a1_minutes_candidate if strict else minutes
    target = solver.game_targets(states)
    cap = np.asarray([s['cap'] for s in states], dtype=float)
    spread = minutes.sd_for(sd_table, target)
    if not np.isfinite(spread).all():
        raise ValueError('minute residual spread is not finite')
    draws = solver.redraw(target, cap, spread, worlds, np.random.default_rng(seed))
    if not np.isfinite(draws).all() or not np.isfinite(actual).all():
        raise ValueError('minute target draws or actuals are not finite')
    lo, hi = np.quantile(draws, (0.1, 0.9), axis=0)
    return {'mean': draws.mean(axis=0), 'crps': aggregate.crps_samples(draws, actual),
            'covered': ((actual >= lo) & (actual <= hi)).astype(float)}


def score_fold(fold: str, games: pd.DataFrame, pre: pd.DataFrame, worlds: int) -> pd.DataFrame:
    print(f'{fold}: building cutoff-specific original D29 states', flush=True)
    original = minutes.build(FOLDS[fold][1], include_current=False)
    print(f'{fold}: building cutoff-specific NBA-only states', flush=True)
    clean = a1_minutes_candidate.build(FOLDS[fold][1], include_current=False)
    ids = set(games['game_id'])
    cols = ['game_id', 'player', 'team', 'date_et', 'healthy', 'cap', 'ramp', 'priority']
    a = original['rows'].loc[original['rows']['game_id'].isin(ids), cols]
    b = clean['rows'].loc[clean['rows']['game_id'].isin(ids), cols]
    a1_compare._same_keys(a, b, ['game_id', 'player'], f'{fold} minute variants')
    rows = a.merge(b, on=['game_id', 'player'], suffixes=('_control', '_nba'), validate='one_to_one')
    for col in ('team', 'date_et'):
        if not rows[f'{col}_control'].equals(rows[f'{col}_nba']):
            raise ValueError(f'{fold} candidate changes {col}')
    rows = rows.rename(columns={'team_control': 'team', 'date_et_control': 'date_et'}).drop(
        columns=['team_nba', 'date_et_nba'])
    pg = original['pg'][['game_id', 'player', 'reg']]
    a1_compare._unique(pg, ['game_id', 'player'], f'{fold} regulation actuals')
    rows = rows.merge(pg, on=['game_id', 'player'], validate='one_to_one')
    if set(rows['game_id']) != ids:
        raise ValueError(f'{fold} minute histories do not cover the fixed games')
    games_by_id = games.set_index('game_id')
    if rows['date_et'].ne(rows['game_id'].map(games_by_id['date_et'])).any():
        raise ValueError(f'{fold} minute and manifest game dates differ')
    roles = a1_compare.roles(rows[['game_id', 'player']], pre, games)
    rows = rows.merge(roles, on=['game_id', 'player'], validate='one_to_one')
    results = []
    start = time.monotonic()
    grouped = list(rows.groupby(['game_id', 'team'], sort=True))
    for index, ((game_id, team), part) in enumerate(grouped, 1):
        state_control, state_nba = state_dicts(part, 'control'), state_dicts(part, 'nba')
        actual = part['reg'].to_numpy(dtype=float)
        if len(part) < 5 or (actual < 0).any() or (actual > 48).any():
            raise ValueError(f'{fold} {game_id} {team}: invalid regulation-minute population')
        seed = projection.seed_for('a1_s05_minutes', fold, str(game_id), str(team))
        outputs = {
            'control': distribution(state_control, original['sd'], actual, seed, False, worlds),
            'nba_only': distribution(state_nba, clean['sd'], actual, seed, False, worlds),
            'strict': distribution(state_control, original['sd'], actual, seed, True, worlds),
            'combined': distribution(state_nba, clean['sd'], actual, seed, True, worlds),
        }
        out = part[['game_id', 'team', 'player', 'date_et', 'reg', 'tier']].copy()
        out['fold'] = fold
        for variant, values in outputs.items():
            for name, value in values.items():
                out[f'{variant}_{name}'] = value
        results.append(out)
        if index % 40 == 0 or index == len(grouped):
            print(f'{fold}: {index}/{len(grouped)} team-games in {time.monotonic() - start:.1f}s', flush=True)
    if len(grouped) != 400:
        raise ValueError(f'{fold} does not have exactly two observed team sets per game')
    return pd.concat(results, ignore_index=True)


def summaries(rows: pd.DataFrame, ids: list[str]) -> dict:
    draws = np.random.default_rng(a1_compare.BOOTSTRAP_SEED).integers(
        0, len(ids), (a1_compare.BOOTSTRAP_REPLICATES, len(ids)))
    weights = np.zeros(draws.shape, dtype=np.int16)
    np.add.at(weights, (np.arange(len(draws))[:, None], draws), 1)
    for variant in VARIANTS:
        rows[f'{variant}_bias'] = rows[f'{variant}_mean'] - rows['reg']
        if variant != 'control':
            for metric in ('crps', 'bias', 'covered'):
                rows[f'{variant}_minus_control_{metric}'] = rows[f'{variant}_{metric}'] - rows[f'control_{metric}']
    names = [f'{variant}_{metric}' for variant in VARIANTS for metric in ('crps', 'bias', 'covered')]
    names += [f'{variant}_minus_control_{metric}' for variant in VARIANTS if variant != 'control'
              for metric in ('crps', 'bias', 'covered')]
    return {tier: a1_flow_compare.mean_report(rows if tier == 'all' else rows.loc[rows['tier'].eq(tier)],
                                               names, ids, weights, player=True)
            for tier in ('all', *a1_compare.ROLE_TIERS)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worlds', type=int, default=1000)
    parser.add_argument('--output', type=Path, default=EXPERIMENTS / '20261122_a1_s05_minutes_fold_screen.json')
    parser.add_argument('--rows-output', type=Path, default=DERIVED / 'experiments' / '20261122_a1_s05_minutes_fold_screen.parquet')
    args = parser.parse_args()
    if args.worlds != 1000:
        raise ValueError('the preregistered conditional screen requires 1,000 worlds')
    if args.output.exists() or args.rows_output.exists():
        raise FileExistsError('refusing to overwrite an existing fold screen')
    manifest = json.loads(PREREG.read_text())
    pre = pd.read_parquet(CAUSAL_PROFILES)
    frames, reports, integrity = [], {}, {}
    for fold in FOLDS:
        start = time.monotonic()
        games = fold_games(manifest, fold)
        rows = score_fold(fold, games, pre, args.worlds)
        reports[fold] = summaries(rows, sorted(games['game_id'].tolist()))
        real_team_minutes = rows.groupby(['game_id', 'team'])['reg'].sum()
        integrity[fold] = {'team_games': len(real_team_minutes),
                           'team_games_not_exactly_240_at_1e_6': int((real_team_minutes.sub(240).abs() > 1e-6).sum()),
                           'max_absolute_team_minutes_error': float(real_team_minutes.sub(240).abs().max())}
        frames.append(rows)
        print(f'{fold}: {len(games)}/200 games, {len(rows)} player-games, {time.monotonic() - start:.1f}s', flush=True)
    all_rows = pd.concat(frames, ignore_index=True)
    paths = [PREREG, CAUSAL_PROFILES, ROOT / 'scripts/minutes.py', Path(a1_minutes_candidate.__file__), Path(__file__)]
    paths += sorted((DERIVED / 'history').glob('*/on_court.parquet'))
    paths += sorted((ROOT / 'data/raw/hoopr').glob('player_box_*.parquet'))
    report = {
        'experiment': 'a1_s05_conditional_minutes_fold_screen',
        'method': 'On each fixed historical fold, compare 1,000-world regulation-minute targets conditional on '
                  'the actual participant sets. The four variants use matching per-game/team normal draws and each '
                  'fold’s own pre-validation ramp/spread fit; tiers come from the causal-base pregame profiles.',
        'limitations': 'Target distributions are not the complete possession-engine output. Actual participants '
                       'are supplied after the game, so these results do not score pre-game availability or '
                       'unconditional minutes; all candidate differences remain exploratory.',
        'folds': reports, 'real_regulation_minute_integrity': integrity,
        'input_sha256': {str(p.relative_to(ROOT)): sha256_file(p) for p in paths},
    }
    atomic_bytes(args.rows_output, all_rows.to_parquet(index=False))
    write_json(args.output, report, pretty=True)
    print(f'saved {len(all_rows)} conditional player-game distributions and {args.output}', flush=True)


if __name__ == '__main__':
    main()
