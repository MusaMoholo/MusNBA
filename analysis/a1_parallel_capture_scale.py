#!/usr/bin/env python3
"""Persist a fixed-game, independently seeded 10k-world retry research run."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from analysis.a1_parallel_world_probe import _WORKER, capture_digest, init_worker  # noqa: E402
from analysis.a1_parallel_world_retry import simulate_parallel  # noqa: E402
from basketball_common import read_json, sha256_file, write_json  # noqa: E402
from scripts import a1_branch_world_probe, a1_substitution_world_audit, a1_world_retry  # noqa: E402
from scripts.projection import seed_for  # noqa: E402

STATIC = ('game_id', 'player_ids', 'side')
LIMITATIONS = [
    'One rejection is injected; remaining rejections are not representative of NBA games.',
    'This is one synthetic-availability F4 game, not a fold comparison or calibrated forecast.',
    'Per-world seeds differ from production vectorized streams.',
    'This is not a full-slate or nightly runtime.',
]


def capture_world(world: int, attempt: int, seed: int, *, inject: bool) -> dict:
    policy = a1_branch_world_probe.RepairedTrace()
    eng, branch = _WORKER['engine'], _WORKER['branch']
    eng.rotation_policy = policy
    _WORKER['simulate'](branch, 1, seed)
    capture = policy.capture(branch, eng.last)
    audit = a1_substitution_world_audit.audit_worlds(capture)
    if inject and world == 1 and attempt == 0:
        raise a1_world_retry.RecoverableWorldError('deliberately injected after successful world audit')
    return {'capture': capture, 'audit': audit}


def merge_captures(captures: list[dict[str, np.ndarray]]) -> dict[str, np.ndarray]:
    if not captures or any(c.keys() != captures[0].keys() for c in captures):
        raise ValueError('capture keys differ or batch is empty')
    if any(not np.array_equal(c[key], captures[0][key]) for c in captures for key in STATIC):
        raise ValueError('capture identities differ')
    merged = {key: captures[0][key] for key in STATIC}
    for key in captures[0]:
        if key in STATIC:
            continue
        if key == 'trace_world':
            if any(not np.equal(c[key], 0).all() for c in captures):
                raise ValueError('expected single-world traces')
            merged[key] = np.concatenate([np.full_like(c[key], index) for index, c in enumerate(captures)])
        else:
            merged[key] = np.concatenate([c[key] for c in captures])
    return merged


def resume_records(directory: Path, config: dict) -> list[dict]:
    if read_json(directory / 'run.json') != config:
        raise ValueError('resume configuration or fingerprints changed')
    names = {path.name for path in directory.iterdir()}
    records = []
    for batch in range(config['batches']):
        json_name, npz_name = f'batch_{batch:03d}.json', f'batch_{batch:03d}.npz'
        if json_name not in names and npz_name not in names:
            break
        if json_name not in names or npz_name not in names:
            raise ValueError(f'batch {batch}: incomplete saved pair')
        record = read_json(directory / json_name)
        if record.get('path') != str(directory / npz_name):
            raise ValueError(f'batch {batch}: capture path differs from run directory')
        records.append(record)
        names.remove(json_name)
        names.remove(npz_name)
    if names != {'run.json'}:
        raise ValueError('unexpected or non-contiguous saved files')
    return records


def audit_prefix(records: list[dict], config: dict) -> None:
    if not records:
        return
    report = {
        'pilot': config['pilot'], 'fingerprints': config['fingerprints'],
        'worlds': 100 * len(records), 'base_seed': config['base_seed'], 'batches': records,
        'rejection_count': sum(len(record['rejections']) for record in records),
        'limitations': LIMITATIONS,
    }
    with tempfile.TemporaryDirectory(prefix='musnba-a1-resume-audit-') as tmp:
        report_path, output_path = Path(tmp) / 'prefix.json', Path(tmp) / 'audit.json'
        write_json(report_path, report, pretty=True)
        subprocess.run([sys.executable, str(ROOT / 'analysis/a1_parallel_capture_audit.py'),
                        str(report_path), '--output', str(output_path)], check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pilot', type=Path, required=True)
    parser.add_argument('--worlds-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--batches', type=int, default=100)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--stop-after-batches', type=int,
                        help='Stop cleanly after this many batches for a restart experiment.')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an experiment')
    if args.worlds_dir.exists() != args.resume:
        raise FileExistsError('new captures require a new directory; resume requires an existing directory')
    if not 1 <= args.batches <= 100:
        raise ValueError('batches must be between 1 and 100')
    if args.stop_after_batches is not None and not 1 <= args.stop_after_batches < args.batches:
        raise ValueError('stop-after-batches must leave at least one batch unfinished')
    if any(os.environ.get(name) != '1' for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS')):
        raise ValueError('set OMP_NUM_THREADS=1 and OPENBLAS_NUM_THREADS=1')
    pilot = read_json(args.pilot)
    if pilot['worlds'] != 20 or pilot['game'] != '401810327':
        raise ValueError('expected the fixed 20-world F4 pilot')
    provenance = read_json(ROOT / pilot['provenance'])
    fingerprints = {**provenance['input_sha256'], **provenance['sha256'], **pilot['source_sha256']}
    fingerprints[str(args.pilot)] = sha256_file(args.pilot)
    fingerprints[str(Path(__file__).relative_to(ROOT))] = sha256_file(Path(__file__))
    fingerprints['analysis/a1_parallel_capture_audit.py'] = sha256_file(ROOT / 'analysis/a1_parallel_capture_audit.py')

    def verify_inputs() -> None:
        if any(sha256_file(ROOT / name) != digest for name, digest in fingerprints.items()):
            raise ValueError('pilot inputs, models or sources changed')
        if sha256_file(ROOT / pilot['provenance']) != pilot['provenance_sha256']:
            raise ValueError('pilot provenance changed')

    verify_inputs()
    base_seed = int(pilot['seed'])
    config = {'pilot': str(args.pilot), 'output': str(args.output), 'batches': args.batches,
              'base_seed': str(base_seed), 'fingerprints': fingerprints}
    if args.resume:
        records = resume_records(args.worlds_dir, config)
        audit_prefix(records, config)
        verify_inputs()
    else:
        args.worlds_dir.mkdir(parents=True)
        write_json(args.worlds_dir / 'run.json', config, pretty=True)
        records = []
    if args.stop_after_batches is not None and len(records) >= args.stop_after_batches:
        raise ValueError('stop-after-batches must exceed the completed prefix')
    rejection_count = sum(len(record['rejections']) for record in records)
    resumed_batches = len(records)
    started = time.monotonic()
    with ProcessPoolExecutor(max_workers=10, initializer=init_worker, initargs=(pilot['game'],)) as pool:
        for batch in range(len(records), args.batches):
            batch_seed = base_seed if batch == 0 else seed_for('a1-scale-batch-v1', base_seed, batch)
            result = simulate_parallel(partial(capture_world, inject=batch == 0), pool, worlds=100,
                                       seed=batch_seed, attempts_per_world=3,
                                       max_rejections=100 - rejection_count, window=10)
            rejection_count += len(result.rejections)
            captures = [item['capture'] for item in result.worlds]
            digests = [capture_digest(c) for c in captures]
            if batch == 0:
                for world in range(20):
                    if world == 1:
                        if str(result.accepted_seeds[world]) != pilot['retry_seeds'][world]:
                            raise ValueError('replacement seed differs from the pilot')
                    elif (digests[world] != pilot['control'][world]['capture_sha256']
                          or str(result.accepted_seeds[world]) != pilot['control_seeds'][world]):
                        raise ValueError(f'world {world} differs from serial pilot')
            path = args.worlds_dir / f'batch_{batch:03d}.npz'
            merged = merge_captures(captures)
            overrides = [{key: value.dtype.str for key, value in capture.items()
                          if value.dtype != merged[key].dtype} for capture in captures]
            np.savez_compressed(path, allow_pickle=False, **merged)
            record = {
                'batch': batch, 'batch_seed': str(batch_seed), 'path': str(path),
                'sha256': sha256_file(path), 'capture_sha256': digests,
                'dtype_overrides': overrides,
                'accepted_seeds': [str(seed) for seed in result.accepted_seeds],
                'rejections': [{'world': r.world, 'attempt': r.attempt, 'seed': str(r.seed), 'reason': r.reason}
                               for r in result.rejections],
            }
            write_json(args.worlds_dir / f'batch_{batch:03d}.json', record, pretty=True)
            records.append(record)
            if (batch + 1) % 10 == 0:
                elapsed = time.monotonic() - started
                print(f'{(batch + 1) * 100}/{args.batches * 100} worlds in {elapsed:.1f}s; '
                      f'{(batch + 1 - resumed_batches) * 100 / elapsed:.2f} new worlds/s; '
                      f'{rejection_count} rejections', flush=True)
            if batch + 1 == args.stop_after_batches:
                verify_inputs()
                print(f'Stopped after {batch + 1} complete batches; resume with --resume', flush=True)
                return
    verify_inputs()
    write_json(args.output, {
        'kind': 'synthetic-injection isolated-world scale research; not a forecast or promotion',
        'game': pilot['game'], 'model': pilot['model'], 'worlds': args.batches * 100, 'workers': 10,
        'threads': 'OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1', 'base_seed': str(base_seed),
        'pilot': str(args.pilot), 'fingerprints': fingerprints, 'batches': records,
        'elapsed_seconds': round(time.monotonic() - started, 3), 'resumed_batches': resumed_batches,
        'elapsed_limitation': 'Elapsed time covers this invocation only, excluding any earlier batches and prefix audit.',
        'rejection_count': rejection_count,
        'limitations': LIMITATIONS,
    }, pretty=True)


if __name__ == '__main__':
    main()
