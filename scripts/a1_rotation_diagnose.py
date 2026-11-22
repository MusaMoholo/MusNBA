#!/usr/bin/env python3
"""Trace D29's rotation-weighted target and overlapping recent-nonappearance fallback."""
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
from scripts import a1_availability_cohort, a1_compare, a1_flow_compare, a1_minutes_audit, a1_minutes_diagnose, a1_signal, minutes  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS  # noqa: E402

CONTROL = a1_minutes_audit.CONTROL
POPULATION = DERIVED / 'experiments' / '20261122_a1_s05_minutes_population.parquet'
RAW_BOX = a1_minutes_audit.BOX


def recent_flags(population: pd.DataFrame, raw: pd.DataFrame) -> pd.DataFrame:
    """Recreate the last-five team-game window using only earlier retained NBA boxes."""
    team_games = (raw[['day', 'game_id', 'team']].drop_duplicates()
                  .sort_values(['team', 'day', 'game_id'], kind='stable'))
    schedule = {team: list(zip(group['day'], group['game_id'])) for team, group in team_games.groupby('team')}
    lookup = {(row.game_id, row.player): (row.did_not_play, row.reason) for row in raw.itertuples(index=False)}
    records = []
    for row in population.itertuples(index=False):
        prior = [(day, gid) for day, gid in schedule[row.team] if day < row.date_et][-5:]
        played = 0
        coach = 0
        unknown = 0
        for _, gid in prior:
            found = lookup.get((gid, row.player))
            if found is None or pd.isna(found[0]):
                unknown += 1
            elif bool(found[0]):
                reason = '' if pd.isna(found[1]) else str(found[1])
                coach += int('COACH' in reason.upper())
            else:
                played += 1
        records.append((len(prior), played, coach, unknown))
    out = population.copy()
    out[['recent_window', 'recent_played', 'recent_coach_dnps', 'recent_unknown']] = pd.DataFrame(
        records, index=out.index)
    if (out['recent_window'] < out['recent_played'] + out['recent_coach_dnps'] + out['recent_unknown']).any():
        raise ValueError('recent status counts exceed the available team-game window')
    return out


def weighted_targets(rows: pd.DataFrame) -> pd.DataFrame:
    """Apply rotation weights to the known-participant roster as a labelled counterfactual."""
    frames = []
    for _, part in rows.groupby(['game_id', 'team'], sort=False):
        if len(part) < 5:
            raise ValueError('fixed simulated team has fewer than five players')
        states = []
        values = part[['healthy', 'cap', 'start_share', 'ramp', 'rotation_share']].to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise ValueError('rotation target states contain missing or non-finite values')
        for h, cap, start, ramp, rot in values:
            states.append({'healthy': h, 'cap': cap, 'start_share': start, 'ramp': ramp, 'rotation': rot,
                           'priority': h * rot + minutes.MINUTES['start_bonus'] * start})
        weighted = minutes.game_targets(states)
        unweighted = minutes.game_targets([{**s, 'rotation': 1.0,
                                            'priority': s['healthy'] + minutes.MINUTES['start_bonus'] * s['start_share']}
                                           for s in states])
        for target in (weighted, unweighted):
            if not np.isfinite(target).all() or (target < 0).any() or (target > 48).any() or abs(target.sum() - 240) > 1e-5:
                raise ValueError('target allocation violates regulation minutes')
        frame = part.copy()
        frame['target_rotation_weighted'] = weighted
        frame['target_known_play'] = unweighted
        frame['target_change'] = weighted - unweighted
        frame['rotation_weighted_below_5'] = weighted < 5
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def build() -> tuple[dict, pd.DataFrame]:
    manifest = json.loads(a1_signal.MANIFEST.read_text())
    data = DERIVED / 'experiments'
    games_path = data / f'{CONTROL}.parquet'
    players_path = data / f'{CONTROL}_players.parquet'
    games = a1_signal.fixed_games(pd.read_parquet(games_path), manifest)
    ids = sorted(games['game_id'].tolist())
    players = pd.read_parquet(players_path)
    population = pd.read_parquet(POPULATION)
    print('loading pre-origin D29 participation and DNP histories', flush=True)
    pg = minutes.player_games(include_current=False)
    cd = minutes.coach_dnps(include_current=False)
    events = a1_minutes_diagnose.rotation_events(pg, cd)
    pop = a1_minutes_audit.prior_join(population, events, ['rotation_share'])
    pop.loc[pop['rotation_share'].isna(), 'rotation_share'] = 0.5

    raw = pd.read_parquet(RAW_BOX, columns=['game_id', 'game_date', 'team_id', 'athlete_id', 'season_type',
                                           'did_not_play', 'minutes', 'reason'])
    raw = raw.loc[raw['season_type'].eq(2)].dropna(subset=['game_id', 'game_date', 'team_id', 'athlete_id']).copy()
    raw['game_id'] = raw['game_id'].astype('int64').astype(str)
    raw['team'] = raw['team_id'].astype('int64').astype(str)
    raw['player'] = raw['athlete_id'].astype('int64').astype(str)
    raw['day'] = pd.to_datetime(raw['game_date'], errors='raise').dt.normalize()
    teams_path = DERIVED / 'teams.json'
    raw, excluded = a1_availability_cohort.nba_team_records(raw, set(json.loads(teams_path.read_text())))
    a1_compare._unique(raw, ['game_id', 'player'], 'NBA box history')
    pop = recent_flags(pop, raw)
    no_plays = pop['recent_window'].ge(3) & pop['recent_played'].eq(0)
    overlap = no_plays & pop['recent_coach_dnps'].gt(0)

    print('building known-participant D29 target counterfactual', flush=True)
    model = minutes.build(FOLDS['F4'][1], include_current=False)
    history = model['rows'].loc[model['rows']['game_id'].isin(ids)].copy()
    history = history.merge(players[['game_id', 'player']], on=['game_id', 'player'],
                            validate='one_to_one')
    history = history.merge(pg[['game_id', 'player', 'reg']], on=['game_id', 'player'], validate='one_to_one')
    a1_compare._same_keys(players, history, ['game_id', 'player'], 'rotation target participant panel')
    history['date_et'] = pd.to_datetime(history['date_et'], errors='raise')
    history = a1_minutes_audit.prior_join(history, events, ['rotation_share'])
    history.loc[history['rotation_share'].isna(), 'rotation_share'] = 0.5
    targets = weighted_targets(history)
    qualifying = targets['healthy'].ge(15)
    tiny = qualifying & targets['rotation_weighted_below_5']
    already_tiny = tiny & targets['target_known_play'].lt(5)
    caused_tiny = tiny & ~already_tiny
    draws = np.random.default_rng(a1_compare.BOOTSTRAP_SEED).integers(
        0, len(ids), (a1_compare.BOOTSTRAP_REPLICATES, len(ids)))
    weights = np.zeros(draws.shape, dtype=np.int16)
    np.add.at(weights, (np.arange(len(draws))[:, None], draws), 1)
    target_report = {}
    for name, mask in (('all', pd.Series(True, index=targets.index)), ('healthy_15_plus', qualifying),
                       ('healthy_15_plus_weighted_target_below_5', tiny)):
        target_report[name] = a1_flow_compare.mean_report(
            targets.loc[mask], ['healthy', 'reg', 'rotation_share', 'target_known_play',
                                'target_rotation_weighted', 'target_change'], ids, weights, player=True)
    source_paths = [a1_signal.MANIFEST, games_path, players_path, POPULATION, RAW_BOX, teams_path,
                    ROOT / 'scripts/minutes.py', ROOT / 'scripts/projection.py', ROOT / 'scripts/engine.py',
                    ROOT / 'scripts/season_stats.py', Path(__file__)]
    source_paths += sorted((DERIVED / 'history').glob('*/on_court.parquet'))
    report = {
        'experiment': 'a1_s05_rotation_weight_and_fallback_diagnostic',
        'method': 'Trace the existing rotation probability through a counterfactual 240-minute allocator on the '
                  'actual-participant panel; independently inspect the last-five-team-games rule which can reduce '
                  'the separate availability value when a hypothetical status is Active.',
        'limitations': 'The allocator comparison is not a forecast: the roster is known after the game, and no '
                       'historical status reports are available. The recent nonappearance fallback also uses '
                       'unlisted games; it overlaps coach-DNP evidence but may represent physical absence instead. '
                       'Physical availability and rotation are different concepts; a product of the two is not by '
                       'itself proof of double-counting or a calibrated play probability.',
        'recent_nonappearance': {
            'candidate_player_games': len(pop), 'at_least_three_games_no_known_play': int(no_plays.sum()),
            'overlapping_coach_dnp': int(overlap.sum()),
            'overlapping_coach_dnp_with_unknown_prior_listing': int((overlap & pop['recent_unknown'].gt(0)).sum()),
            'overlap_played': int((overlap & pop['played'].eq(1)).sum()),
            'overlap_coach_dnp': int((overlap & pop['dnp_coach']).sum()),
            'overlap_other_or_unknown': int((overlap & ~pop['played'].eq(1) & ~pop['dnp_coach']).sum()),
            'scope': 'Hypothetical Active status only; historical status and exact live EWMA are not reconstructed.',
        },
        'conditional_target_accounting': {
            'player_games': len(targets), 'team_games': int(targets.groupby(['game_id', 'team']).ngroups),
            'healthy_15_plus_weighted_target_under_5': int(tiny.sum()),
            'already_under_5_with_known_play': int(already_tiny.sum()),
            'newly_under_5_after_rotation_weighting': int(caused_tiny.sum()),
        },
        'target_comparison': target_report,
        **excluded,
        'input_sha256': {str(p.relative_to(ROOT)): sha256_file(p) for p in source_paths},
    }
    return report, targets


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=EXPERIMENTS / '20261122_a1_s05_rotation_diagnostic.json')
    parser.add_argument('--rows-output', type=Path, default=DERIVED / 'experiments' / '20261122_a1_s05_rotation_diagnostic.parquet')
    args = parser.parse_args()
    if args.output.exists() or args.rows_output.exists():
        raise FileExistsError('refusing to overwrite an existing rotation diagnostic')
    report, rows = build()
    atomic_bytes(args.rows_output, rows.to_parquet(index=False))
    write_json(args.output, report, pretty=True)
    print(json.dumps({k: v for k, v in report.items() if k != 'target_comparison'}, indent=2))


if __name__ == '__main__':
    main()
