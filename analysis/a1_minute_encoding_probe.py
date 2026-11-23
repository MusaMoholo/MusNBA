#!/usr/bin/env python3
"""Compare saved-world minute encodings without changing forecasts or scoring outcomes."""
from __future__ import annotations

import argparse
import gzip
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import read_json, sha256_file, write_json  # noqa: E402


def compare(minutes: np.ndarray) -> dict:
    if (minutes.ndim != 3 or minutes.shape[2] != 5 or not minutes.size
            or not np.isfinite(minutes).all() or (minutes < 0).any()):
        raise ValueError('expected finite nonnegative world-by-player-by-period minutes')
    full = minutes.sum(axis=2)
    if np.max(full * 60) > np.iinfo(np.uint16).max:
        raise ValueError('seconds exceed the comparison encoding')
    encodings = {
        'float64_minutes': np.ascontiguousarray(full, dtype='<f8'),
        'float32_minutes': np.ascontiguousarray(full, dtype='<f4'),
        'rounded_seconds': np.ascontiguousarray(np.rint(full * 60), dtype='<u2'),
        'floored_seconds': np.ascontiguousarray(np.floor(full * 60), dtype='<u2'),
    }
    results = {}
    for name, values in encodings.items():
        restored = values.astype(np.float64) / (60 if name.endswith('_seconds') else 1)
        differences = {
            str(threshold): int(np.count_nonzero((full >= threshold) != (restored >= threshold)))
            for threshold in (10, 20, 30, 40, 48)
        }
        results[name] = {
            'raw_bytes': int(values.nbytes),
            'gzip_bytes': len(gzip.compress(values.tobytes(), compresslevel=6, mtime=0)),
            'max_error_seconds': float(np.max(np.abs(full - restored)) * 60),
            'positive_minutes_lost': int(np.count_nonzero((full > 0) & (restored == 0))),
            'integer_minute_threshold_disagreements': differences,
        }
    unique = [len(np.unique(full[:, index])) for index in range(full.shape[1])]
    return {'worlds': int(full.shape[0]), 'players': int(full.shape[1]),
            'distinct_full_game_values_per_player_median': float(np.median(unique)),
            'distinct_full_game_values_per_player_max': max(unique), 'encodings': results}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an experiment')
    manifest_hash = sha256_file(args.manifest)
    manifest = read_json(args.manifest)
    captures = []
    for branch in manifest['branches']:
        path = ROOT / branch['capture']
        digest = sha256_file(path)
        if digest != branch['capture_sha256']:
            raise ValueError(f'{path}: capture hash differs from manifest')
        with np.load(path, allow_pickle=False) as data:
            result = compare(data['minutes'])
        if result['worlds'] != branch['worlds'] or sha256_file(path) != digest:
            raise ValueError(f'{path}: world count or input hash changed')
        captures.append({'capture': branch['capture'], 'capture_sha256': digest, **result})
    if sha256_file(args.manifest) != manifest_hash:
        raise ValueError('manifest changed during measurement')
    write_json(args.output, {
        'kind': 'isolated minute encoding accounting; not a forecast or predictive test',
        'manifest': str(args.manifest), 'manifest_sha256': manifest_hash,
        'algorithm_sha256': sha256_file(Path(__file__)), 'branches': captures,
        'limitations': ['One game and four saved research branches; no real outcomes scored.',
                        'Compressed sizes cover full-game minute arrays only, not a PWA bundle.'],
    }, pretty=True)
    print(f"Compared {len(captures)} branches and {sum(x['worlds'] for x in captures):,} saved worlds")


if __name__ == '__main__':
    main()
