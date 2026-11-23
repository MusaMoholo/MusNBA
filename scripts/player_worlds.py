"""Versioned player-world minute storage and legacy decoding."""

import numpy as np


MINUTES_SCHEMA = 1


def read_player_worlds(archive, game_id: str) -> dict:
    """Read the original integer lines and, when present, exact period minutes."""
    prefix = f'{game_id}__'
    result = {key: archive[prefix + key] for key in ('ids', 'side', 'lines')}
    schema_key, minutes_key = prefix + 'minutes_schema', prefix + 'minutes'
    if schema_key not in archive and minutes_key not in archive:
        return result
    if schema_key not in archive or minutes_key not in archive:
        raise ValueError(f'{game_id}: incomplete precise minute worlds')
    schema, minutes = archive[schema_key], archive[minutes_key]
    lines, ids = result['lines'], result['ids']
    if (schema.shape != () or schema.dtype.kind not in 'iu' or int(schema) != MINUTES_SCHEMA
            or lines.ndim != 3 or lines.shape[2] < 1 or ids.ndim != 1
            or minutes.shape != (lines.shape[0], len(ids), 5) or lines.shape[1] != len(ids)
            or minutes.dtype.kind != 'f' or minutes.dtype.itemsize != 8
            or not np.isfinite(minutes).all() or (minutes < 0).any()
            or not np.array_equal(np.clip(np.rint(minutes.sum(axis=2)), 0, 255), lines[:, :, 0])):
        raise ValueError(f'{game_id}: invalid precise minute worlds or unsupported schema')
    result.update(minutes_schema=schema, minutes=minutes)
    return result
