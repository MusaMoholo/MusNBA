"""Offline exact weighted minute CDFs for Expected-only device payloads."""
import base64

import numpy as np

from scripts.projection import SLICES
from scripts.world_mass import WorldMass


def encode(minutes, players, weights):
    minutes = np.asarray(minutes)
    players = list(players)
    if (minutes.ndim != 3 or minutes.shape[1:] != (len(players), 5) or not len(set(players)) == len(players)
            or any(not isinstance(p, str) for p in players) or not players
            or minutes.dtype.kind != 'f' or minutes.dtype.itemsize != 8 or not np.isfinite(minutes).all() or (minutes < 0).any()):
        raise ValueError('precise minute arrays and unique player IDs required')
    mass = WorldMass(int(minutes.shape[0]), weights)
    offsets, support, cumulative = [0], [], []
    values = [minutes[:, :, cols].sum(2) for cols in SLICES.values()]
    for i in range(len(players)):
        for period in values:
            x, inverse = np.unique(period[:, i], return_inverse=True)
            counts = np.zeros(len(x), np.int64)
            np.add.at(counts, inverse, 1 if mass.weights is None else mass.weights)
            cdf = np.cumsum(counts)
            if int(cdf[-1]) != mass.total or (counts <= 0).any():
                raise ValueError('minute CDF mass differs')
            offsets.append(offsets[-1] + len(x))
            support.append(x)
            cumulative.append(cdf)
    pack = lambda parts: base64.b64encode(np.ascontiguousarray(np.concatenate(parts), dtype='<f8').tobytes()).decode()
    return {'schema': 2, 'worlds': mass.worlds, 'probability_mass': mass.total, 'players': list(players),
            'periods': list(SLICES), 'offsets': offsets, 'minutes_f64_le': pack(support),
            'cumulative_f64_le': pack(cumulative)}
