#!/usr/bin/env python3
"""Opt-in clock and scheduled-lineup accounting for the matched engine control."""
from __future__ import annotations

import numpy as np
import pandas as pd


def scheduled_overlap(tables: np.ndarray, combo: np.ndarray, ids: list[str], profiles: dict,
                      stints: pd.DataFrame, team: str, side: int) -> dict:
    ticks = np.arange(5, 2880, 10)
    if tables.ndim != 3 or tables.shape[1:] != (2880, 5) or combo.ndim != 2 or combo.shape[1] != 2:
        raise ValueError('unexpected scheduled-rotation table shapes')
    if len(set(ids)) != len(ids) or not np.isin(combo, np.arange(len(tables))).all():
        raise ValueError('duplicate players or invalid scheduled-rotation indices')
    position = {str(player): i for i, player in enumerate(ids)}
    real = stints[(stints['team'] == team) & (stints['period'] <= 4)]
    if real.empty:
        raise ValueError(f'no retained regulation stints for team {team}')
    membership = np.zeros((len(ids), len(ticks)), dtype=np.int16)
    unknown = np.zeros(len(ticks), dtype=bool)
    unknown_stints = 0
    bounds = real[['start_t', 'end_t']].apply(pd.to_numeric, errors='raise').to_numpy(dtype=float)
    for (start, end), player_id in zip(bounds, real['player'].astype(str)):
        if not (np.isfinite(start) and np.isfinite(end) and start <= end):
            raise ValueError(f'{team}: invalid stint bounds')
        occupied = (ticks >= start) & (ticks < end)
        player = position.get(player_id)
        if player is None:
            unknown_stints += 1
            unknown |= occupied
        else:
            membership[player, occupied] += 1
    valid = (membership.sum(axis=0) == 5) & (membership.max(axis=0) <= 1) & ~unknown
    result = {'ticks': len(ticks), 'valid_ticks': int(valid.sum()), 'invalid_ticks': int((~valid).sum()),
              'unknown_player_stints': unknown_stints, 'scheduled_exact_five': None, 'scheduled_matching_slots': None}
    if not valid.any():
        return result
    actual = np.stack([np.flatnonzero(membership[:, i]) for i in np.flatnonzero(valid)])
    simulated = tables[combo[:, side, None], ticks[None, valid], :]
    if not ((simulated >= 0) & (simulated < len(ids))).all():
        raise ValueError('scheduled rotation refers to an unknown player index')
    matches = (simulated[:, :, :, None] == actual[None, :, None, :]).any(axis=3).sum(axis=2)
    result['scheduled_exact_five'] = float((matches == 5).mean())
    result['scheduled_matching_slots'] = float(matches.mean())
    for column in ('usage', 'fg_rim', 'd_fg_rim'):
        values = np.asarray(profiles[column], dtype=float)
        if values.shape != (len(ids),):
            raise ValueError(f'{column} does not cover the roster')
        actual_values, simulated_values = values[actual], values[simulated]
        actual_known = np.asarray(np.isfinite(actual_values).all(axis=1), dtype=bool).reshape(1, -1)
        simulated_known = np.asarray(np.isfinite(simulated_values).all(axis=2), dtype=bool)
        both = np.logical_and(actual_known, simulated_known)
        actual_means = np.broadcast_to(actual_values.mean(axis=1), both.shape)
        sim_means = simulated_values.mean(axis=2)
        result[f'{column}_known_world_ticks'] = int(both.sum())
        result[f'{column}_actual'] = float(actual_means[both].mean()) if both.any() else None
        result[f'{column}_scheduled'] = float(sim_means[both].mean()) if both.any() else None
    return result


def clock_summary(diag: list, seg: pd.DataFrame, worlds: int) -> dict:
    if worlds <= 0 or not diag:
        raise ValueError('clock diagnostics require simulated worlds and segments')
    seconds = np.concatenate([x[1] for x in diag])
    clock = np.concatenate([x[2] for x in diag])
    observed_seconds = pd.to_numeric(seg['duration'], errors='raise').to_numpy(dtype=float)
    observed_clock = pd.to_numeric(seg['start_clock'], errors='raise').to_numpy(dtype=float)
    valid = np.isfinite(observed_seconds) & np.isfinite(observed_clock)
    if not np.isfinite(seconds).all() or not np.isfinite(clock).all() or (seconds < 0).any():
        raise ValueError('simulated clock diagnostics contain invalid values')
    if (observed_seconds[valid] < 0).any() or not valid.any():
        raise ValueError('recorded segment durations are invalid or missing')
    return {'simulated_segments_per_world': len(seconds) / worlds,
            'recorded_segments': len(seg), 'recorded_clock_missing': int((~valid).sum()),
            'simulated_mean_duration': float(seconds.mean()),
            'recorded_mean_duration': float(observed_seconds[valid].mean()),
            'simulated_start_at_or_below_24s': float((clock <= 24).mean()),
            'recorded_start_at_or_below_24s': float((observed_clock[valid] <= 24).mean())}
