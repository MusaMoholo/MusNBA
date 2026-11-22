#!/usr/bin/env python3
"""Independently replay saved batch accounting and verify isolated-world identities."""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from analysis.a1_parallel_capture_scale import STATIC  # noqa: E402
from analysis.a1_parallel_world_probe import capture_digest  # noqa: E402
from basketball_common import read_json, sha256_file, write_json  # noqa: E402
from scripts.a1_substitution_world_audit import audit_worlds  # noqa: E402
from scripts.projection import seed_for  # noqa: E402


def extract_world(data, index: int, overrides: dict[str, str]) -> dict[str, np.ndarray]:
    trace = data['trace_world'] == index
    result = {}
    for key in data.files:
        if key in STATIC:
            result[key] = data[key]
        elif key == 'trace_world':
            result[key] = np.zeros_like(data[key][trace])
        elif key.startswith('trace_'):
            result[key] = data[key][trace]
        else:
            result[key] = data[key][index:index + 1]
    for key, dtype in overrides.items():
        original = result[key]
        result[key] = original.astype(np.dtype(dtype))
        if not np.array_equal(result[key], original):
            raise ValueError(f'world {index}: lossy dtype restoration for {key}')
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an audit')
    report = read_json(args.report)
    pilot = read_json(ROOT / report['pilot'])
    fingerprints = report['fingerprints']
    if any(sha256_file(ROOT / name) != digest for name, digest in fingerprints.items()):
        raise ValueError('source or input differs from generation')
    if report['worlds'] != 100 * len(report['batches']):
        raise ValueError('batch and world counts differ')
    started = time.monotonic()
    base_seed = int(report['base_seed'])
    snapshots = rejections = 0
    identity = None
    for batch, record in enumerate(report['batches']):
        batch_seed = base_seed if batch == 0 else seed_for('a1-scale-batch-v1', base_seed, batch)
        path = ROOT / record['path']
        if (record['batch'] != batch or int(record['batch_seed']) != batch_seed
                or sha256_file(path) != record['sha256']
                or read_json(path.with_suffix('.json')) != record):
            raise ValueError(f'batch {batch}: manifest or fingerprint differs')
        attempts = [0] * 100
        last_world = -1
        for rejection in record['rejections']:
            world = rejection['world']
            if not 0 <= world < 100 or world < last_world or rejection['attempt'] != attempts[world]:
                raise ValueError(f'batch {batch}: rejection order differs')
            expected = seed_for('a1-isolated-world-v1', batch_seed, world, attempts[world])
            if int(rejection['seed']) != expected or not rejection['reason']:
                raise ValueError(f'batch {batch}: invalid rejection')
            attempts[world] += 1
            last_world = world
        rejections += len(record['rejections'])
        if (len(record['accepted_seeds']) != 100 or len(record['capture_sha256']) != 100
                or len(record['dtype_overrides']) != 100):
            raise ValueError(f'batch {batch}: incomplete world manifest')
        with np.load(path, allow_pickle=False) as data:
            current_identity = tuple(data[key].tolist() for key in STATIC)
            if identity is None:
                identity = current_identity
            elif current_identity != identity:
                raise ValueError(f'batch {batch}: game or roster differs')
            audit = audit_worlds(data)
            if audit['worlds'] != 100:
                raise ValueError(f'batch {batch}: capture count differs')
            snapshots += audit['lineup_snapshots']
            for world in range(100):
                expected = seed_for('a1-isolated-world-v1', batch_seed, world, attempts[world])
                if attempts[world] >= 3 or int(record['accepted_seeds'][world]) != expected:
                    raise ValueError(f'batch {batch}, world {world}: accepted seed differs')
                digest = capture_digest(extract_world(data, world, record['dtype_overrides'][world]))
                if digest != record['capture_sha256'][world]:
                    raise ValueError(f'batch {batch}, world {world}: capture differs')
                if batch == 0 and world < 20:
                    baseline = pilot['retry'] if world == 1 else pilot['control']
                    seeds = pilot['retry_seeds'] if world == 1 else pilot['control_seeds']
                    if digest != baseline[world]['capture_sha256'] or str(expected) != seeds[world]:
                        raise ValueError(f'world {world}: serial pilot mismatch')
        if (batch + 1) % 10 == 0:
            elapsed = time.monotonic() - started
            print(f'audited {(batch + 1) * 100}/{report["worlds"]} worlds in {elapsed:.1f}s', flush=True)
    if rejections != report['rejection_count'] or rejections > 100:
        raise ValueError('rejection count differs or exceeds cap')
    if any(sha256_file(ROOT / name) != digest for name, digest in fingerprints.items()):
        raise ValueError('source or input changed during audit')
    write_json(args.output, {
        'kind': 'independent saved-trace accounting and identity audit',
        'report': str(args.report), 'report_sha256': sha256_file(args.report),
        'worlds': report['worlds'], 'batches': len(report['batches']), 'lineup_snapshots': snapshots,
        'rejections': rejections, 'serial_pilot_worlds_checked': 20,
        'elapsed_seconds': round(time.monotonic() - started, 3),
        'limitations': report['limitations'],
    }, pretty=True)


if __name__ == '__main__':
    main()
