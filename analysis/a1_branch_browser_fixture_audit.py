#!/usr/bin/env python3
"""Independently decode and reconcile an isolated branch browser fixture."""
from __future__ import annotations

import argparse
import base64
import json
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import sha256_file, write_json  # noqa: E402

STATS = ('min', 'pts', 'reb', 'ast', 'fg3m', 'stl', 'blk', 'tov', 'fgm', 'fga', 'fg3a', 'fta', 'oreb', 'dreb', 'ftm')


def decode(value: str, shape: tuple[int, ...]) -> np.ndarray:
    return np.frombuffer(base64.b64decode(value, validate=True), dtype=np.uint8).reshape(shape)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fixture', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an existing audit')
    fixture = json.loads(args.fixture.read_text())
    source = Path(fixture['source'])
    if sha256_file(source) != fixture['source_sha256']:
        raise ValueError('branch manifest hash differs')
    report = json.loads(source.read_text())
    if (fixture['game'] != report['game'] or fixture['origin'] != report['origin']
            or fixture['selected_players'] != report['selected']
            or fixture['weight_assumptions'] != report['weight_assumptions']
            or len(fixture['branches']) != len(report['branches'])):
        raise ValueError('fixture metadata differs from branch manifest')
    if any(key in fixture for key in ('engine', 'model', 'snapshot_inputs')):
        snapshot_paths = [f"data/snapshots/{report['origin']}/{name}.json" for name in ('meta', 'games')]
        if (fixture.get('engine') != report['engine'] or fixture.get('model') != report['model']
                or fixture.get('snapshot_inputs') != {path: report['input_sha256'][path] for path in snapshot_paths}):
            raise ValueError('fixture model or snapshot provenance differs')
        for path in snapshot_paths:
            if sha256_file(ROOT / path) != fixture['snapshot_inputs'][path]:
                raise ValueError('snapshot file hash differs')
        snapshot_game = json.loads((ROOT / snapshot_paths[1]).read_text())[report['game']]
        source_players = {}
        for side, name in enumerate(('home', 'away')):
            for player in snapshot_game[name]['players']:
                if player['id'] in source_players:
                    raise ValueError('snapshot player identity is duplicated')
                source_players[player['id']] = (side, player)
        roster = fixture['branches'][0]['worlds']
        fields = ('id', 'name', 'pos', 'jersey', 'status', 'injury', 'availability_basis')
        if (set(roster['players']) != set(source_players)
                or any(source_players[player][0] != side for player, side in zip(roster['players'], roster['side'], strict=True))
                or fixture.get('player_metadata') != [
                    {key: source_players[player][1].get(key) for key in fields} for player in roster['players']]):
            raise ValueError('fixture identity metadata differs from origin snapshot')
    total_weight = Fraction()
    worlds = line_values = availability_values = played_values = minute_values = period_values = 0
    player_period_values = player_period_minute_values = 0
    final_period_values = opening_lineup_values = 0
    opening_branch_starts: list[dict] = []
    overtime_mass: dict[int, Fraction] = {}
    slices = {'q1': [0], 'q2': [1], 'q3': [2], 'q4': [3], 'h1': [0, 1], 'h2': [2, 3], 'fg': [0, 1, 2, 3, 4]}
    selected_period_means = {key: {'minutes': 0.0, 'player_points': 0.0, 'home_points': 0.0} for key in slices}
    positive_rounded_to_zero = available_did_not_play = threshold_disagreements = 0
    selected_player = report['selected'][0]['player_id']
    for branch, original in zip(fixture['branches'], report['branches'], strict=True):
        if any(branch[key] != original[key] for key in ('branch_id', 'assignments', 'weight', 'capture_sha256')):
            raise ValueError('fixture branch metadata differs')
        weight = branch['weight']
        total_weight += Fraction(int(weight['numerator']), int(weight['denominator']))
        if sha256_file(Path(original['capture'])) != original['capture_sha256']:
            raise ValueError('source capture hash differs')
        packed = branch['worlds']
        if packed['stats'] != list(STATS) or packed['periods'] != ['q1', 'q2', 'q3', 'q4', 'ot']:
            raise ValueError('fixture columns differ from the browser contract')
        W, P = packed['worlds'], len(packed['players'])
        if W != original['worlds']:
            raise ValueError('fixture world count differs')
        lines = decode(packed['lines'], (W, P, len(STATS)))
        availability = decode(packed['availability'], (W, P))
        played = decode(packed['played'], (W, P))
        minutes = np.frombuffer(base64.b64decode(packed['minutes_f64_le'], validate=True), dtype='<f8').reshape(W, P)
        periods = decode(packed['team_periods'], (W, 2, 5))
        final_period = decode(packed['final_period'], (W,)) if 'final_period' in packed else None
        opening = decode(packed['opening_lineups'], (W, 2, 5)) if 'opening_lineups' in packed else None
        period_fields = ('period_stats', 'period_lines', 'period_minutes_f64_le')
        has_player_periods = any(key in packed for key in period_fields)
        if has_player_periods:
            if packed.get('period_stats') != list(STATS[1:]):
                raise ValueError('fixture player-period columns differ')
            player_periods = decode(packed['period_lines'], (W, P, 5, len(STATS) - 1))
            player_period_minutes = np.frombuffer(base64.b64decode(packed['period_minutes_f64_le'], validate=True),
                                                   dtype='<f8').reshape(W, P, 5)
        with np.load(original['capture'], allow_pickle=False) as data:
            if opening is not None:
                # First trace records are the opening lineups; verify against the trace, not the packer.
                trace_world = data['trace_world']
                first = np.full(W, -1, dtype=int)
                for position, world in enumerate(trace_world):
                    if first[world] == -1:
                        first[world] = position
                if ((first < 0).any() or not np.array_equal(opening, data['trace_lineups'][first])
                        or not np.all(data['trace_period'][first] == 1)
                        or not np.all(data['trace_clock'][first] == 720)
                        or not np.all(data['trace_phase'][first] == 0)):
                    raise ValueError('fixture opening lineups differ from first captured traces')
                counts = np.bincount(data['trace_lineups'][first].ravel(), minlength=P)
                opening_branch_starts.append({
                    'branch_id': branch['branch_id'], 'players': packed['players'],
                    'counts': counts.tolist(),
                })
            if (packed['players'] != data['player_ids'].tolist() or packed['side'] != data['side'].tolist()
                    or not np.array_equal(availability, data['available'])
                    or not np.array_equal(played, data['minutes'].sum(axis=2) > 0)
                    or not np.array_equal(minutes, data['minutes'].sum(axis=2))
                    or (has_player_periods and not np.array_equal(player_period_minutes, data['minutes']))
                    or (final_period is not None and not np.array_equal(final_period, data['final_period']))
                    or not np.array_equal(periods, data['team_points'])):
                raise ValueError('fixture roster, availability, playing time or team periods differ')
            positive_rounded_to_zero += int(((played == 1) & (lines[:, :, 0] == 0)).sum())
            available_did_not_play += int(((availability == 1) & (played == 0)).sum())
            player = packed['players'].index(selected_player)
            for value, count in zip(*np.unique(data['final_period'] - 4, return_counts=True), strict=True):
                overtime_mass[int(value)] = overtime_mass.get(int(value), Fraction()) + (
                    Fraction(int(weight['numerator']), int(weight['denominator'])) * int(count) / W)
            for name, indices in slices.items():
                selected_period_means[name]['minutes'] += float(weight['numerator']) / float(weight['denominator']) * float(data['minutes'][:, player, indices].sum(axis=1).mean())
                selected_period_means[name]['player_points'] += float(weight['numerator']) / float(weight['denominator']) * float(data['box_pts'][:, player, indices].sum(axis=1).mean())
                selected_period_means[name]['home_points'] += float(weight['numerator']) / float(weight['denominator']) * float(data['team_points'][:, 0, indices].sum(axis=1).mean())
            threshold_disagreements += int(((minutes[:, player] >= 30)
                                            != (lines[:, player, 0].astype(float) >= 30)).sum())
            for col, stat in enumerate(STATS):
                if stat == 'min':
                    expected = np.rint(data['minutes'].sum(axis=2))
                elif stat == 'reb':
                    expected = data['box_oreb'].sum(axis=2) + data['box_dreb'].sum(axis=2)
                else:
                    expected = data[f'box_{stat}'].sum(axis=2)
                if not np.array_equal(lines[:, :, col], expected):
                    raise ValueError(f'fixture {stat} differs from source capture')
                if has_player_periods and stat != 'min':
                    expected_periods = (data['box_oreb'] + data['box_dreb'] if stat == 'reb'
                                        else data[f'box_{stat}'])
                    if not np.array_equal(player_periods[:, :, :, col - 1], expected_periods):
                        raise ValueError(f'fixture {stat} periods differ from source capture')
        worlds += W
        line_values += lines.size
        availability_values += availability.size
        played_values += played.size
        minute_values += minutes.size
        period_values += periods.size
        if has_player_periods:
            player_period_values += player_periods.size
            player_period_minute_values += player_period_minutes.size
        if final_period is not None:
            final_period_values += final_period.size
        if opening is not None:
            opening_lineup_values += opening.size
    if total_weight != 1:
        raise ValueError('fixture branch weights do not total one')
    write_json(args.output, {
        'kind': 'independent research browser fixture accounting; not a forecast',
        'fixture': str(args.fixture), 'fixture_sha256': sha256_file(args.fixture),
        'fixture_bytes': args.fixture.stat().st_size, 'source': str(source),
        'source_sha256': sha256_file(source), 'audit_sha256': sha256_file(Path(__file__)),
        'branches': len(fixture['branches']), 'worlds': worlds, 'player_stat_values': line_values,
        'availability_values': availability_values, 'played_values': played_values,
        'exact_minute_values': minute_values, 'team_period_values': period_values,
        'player_period_stat_values': player_period_values,
        'player_period_exact_minute_values': player_period_minute_values,
        'final_period_values': final_period_values,
        'opening_lineup_values': opening_lineup_values,
        'opening_branch_starts_from_captures': opening_branch_starts,
        'overtime_period_mass_from_captures': {
            str(k): {'numerator': str(v.numerator), 'denominator': str(v.denominator)}
            for k, v in sorted(overtime_mass.items())
        },
        'positive_minutes_rounded_to_zero': positive_rounded_to_zero,
        'available_did_not_play': available_did_not_play,
        'threshold_player': selected_player, 'threshold_minutes': 30,
        'exact_vs_rounded_threshold_disagreements': threshold_disagreements,
        'exact_total_weight': str(total_weight),
        'selected_period_means_from_captures': selected_period_means,
    }, pretty=True)
    print(f'{worlds} worlds, {line_values} player-stat values, availability and scores reconciled')


if __name__ == '__main__':
    main()
