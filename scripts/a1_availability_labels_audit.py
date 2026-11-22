#!/usr/bin/env python3
"""Reconcile development-only prior-box membership and retrospective absence labels."""
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
from scripts.evaluate import EXPERIMENTS, FOLDS  # noqa: E402

CONTROL = '20261122T022323Z_a1_s01_control'
MEMBERSHIP = DERIVED / 'experiments/20261122_a1_prior_box_membership_nba_only.parquet'
POPULATION = DERIVED / 'experiments/20261122_a1_s05_minutes_population.parquet'
BOX = ROOT / 'data/raw/hoopr/player_box_2026.parquet'
POPULATION_REPORT = EXPERIMENTS / '20261122_a1_s05_minutes_population.json'


def reason_category(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        return 'missing_reason'
    reason = value.strip().upper()
    if 'COACH' in reason:
        return 'coach'
    if reason == 'REST':
        return 'rest'
    if 'INJURY' in reason and 'ILLNESS' in reason:
        return 'injury_or_illness'
    if 'INJURY' in reason:
        return 'explicit_injury'
    if 'ILLNESS' in reason:
        return 'illness'
    return 'other_recorded_reason'


def latest_membership(history: pd.DataFrame, day: str) -> pd.DataFrame:
    prior = history.loc[history['day'] < day, ['day', 'player', 'team']].drop_duplicates()
    latest = prior.groupby('player')['day'].transform('max')
    last = prior.loc[prior['day'].eq(latest)]
    unambiguous = last.groupby('player')['team'].transform('nunique').eq(1)
    return last.loc[unambiguous].drop_duplicates('player').rename(columns={'day': 'prior_day'})


def build() -> dict:
    prior_report = json.loads(POPULATION_REPORT.read_text())
    for path, digest in prior_report['input_sha256'].items():
        if sha256_file(ROOT / path) != digest:
            raise ValueError(f'previous development-population fingerprint differs: {path}')
    games_path = DERIVED / 'experiments' / f'{CONTROL}.parquet'
    oracle_path = DERIVED / 'experiments' / f'{CONTROL}_players.parquet'
    games = pd.read_parquet(games_path, columns=['game_id', 'date_et', 'home', 'away'])
    _, first, last = FOLDS['F4']
    if (games['game_id'].duplicated().any() or games.empty
            or not games['date_et'].between(first, last).all()):
        raise ValueError('fixed development games are missing, duplicated or outside F4')
    membership, population = pd.read_parquet(MEMBERSHIP), pd.read_parquet(POPULATION)
    keys = ['game_id', 'team', 'player']
    if membership.duplicated(keys).any() or population.duplicated(keys).any():
        raise ValueError('development membership has duplicate game/team/player keys')
    if not membership['prior_day'].lt(membership['date_et']).all():
        raise ValueError('membership includes a same-day or future source')
    for col in ('prior_team_date', 'prior_appearance_date'):
        values = pd.to_datetime(population[col], errors='raise')
        origin = pd.to_datetime(population['date_et'], errors='raise')
        if (values.notna() & values.ge(origin)).any():
            raise ValueError(f'{col} is not strictly before its origin')

    raw = pd.read_parquet(BOX, columns=['game_id', 'game_date', 'athlete_id', 'team_id', 'season_type',
                                        'did_not_play', 'minutes', 'reason'])
    raw = raw.loc[raw['season_type'].eq(2)].dropna(
        subset=['game_id', 'game_date', 'athlete_id', 'team_id']).copy()
    for source, target in (('game_id', 'game_id'), ('athlete_id', 'player'), ('team_id', 'team')):
        raw[target] = raw[source].astype('int64').astype(str)
    raw['day'] = pd.to_datetime(raw['game_date'], errors='raise').dt.strftime('%Y-%m-%d')
    teams_path = DERIVED / 'teams.json'
    teams = set(json.loads(teams_path.read_text()))
    if len(teams) != 30:
        raise ValueError('canonical NBA team universe is incomplete')
    raw = raw.loc[raw['team'].isin(teams)].copy()
    if raw.duplicated(['game_id', 'player']).any():
        raise ValueError('raw development boxes contain duplicate game/player keys')
    expected = []
    for day, date_games in games.groupby('date_et', sort=True):
        members = latest_membership(raw, str(day))
        for game in date_games.itertuples(index=False):
            for team in (game.home, game.away):
                group = members.loc[members['team'].eq(team)].copy()
                expected.append(group.assign(game_id=game.game_id, date_et=day))
    expected_rows = pd.concat(expected, ignore_index=True)
    comparison = membership.merge(expected_rows, on=keys, how='outer', suffixes=('_saved', '_check'),
                                  indicator=True, validate='one_to_one')
    if (comparison['_merge'].ne('both').any()
            or comparison['prior_day_saved'].ne(comparison['prior_day_check']).any()
            or comparison['date_et_saved'].ne(comparison['date_et_check']).any()):
        raise ValueError('saved prior-box memberships differ from independent reconstruction')
    pop_keys = membership[keys].merge(population[keys], on=keys, how='outer', indicator=True, validate='one_to_one')
    if pop_keys['_merge'].ne('both').any():
        raise ValueError('population and prior-box membership keys differ')

    selected = raw.loc[raw['game_id'].isin(games['game_id'])].copy()
    dnp = selected['did_not_play'].astype('boolean')
    mins = pd.to_numeric(selected['minutes'], errors='raise')
    if mins.lt(0).any() or (dnp.eq(True).fillna(False) & mins.gt(0)).any():
        raise ValueError('development box has contradictory DNP/minutes labels')
    selected['check_played'] = np.select(
        [dnp.eq(True).fillna(False).to_numpy(dtype=bool),
         (dnp.eq(False).fillna(False) & mins.gt(0)).to_numpy(dtype=bool)],
        [0.0, 1.0], default=np.nan)
    joined = membership.merge(selected[keys + ['check_played', 'reason']], on=keys, how='left',
                              indicator=True, validate='one_to_one')
    if not joined['listed_in_box'].eq(joined['_merge'].eq('both')).all():
        raise ValueError('saved box-listing coverage differs from the raw boxes')
    same = joined['played'].eq(joined['check_played']) | (joined['played'].isna() & joined['check_played'].isna())
    if not same.all():
        raise ValueError('saved play/DNP labels differ from the raw boxes')
    labels = joined.loc[joined['check_played'].eq(0), 'reason'].map(reason_category)
    label_counts = {str(k): int(v) for k, v in labels.value_counts().items()}
    if sum(label_counts.values()) != int(joined['played'].eq(0).sum()):
        raise ValueError('DNP reason categories do not partition known DNPs')
    population_labels = population[keys + ['dnp_coach']].merge(joined[keys + ['check_played', 'reason']], on=keys,
                                                               validate='one_to_one')
    coach = population_labels['check_played'].eq(0) & population_labels['reason'].map(reason_category).eq('coach')
    if not population_labels['dnp_coach'].eq(coach).all():
        raise ValueError('saved coach-DNP labels differ from independent reason classification')

    oracle = pd.read_parquet(oracle_path, columns=['game_id', 'player'])
    if oracle.duplicated(['game_id', 'player']).any():
        raise ValueError('actual-participant oracle contains duplicate player-games')
    oracle_keys = set(map(tuple, oracle[['game_id', 'player']].to_numpy()))
    played_keys = set(map(tuple, joined.loc[joined['played'].eq(1), ['game_id', 'player']].to_numpy()))
    return {
        'experiment': 'a1_s07_development_membership_and_labels_independent_audit',
        'fold': 'F4', 'games': len(games), 'candidates': len(joined),
        'membership_date_violations': 0, 'independently_reconstructed_memberships': len(comparison),
        'played': int(joined['played'].eq(1).sum()), 'dnp': int(joined['played'].eq(0).sum()),
        'unlisted_unknown': int((~joined['listed_in_box']).sum()),
        'listed_unknown': int((joined['listed_in_box'] & joined['played'].isna()).sum()),
        'dnp_reason_categories': label_counts,
        'oracle_player_games': len(oracle_keys),
        'oracle_and_prior_box_played': len(oracle_keys & played_keys),
        'oracle_outside_prior_box_played': len(oracle_keys - played_keys),
        'prior_box_played_outside_oracle': len(played_keys - oracle_keys),
        'limitations': 'Membership is inferred from strictly earlier same-season NBA boxes, not an official roster '
                       'or proof of physical eligibility. DNP reasons are retrospective outcome labels, not '
                       'pre-tip injury reports; only explicit text is classified and all other reasons remain '
                       'separate. Unlisted and ambiguous players are unknown; prior boxes lack publication times.',
        'input_sha256': {str(p.relative_to(ROOT)): sha256_file(p)
                         for p in (Path(__file__), games_path, oracle_path, MEMBERSHIP, POPULATION,
                                   BOX, teams_path, POPULATION_REPORT)},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f'refusing to overwrite {args.output}')
    result = build()
    write_json(args.output, result, pretty=True)
    print(f"{result['games']} development games and {result['candidates']} inferred memberships independently checked")


if __name__ == '__main__':
    main()
