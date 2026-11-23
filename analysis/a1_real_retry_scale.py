#!/usr/bin/env python3
"""Extend the audited paired-retry stress with restartable 100-world batches."""
from __future__ import annotations

import argparse
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from analysis import a1_f4_six_roster_stress as stress, a1_real_retry_paired as paired  # noqa: E402
from analysis import a1_real_retry_paired_audit as paired_audit  # noqa: E402
from analysis.a1_parallel_world_retry import simulate_parallel  # noqa: E402
from basketball_common import read_json, sha256_file, write_json  # noqa: E402
from scripts.projection import seed_for  # noqa: E402

PREFIX = ROOT / 'analysis/experiments/20261123_a1_real_retry_paired_full_v1.json'
PREFIX_AUDIT = ROOT / 'analysis/experiments/20261123_a1_real_retry_paired_full_v1_audit.json'


def prefix():
    report, audit = read_json(PREFIX), read_json(PREFIX_AUDIT)
    if (audit['report_sha256'] != sha256_file(PREFIX) or report['worlds'] != 1000
            or report['base_seed'] != paired.BASE_SEED or report['game'] != stress.GAME):
        raise ValueError('audited retry prefix differs')
    manifest_path = ROOT / report['manifest']
    if sha256_file(manifest_path) != report['manifest_sha256']:
        raise ValueError('retry prefix manifest differs')
    manifest = read_json(manifest_path)
    if (len(manifest['first']) != 1000 or len(manifest['accepted']) != 1000
            or len(manifest['rejections']) != report['rejections']):
        raise ValueError('retry prefix population differs')
    for slot, (first, accepted) in enumerate(zip(manifest['first'], manifest['accepted'], strict=True)):
        if first['slot'] != slot or accepted['slot'] != slot:
            raise ValueError('retry prefix slot differs')
        for item in (first, accepted):
            if sha256_file(ROOT / item['capture']['path']) != item['capture']['sha256']:
                raise ValueError('retry prefix capture changed')
        if read_json(manifest_path.parent / f'first-{slot:04d}.json') != first:
            raise ValueError('retry prefix record changed')
    return report, manifest


def records(directory, config):
    if read_json(directory / 'run.json') != config:
        raise ValueError('resume configuration differs')
    names = {path.name for path in directory.iterdir()}
    names.remove('run.json')
    batches = []
    for batch in range(10, config['batches']):
        name = f'batch-{batch:03d}.json'
        if name not in names:
            break
        record = read_json(directory / name)
        if record['batch'] != batch or len(record['first']) != 100 or len(record['accepted']) != 100:
            raise ValueError('incomplete batch record')
        expected_names = {name}
        for offset, (first, accepted) in enumerate(zip(record['first'], record['accepted'], strict=True)):
            slot = first['slot']
            if accepted['slot'] != slot or slot != batch * 100 + offset:
                raise ValueError('batch slot differs')
            expected_names.add(f'first-{slot:04d}.json')
            expected_names.add(f'accepted-{slot:04d}.npz')
            if first['status'] == 'exhausted':
                expected_names.add(f'first-{slot:04d}.npz')
            elif first['status'] != 'complete':
                raise ValueError('unknown first attempt status')
        if not expected_names <= names:
            raise ValueError('incomplete batch files')
        names -= expected_names
        batches.append(record)
    if names:
        raise ValueError('orphaned, partial or non-contiguous batch files')
    return batches


def replay_prefix(pool, batches, directory):
    for batch in batches:
        rejected = {first['slot']: [] for first in batch['first']}
        for item in batch['rejections']:
            if item['slot'] not in rejected:
                raise ValueError('rejection outside batch')
            rejected[item['slot']].append(item)
        futures = [pool.submit(paired_audit.check, first, accepted, rejected[first['slot']],
                               directory, paired.BASE_SEED)
                   for first, accepted in zip(batch['first'], batch['accepted'], strict=True)]
        for future in futures:
            future.result()
        print(f"resume audit: batch {batch['batch']} replayed", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worlds-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--batches', type=int, default=100)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--stop-after-batches', type=int)
    args = parser.parse_args()
    if args.output.exists() or args.worlds_dir.exists() != args.resume:
        raise FileExistsError('new run needs new paths; resume needs its existing directory')
    if not 11 <= args.batches <= 100:
        raise ValueError('batches must be between 11 and 100')
    if args.stop_after_batches is not None and not 11 <= args.stop_after_batches < args.batches:
        raise ValueError('stop must leave at least one new batch')
    if any(os.environ.get(name) != '1' for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS')):
        raise ValueError('set OMP_NUM_THREADS=1 and OPENBLAS_NUM_THREADS=1')
    prior, original = prefix()
    fingerprints = dict(original['fingerprints'])
    for path in (PREFIX, PREFIX_AUDIT, Path(__file__), ROOT / 'analysis/a1_real_retry_scale_audit.py'):
        fingerprints[str(path.relative_to(ROOT))] = sha256_file(path)

    def verify():
        if any(sha256_file(ROOT / name) != digest for name, digest in fingerprints.items()):
            raise ValueError('source, input or model changed')

    verify()
    config = {'prefix': str(PREFIX.relative_to(ROOT)), 'prefix_sha256': sha256_file(PREFIX),
              'output': str(args.output), 'batches': args.batches, 'fingerprints': fingerprints}
    if args.resume:
        batches = records(args.worlds_dir, config)
    else:
        args.worlds_dir.mkdir(parents=True)
        write_json(args.worlds_dir / 'run.json', config, pretty=True)
        batches = []
    if args.stop_after_batches is not None and 10 + len(batches) >= args.stop_after_batches:
        raise ValueError('stop must exceed completed prefix')
    panel = read_json(ROOT / read_json(stress.SUMMARY)['details'])
    selected = [game for game in panel['games'] if game['game'] == stress.GAME]
    if len(selected) != 1:
        raise ValueError('selected game differs')
    rejections = len(original['rejections']) + sum(len(batch['rejections']) for batch in batches)
    if rejections > 5000:
        raise ValueError('saved rejection cap exceeded')
    resumed = len(batches)
    started = time.monotonic()
    with ProcessPoolExecutor(max_workers=10, initializer=stress.init_worker,
                             initargs=(selected[0]['selected_player'],)) as pool:
        if args.resume:
            replay_prefix(pool, batches, args.worlds_dir)
            verify()
        for batch in range(10 + len(batches), args.batches):
            batch_started = time.monotonic()
            seed = seed_for('a1-real-retry-paired-batch-v1', paired.BASE_SEED, batch)
            result = simulate_parallel(partial(paired.attempt, batch=batch, directory=str(args.worlds_dir)),
                                       pool, worlds=100, seed=seed, attempts_per_world=10,
                                       max_rejections=5000 - rejections, window=10)
            first = [read_json(args.worlds_dir / f'first-{slot:04d}.json')
                     for slot in range(batch * 100, (batch + 1) * 100)]
            rejected = [{'slot': batch * 100 + r.world, 'attempt': r.attempt, 'seed': str(r.seed),
                         'reason': r.reason} for r in result.rejections]
            record = {'batch': batch, 'first': first, 'accepted': list(result.worlds), 'rejections': rejected,
                      'generation_seconds': round(time.monotonic() - batch_started, 3)}
            write_json(args.worlds_dir / f'batch-{batch:03d}.json', record, pretty=True)
            batches.append(record)
            rejections += len(rejected)
            print(f'{(batch + 1) * 100}/{args.batches * 100} accepted, {rejections} rejected; '
                  f'{time.monotonic() - started:.1f}s this invocation', flush=True)
            if batch + 1 == args.stop_after_batches:
                verify()
                print(f'clean stop after {batch + 1} batches; resume with --resume', flush=True)
                return
    verify()
    if len(batches) != args.batches - 10:
        raise ValueError('incomplete scale run')
    manifest_path = args.worlds_dir / 'manifest.json'
    write_json(manifest_path, {'prefix': str(PREFIX.relative_to(ROOT)), 'fingerprints': fingerprints,
                               'batches': batches}, pretty=True)
    write_json(args.output, {'kind': 'selected-roster paired retry scale research; not a forecast',
                             'worlds': args.batches * 100, 'workers': 10, 'rejections': rejections,
                             'manifest': str(manifest_path), 'manifest_sha256': sha256_file(manifest_path),
                             'resumed_new_batches': resumed, 'elapsed_seconds': round(time.monotonic() - started, 3),
                             'elapsed_limitation': 'This invocation includes resume replay but excludes earlier runs.',
                             'limitations': prior['limitations'] + ['Not a full-slate runtime or production gate.']},
               pretty=True)


if __name__ == '__main__':
    main()
