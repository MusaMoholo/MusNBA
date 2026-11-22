#!/usr/bin/env python3
"""Build isolated, strictly prior tracking-defence features for historical shots."""
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
from scripts import a1_tracking_coverage, fetch_nbastats, nbastats, nodes  # noqa: E402
from scripts.evaluate import FOLDS, TEST_FROM  # noqa: E402

BUCKETS = {'rim': 'Less Than 6Ft', 'three': '3 Pointers'}
SEASONS = tuple(season for season in fetch_nbastats.SEASONS if season != '2026-27')


def cumulative_history(rows: pd.DataFrame) -> pd.DataFrame:
    required = {'day', 'player', 'bucket', 'made', 'attempted'}
    if not required.issubset(rows.columns) or rows[list(required)].isna().any().any():
        raise ValueError('tracking history has missing fields')
    if rows.duplicated(['day', 'player', 'bucket']).any():
        raise ValueError('tracking history has duplicate player/day/bucket rows')
    if ((rows['made'] < 0) | (rows['attempted'] < 0) | (rows['made'] > rows['attempted'])).any():
        raise ValueError('tracking history has invalid made/attempted counts')
    out = rows.sort_values(['player', 'bucket', 'day']).copy()
    out[['made', 'attempted']] = out.groupby(['player', 'bucket'])[['made', 'attempted']].cumsum()
    return out


def previous_rates(targets: pd.DataFrame, history: pd.DataFrame, bucket: str) -> pd.DataFrame:
    if targets[['day', 'player']].isna().any().any():
        raise ValueError('tracking target has a missing date or player')
    left = targets[['day', 'player']].copy()
    left['ordinal'] = np.arange(len(left))
    right = history.loc[history['bucket'].eq(bucket), ['day', 'player', 'made', 'attempted']].copy()
    left['day'] = pd.to_datetime(left['day'], errors='raise')
    right['source_day'] = pd.to_datetime(right.pop('day'), errors='raise')
    left = left.sort_values(['day', 'player'])
    right = right.sort_values(['source_day', 'player'])
    out = pd.merge_asof(left, right, left_on='day', right_on='source_day', by='player',
                        allow_exact_matches=False, direction='backward')
    if (out['source_day'].notna() & (out['source_day'] >= out['day'])).any():
        raise ValueError('tracking feature used the target date or a later date')
    out['rate'] = (out['made'] / out['attempted']).where(out['attempted'] > 0)
    return out.sort_values('ordinal').reset_index(drop=True)


def load_tracking() -> tuple[pd.DataFrame, dict, list[Path]]:
    _, game_log = nbastats.nba_tables(list(SEASONS))
    game_log = game_log.loc[game_log['date'] < TEST_FROM, ['date', 'PLAYER_ID', 'TEAM_ABBREVIATION']].drop_duplicates()
    if game_log.duplicated(['date', 'PLAYER_ID']).any():
        raise ValueError('NBA player/day is associated with more than one team')
    teams = {(str(r.date), int(r.PLAYER_ID)): str(r.TEAM_ABBREVIATION)
             for r in game_log.itertuples(index=False)}
    crosswalk_path = DERIVED / 'nbastats/players.parquet'
    crosswalk = pd.read_parquet(crosswalk_path)
    if crosswalk[['person', 'player']].isna().any().any() or crosswalk['person'].duplicated().any() or crosswalk['player'].duplicated().any():
        raise ValueError('NBA-to-ESPN tracking crosswalk is not one-to-one')
    player_of = dict(zip(crosswalk['person'].astype(int), crosswalk['player'].astype(str)))
    games = fetch_nbastats.logged_games(list(SEASONS))
    dates = {season: sorted({day for game_season, _, _, day in games
                             if game_season == season and day < TEST_FROM}) for season in SEASONS}
    total = sum(len(days) for days in dates.values()) * len(BUCKETS)
    rows = []
    files = 0
    mismatched_latest_team = 0
    manifests = []
    started = time.monotonic()
    for season in SEASONS:
        folder = fetch_nbastats.NBA_RAW / 'leaguedashptdefend' / season
        manifest_path = folder / 'manifest.json'
        manifests.append(manifest_path)
        manifest = json.loads(manifest_path.read_text())
        for day in dates[season]:
            for bucket, category in BUCKETS.items():
                key = f'{category.lower().replace(" ", "")}_{day}'
                path = folder / f'{key}.json.gz'
                if key not in manifest or not path.is_file():
                    raise FileNotFoundError(f'missing historical tracking response or manifest entry: {path}')
                _, source = a1_tracking_coverage.decode(path, manifest[key], season, day, category)
                made_field, attempts_field = a1_tracking_coverage.ATTEMPT_FIELDS[category]
                seen = set()
                for item in source:
                    person_value = item['CLOSE_DEF_PERSON_ID']
                    if person_value is None:
                        raise ValueError(f'{path}: missing defender identity')
                    person = int(person_value)
                    if person in seen:
                        raise ValueError(f'{path}: duplicate defender identity')
                    seen.add(person)
                    team = teams.get((day, person))
                    player = player_of.get(person)
                    if team is None or player is None or item['GP'] != 1:
                        raise ValueError(f'{path}: defender lacks a unique dated NBA team or ESPN identity')
                    made, attempted = item[made_field], item[attempts_field]
                    if (made is None or attempted is None or not np.isfinite(made) or not np.isfinite(attempted)
                            or made < 0 or attempted < 0 or made > attempted):
                        raise ValueError(f'{path}: invalid defended-shot counts')
                    mismatched_latest_team += team != item['PLAYER_LAST_TEAM_ABBREVIATION']
                    rows.append((day, player, bucket, float(made), float(attempted)))
                files += 1
                if files % max(1, total // 10) == 0 or files == total:
                    print(f'tracking files {files}/{total} {time.monotonic() - started:.1f}s', flush=True)
    source = pd.DataFrame(rows, columns=['day', 'player', 'bucket', 'made', 'attempted'])
    if source.empty or files != total:
        raise ValueError('tracking response coverage is empty or incomplete')
    return cumulative_history(source), {'files': files, 'rows': len(source),
                                        'latest_team_disagreements': mismatched_latest_team}, [crosswalk_path, *manifests]


def player_game_targets(shots: pd.DataFrame, pregame: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
    defenders = [f'def_{i}' for i in range(1, 6)]
    values = shots[defenders]
    valid_five = values.notna().all(axis=1) & values.nunique(axis=1).eq(5)
    exposures = pd.concat(
        [shots[['game_id', 'date_et', 'defense', name]].rename(columns={name: 'player'})
         for name in defenders], ignore_index=True).dropna(subset=['player']).drop_duplicates()
    pre = pregame[['game_id', 'player', 'team']].copy()
    for col in ('game_id', 'player', 'team'):
        pre[col] = pre[col].astype(str)
    if pre.duplicated(['game_id', 'player']).any():
        raise ValueError('pregame roster has duplicate player/game identities')
    for col in ('game_id', 'defense', 'player'):
        exposures[col] = exposures[col].astype(str)
    exposures = exposures.merge(pre, on=['game_id', 'player'], how='left', validate='many_to_one')
    exposures['team_valid'] = exposures['team'].notna() & exposures['team'].eq(exposures['defense'])
    if exposures.duplicated(['game_id', 'defense', 'player']).any():
        raise ValueError('defensive game/player exposure is not unique')
    return exposures, valid_five.to_numpy()


def build() -> tuple[pd.DataFrame, dict]:
    history, source_stats, inputs = load_tracking()
    seg = nodes.load_segments()
    shots = seg.loc[(seg['end_type'] == 'shot') & ~seg['heave'] & seg['zone'].isin(nodes.ZONES)].copy()
    if 'lineup_valid' in shots:
        if not pd.api.types.is_bool_dtype(shots['lineup_valid']) or shots['lineup_valid'].isna().any():
            raise ValueError('segment lineup validity is missing or not boolean')
        shots = shots.loc[shots['lineup_valid']]
    shots = shots.reset_index(drop=True)
    pregame_paths = [DERIVED / 'variants' / f'a1_scheduled_{fold}_20261122_v3/features/pregame.parquet'
                     for fold in FOLDS]
    first = pd.read_parquet(pregame_paths[0], columns=['game_id', 'player', 'team']).astype(str)
    identity = first.sort_values(['game_id', 'player', 'team']).reset_index(drop=True)
    for path in pregame_paths[1:]:
        other = pd.read_parquet(path, columns=['game_id', 'player', 'team']).astype(str)
        if not identity.equals(other.sort_values(['game_id', 'player', 'team']).reset_index(drop=True)):
            raise ValueError(f'{path}: guarded fold roster identities differ')
    targets, valid_five = player_game_targets(shots, first)
    counts = {'invalid_defensive_fives': int((~valid_five).sum()),
              'player_game_exposures': len(targets), 'wrong_or_missing_team_exposures': int((~targets['team_valid']).sum())}
    target_days = targets.rename(columns={'date_et': 'day'})
    for bucket in BUCKETS:
        prior = previous_rates(target_days, history, bucket)
        targets[f'{bucket}_rate'] = prior['rate'].where(targets['team_valid'])
        targets[f'{bucket}_source_day'] = prior['source_day'].where(targets['team_valid'])
        counts[f'{bucket}_known_player_game_rates'] = int(targets[f'{bucket}_rate'].notna().sum())
    output = shots[['game_id', 'date_et', 'zone']].copy()
    output['outcome'] = np.where(shots['made'] == 1, np.where(shots['and_one'], 2, 1), 0)
    output['valid_five'] = valid_five
    keys = ['game_id', 'defense', 'player']
    for bucket in BUCKETS:
        matrix = np.full((len(shots), 5), np.nan)
        lookup = targets[keys + [f'{bucket}_rate']]
        for i in range(5):
            name = f'def_{i + 1}'
            exposure = shots[['game_id', 'defense', name]].rename(columns={name: 'player'}).copy()
            exposure[['game_id', 'defense', 'player']] = exposure[['game_id', 'defense', 'player']].astype(str)
            joined = exposure.merge(lookup, on=keys, how='left', validate='many_to_one', sort=False)
            if len(joined) != len(shots):
                raise ValueError('defensive player-rate join changed the shot population')
            matrix[:, i] = joined[f'{bucket}_rate'].to_numpy(dtype=float)
        complete = valid_five & np.isfinite(matrix).all(axis=1)
        output[f'{bucket}_known_defenders'] = np.isfinite(matrix).sum(axis=1)
        output[f'{bucket}_five_mean'] = np.where(complete, np.nan_to_num(matrix).sum(axis=1) / 5, np.nan)
        counts[f'{bucket}_complete_five_shots'] = int(complete.sum())
    inputs += pregame_paths + nodes.segment_files() + [Path(__file__), Path(a1_tracking_coverage.__file__),
                                                      Path(fetch_nbastats.__file__), Path(nbastats.__file__)]
    for season in SEASONS:
        inputs.extend(sorted((fetch_nbastats.NBA_RAW / 'gamelogs' / season).glob('*.json.gz')))
    result = {'source': source_stats, 'coverage': counts,
              'semantics': 'cumulative defended-shot counts from dates strictly before target; all five known or missing',
              'provenance_limit': 'historical source publication/revision timing and contemporaneous crosswalk are unproven',
              'input_sha256': {str(p.resolve().relative_to(ROOT)): sha256_file(p) for p in inputs}}
    return output, result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.report.exists():
        raise FileExistsError('refusing to overwrite tracking-feature output')
    if not args.output.resolve().is_relative_to((DERIVED / 'experiments').resolve()):
        raise ValueError('tracking-feature rows must remain under ignored data/derived/experiments')
    features, report = build()
    atomic_bytes(args.output, features.to_parquet(index=False))
    report.update({'experiment': 'a1_s04_tracking_defence_prior_features', 'shots': len(features),
                   'rows_sha256': sha256_file(args.output)})
    write_json(args.report, report, pretty=True)
    print(json.dumps(report, indent=1), flush=True)


if __name__ == '__main__':
    main()
