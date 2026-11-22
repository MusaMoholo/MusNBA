#!/usr/bin/env python3
"""Independently replay and audit the research weighted-season accounting."""
from __future__ import annotations

import argparse
import sys
import time
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, SNAPSHOTS, read_json, sha256_file, write_json  # noqa: E402
from scripts import box_scores, master_fixtures, pathway, projection  # noqa: E402
from scripts.season_stats import team_table  # noqa: E402


def fraction(value: dict) -> Fraction:
    return Fraction(int(value['numerator']), int(value['denominator']))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--coupling-report', required=True, type=Path)
    parser.add_argument('--pathway-report', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an experiment')
    start = time.monotonic()
    coupled = read_json(args.coupling_report)
    expected = read_json(args.pathway_report)
    if (expected['origin'] != coupled['origin']
            or sha256_file(coupled['worlds_output']) != coupled['worlds_sha256']
            or sha256_file(expected['source']) != expected['source_sha256']):
        raise ValueError('origin or saved world hash mismatch')
    sources = {}
    for source in coupled['sources']:
        if sha256_file(source['report']) != source['sha256'] or source['game'] in sources:
            raise ValueError('changed or duplicate branch source')
        report = read_json(source['report'])
        pieces = []
        for branch in report['branches']:
            if sha256_file(branch['capture']) != branch['capture_sha256']:
                raise ValueError('branch capture hash changed')
            with np.load(branch['capture'], allow_pickle=False) as data:
                pieces.append((data['team_points'], fraction(branch['weight'])))
        sources[source['game']] = pieces
    for source in coupled['snapshot_sources']:
        snapshot = SNAPSHOTS / source['day']
        path = snapshot / 'engine_worlds.npz'
        if sha256_file(path) != source['worlds_sha256'] or sha256_file(snapshot / 'meta.json') != source['meta_sha256']:
            raise ValueError('snapshot hash changed')
        with np.load(path, allow_pickle=False) as data:
            for game in data.files:
                if game in coupled['unbranched_games']:
                    if game in sources:
                        raise ValueError('duplicate game')
                    sources[game] = [(data[game], Fraction(1))]
    if set(sources) != set(coupled['unbranched_games']) | {s['game'] for s in coupled['sources']}:
        raise ValueError('near-term game inventory mismatch')
    with np.load(coupled['worlds_output'], allow_pickle=False) as saved, \
            np.load(expected['source'], allow_pickle=False) as original:
        if set(saved.files) != set(original.files):
            raise ValueError('pathway source arrays do not match')
        for key in saved.files:
            if not np.array_equal(saved[key], original[key]):
                raise ValueError(f'pathway source array {key} changed')
        weights = saved['numerators']
        denominator = int(saved['denominator'].item())
        if sum(map(int, weights)) != denominator or (weights <= 0).any():
            raise ValueError('invalid path weights')
        engine = {game: saved[game] for game in sources}
    marginal_results = []
    for game, pieces in sorted(sources.items()):
        src, dst = defaultdict(int), defaultdict(int)
        for worlds, probability in pieces:
            per_world = probability * denominator / len(worlds)
            if per_world.denominator != 1:
                raise ValueError('nonintegral score weight')
            for row in worlds:
                src[tuple(map(int, row.ravel()))] += per_world.numerator
        for row, weight in zip(engine[game], weights, strict=True):
            dst[tuple(map(int, row.ravel()))] += int(weight)
        if src != dst:
            raise ValueError(f'{game}: complete score-vector marginal mismatch')
        marginal_results.append({'game': game, 'distinct_vectors': len(src)})
    origin = coupled['origin']
    schedule = sorted((g for g in master_fixtures.load() if g['date_et'] >= origin),
                      key=lambda g: (g['date_et'], g['tip_utc'], g['game_id']))
    ids = [g['game_id'] for g in schedule]
    if len(set(ids)) != len(ids) or not set(engine) <= set(ids):
        raise ValueError('duplicate or absent scheduled game')
    teams = read_json(DERIVED / 'teams.json')
    standings, league = team_table(box_scores.load_csv('team_games.csv'), origin, teams)
    played = pathway.play(standings, league, schedule, len(weights),
                          projection.rng_for('a1-weighted-pathway', origin), engine)
    rows = expected['results']['games']
    if [row['game_id'] for row in rows] != ids:
        raise ValueError('pathway game inventory/order differs')
    team_ids = sorted(teams, key=int)
    index = {team: n for n, team in enumerate(team_ids)}
    wins = np.broadcast_to(np.array([standings[t]['w'] for t in team_ids], dtype=np.int16),
                           (len(weights), len(team_ids))).copy()
    for column, (game, row) in enumerate(zip(schedule, rows, strict=True)):
        won = played['home_win'][:, column]
        if fraction(row['home_win']) != Fraction(sum(map(int, weights[won])), denominator):
            raise ValueError(f'{ids[column]}: game win probability mismatch')
        wins[:, index[game['home_id']]] += won
        wins[:, index[game['away_id']]] += ~won
        if ids[column] in engine:
            points = engine[ids[column]].sum(axis=2)
            if (not np.array_equal(points, played['points'][:, column])
                    or not np.array_equal(points[:, 0] > points[:, 1], won)):
                raise ValueError(f'{ids[column]}: per-path engine score or win mismatch')
    tie = np.random.default_rng(20261122).random(wins.shape)
    ranks = np.zeros_like(wins)
    for conference in ('East', 'West'):
        columns = np.array([index[t] for t in team_ids if teams[t]['conf'] == conference])
        order = np.lexsort((-tie[:, columns], -wins[:, columns]), axis=1)
        ranks[np.arange(len(weights))[:, None], columns[order]] = np.arange(1, len(columns) + 1)
    for team in team_ids:
        column = index[team]
        result = expected['results']['teams'][team]
        histogram = {int(row['wins']): fraction(row) for row in result['wins']}
        actual = {int(value): Fraction(sum(map(int, weights[wins[:, column] == value])), denominator)
                  for value in np.unique(wins[:, column])}
        if histogram != actual or fraction(result['mean_wins']) != sum((v * p for v, p in actual.items()), Fraction()):
            raise ValueError(f'{team}: wins summary mismatch')
        for rank, value in enumerate(result['seeds'], 1):
            if fraction(value) != Fraction(sum(map(int, weights[ranks[:, column] == rank])), denominator):
                raise ValueError(f'{team}: seed {rank} mismatch')
    inputs = [ROOT / 'scripts/pathway.py', ROOT / 'scripts/projection.py', ROOT / 'scripts/season_stats.py',
              ROOT / 'scripts/box_scores.py', master_fixtures.MASTER_CSV, DERIVED / 'team_games.csv',
              DERIVED / 'teams.json', Path(__file__)]
    write_json(args.output, {
        'kind': 'independent research accounting audit; not a forecast or predictive acceptance',
        'coupling_report_sha256': sha256_file(args.coupling_report),
        'pathway_report_sha256': sha256_file(args.pathway_report),
        'origin': origin, 'paths': len(weights), 'schedule_games': len(ids), 'teams': len(team_ids),
        'engine_game_marginals': marginal_results, 'win_histograms_and_seed_distributions_verified': len(team_ids),
        'input_sha256': {str(p.relative_to(ROOT)): sha256_file(p) for p in inputs}, 'numpy_version': np.__version__,
        'elapsed_seconds': round(time.monotonic() - start, 3),
        'limitation': 'Two branch mixtures and 15 unconditional inputs; no dependence or promotion claim.',
    }, pretty=True)
    print(f'{len(engine)} exact marginals and per-path results; {len(ids)} game wins; '
          f'{len(team_ids)} team win and seed distributions verified', flush=True)


if __name__ == '__main__':
    main()
