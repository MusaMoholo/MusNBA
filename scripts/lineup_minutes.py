"""Offline exact weighted minute CDFs for Expected-only device payloads."""
import base64
from pathlib import Path
import re

import numpy as np

from basketball_common import write_json
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
    def pack(parts):
        # Reorder bytes losslessly so gzip can compress the slowly varying exponent/mantissa lanes.
        values = np.ascontiguousarray(np.concatenate(parts), dtype='<f8').view(np.uint8).reshape(-1, 8)
        return base64.b64encode(values.T.copy().tobytes()).decode()
    return {'schema': 2, 'worlds': mass.worlds, 'probability_mass': mass.total, 'players': list(players),
            'periods': list(SLICES), 'offsets': offsets, 'byte_shuffle': 8, 'minutes_f64_le': pack(support),
            'cumulative_f64_le': pack(cumulative)}


def encode_players(minutes, players, weights, folder, source_id):
    """Write one small independently verifiable record per player, before bundle publication."""
    players = list(players)
    minutes = np.asarray(minutes)
    if (not isinstance(source_id, str) or not re.fullmatch(r'[a-f0-9]{64}', source_id) or not players
            or len(set(players)) != len(players) or any(not isinstance(p, str) or not p.isascii() or not p.isdigit() for p in players)):
        raise ValueError('valid source hash and digit player IDs required')
    if minutes.ndim != 3 or minutes.shape[1:] != (len(players), 5) or minutes.dtype != np.float64 or not np.isfinite(minutes).all() or (minutes < 0).any():
        raise ValueError('valid precise minute arrays required')
    mass = WorldMass(int(minutes.shape[0]), weights)
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    for i, pid in enumerate(players):
        record = encode(minutes[:, i:i + 1], [pid], weights)
        write_json(folder / f'{pid}.json', {**record, 'source_id': source_id}, pretty=False)
    return {'schema': 2, 'scope': 'player', 'source_id': source_id, 'worlds': mass.worlds,
            'probability_mass': mass.total, 'players': players}
