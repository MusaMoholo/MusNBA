#!/usr/bin/env python3
"""Isolated D29 candidate that trains minute states only on canonical NBA-team games."""
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
from scripts import a1_compare, minutes  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS  # noqa: E402


def nba_history(pg: pd.DataFrame, team_ids: set[str]) -> pd.DataFrame:
    if len(team_ids) != 30 or pg[['game_id', 'date_et', 'team', 'player']].isna().any().any():
        raise ValueError('canonical NBA team IDs or minutes-history keys are missing')
    clean = pg.loc[pg['team'].isin(team_ids)].copy()
    if clean.empty:
        raise ValueError('NBA-only minutes history is empty')
    if clean.duplicated(['date_et', 'player']).any():
        raise ValueError('NBA-only minutes history has multiple player games on one date')
    team_games = clean[['date_et', 'game_id', 'team']].drop_duplicates()
    if team_games.duplicated(['date_et', 'team']).any():
        raise ValueError('NBA-only minutes history has multiple team games on one date')
    if not team_games.groupby('game_id')['team'].nunique().eq(2).all():
        raise ValueError('NBA-only minutes history has a game without exactly two NBA teams')
    return clean


def build(before: str, params: dict | None = None, include_current: bool = True, upto: str | None = None) -> dict:
    """Same D29 state/ramp/spread algorithm with the candidate's explicitly restricted history."""
    pg = nba_history(minutes.player_games(include_current), set(json.loads((DERIVED / 'teams.json').read_text())))
    rows0, _, _ = minutes.state_pass(pg, params, None, upto)
    ramp = minutes.learn_ramp(pg, rows0, before)
    rows, latest, team_dates = minutes.state_pass(pg, params, ramp, upto, minutes.coach_dnps(include_current))
    sd = minutes.residual_sd(pg, rows, before)
    return {'pg': pg, 'rows': rows, 'latest': latest, 'team_dates': team_dates, 'ramp': ramp, 'sd': sd,
            'params': {**minutes.MINUTES, **(params or {})}}


def legal_minutes(values: np.ndarray, total: float = 240.0) -> np.ndarray:
    """Conserve team minutes with a hard 48-minute regulation limit, including five-player rosters."""
    data = np.asarray(values, dtype=float)
    if data.ndim not in (1, 2) or not np.isfinite(data).all() or (data < 0).any():
        raise ValueError('minute allocations must be finite non-negative vectors or matrices')
    if not np.isfinite(total) or total <= 0 or data.shape[-1] * 48 < total:
        raise ValueError('the available players cannot cover the required regulation minutes')
    rows = np.atleast_2d(data).copy()
    rows = np.minimum(rows, 48.0)
    sums = rows.sum(axis=1)
    over = sums > total
    rows[over] *= (total / sums[over])[:, None]
    deficit = total - rows.sum(axis=1)
    room = 48.0 - rows
    room_sum = room.sum(axis=1)
    needs_fill = deficit > 0
    if (room_sum[needs_fill] <= 0).any():
        raise ValueError('no legal player headroom remains for unallocated minutes')
    rows[needs_fill] += (deficit[needs_fill] / room_sum[needs_fill])[:, None] * room[needs_fill]
    rows = np.minimum(rows, 48.0)
    if (rows < 0).any() or (rows > 48).any() or not np.allclose(rows.sum(axis=1), total, rtol=0, atol=1e-10):
        raise ValueError('minute conservation or player limits failed')
    return rows[0] if data.ndim == 1 else rows


def allocate(h, cap, priority, total: float = 240.0, gamma: float = 1.0, room: float = 0.0) -> np.ndarray:
    arrays = [np.asarray(value, dtype=float) for value in (h, cap, priority)]
    if (any(array.ndim != 1 for array in arrays) or
            len({len(array) for array in arrays}) != 1 or
            any(not np.isfinite(array).all() for array in arrays) or
            (arrays[0] < 0).any() or (arrays[1] < 0).any()):
        raise ValueError('minute targets, caps and priorities must be aligned, finite vectors')
    if not np.isfinite(total) or total <= 0:
        raise ValueError('regulation minute total must be positive and finite')
    if len(arrays[0]) * 48 < total:
        raise ValueError('fewer than five available players cannot cover regulation')
    return legal_minutes(minutes.allocate(arrays[0], arrays[1], arrays[2], total=total, gamma=gamma, room=room), total)


def redraw(mu, cap, sd, worlds: int, rng: np.random.Generator, total: float = 240.0) -> np.ndarray:
    arrays = [np.asarray(value, dtype=float) for value in (mu, cap, sd)]
    if (any(array.ndim != 1 for array in arrays) or
            len({len(array) for array in arrays}) != 1 or
            any(not np.isfinite(array).all() or (array < 0).any() for array in arrays) or worlds < 1):
        raise ValueError('minute draws require aligned, finite, non-negative inputs and positive worlds')
    if arrays[0].sum() <= 0:
        raise ValueError('minute draws require a positive target total')
    if not np.isfinite(total) or total <= 0:
        raise ValueError('regulation minute total must be positive and finite')
    if len(arrays[0]) * 48 < total:
        raise ValueError('fewer than five available players cannot cover regulation')
    return legal_minutes(minutes.redraw(arrays[0], arrays[1], arrays[2], worlds, rng, total=total), total)


def game_targets(states: list[dict], params: dict | None = None) -> np.ndarray:
    settings = {**minutes.MINUTES, **(params or {})}
    h = np.array([s['healthy'] * s['ramp'] * s.get('rotation', 1.0) for s in states])
    cap = np.array([s['cap'] for s in states])
    priority = np.array([s['priority'] for s in states])
    return allocate(h, cap, priority, settings['total'], settings['gamma'], settings['room'])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit-f4', action='store_true', required=True,
                        help='compare candidate states with the independently built fixed-panel diagnostic')
    parser.add_argument('--output', type=Path, default=EXPERIMENTS / '20261122_a1_s05_nba_candidate_wiring.json')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f'refusing to overwrite {args.output}')
    diagnostic_report = EXPERIMENTS / '20261122_a1_s05_minutes_diagnostic.json'
    diagnostic_rows = DERIVED / 'experiments' / '20261122_a1_s05_minutes_diagnostic.parquet'
    previous = json.loads(diagnostic_report.read_text())
    for path, digest in previous['input_sha256'].items():
        if sha256_file(ROOT / path) != digest:
            raise ValueError(f'previous diagnostic input changed: {path}')
    expected = pd.read_parquet(diagnostic_rows)
    candidate = build(FOLDS['F4'][1], include_current=False)
    states = candidate['rows'].loc[candidate['rows']['game_id'].isin(expected['game_id'].unique())]
    matched = expected[['game_id', 'player', 'healthy_clean', 'alloc_clean', 'missed_clean', 'k_back_clean']].merge(
        states[['game_id', 'player', 'healthy', 'alloc', 'missed', 'k_back']],
        on=['game_id', 'player'], validate='one_to_one')
    a1_compare._same_keys(expected, matched, ['game_id', 'player'], 'NBA-only candidate wiring')
    differences = {}
    for name in ('healthy', 'alloc', 'missed', 'k_back'):
        left = matched[f'{name}_clean'].to_numpy(dtype=float)
        right = matched[name].to_numpy(dtype=float)
        if not np.isfinite(left).all() or not np.isfinite(right).all():
            raise ValueError(f'candidate or independent {name} has missing values')
        differences[name] = float(np.max(np.abs(left - right)))
        if differences[name] > 1e-12:
            raise ValueError(f'candidate {name} does not match the independent diagnostic')
    paths = [diagnostic_report, diagnostic_rows, ROOT / 'scripts/minutes.py', Path(__file__), DERIVED / 'teams.json']
    report = {
        'experiment': 'a1_s05_nba_only_candidate_wiring',
        'method': 'Run the isolated NBA-only D29 build with the same F4 fitting cutoff and compare each saved '
                  'conditional player state with the independently constructed target-screen variant.',
        'cutoff': FOLDS['F4'][1], 'games': int(matched['game_id'].nunique()), 'player_games': len(matched),
        'maximum_absolute_differences': differences,
        'limitations': 'Candidate only; these state checks do not score player or team engine predictions.',
        'input_sha256': {str(p.relative_to(ROOT)): sha256_file(p) for p in paths},
    }
    write_json(args.output, report, pretty=True)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
