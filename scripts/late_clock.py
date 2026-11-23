"""Opt-in contextual late-clock sampler; not selected by the accepted engine yet."""
from __future__ import annotations

import numpy as np

from scripts.projection import seed_for


class ContextClock:
    def __init__(self, tables, support):
        self.pools = {}
        for kind, upper in (('bridge', 24.), ('contextual', 1.)):
            self.pools[kind] = {}
            for key, raw in tables[kind].items():
                key = int(key)
                x = np.sort(np.asarray(raw['x'], float))
                q = float(raw['quiet'])
                if x.ndim != 1 or not len(x) or not np.isfinite(x).all() or ((x < 0) | (x > upper)).any() or not 0 <= q <= 1:
                    raise ValueError('invalid contextual clock pool')
                count = int(round(q * len(x)))
                if abs(count - q * len(x)) > 1e-8 or (count and not np.equal(x[-count:], upper).all()):
                    raise ValueError('no-action mass must consume all remaining clock')
                if kind == 'contextual':
                    cell = support.get(str(key), support.get(key, {}))
                    if len(x) < 100 or cell.get('opportunities') != len(x) or cell.get('games', 0) < 30 or not cell.get('supported'):
                        raise ValueError('unsupported contextual clock cell')
                if not 0 <= key < (28 if kind == 'contextual' else 25):
                    raise ValueError('invalid contextual clock cell')
                quiet = np.zeros(len(x), bool)
                if count:
                    quiet[-count:] = True
                # No-action is possible only at the upper atom, so this recovers the full joint distribution.
                self.pools[kind][key] = (x, quiet)

    def begin(self, seed):
        self.rng = np.random.default_rng(seed_for('a2-context-clock-v1', seed))

    def sample(self, period, clock, margin, seconds, quiet):
        period, clock, margin = map(np.asarray, (period, clock, margin))
        if not (period.shape == clock.shape == margin.shape == np.shape(seconds) == np.shape(quiet)) or clock.ndim != 1:
            raise ValueError('contextual clock dimensions differ')
        result, no_action = np.array(seconds, dtype=float, copy=True), np.array(quiet, dtype=bool, copy=True)
        active = np.flatnonzero((period >= 4) & (clock > 0) & (clock <= 24) & np.isfinite(clock) & np.isfinite(margin))
        if not len(active):
            return result, no_action
        cells = np.searchsorted([4, 8, 16], clock[active], side='left') * 7 + np.searchsorted([-8, -3, 0, 1, 4, 9], margin[active], side='right')
        keys = {}
        for i, cell in zip(active, cells):
            kind, key = ('contextual', int(cell)) if int(cell) in self.pools['contextual'] else ('bridge', int(np.floor(clock[i])))
            if key in self.pools[kind]:
                keys.setdefault((kind, key), []).append(i)
        for (kind, key), rows in sorted(keys.items()):
            idx = np.asarray(rows, int)
            values, none = self.pools[kind][key]
            pick = self.rng.integers(len(values), size=len(idx))
            no_action[idx] = none[pick]
            drawn = values[pick] * clock[idx] if kind == 'contextual' else values[pick]
            result[idx] = np.where(no_action[idx], clock[idx], np.minimum(drawn, clock[idx]))
        return result, no_action
