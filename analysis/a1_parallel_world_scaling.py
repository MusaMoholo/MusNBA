#!/usr/bin/env python3
"""Compare process counts for the same independently audited F4 worlds."""
from __future__ import annotations

import argparse
import os
import resource
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from analysis.a1_parallel_world_probe import init_worker, run_world  # noqa: E402
from basketball_common import read_json, sha256_file, write_json  # noqa: E402
from scripts.projection import seed_for  # noqa: E402


def sample(world: int, base_seed: int) -> tuple[dict, str, int]:
    seed = seed_for('a1-isolated-world-v1', base_seed, world, 0)
    result = run_world(world, 0, seed, inject=False)
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return result, str(seed), int(rss if sys.platform == 'darwin' else rss * 1024)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pilot', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an experiment')
    if any(os.environ.get(name) != '1' for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS')):
        raise ValueError('set OMP_NUM_THREADS=1 and OPENBLAS_NUM_THREADS=1')
    pilot = read_json(args.pilot)
    if pilot['worlds'] != 20 or pilot['game'] != '401810327':
        raise ValueError('expected the fixed 20-world F4 pilot')
    provenance = read_json(ROOT / pilot['provenance'])
    fingerprints = {**provenance['input_sha256'], **provenance['sha256'], **pilot['source_sha256']}
    fingerprints[str(args.pilot)] = sha256_file(args.pilot)
    fingerprints[str(Path(__file__).relative_to(ROOT))] = sha256_file(Path(__file__))

    def verify_inputs() -> None:
        if any(sha256_file(ROOT / name) != digest for name, digest in fingerprints.items()):
            raise ValueError('pilot inputs, models or sources changed')
        if sha256_file(ROOT / pilot['provenance']) != pilot['provenance_sha256']:
            raise ValueError('pilot provenance changed')

    verify_inputs()
    base_seed = int(pilot['seed'])
    measurements = {}
    baseline = None
    for workers in (8, 10, 12):
        started = time.monotonic()
        results, seeds, peak_rss = [], [], 0
        with ProcessPoolExecutor(max_workers=workers, initializer=init_worker,
                                 initargs=(pilot['game'],)) as pool:
            for result, seed, rss in pool.map(sample, range(120), [base_seed] * 120):
                results.append(result)
                seeds.append(seed)
                peak_rss = max(peak_rss, rss)
                if len(results) % 12 == 0:
                    elapsed = time.monotonic() - started
                    print(f'{workers} processes: {len(results)}/120 ({len(results) // 12 * 10}%) '
                          f'in {elapsed:.1f}s; {len(results) / elapsed:.2f} worlds/s', flush=True)
        if results[:20] != pilot['control'] or seeds[:20] != pilot['control_seeds']:
            raise ValueError(f'{workers} workers do not reproduce the single-process pilot')
        if baseline is None:
            baseline = (results, seeds)
        elif (results, seeds) != baseline:
            raise ValueError(f'{workers} workers produced different world results or seeds')
        measurements[str(workers)] = {
            'seconds': round(time.monotonic() - started, 3),
            'max_individual_worker_peak_rss_bytes': peak_rss,
        }
    verify_inputs()
    write_json(args.output, {
        'kind': 'fixed-game independent-world process-scaling probe; not a forecast or promotion',
        'game': pilot['game'], 'model': pilot['model'], 'worlds_per_worker_count': 120,
        'base_seed': str(base_seed), 'threads': 'OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1',
        'source_and_input_sha256': fingerprints,
        'measurements': measurements, 'seeds': baseline[1], 'worlds': baseline[0],
        'limitations': [
            'No rejection is injected or measured in this scaling probe.',
            '120 worlds from one fixed game are not a measured 10,000-world runtime.',
            'Per-worker peak RSS is not simultaneous total memory usage.',
            'Audited capture hashes are retained, but captures are not independently replayable.',
            'Independent seeds do not reproduce production vectorized streams.',
        ],
    }, pretty=True)


if __name__ == '__main__':
    main()
