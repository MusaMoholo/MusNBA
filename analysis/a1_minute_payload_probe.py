#!/usr/bin/env python3
"""Measure precise-minute storage options from isolated saved branch captures."""
from __future__ import annotations

import argparse
import base64
import gzip
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import read_json, sha256_file, write_json  # noqa: E402
from scripts.projection import SLICES  # noqa: E402


def encode(minutes: np.ndarray, marginal: bool) -> dict:
    if (minutes.ndim != 3 or minutes.shape[2] != 5 or not minutes.size
            or not np.isfinite(minutes).all() or (minutes < 0).any()):
        raise ValueError('expected finite nonnegative world-by-player-by-period minutes')
    if marginal:
        # Sorted independent period marginals deliberately discard world identities.
        values = np.stack([np.sort(minutes[:, :, cols].sum(axis=2), axis=0)
                           for cols in SLICES.values()], axis=2)
        periods = list(SLICES)
    else:
        values = minutes
        periods = ['q1', 'q2', 'q3', 'q4', 'ot']
    raw = np.ascontiguousarray(values, dtype='<f8')
    return {'shape': list(raw.shape), 'periods': periods,
            'minutes_f64_le': base64.b64encode(raw.tobytes()).decode('ascii')}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an experiment')
    started = time.monotonic()
    manifest_hash = sha256_file(args.manifest)
    manifest = read_json(args.manifest)
    layouts: dict[str, list[dict]] = {'period_worlds': [], 'sorted_marginals': []}
    captures = []
    for branch in manifest['branches']:
        path = ROOT / branch['capture']
        digest = sha256_file(path)
        if digest != branch['capture_sha256']:
            raise ValueError(f'{path}: capture hash differs')
        with np.load(path, allow_pickle=False) as data:
            minutes = data['minutes']
        if minutes.shape[0] != branch['worlds']:
            raise ValueError(f'{path}: world count differs')
        for key, marginal in (('period_worlds', False), ('sorted_marginals', True)):
            layouts[key].append(encode(minutes, marginal))
        if sha256_file(path) != digest:
            raise ValueError(f'{path}: capture changed during measurement')
        captures.append({'capture': branch['capture'], 'capture_sha256': digest,
                         'worlds': int(minutes.shape[0]), 'players': int(minutes.shape[1])})
    if sha256_file(args.manifest) != manifest_hash:
        raise ValueError('manifest changed during measurement')
    sizes = {}
    for key, branches in layouts.items():
        payload = json.dumps({'schema': 1, 'branches': branches}, separators=(',', ':')).encode()
        sizes[key] = {'json_bytes': len(payload),
                      'gzip_bytes': len(gzip.compress(payload, compresslevel=6, mtime=0))}
    write_json(args.output, {
        'kind': 'isolated minute payload sizing; not a PWA bundle or predictive test',
        'manifest': str(args.manifest), 'manifest_sha256': manifest_hash,
        'algorithm_sha256': sha256_file(Path(__file__)), 'captures': captures,
        'layouts': sizes, 'seconds': round(time.monotonic() - started, 3),
        'limitations': ['One game only; JSON includes minute arrays and shape metadata, not other game data.',
                        'Sorted period marginals discard world identity and cannot support joint conditions.',
                        'No phone or browser benchmark; not a proposed production format.'],
    }, pretty=True)
    print(f"Measured {len(captures)} branches in {time.monotonic() - started:.2f}s")


if __name__ == '__main__':
    main()
