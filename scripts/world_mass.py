"""Exact integer probability masses for stored empirical mixtures (distinct from world counts)."""
from __future__ import annotations

from fractions import Fraction
from math import lcm

import numpy as np


def branch_masses(counts, probabilities):
    if (not counts or len(counts) != len(probabilities) or any(not isinstance(n, int) or isinstance(n, bool) or n < 1 for n in counts)
            or any(not isinstance(p, Fraction) or p <= 0 for p in probabilities) or sum(probabilities, Fraction()) != 1):
        raise ValueError('positive world counts and exact unit-sum branch probabilities required')
    denominator = lcm(*[(p / n).denominator for n, p in zip(counts, probabilities)])
    if denominator > 2**53 - 1:
        raise ValueError('probability masses exceed the browser exact-integer limit')
    return np.concatenate([np.full(n, int(p * denominator / n), np.int64) for n, p in zip(counts, probabilities)])


class WorldMass:
    def __init__(self, worlds, weights=None):
        if not isinstance(worlds, int) or isinstance(worlds, bool) or worlds < 1:
            raise ValueError('positive world count required')
        self.worlds = worlds
        self.weights = None
        if weights is not None:
            a = np.asarray(weights)
            if a.shape != (worlds,) or a.dtype.kind not in 'iu' or (a <= 0).any():
                raise ValueError('world masses must be positive integers matching worlds')
            total = sum(map(int, a))
            if total > 2**53 - 1:
                raise ValueError('probability masses exceed the browser exact-integer limit')
            self.weights = a.astype(np.int64, copy=True)
            self.weights.flags.writeable = False
        self.total = worlds if self.weights is None else total

    def mean(self, values):
        a = np.asarray(values)
        if not a.ndim or a.shape[0] != self.worlds or not np.isfinite(a).all():
            raise ValueError('finite values must match worlds')
        return a.mean(axis=0) if self.weights is None else np.tensordot(self.weights / self.total, a, axes=(0, 0))

    def counts(self, values, offset=False):
        a = np.asarray(values)
        if a.shape != (self.worlds,) or not np.isfinite(a).all() or (a != np.floor(a)).any():
            raise ValueError('one integer outcome per world required')
        a = a.astype(np.int64)
        lo = int(a.min()) if offset else 0
        if (a < lo).any():
            raise ValueError('negative outcomes need an offset histogram')
        result = np.zeros(int(a.max()) - lo + 1, np.int64)
        np.add.at(result, a - lo, 1 if self.weights is None else self.weights)
        if int(result.sum()) != self.total:
            raise ValueError('histogram probability mass does not reconcile')
        return lo, result

    def summary(self, values, offset=False):
        if self.weights is None:
            from scripts.projection import summary
            return summary(values, offset=offset)
        lo, counts = self.counts(values, offset)
        mu = float(self.mean(values))
        cumulative = np.cumsum(counts)
        quantiles = [int(np.searchsorted(cumulative * d, n * self.total, side='left')) + lo
                     for n, d in ((1, 10), (1, 4), (1, 2), (3, 4), (9, 10))]
        return {'mean': round(mu, 3), 'sd': round(float(np.sqrt(self.mean((np.asarray(values, float) - mu)**2))), 3),
                'q': quantiles, 'min': lo, 'hist': counts.tolist()}

    def subset(self, mask):
        a = np.asarray(mask)
        if a.shape != (self.worlds,) or a.dtype != bool or not a.any():
            raise ValueError('nonempty matching boolean subset required')
        return WorldMass(int(a.sum()), None if self.weights is None else self.weights[a])
