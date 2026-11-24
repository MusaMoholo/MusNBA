"""Versioned NBA-style regions derived from retained, rounded ESPN coordinates.

These are derived labels, not native annotations or tracking positions. Shot value
stays authoritative; missing/conflicting geometry retains an explicit unknown bin.
"""
import numpy as np

SCHEMA = 'nba-derived-zones-v1'
CELLS = [
    ('Restricted Area', 'Center(C)', 'Less Than 8 ft.'),
    ('In The Paint (Non-RA)', 'Center(C)', 'Less Than 8 ft.'),
    ('In The Paint (Non-RA)', 'Left Side(L)', '8-16 ft.'),
    ('In The Paint (Non-RA)', 'Center(C)', '8-16 ft.'),
    ('In The Paint (Non-RA)', 'Right Side(R)', '8-16 ft.'),
    ('Mid-Range', 'Left Side(L)', '8-16 ft.'),
    ('Mid-Range', 'Center(C)', '8-16 ft.'),
    ('Mid-Range', 'Right Side(R)', '8-16 ft.'),
    ('Mid-Range', 'Left Side(L)', '16-24 ft.'),
    ('Mid-Range', 'Left Side Center(LC)', '16-24 ft.'),
    ('Mid-Range', 'Center(C)', '16-24 ft.'),
    ('Mid-Range', 'Right Side Center(RC)', '16-24 ft.'),
    ('Mid-Range', 'Right Side(R)', '16-24 ft.'),
    ('Left Corner 3', 'Left Side(L)', '24+ ft.'),
    ('Right Corner 3', 'Right Side(R)', '24+ ft.'),
    ('Above the Break 3', 'Left Side Center(LC)', '24+ ft.'),
    ('Above the Break 3', 'Center(C)', '24+ ft.'),
    ('Above the Break 3', 'Right Side Center(RC)', '24+ ft.'),
    ('Above the Break 3', 'Back Court(BC)', 'Back Court Shot'),
    ('Backcourt', 'Back Court(BC)', 'Back Court Shot'),
    ('Unknown two-point geometry', 'Unknown', 'Unknown'),
    ('Unknown three-point geometry', 'Unknown', 'Unknown'),
]
VALUES = np.array([2] * 13 + [3] * 7 + [2, 3])
UNKNOWN_TWO, UNKNOWN_THREE = 20, 21
# Physical court dimensions; 1ft coordinate quantisation can move radius by sqrt(.5).
PAINT_Y, CORNER_Y, HALF_Y = 13.75, np.sqrt(23.75**2 - 22**2), 41.75
ROUNDING_RADIUS = np.sqrt(.5)


def derive(x, y, value):
    x, y, value = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float), np.asarray(value))
    dx, r = x - 25, np.hypot(x - 25, y)
    angle = np.degrees(np.arctan2(dx, y))
    valid = np.isfinite(x) & np.isfinite(y) & (x >= 0) & (x <= 50) & (y >= -5.25) & (y <= 88.75)
    result = np.where(value == 3, UNKNOWN_THREE, UNKNOWN_TWO).astype(np.int16)
    two = valid & (value == 2) & (r <= 23.75 + ROUNDING_RADIUS)
    rim = two & (r <= 4)
    result[rim] = 0
    paint = two & ~rim & (np.abs(dx) <= 8) & (y <= PAINT_Y)
    result[paint & (r < 8)] = 1
    side3 = np.where(angle < -30, 0, np.where(angle > 30, 2, 1))
    result[paint & (r >= 8)] = (2 + side3[paint & (r >= 8)])
    mid = two & ~rim & ~paint
    result[mid & (r < 16)] = 5 + side3[mid & (r < 16)]
    side5 = np.digitize(angle, [-54, -18, 18, 54])
    result[mid & (r >= 16)] = 8 + side5[mid & (r >= 16)]
    three = valid & (value == 3) & (r >= 22 - ROUNDING_RADIUS)
    corner = three & (np.abs(dx) >= 22) & (y <= CORNER_Y)
    result[corner] = np.where(dx[corner] < 0, 13, 14)
    above = three & ~corner
    result[above] = np.where(angle[above] < -18, 15, np.where(angle[above] > 18, 17, 16))
    # Native charts distinguish long frontcourt attempts from backcourt attempts.
    result[above & (r >= 40)] = np.where(y[above & (r >= 40)] > HALF_Y, 19, 18)
    result[~np.isin(value, [2, 3])] = -1
    return result


def native_codes(basic, area, distance_range):
    codes = {cell: i for i, cell in enumerate(CELLS[:20])}
    return np.array([codes.get(tuple(v), -1) for v in zip(basic, area, distance_range)], np.int16)


def legacy_codes(x, y, value):
    x, y, value = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float), np.asarray(value))
    dx = np.abs(x - 25)
    codes = np.where(value == 3, np.where((dx >= 21.8) & (y <= 14), 3, 4),
                     np.where(np.hypot(dx, y) <= 4, 0, np.where((dx <= 8) & (y <= 19), 1, 2)))
    return np.where(np.isfinite(x) & np.isfinite(y) & np.isin(value, [2, 3]), codes, -1).astype(np.int16)


def layout(within_distance=False):
    """Fixed geometric support, independent of fitted data or validation outcomes."""
    from scripts import nodes
    xx, yy = np.meshgrid(np.arange(0, 50.001, .25), np.arange(-5.25, 88.751, .25))
    x, y = np.tile(xx.ravel(), 2), np.tile(yy.ravel(), 2)
    values = np.repeat([2, 3], xx.size)
    coarse, cell = legacy_codes(x, y, values), derive(x, y, values)
    band = nodes.location_band(np.array(nodes.ZONES, object)[coarse], np.hypot(x - 25, y))
    parent = band if within_distance else coarse
    pairs = sorted(set(zip(parent.tolist(), cell.tolist())))
    return {'schema': SCHEMA, 'within_distance': bool(within_distance), 'pairs': [list(v) for v in pairs],
            'legacy_zones': list(nodes.ZONES), 'cells': [list(v) for v in CELLS]}


def encode(spec, x, y, value):
    from scripts import nodes
    coarse, cell = legacy_codes(x, y, value), derive(x, y, value)
    parent = nodes.location_band(np.array(nodes.ZONES, object)[coarse], np.hypot(np.asarray(x) - 25, y)) if spec['within_distance'] else coarse
    lookup = {tuple(v): i for i, v in enumerate(spec['pairs'])}
    codes = np.array([lookup.get((int(p), int(c)), -1) for p, c in zip(parent, cell)], np.int32)
    return codes


def decoder(spec):
    from scripts import nodes
    legacy_band_zone = np.array([i for i, z in enumerate(nodes.ZONES) for _ in range(len(nodes.LOCATION_EDGES[z]) + 1)])
    parents = np.array([p for p, c in spec['pairs']], int)
    coarse = legacy_band_zone[parents] if spec['within_distance'] else parents
    cells = np.array([c for p, c in spec['pairs']], int)
    mask = np.arange(5)[:, None] == coarse[None, :]
    return coarse, cells, mask
