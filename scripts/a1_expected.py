#!/usr/bin/env python3
"""Research-only exact mixtures of saved lineup-branch worlds; not connected to serving."""
from __future__ import annotations

import argparse
import json
import sys
from fractions import Fraction
from itertools import product
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from analysis import a1_branch_persist_audit  # noqa: E402
from basketball_common import sha256_file, write_json  # noqa: E402


def fraction_json(value: Fraction) -> dict[str, str]:
    return {'numerator': str(value.numerator), 'denominator': str(value.denominator)}


def selected_branches(report: dict, conditions: dict[str, bool]) -> list[tuple[dict, Fraction]]:
    selected = report['selected']
    if not 1 <= len(selected) <= 2:
        raise ValueError('an exhaustive one- or two-player branch report is required')
    ids = {player['player_id'] for player in selected}
    if len(ids) != len(selected):
        raise ValueError('selected players must be unique')
    if not set(conditions) <= ids or any(not isinstance(value, bool) for value in conditions.values()):
        raise ValueError('conditions must identify selected players and boolean availability')
    records = report['branches']
    if len(records) != 2 ** len(selected):
        raise ValueError('all exhaustive branches are required')
    expected_choices = set(product((True, False), repeat=len(selected)))
    weighted = []
    for record in records:
        assignments = record['assignments']
        if (len(assignments) != len(selected)
                or any((team, player) != (source['team_id'], source['player_id']) or not isinstance(plays, bool)
                       for (team, player, plays), source in zip(assignments, selected, strict=True))):
            raise ValueError('branch assignments do not match selected players')
        choice = tuple(item[2] for item in assignments)
        if choice not in expected_choices:
            raise ValueError('duplicate or invalid branch assignment')
        expected_choices.remove(choice)
        weight = record['weight']
        if weight is None:
            raise ValueError('non-exhaustive branches cannot form an Expected distribution')
        probability = Fraction(int(weight['numerator']), int(weight['denominator']))
        if probability <= 0:
            raise ValueError('branch weights must be positive')
        expected = Fraction(1)
        for source, plays in zip(selected, choice, strict=True):
            p = Fraction(str(source['probability']))
            if not 0 < p < 1:
                raise ValueError('selected availability must be strictly uncertain')
            expected *= p if plays else 1 - p
        if probability != expected:
            raise ValueError('branch weight does not match the selected probabilities')
        assigned = {player: plays for _, player, plays in assignments}
        if all(assigned.get(player) == plays for player, plays in conditions.items()):
            weighted.append((record, probability))
    if expected_choices:
        raise ValueError('all exhaustive branches are required')
    mass = sum((weight for _, weight in weighted), Fraction())
    if not mass:
        raise ValueError('no positive-weight branch matches the conditions')
    return [(record, weight / mass) for record, weight in weighted]


def weighted_distribution(values: list[np.ndarray], weights: list[Fraction]) -> dict:
    """Use every world with exact probability mass; NaN denotes an undefined metric."""
    if not values or len(values) != len(weights) or sum(weights, Fraction()) != 1:
        raise ValueError('world arrays and exact unit-sum branch weights are required')
    if any(not isinstance(weight, Fraction) or weight <= 0 for weight in weights):
        raise ValueError('branch weights must be positive fractions')
    masses: dict[int | float, Fraction] = {}
    undefined = Fraction()
    worlds = 0
    for raw, weight in zip(values, weights, strict=True):
        array = np.asarray(raw)
        if array.ndim != 1 or not array.size or array.dtype.kind not in 'biuf':
            raise ValueError('each branch must contain a nonempty one-dimensional numeric array')
        if np.isinf(array).any():
            raise ValueError('infinite metric values are invalid')
        defined = ~np.isnan(array)
        per_world = weight / len(array)
        undefined += per_world * int((~defined).sum())
        unique, counts = np.unique(array[defined], return_counts=True)
        for value, count in zip(unique, counts, strict=True):
            key = int(value) if array.dtype.kind in 'biu' else float(value)
            masses[key] = masses.get(key, Fraction()) + per_world * int(count)
        worlds += len(array)
    defined_mass = 1 - undefined
    if not defined_mass:
        return {'worlds': worlds, 'defined_mass': fraction_json(defined_mass),
                'undefined_mass': fraction_json(undefined), 'status': 'undefined in every selected world',
                'mean': None, 'quantiles': None, 'histogram': []}
    ordered = sorted(masses.items())
    if sum((mass for _, mass in ordered), Fraction()) != defined_mass:
        raise ValueError('defined and undefined world masses do not reconcile')
    quantiles = []
    cumulative = Fraction()
    thresholds = iter((Fraction(1, 10), Fraction(1, 4), Fraction(1, 2), Fraction(3, 4), Fraction(9, 10)))
    target = next(thresholds, None)
    for value, mass in ordered:
        cumulative += mass
        while target is not None and cumulative >= target * defined_mass:
            quantiles.append(value)
            target = next(thresholds, None)
    if target is not None:
        raise ValueError('weighted quantiles do not reconcile')
    mean = sum((Fraction(value) * mass for value, mass in ordered), Fraction()) / defined_mass
    return {'worlds': worlds, 'defined_mass': fraction_json(defined_mass),
            'undefined_mass': fraction_json(undefined), 'status': 'defined',
            'mean': float(mean), 'quantiles': quantiles,
            'histogram': [{'value': value, **fraction_json(mass / defined_mass)} for value, mass in ordered]}


def weighted_joint(events: list[np.ndarray], conditions: list[np.ndarray], weights: list[Fraction]) -> dict:
    """Exact event, condition, intersection and conditional masses from the same branch worlds."""
    if (not events or len(events) != len(conditions) or len(events) != len(weights)
            or any(not isinstance(weight, Fraction) or weight <= 0 for weight in weights)
            or sum(weights, Fraction()) != 1):
        raise ValueError('events, conditions and positive exact unit-sum branch weights are required')
    event_mass = condition_mass = joint_mass = Fraction()
    for event, condition, weight in zip(events, conditions, weights, strict=True):
        event, condition = np.asarray(event), np.asarray(condition)
        if (event.ndim != 1 or not event.size or event.dtype != bool
                or condition.shape != event.shape or condition.dtype != bool):
            raise ValueError('branch event and condition masks must be nonempty matching boolean arrays')
        per_world = weight / len(event)
        event_mass += per_world * int(event.sum())
        condition_mass += per_world * int(condition.sum())
        joint_mass += per_world * int(np.count_nonzero(event & condition))
    return {'event': fraction_json(event_mass), 'condition': fraction_json(condition_mass),
            'joint': fraction_json(joint_mass),
            'given': fraction_json(joint_mass / condition_mass) if condition_mass else None,
            'status': 'defined' if condition_mass else 'no matching condition worlds'}


def metric(data: np.lib.npyio.NpzFile, side: str, player_id: str | None, stat: str) -> np.ndarray:
    sides = data['side']
    ids = data['player_ids']
    side_index = {'home': 0, 'away': 1}[side]
    if player_id is None:
        indexes = np.flatnonzero(sides == side_index)
    else:
        indexes = np.flatnonzero((ids == player_id) & (sides == side_index))
        if len(indexes) != 1:
            raise ValueError('player is not uniquely present on the selected side')
    if not len(indexes):
        raise ValueError('selected side has no players')

    def totals(name: str) -> np.ndarray:
        key = 'minutes' if name == 'minutes' else f'box_{name}'
        if key not in data.files:
            raise ValueError(f'worlds do not contain {name}')
        return data[key][:, indexes, :].sum(axis=(1, 2))

    ratios = {'fgpct': ('fgm', 'fga'), 'fg3pct': ('fg3m', 'fg3a'), 'ftpct': ('ftm', 'fta')}
    if stat in ratios:
        made, attempted = (totals(name) for name in ratios[stat])
        return np.divide(100.0 * made, attempted, out=np.full(len(attempted), np.nan), where=attempted > 0)
    return totals(stat)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--side', choices=('home', 'away'), required=True)
    parser.add_argument('--player', help='player ID; omit to aggregate the selected team')
    parser.add_argument('--stat', required=True, help='saved box statistic, minutes, fgpct, fg3pct or ftpct')
    parser.add_argument('--condition', action='append', default=[], metavar='PLAYER=plays|sits')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an existing mixture report')
    conditions = {}
    for condition in args.condition:
        player, sep, decision = condition.partition('=')
        if not sep or not player.isascii() or not player.isdigit() or decision not in ('plays', 'sits') or player in conditions:
            raise ValueError('conditions must be unique PLAYER=plays|sits assignments')
        conditions[player] = decision == 'plays'
    report = json.loads(args.report.read_text())
    a1_branch_persist_audit.audit(report)
    branches = selected_branches(report, conditions)
    values, weights = [], []
    for record, weight in branches:
        with np.load(record['capture'], allow_pickle=False) as data:
            values.append(metric(data, args.side, args.player, args.stat))
        weights.append(weight)
    result = weighted_distribution(values, weights)
    write_json(args.output, {'kind': 'research weighted empirical mixture; not a forecast or promotion',
                             'source_report': str(args.report), 'source_sha256': sha256_file(args.report),
                             'algorithm_sha256': sha256_file(Path(__file__)),
                             'selected_players': report['selected'],
                             'weight_assumptions': report['weight_assumptions'],
                             'limitations': ['Availability probabilities are not calibrated.',
                                             'Joint availability independence is unvalidated.',
                                             'Prior roles and missing status or usage are identified per player.',
                                             'This isolated mixture is not integrated into served forecasts.'],
                             'conditions': conditions, 'side': args.side, 'player': args.player, 'stat': args.stat,
                             'branches': [{'branch_id': record['branch_id'], 'weight': fraction_json(weight),
                                           'capture_sha256': record['capture_sha256']} for record, weight in branches],
                             'distribution': result}, pretty=True)
    print(f"{result['worlds']} saved worlds, {len(branches)} branches, status: {result['status']}", flush=True)


if __name__ == '__main__':
    main()
