"""Versioned player-world minute storage and legacy decoding."""

import base64

import numpy as np


MINUTES_SCHEMA = 1


def read_player_worlds(archive, game_id: str) -> dict:
    """Read the original integer lines and, when present, exact period minutes."""
    prefix = f'{game_id}__'
    result = {key: archive[prefix + key] for key in ('ids', 'side', 'lines')}
    if prefix + 'weights' in archive:
        from scripts.world_mass import WorldMass
        weights = archive[prefix + 'weights']
        WorldMass(len(result['lines']), weights)
        result['weights'] = weights
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


def packed_bytes(values: np.ndarray) -> str:
    values = np.asarray(values)
    if (not np.isfinite(values).all() or (values < 0).any() or (values > 255).any()
            or not np.equal(values, np.floor(values)).all()):
        raise ValueError('browser fixture values must be whole bytes without clipping')
    return base64.b64encode(np.ascontiguousarray(values, dtype=np.uint8).tobytes()).decode('ascii')

def opening_lineups(data: dict[str, np.ndarray], worlds: int, side: np.ndarray,
                    available: np.ndarray) -> np.ndarray:
    if 'opening_lineups' in data:
        lineup = np.asarray(data['opening_lineups'])
        if (lineup.shape != (worlds, 2, 5) or lineup.dtype.kind not in 'iu' or (lineup < 0).any() or (lineup >= len(side)).any()
                or (np.diff(np.sort(lineup, axis=2), axis=2) == 0).any()
                or not np.equal(side[lineup], np.arange(2)[None, :, None]).all()
                or not available[np.arange(worlds)[:, None, None], lineup].all()):
            raise ValueError('invalid stored opening lineups')
        return lineup
    trace_world = np.asarray(data['trace_world'])
    if trace_world.ndim != 1 or not np.isin(trace_world, np.arange(worlds)).all():
        raise ValueError('invalid trace-world identifiers')
    ids, first = np.unique(trace_world, return_index=True)
    if not np.array_equal(ids, np.arange(worlds)):
        raise ValueError('every world requires an opening lineup')
    lineup = np.asarray(data['trace_lineups'])[first]
    if (lineup.shape != (worlds, 2, 5)
            or not np.equal(np.asarray(data['trace_period'])[first], 1).all()
            or not np.equal(np.asarray(data['trace_clock'])[first], 720).all()
            or not np.equal(np.asarray(data['trace_phase'])[first], 0).all()
            or (lineup < 0).any() or (lineup >= len(side)).any()):
        raise ValueError('invalid opening trace')
    if (np.any(np.diff(np.sort(lineup, axis=2), axis=2) == 0)
            or not np.equal(side[lineup], np.arange(2)[None, :, None]).all()
            or not available[np.arange(worlds)[:, None, None], lineup].all()):
        raise ValueError('opening lineups must contain five distinct available teammates per side')
    return lineup

def pack_capture(data: dict[str, np.ndarray]) -> dict:
    from scripts import views
    ids, side = np.asarray(data['player_ids']), np.asarray(data['side'])
    available, minutes = np.asarray(data['available']), np.asarray(data['minutes'])
    periods = np.asarray(data['team_points'])
    final_period = np.asarray(data['final_period'])
    if available.ndim != 2 or available.dtype != bool:
        raise ValueError('availability must be a world-by-player boolean array')
    worlds, players = available.shape
    if (not worlds or not players or ids.shape != (players,) or side.shape != (players,)
            or len(set(map(str, ids))) != players or not np.isin(side, (0, 1)).all()
            or minutes.shape != (worlds, players, 5) or periods.shape != (worlds, 2, 5)
            or final_period.shape != (worlds,) or (final_period < 4).any()):
        raise ValueError('capture roster or world dimensions are invalid')
    box = {}
    period_box = {}
    for stat in ('pts', 'oreb', 'dreb', 'ast', 'fg3m', 'stl', 'blk', 'tov', 'fgm', 'fga', 'fg3a', 'fta', 'ftm'):
        values = np.asarray(data[f'box_{stat}'])
        if values.shape != minutes.shape or not np.isfinite(values).all() or (values < 0).any():
            raise ValueError(f'capture {stat} has invalid dimensions or values')
        period_box[stat] = values
        box[stat] = values.sum(axis=2)
    exact_minutes = minutes.sum(axis=2)
    lines = {'min': np.rint(exact_minutes), **box}
    lines['reb'] = lines['oreb'] + lines['dreb']
    period_box['reb'] = period_box['oreb'] + period_box['dreb']
    if (not np.isfinite(minutes).all() or (minutes < 0).any()
            or (minutes[~available] != 0).any()
            or any((values[~available] != 0).any() for values in box.values())):
        raise ValueError('unavailable players or invalid minutes in capture')
    if np.any((final_period == 4) & (periods[:, :, 4].sum(axis=1) != 0)):
        raise ValueError('overtime scores without an overtime period')
    opening = opening_lineups(data, worlds, side, available)
    for team in (0, 1):
        if not np.array_equal(period_box['pts'][:, side == team].sum(axis=1), periods[:, team]):
            raise ValueError('player and team scores do not reconcile')
    return {
        'worlds': worlds, 'stats': list(views.WORLD_STATS), 'players': list(map(str, ids)),
        'side': side.astype(int).tolist(),
        'lines': packed_bytes(np.stack([lines[stat] for stat in views.WORLD_STATS], axis=2)),
        'team_periods': packed_bytes(periods),
        'availability': packed_bytes(available),
        'played': packed_bytes(exact_minutes > 0),
        'minutes_f64_le': base64.b64encode(np.ascontiguousarray(exact_minutes, dtype='<f8').tobytes()).decode('ascii'),
        'period_stats': list(views.WORLD_STATS[1:]),
        'period_lines': packed_bytes(np.stack([period_box[stat] for stat in views.WORLD_STATS[1:]], axis=3)),
        'period_minutes_f64_le': base64.b64encode(np.ascontiguousarray(minutes, dtype='<f8').tobytes()).decode('ascii'),
        'final_period': packed_bytes(final_period),
        'opening_lineups': packed_bytes(opening),
        'periods': ['q1', 'q2', 'q3', 'q4', 'ot'],
    }
