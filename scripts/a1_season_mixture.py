#!/usr/bin/env python3
"""Research-only exact-marginal coupling of near-term game worlds for a weighted season."""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import date
from fractions import Fraction
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from analysis import a1_branch_persist_audit  # noqa: E402
from basketball_common import SNAPSHOTS, read_json, sha256_file, write_json  # noqa: E402
from scripts import a1_expected, projection  # noqa: E402


def couple(games: dict[str, list[tuple[np.ndarray, Fraction]]], seed: int,
           *, max_paths: int = 200_000) -> dict:
    """Partition a shared unit interval so each game's complete weighted marginal is exact."""
    if not games:
        raise ValueError('at least one near-term game is required')
    if not isinstance(max_paths, int) or isinstance(max_paths, bool) or max_paths < 1:
        raise ValueError('max_paths must be a positive integer')
    denominator = 1
    for game, pieces in games.items():
        if not isinstance(game, str) or not game or not pieces:
            raise ValueError('each game needs an identifier and branch worlds')
        if any(not isinstance(weight, Fraction) or weight <= 0 for _, weight in pieces):
            raise ValueError('branch weights must be positive exact fractions')
        if sum((weight for _, weight in pieces), Fraction()) != 1:
            raise ValueError('each game must have exact unit branch weight')
        for worlds, weight in pieces:
            if (not isinstance(worlds, np.ndarray) or worlds.ndim != 3 or worlds.shape[1:] != (2, 5)
                    or not len(worlds) or worlds.dtype.kind not in 'iu' or (worlds < 0).any()):
                raise ValueError('game worlds must be nonempty nonnegative integer period scores')
            denominator = math.lcm(denominator, (weight / len(worlds)).denominator)
    if denominator > np.iinfo(np.int64).max // 2:
        raise ValueError('exact mixture denominator exceeds the safe integer range')
    layouts, boundaries = {}, [np.array([0, denominator], dtype=np.int64)]
    for game, pieces in sorted(games.items()):
        worlds = np.concatenate([world for world, _ in pieces], axis=0)
        widths = []
        for values, weight in pieces:
            units = weight * denominator / len(values)
            if units.denominator != 1 or units <= 0:
                raise ValueError('world weights cannot be represented by the common denominator')
            widths.append(np.full(len(values), units.numerator, dtype=np.int64))
        widths = np.concatenate(widths)
        rng = np.random.default_rng(projection.seed_for('a1-season-weighted-v1', seed, game))
        permutation = rng.permutation(len(worlds))
        ends = np.cumsum(widths[permutation], dtype=np.int64)
        if int(ends[-1]) != denominator:
            raise ValueError('game world weights do not total the common denominator')
        offset = int(rng.integers(denominator))
        boundaries.append((ends + offset) % denominator)
        layouts[game] = (worlds, permutation, ends, offset)
    edges = np.unique(np.concatenate(boundaries))
    numerators = np.diff(edges)
    if not len(numerators) or (numerators <= 0).any() or int(numerators.sum()) != denominator:
        raise ValueError('season interval weights do not partition the unit interval')
    if len(numerators) > max_paths:
        raise ValueError(f'weighted season needs {len(numerators)} paths, exceeding limit {max_paths}')
    coupled = {}
    for game, (worlds, permutation, ends, offset) in layouts.items():
        positions = (edges[:-1] - offset) % denominator
        indices = permutation[np.searchsorted(ends, positions, side='right')]
        coupled[game] = worlds[indices]
    return {'numerators': numerators, 'denominator': denominator, 'games': coupled}


def from_reports(paths: list[Path]) -> tuple[dict, list[dict], str]:
    games, provenance = {}, []
    origin = None
    for path in paths:
        report = json.loads(path.read_text())
        a1_branch_persist_audit.audit(report)
        if report['game'] in games:
            raise ValueError('a near-term game cannot be supplied twice')
        if origin is not None and report['origin'] != origin:
            raise ValueError('all games must share the same forecast origin')
        origin = report['origin']
        pieces = []
        for branch, weight in a1_expected.selected_branches(report, {}):
            with np.load(branch['capture'], allow_pickle=False) as data:
                pieces.append((data['team_points'], weight))
        games[report['game']] = pieces
        if not report.get('weight_assumptions') or not report.get('availability_policy'):
            raise ValueError('branch report must identify availability and weight assumptions')
        provenance.append({'game': report['game'], 'engine': report['engine'],
                           'report': str(path), 'sha256': sha256_file(path),
                           'selected_players': report['selected'],
                           'availability_policy': report['availability_policy'],
                           'weight_assumptions': report['weight_assumptions']})
    if origin is None:
        raise ValueError('at least one branch report is required')
    return games, provenance, origin


def summarize_pathway(teams: dict, standings: dict, games: list[dict], played: dict,
                      numerators: np.ndarray, denominator: int, seed: int) -> dict:
    """Aggregate season paths with exact interval weights, never equal-path counts."""
    numerators = np.asarray(numerators)
    if (numerators.ndim != 1 or not len(numerators) or numerators.dtype.kind not in 'iu'
            or (numerators <= 0).any() or denominator <= 0
            or sum(map(int, numerators)) != denominator):
        raise ValueError('season path weights must be positive and sum exactly to their denominator')
    ids = sorted(teams, key=int)
    if any(teams[team]['conf'] not in ('East', 'West') for team in ids):
        raise ValueError('each team must have a known conference')
    index = {team: i for i, team in enumerate(ids)}
    if len(set(row['game_id'] for row in games)) != len(games):
        raise ValueError('season schedule contains duplicate games')
    home_win = np.asarray(played['home_win'])
    points = np.asarray(played['points'])
    if (home_win.shape != (len(numerators), len(games)) or home_win.dtype != bool
            or points.shape != (len(numerators), len(games), 2)
            or points.dtype.kind not in 'iu' or (points < 0).any()):
        raise ValueError('pathway results do not match the season paths and schedule')
    wins = np.broadcast_to(np.array([standings[team]['w'] for team in ids], dtype=np.int64),
                           (len(numerators), len(ids))).copy()
    game_results = []
    for column, game in enumerate(games):
        home, away = game['home_id'], game['away_id']
        if home not in index or away not in index or home == away:
            raise ValueError('season game has an invalid team pairing')
        won = home_win[:, column]
        wins[:, index[home]] += won
        wins[:, index[away]] += ~won
        numerator = sum(map(int, numerators[won]))
        game_results.append({'game_id': game['game_id'],
                             'home_win': a1_expected.fraction_json(Fraction(numerator, denominator))})
    rng = np.random.default_rng(seed)
    tie = rng.random(wins.shape)
    seed_rank = np.zeros_like(wins)
    for conference in ('East', 'West'):
        columns = np.array([index[team] for team in ids if teams[team]['conf'] == conference], dtype=int)
        if not len(columns):
            raise ValueError(f'no teams in {conference} conference')
        order = np.argsort(-(wins[:, columns] + 0.5 * tie[:, columns]), axis=1, kind='stable')
        ranks = np.empty_like(order)
        ranks[np.arange(len(numerators))[:, None], order] = np.arange(1, len(columns) + 1)[None, :]
        seed_rank[:, columns] = ranks
    result = {}
    for team in ids:
        col = index[team]
        win_values = np.unique(wins[:, col])
        histogram = []
        mean = Fraction()
        for value in win_values:
            mass = Fraction(sum(map(int, numerators[wins[:, col] == value])), denominator)
            mean += int(value) * mass
            histogram.append({'wins': int(value), **a1_expected.fraction_json(mass)})
        ranks = []
        count = sum(teams[t]['conf'] == teams[team]['conf'] for t in ids)
        for rank in range(1, count + 1):
            mass = Fraction(sum(map(int, numerators[seed_rank[:, col] == rank])), denominator)
            ranks.append(a1_expected.fraction_json(mass))
        result[team] = {'mean_wins': a1_expected.fraction_json(mean), 'wins': histogram, 'seeds': ranks}
    return {'games': game_results, 'teams': result}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', action='append', type=Path, required=True)
    parser.add_argument('--unconditional-day', action='append', default=[],
                        help='include retained unbranched snapshot games for this slate')
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--max-paths', type=int, default=200_000,
                        help='research safety limit; not a full memory guarantee')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--worlds-output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.worlds_output.exists():
        raise FileExistsError('refusing to overwrite an existing report or season worlds')
    if args.worlds_output.suffix != '.npz':
        raise ValueError('season worlds output must have an .npz suffix')
    games, provenance, origin = from_reports(args.report)
    branched = set(games)
    encountered: set[str] = set()
    snapshot_sources = []
    for day in args.unconditional_day:
        if date.fromisoformat(day).isoformat() != day:
            raise ValueError('snapshot slate date must be ISO formatted')
        snapshot = SNAPSHOTS / day
        meta = read_json(snapshot / 'meta.json')
        if (meta['slate_date'] != day or meta['kind'] != 'prospective' or meta['origin'] != origin
                or any(source['engine'] != meta['model']['id'] for source in provenance)):
            raise ValueError('snapshot and branch origin or engine do not match')
        path = snapshot / 'engine_worlds.npz'
        with np.load(path, allow_pickle=False) as data:
            for game in data.files:
                if game in encountered:
                    raise ValueError('a near-term snapshot game appears more than once')
                encountered.add(game)
                if game not in branched:
                    if len(data[game]) != meta['model']['sims']:
                        raise ValueError('snapshot game world count differs from its model metadata')
                    games[game] = [(data[game], Fraction(1))]
        snapshot_sources.append({'day': day, 'worlds_sha256': sha256_file(path),
                                 'meta_sha256': sha256_file(snapshot / 'meta.json')})
    if args.unconditional_day and not branched <= encountered:
        raise ValueError('a branch game is missing from the supplied near-term snapshots')
    coupled = couple(games, args.seed, max_paths=args.max_paths)
    args.worlds_output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.worlds_output, numerators=coupled['numerators'],
                        denominator=np.asarray(str(coupled['denominator'])), **coupled['games'])
    write_json(args.output, {'kind': 'research exact-marginal season coupling; cross-game dependence unvalidated',
                             'origin': origin, 'seed': str(args.seed), 'sources': provenance,
                             'snapshot_sources': snapshot_sources,
                             'algorithm_sha256': sha256_file(Path(__file__)), 'max_paths': args.max_paths,
                             'helper_sha256': {'a1_expected': sha256_file(ROOT / 'scripts/a1_expected.py'),
                                               'projection': sha256_file(ROOT / 'scripts/projection.py')},
                             'limitations': ['Branch availability probabilities are uncalibrated.',
                                             'Within-game and across-game availability dependence is unvalidated.',
                                             'Unbranched games use retained unconditional inputs.',
                                             'Prior roles and missing status or usage are identified per selected player.',
                                             'This coupling is not integrated into served forecasts.'],
                             'unbranched_games': sorted(set(games) - branched),
                             'paths': len(coupled['numerators']), 'denominator': str(coupled['denominator']),
                             'worlds_output': str(args.worlds_output),
                             'worlds_sha256': sha256_file(args.worlds_output)}, pretty=True)
    print(f"{len(games)} games, {len(coupled['numerators'])} weighted paths; "
          f"denominator {coupled['denominator']}", flush=True)


if __name__ == '__main__':
    main()
