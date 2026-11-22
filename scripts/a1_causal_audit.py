#!/usr/bin/env python3
"""Independently account for the isolated historical first-season-causal feature build.

  .venv/bin/python -m scripts.a1_causal_audit --output analysis/experiments/new-causal-audit.json
"""
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

BASE = DERIVED / 'features'
CANDIDATE = DERIVED / 'variants' / 'a1_causal_base_20261122_v2' / 'features'
TEST_FROM = '2026-07-01'


def compare(candidate: pd.DataFrame, baseline: pd.DataFrame, keys: list[str], columns: list[str]) -> dict:
    if candidate.duplicated(keys).any() or baseline.duplicated(keys).any():
        raise ValueError(f'duplicate feature key {keys}')
    combined = candidate[keys + ['season', 'date_et'] + columns].merge(
        baseline[keys + ['date_et'] + columns], on=keys, suffixes=('_candidate', '_baseline'),
        how='left', validate='one_to_one', indicator=True)
    if combined['_merge'].ne('both').any() or combined['date_et_candidate'].ne(combined['date_et_baseline']).any():
        raise ValueError('candidate feature rows do not match dated baseline identities')
    first = combined['season'].min()
    result = {}
    for column in columns:
        a = combined[f'{column}_candidate'].to_numpy(float)
        b = combined[f'{column}_baseline'].to_numpy(float)
        same = np.isclose(a, b, rtol=1e-6, atol=1e-7, equal_nan=True)
        result[column] = {'first_season_different': int((~same & combined['season'].eq(first).to_numpy()).sum()),
                          'later_seasons_different': int((~same & combined['season'].gt(first).to_numpy()).sum())}
    return {'matched_rows': len(combined), 'first_season': int(first),
            'first_season_rows': int(combined['season'].eq(first).sum()),
            'later_season_rows': int(combined['season'].gt(first).sum()), 'columns': result}


def audit() -> dict:
    report = json.loads((CANDIDATE / 'features_report.json').read_text())
    if not report.get('causal_first_priors') or not report.get('history_only'):
        raise ValueError('feature report does not describe the required isolated historical build')
    for path, digest in report['input_sha256'].items():
        if sha256_file(Path(path)) != digest:
            raise ValueError(f'causal feature input changed: {path}')
    players = pd.read_parquet(CANDIDATE / 'pregame.parquet')
    teams = pd.read_parquet(CANDIDATE / 'team_pregame.parquet')
    if players['date_et'].max() >= TEST_FROM or teams['date_et'].max() >= TEST_FROM:
        raise ValueError('protected final-test season present in historical candidate')
    if players['game_id'].nunique() != report['team_games'] // 2 or len(players) != report['player_games']:
        raise ValueError('feature report player/game totals do not reconcile')
    if not teams.groupby('game_id').size().eq(2).all() or teams['game_id'].nunique() != players['game_id'].nunique():
        raise ValueError('candidate team/player game coverage does not reconcile')
    old_players, old_teams = pd.read_parquet(BASE / 'pregame.parquet'), pd.read_parquet(BASE / 'team_pregame.parquet')
    player_cols = [c for c in report['feature_columns'] if c in old_players and pd.api.types.is_numeric_dtype(players[c])]
    team_cols = [c for c in report['team_columns'] if c in old_teams and pd.api.types.is_numeric_dtype(teams[c])]
    player_comp = compare(players, old_players, ['game_id', 'player'], player_cols)
    team_comp = compare(teams, old_teams, ['game_id', 'team'], team_cols)
    earliest = players['date_et'].min()
    paths = [CANDIDATE / name for name in ('pregame.parquet', 'latest.parquet', 'team_pregame.parquet',
                                            'team_latest.parquet', 'features_report.json')]
    return {'experiment': 'a1_causal_base_accounting', 'population': 'four retained historical seasons, no final-test dates',
            'date_min': earliest, 'date_max': players['date_et'].max(), 'player_games': len(players),
            'games': int(players['game_id'].nunique()), 'team_games': len(teams),
            'first_date_player_rows': int(players['date_et'].eq(earliest).sum()),
            'first_date_usage_known': int(players.loc[players['date_et'].eq(earliest), 'usage'].notna().sum()),
            'players_vs_retained': player_comp, 'teams_vs_retained': team_comp,
            'scope': report['causal_scope'], 'input_sha256': report['input_sha256'],
            'output_sha256': {str(p.relative_to(ROOT)): sha256_file(p) for p in paths},
            'baseline_sha256': {str(p.relative_to(ROOT)): sha256_file(p)
                                for p in (BASE / 'pregame.parquet', BASE / 'team_pregame.parquet')}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output', type=Path, required=True, help='new report path; existing reports are never overwritten')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f'refusing to overwrite {args.output}')
    report = audit()
    write_json(args.output, report, pretty=True)
    print(f"saved {args.output}: {report['player_games']} player-games, {report['games']} games")


if __name__ == '__main__':
    main()
