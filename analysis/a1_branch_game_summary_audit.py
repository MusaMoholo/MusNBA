#!/usr/bin/env python3
"""Reconstruct an isolated weighted game summary from original branch captures."""
from __future__ import annotations

import argparse
import json
import math
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import sha256_file, write_json  # noqa: E402
from scripts import a1_expected, projection  # noqa: E402


def close(actual: float, expected: float, label: str) -> None:
    if not math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-9):
        raise ValueError(f'{label}: {actual} differs from {expected}')


def audit_distribution(actual: dict, arrays: list[np.ndarray], units: list[int], label: str) -> None:
    counts: dict[int, int] = {}
    total = sum(len(a) * weight for a, weight in zip(arrays, units, strict=True))
    for array, weight in zip(arrays, units, strict=True):
        finite = array[~np.isnan(array)]
        if not len(finite):
            continue
        values, frequency = np.unique(finite.astype(int), return_counts=True)
        for value, n in zip(values, frequency, strict=True):
            counts[int(value)] = counts.get(int(value), 0) + int(n) * weight
    defined = sum(counts.values())
    if not defined:
        if actual is not None:
            raise ValueError(f'{label}: expected no defined distribution')
        return
    if actual is None:
        raise ValueError(f'{label}: missing defined distribution')
    lo, hi = actual['min'], max(counts)
    if lo > min(counts) or actual['hist'] != [counts.get(k, 0) for k in range(lo, hi + 1)]:
        raise ValueError(f'{label}: histogram differs')
    if 'defined_mass' in actual and (actual['defined_mass'] != defined or actual['total_mass'] != total):
        raise ValueError(f'{label}: defined mass differs')
    average = sum(value * count for value, count in counts.items()) / defined
    close(actual['mean'], average, label)
    variance = sum((value - average) ** 2 * count for value, count in counts.items()) / defined
    close(actual['sd'], math.sqrt(variance), label + ' standard deviation')
    quantiles = []
    for target in (Fraction(1, 10), Fraction(1, 4), Fraction(1, 2), Fraction(3, 4), Fraction(9, 10)):
        mass = 0
        for value in sorted(counts):
            mass += counts[value]
            if mass * target.denominator >= defined * target.numerator:
                quantiles.append(value)
                break
    if actual['q'] != quantiles:
        raise ValueError(f'{label}: quantiles differ')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('probe', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an existing audit')
    probe = json.loads(args.probe.read_text())
    for path, key in (('analysis/a1_branch_world_source.mjs', 'source_sha256'),
                      ('scripts/webapp/weighted-worlds.mjs', 'arithmetic_sha256'),
                      ('analysis/a1_branch_game_summary.mjs', 'algorithm_sha256'),
                      ('analysis/a1_branch_game_summary_probe.mjs', 'probe_sha256')):
        if sha256_file(ROOT / path) != probe[key]:
            raise ValueError(f'{path} hash differs from probe')
    summary_path, fixture_path = Path(probe['summary']), Path(probe['fixture'])
    if sha256_file(summary_path) != probe['summary_sha256'] or sha256_file(fixture_path) != probe['fixture_sha256']:
        raise ValueError('summary or fixture hash differs')
    result = json.loads(summary_path.read_text())
    fixture = json.loads(fixture_path.read_text())
    report_path = Path(fixture['source'])
    if (sha256_file(report_path) != fixture['source_sha256'] or result['choices'] != probe['choices']
            or result['fixture'] != probe['fixture'] or result['fixture_sha256'] != probe['fixture_sha256']):
        raise ValueError('source report or choices differ')
    report = json.loads(report_path.read_text())
    all_branches = a1_expected.selected_branches(report, {})
    denominator = math.lcm(*(weight.denominator * branch['worlds'] // math.gcd(weight.numerator, weight.denominator * branch['worlds'])
                             for branch, weight in all_branches))
    selected = a1_expected.selected_branches(report, result['choices'])
    chosen_ids = {branch['branch_id'] for branch, _ in selected}
    loaded, units = [], []
    for branch, weight in all_branches:
        if branch['branch_id'] not in chosen_ids:
            continue
        path = Path(branch['capture'])
        if sha256_file(path) != branch['capture_sha256']:
            raise ValueError('capture hash differs')
        with np.load(path, allow_pickle=False) as data:
            first = np.unique(data['trace_world'], return_index=True)[1]
            loaded.append({key: data[key] for key in ('player_ids', 'side', 'available', 'minutes', 'team_points',
                                                       'final_period', *(f'box_{stat}' for stat in projection.BOX))})
            loaded[-1]['opening'] = data['trace_lineups'][first]
        if (not np.array_equal(loaded[0]['player_ids'], loaded[-1]['player_ids'])
                or not np.array_equal(loaded[0]['side'], loaded[-1]['side'])):
            raise ValueError('capture rosters differ')
        unit = weight * denominator / branch['worlds']
        if unit.denominator != 1:
            raise ValueError('non-integral world mass')
        units.append(int(unit))
    out = result['result']
    if (out['total_mass'] != denominator or out['selected_worlds'] != sum(len(d['minutes']) for d in loaded)
            or out['selected_mass'] != sum(len(d['minutes']) * w for d, w in zip(loaded, units, strict=True))
            or out['game'] != report['game'] or out['origin'] != report['origin'] or out['choices'] != result['choices']
            or out['selected_players'] != report['selected'] or out['weight_assumptions'] != report['weight_assumptions']):
        raise ValueError('selected counts or weights differ')
    mass = out['selected_mass']
    distributions = means = 0
    for period, cols in projection.SLICES.items():
        team_pts = [[d['team_points'][:, team, cols].sum(axis=1) for d in loaded] for team in (0, 1)]
        for name, arrays in (
                ('home', team_pts[0]), ('away', team_pts[1]),
                ('total', [h + a for h, a in zip(*team_pts, strict=True)]),
                ('margin', [h - a for h, a in zip(*team_pts, strict=True)])):
            actual = out['periods'][period][name]
            audit_distribution(actual['pts'] if name in ('home', 'away') else actual, arrays, units, period + ' ' + name)
            distributions += 1
        for team, s in ((0, 'home'), (1, 'away')):
            other = 1 - team
            for name, op in (('win', np.greater), ('tie', np.equal)):
                expected = sum(int(op(a, b).sum()) * w for a, b, w in zip(team_pts[team], team_pts[other], units, strict=True)) / mass
                close(out['periods'][period][s][name], expected, period + ' ' + s + ' ' + name)
                means += 1
    overtime = [d['final_period'] - 4 for d in loaded]
    close(out['ot'], sum(int((a > 0).sum()) * w for a, w in zip(overtime, units, strict=True)) / mass, 'overtime')
    for n, value in enumerate(out['ot_periods']):
        if value != sum(int((a == n).sum()) * w for a, w in zip(overtime, units, strict=True)):
            raise ValueError('overtime counts differ')
    if sum(out['ot_periods']) != mass:
        raise ValueError('overtime counts do not exhaust selected mass')
    for index, player_id in enumerate(loaded[0]['player_ids']):
        team = 'home' if loaded[0]['side'][index] == 0 else 'away'
        player = next(p for p in out[team]['players'] if p['id'] == player_id)
        for key, arrays in (
                ('availability', [d['available'][:, index] for d in loaded]),
                ('played', [d['minutes'][:, index, :].sum(axis=1) > 0 for d in loaded]),
                ('opening_share', [(d['opening'] == index).any(axis=(1, 2)) for d in loaded])):
            expected = sum(int(a.sum()) * w for a, w in zip(arrays, units, strict=True)) / mass
            close(player[key], expected, f'{player_id} {key}')
            means += 1
        for period, cols in projection.SLICES.items():
            arrays = []
            exact_minutes = []
            for d in loaded:
                v = {key: d[f'box_{key}'][:, index, cols].sum(axis=1) for key in projection.BOX}
                v['reb'] = v['oreb'] + v['dreb']
                v['pra'], v['pr'], v['pa'], v['ra'] = v['pts'] + v['reb'] + v['ast'], v['pts'] + v['reb'], v['pts'] + v['ast'], v['reb'] + v['ast']
                v['stocks'] = v['stl'] + v['blk']
                minutes = d['minutes'][:, index, cols].sum(axis=1)
                v['min'] = np.rint(minutes)
                arrays.append(v)
                exact_minutes.append(minutes)
            target = player['periods'][period]
            close(target['sec'], 60 * sum(float(a.sum()) * w for a, w in zip(exact_minutes, units, strict=True)) / mass,
                  f'{player_id} {period} seconds')
            means += 1
            for stat in (*projection.BOX, 'reb'):
                close(target['mean'][stat], sum(float(v[stat].sum()) * w for v, w in zip(arrays, units, strict=True)) / mass,
                      f'{player_id} {period} {stat} mean')
                means += 1
            for stat in (projection.FG_DIST if period == 'fg' else projection.PERIOD_DIST):
                audit_distribution(target['stats'][stat], [v[stat] for v in arrays], units, f'{player_id} {period} {stat}')
                distributions += 1
            for stat, (made, attempted) in projection.SHOOTING_PAIRS.items():
                values = [np.floor(np.divide(100.0 * v[made], v[attempted], out=np.full(len(v[made]), np.nan),
                                              where=v[attempted] > 0) + 0.5) for v in arrays]
                audit_distribution(target['stats'].get(stat), values, units, f'{player_id} {period} {stat}')
                distributions += 1
            if period == 'fg':
                categories = ('pts', 'reb', 'ast', 'stl', 'blk')
                tens = [sum(v[key] >= 10 for key in categories) for v in arrays]
                for key, threshold in (('double_double', 2), ('triple_double', 3),
                                       ('quadruple_double', 4), ('quintuple_double', 5)):
                    expected = sum(int((a >= threshold).sum()) * w for a, w in zip(tens, units, strict=True)) / mass
                    close(player[key], expected, f'{player_id} {key}')
                    means += 1
                expected = sum(int(np.logical_and.reduce([v[key] >= 5 for key in categories]).sum()) * w
                               for v, w in zip(arrays, units, strict=True)) / mass
                close(player['five_by_five'], expected, f'{player_id} five-by-five')
                means += 1
                played = [a > 0 for a in exact_minutes]
                played_mass = sum(int(a.sum()) * w for a, w in zip(played, units, strict=True))
                if 0 < played_mass < mass:
                    conditional = {'min': exact_minutes, **{k: [v[k] for v in arrays] for k in ('pts', 'reb', 'ast', 'fg3m')}}
                    for stat, values in conditional.items():
                        expected = sum(float(a[m].sum()) * w for a, m, w in zip(values, played, units, strict=True)) / played_mass
                        close(player['if_plays'][stat], expected, f'{player_id} if-plays {stat}')
                        means += 1
                elif 'if_plays' in player:
                    raise ValueError(f'{player_id}: unexpected if-plays values')
    for period in projection.PERIODS:
        for team in ('home', 'away'):
            for stat in (*projection.BOX, 'reb'):
                expected = sum(p['periods'][period]['mean'][stat] for p in out[team]['players'])
                close(out[team]['box'][period][stat], expected, f'{team} {period} {stat}')
                means += 1
    write_json(args.output, {'kind': 'independent research summary accounting; not a forecast or browser test',
                             'probe': str(args.probe), 'probe_sha256': sha256_file(args.probe),
                             'summary_sha256': sha256_file(summary_path), 'audit_sha256': sha256_file(Path(__file__)),
                             'choices': result['choices'], 'selected_worlds': out['selected_worlds'],
                             'selected_mass': mass, 'distributions_checked': distributions, 'means_checked': means}, pretty=True)
    print(f"{out['selected_worlds']} worlds: {distributions} distributions and {means} means reconciled")


if __name__ == '__main__':
    main()
