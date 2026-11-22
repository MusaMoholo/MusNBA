"""Synthetic-only player form draw mechanics; not connected to the engine."""
from __future__ import annotations

import numpy as np

from scripts import projection

FACTORS = ('talent', 'form')


def player_effects(game_id: str, player_ids: list[str], worlds: int, seed: int,
                   strengths: np.ndarray, factor: str) -> np.ndarray:
    if not isinstance(game_id, str) or not game_id.isascii() or not game_id.isdigit():
        raise ValueError('game ID must contain ASCII digits')
    if (not player_ids or any(not isinstance(player, str) or not player.isascii() or not player.isdigit()
                              for player in player_ids) or len(set(player_ids)) != len(player_ids)):
        raise ValueError('player IDs must be unique nonempty ASCII digit strings')
    if not isinstance(worlds, int) or isinstance(worlds, bool) or worlds < 1:
        raise ValueError('world count must be a positive integer')
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise ValueError('seed must be a non-negative integer')
    if factor not in FACTORS:
        raise ValueError('unsupported research factor')
    strengths = np.asarray(strengths, dtype=float)
    if (strengths.shape != (len(player_ids),) or not np.isfinite(strengths).all()
            or ((strengths < 0) | (strengths > 1)).any()):
        raise ValueError('player strengths must be finite values between zero and one')
    result = np.zeros((worlds, len(player_ids)), dtype=float)
    for index, player in enumerate(player_ids):
        if strengths[index] == 0:
            continue
        rng = projection.rng_for('a2-synthetic-form-v1', seed, game_id, player, factor)
        result[:, index] = strengths[index] * (2 * rng.random(worlds) - 1)
    return result


def probability_tilt(probability: np.ndarray, effect: np.ndarray) -> np.ndarray:
    probability = np.asarray(probability, dtype=float)
    effect = np.asarray(effect, dtype=float)
    if (probability.shape != effect.shape or not np.isfinite(probability).all()
            or not np.isfinite(effect).all() or ((probability < 0) | (probability > 1)).any()
            or ((effect < -1) | (effect > 1)).any()):
        raise ValueError('probabilities and effects must have matching shapes and valid finite ranges')
    result = probability + effect * probability * (1 - probability)
    if ((result < 0) | (result > 1)).any():
        raise ValueError('probability tilt produced an invalid outcome probability')
    return result
