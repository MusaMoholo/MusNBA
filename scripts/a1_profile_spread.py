#!/usr/bin/env python3
"""Compare fixed-panel pregame shooter/defender profile spread with held-out shot rates."""
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
from scripts import a1_signal, nodes  # noqa: E402
from scripts.evaluate import EXPERIMENTS  # noqa: E402

SPLIT = '2026-03-01'
SHOOTER_ZONES = ('rim', 'paint', 'mid', 'corner3', 'above3')
DEFENDER_ZONES = ('rim', 'paint', 'mid', 'three')
PREGAME = DERIVED / 'variants' / 'matchup' / 'features' / 'pregame.parquet'
SEGMENTS = DERIVED / 'history' / '2026' / 'segments.parquet'


def reliability(values: pd.Series) -> np.ndarray:
    return np.select([values.isna(), values < 250, values <= 750], ['unknown', '<250', '250–750'], default='>750')


def panel_shots(ids: list[str], extra_columns: tuple[str, ...] = ()) -> pd.DataFrame:
    columns = ['game_id', 'date_et', 'game_ok', 'offense', 'defense', 'end_type', 'heave', 'zone', 'made', 'actor',
               *[f'{side}_{i}' for side in ('off', 'def') for i in range(1, 6)], *extra_columns]
    shots = pd.read_parquet(SEGMENTS, columns=list(dict.fromkeys(columns)), filters=[('game_id', 'in', ids)])
    shots = shots[shots['game_ok'] & shots['offense'].astype(str).isin(nodes.NBA_TEAM_IDS) &
                  shots['defense'].astype(str).isin(nodes.NBA_TEAM_IDS) & (shots['end_type'] == 'shot') &
                  ~shots['heave'].fillna(False) & shots['zone'].isin(SHOOTER_ZONES)].reset_index(drop=True)
    if set(shots['game_id']) != set(ids) or not shots['made'].isin([0, 1]).all():
        raise ValueError('shot rows do not cover the fixed games or contain unknown shot outcomes')
    return shots


def profile_exposures(shots: pd.DataFrame, pre: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    if pre.duplicated(['game_id', 'player']).any():
        raise ValueError('pregame profiles have duplicate game/player keys')
    columns = ['game_id', 'player', 'team', 'usage', 'shots_eff', 'd_segs_eff',
               *[f'fg_{z}' for z in SHOOTER_ZONES], *[f'd_fg_{z}' for z in DEFENDER_ZONES]]
    pre = pre[columns]
    source = shots.reset_index(drop=True).copy()
    source['shot_id'] = np.arange(len(source))
    shooter = source[['game_id', 'date_et', 'zone', 'made', 'actor', 'offense']].rename(columns={'actor': 'player'})
    shooter = shooter.merge(pre, on=['game_id', 'player'], how='left', validate='many_to_one')
    shooter['profile'] = np.select([shooter['zone'] == z for z in SHOOTER_ZONES],
                                   [shooter[f'fg_{z}'] for z in SHOOTER_ZONES], default=np.nan)
    shooter['effective'] = shooter['shots_eff']
    shooter['team_valid'] = shooter['team'].notna() & shooter['team'].eq(shooter['offense'])

    defcols = [f'def_{i}' for i in range(1, 6)]
    lineups = source[defcols]
    valid = lineups.notna().all(axis=1) & lineups.nunique(axis=1).eq(5)
    defender = source.loc[valid, ['shot_id', 'game_id', 'date_et', 'zone', 'made', 'defense', *defcols]]
    defender = defender.melt(id_vars=['shot_id', 'game_id', 'date_et', 'zone', 'made', 'defense'],
                             value_vars=defcols, value_name='player').drop(columns='variable')
    defender = defender.merge(pre, on=['game_id', 'player'], how='left', validate='many_to_one')
    defender['zone'] = defender['zone'].replace({'corner3': 'three', 'above3': 'three'})
    defender['profile'] = np.select([defender['zone'] == z for z in DEFENDER_ZONES],
                                    [defender[f'd_fg_{z}'] for z in DEFENDER_ZONES], default=np.nan)
    defender['effective'] = defender['d_segs_eff']
    defender['team_valid'] = defender['team'].notna() & defender['team'].eq(defender['defense'])

    offense = source[[f'off_{i}' for i in range(1, 6)]]
    coverage = {
        'shots': len(source), 'shooter_missing_or_wrong_team': int((~shooter['team_valid']).sum()),
        'actor_not_in_recorded_offensive_five': int((~offense.eq(source['actor'], axis=0).any(axis=1)).sum()),
        'invalid_defensive_lineups': int((~valid).sum()), 'defender_exposures_before_profile_join': len(defender),
        'defender_missing_or_wrong_team': int((~defender['team_valid']).sum()),
        'shooter_profile_missing': int(shooter['profile'].isna().sum()),
        'defender_profile_missing': int(defender['profile'].isna().sum()),
    }
    return shooter, defender, coverage


def exposure_summary(rows: pd.DataFrame, zones: tuple[str, ...]) -> dict:
    rows = rows[rows['team_valid']].copy()
    rows['reliability'] = reliability(rows['effective'])
    result = {}
    for zone in zones:
        result[zone] = {}
        for label in ('all', '<250', '250–750', '>750', 'unknown'):
            subset = rows[rows['zone'] == zone]
            if label != 'all':
                subset = subset[subset['reliability'] == label]
            valid = subset[subset['profile'].notna() & subset['made'].notna()]
            result[zone][label] = {
                'exposures': len(subset), 'profiled_exposures': len(valid),
                'games': subset['game_id'].nunique(), 'players': subset['player'].nunique(),
                'player_games': len(subset[['game_id', 'player']].drop_duplicates()),
                'profile_mean': float(valid['profile'].mean()) if len(valid) else None,
                'profile_sd': float(valid['profile'].std(ddof=0)) if len(valid) else None,
                'observed_make_rate': float(valid['made'].mean()) if len(valid) else None,
            }
    return result


def cross_half_spread(rows: pd.DataFrame, zones: tuple[str, ...]) -> dict:
    data = rows[rows['team_valid'] & rows['profile'].notna() & rows['made'].notna()].copy()
    data['half'] = np.where(data['date_et'] < SPLIT, 'early', 'late')
    grouped = data.groupby(['zone', 'player', 'half'], as_index=False).agg(
        n=('made', 'size'), made=('made', 'sum'), profile_sum=('profile', 'sum'), games=('game_id', 'nunique'))
    early = grouped[grouped['half'] == 'early'].drop(columns='half')
    late = grouped[grouped['half'] == 'late'].drop(columns='half')
    paired = early.merge(late, on=['zone', 'player'], suffixes=('_early', '_late'), validate='one_to_one')
    paired = paired[(paired['n_early'] >= 15) & (paired['n_late'] >= 15) &
                    (paired['games_early'] >= 3) & (paired['games_late'] >= 3)]
    result = {}
    for zone in zones:
        g = paired[paired['zone'] == zone]
        if len(g) < 2:
            result[zone] = {'players': len(g), 'status': 'insufficient'}
            continue
        weight = np.minimum(g['n_early'].to_numpy(dtype=float), g['n_late'].to_numpy(dtype=float))
        first = (g['made_early'] / g['n_early']).to_numpy(dtype=float)
        second = (g['made_late'] / g['n_late']).to_numpy(dtype=float)
        profile = ((g['profile_sum_early'] + g['profile_sum_late']) / (g['n_early'] + g['n_late'])).to_numpy(dtype=float)
        center = lambda a: a - np.average(a, weights=weight)
        result[zone] = {
            'players': len(g), 'early_exposures': int(g['n_early'].sum()), 'late_exposures': int(g['n_late'].sum()),
            'minimum_half_opportunities_weight': int(weight.sum()),
            'profile_variance': float(np.average(center(profile) ** 2, weights=weight)),
            'observed_cross_half_covariance': float(np.average(center(first) * center(second), weights=weight)),
            'early_rate': float(np.average(first, weights=weight)), 'late_rate': float(np.average(second, weights=weight)),
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=EXPERIMENTS / '20261122_a1_s03_profile_spread.json')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f'refusing to overwrite {args.output}')
    manifest = json.loads(a1_signal.MANIFEST.read_text())
    ids = [g['game_id'] for g in manifest['control']['games']]
    control = a1_signal.fixed_games(pd.read_parquet(DERIVED / 'experiments' / f'{a1_signal.CONTROL}.parquet'), manifest)
    shots = panel_shots(ids)
    if control['date_et'].lt(SPLIT).sum() != 112:
        raise ValueError('fixed temporal split differs from its preregistered population')
    pre = pd.read_parquet(PREGAME)
    shooter, defender, coverage = profile_exposures(shots, pre)
    paths = [a1_signal.MANIFEST, SEGMENTS, PREGAME, Path(__file__)]
    write_json(args.output, {
        'experiment': 'a1_s03_player_profile_spread',
        'method': {'games': len(ids), 'split': SPLIT, 'early_games': 112, 'late_games': 88,
                   'profile_unit': 'shot exposure; five on-court defender exposures per valid shot',
                   'cross_half_cohort': 'at least 15 opportunities and 3 games in each half',
                   'cross_half_weight': 'minimum number of opportunities between halves',
                   'limitations': 'descriptive retrospective rates; on-court defenders share outcomes and are not '
                                  'isolated on-ball assignments; selection and opponent effects remain'},
        'coverage': coverage,
        'shooters': {'by_zone_and_exposure': exposure_summary(shooter, SHOOTER_ZONES),
                     'cross_half': cross_half_spread(shooter, SHOOTER_ZONES)},
        'defenders': {'by_zone_and_exposure': exposure_summary(defender, DEFENDER_ZONES),
                      'cross_half': cross_half_spread(defender, DEFENDER_ZONES)},
        'sha256': {str(p.resolve().relative_to(ROOT)): sha256_file(p) for p in paths},
    }, pretty=True)
    print(f"{coverage['shots']} shots; {coverage['invalid_defensive_lineups']} invalid defensive lineups; "
          f"{coverage['actor_not_in_recorded_offensive_five']} actors outside the offensive five")
    print(f'saved {args.output}')


if __name__ == '__main__':
    main()
