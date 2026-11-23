#!/usr/bin/env python3
"""Independently replay and measure the paired 10k retry stress."""
from __future__ import annotations

import argparse
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from analysis import a1_f4_six_roster_stress as stress, a1_real_retry_paired as paired  # noqa: E402
from analysis import a1_real_retry_paired_audit as audit, a1_real_retry_scale as scale  # noqa: E402
from basketball_common import read_json, sha256_file, write_json  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an audit')
    if any(os.environ.get(name) != '1' for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS')):
        raise ValueError('set OMP_NUM_THREADS=1 and OPENBLAS_NUM_THREADS=1')
    report, original_report = read_json(args.report), read_json(scale.PREFIX)
    manifest_path = ROOT / report['manifest']
    if sha256_file(manifest_path) != report['manifest_sha256']:
        raise ValueError('manifest differs')
    manifest, config = read_json(manifest_path), read_json(manifest_path.parent / 'run.json')
    original_path = ROOT / original_report['manifest']
    if (sha256_file(original_path) != original_report['manifest_sha256']
            or sha256_file(scale.PREFIX) != config['prefix_sha256']
            or read_json(scale.PREFIX_AUDIT)['report_sha256'] != config['prefix_sha256']):
        raise ValueError('audited prefix differs')
    original = read_json(original_path)
    count = report['worlds']
    if (count != config['batches'] * 100 or not 1100 <= count <= 10000
            or config['fingerprints'] != manifest['fingerprints']
            or len(manifest['batches']) != config['batches'] - 10):
        raise ValueError('population, configuration or manifest differs')

    def verify():
        if any(sha256_file(ROOT / name) != digest for name, digest in manifest['fingerprints'].items()):
            raise ValueError('source, input or model changed')

    verify()
    first, accepted, rejected = list(original['first']), list(original['accepted']), list(original['rejections'])
    expected_names = {'run.json', 'manifest.json'}
    for batch, item in enumerate(manifest['batches'], start=10):
        filename = f'batch-{batch:03d}.json'
        if item['batch'] != batch or item != read_json(manifest_path.parent / filename):
            raise ValueError('batch record differs')
        expected_names.add(filename)
        if len(item['first']) != 100 or len(item['accepted']) != 100:
            raise ValueError('incomplete batch')
        for row in item['first']:
            expected_names.add(f"first-{row['slot']:04d}.json")
            expected_names.add(f"accepted-{row['slot']:04d}.npz")
            if row['status'] == 'exhausted':
                expected_names.add(f"first-{row['slot']:04d}.npz")
        first.extend(item['first'])
        accepted.extend(item['accepted'])
        rejected.extend(item['rejections'])
    if ({p.name for p in manifest_path.parent.iterdir()} != expected_names
            or len(first) != count or len(accepted) != count
            or len(rejected) != report['rejections'] or len(rejected) > 5000):
        raise ValueError('saved file inventory, count or cap differs')
    if [(r['slot'], r['attempt']) for r in rejected] != sorted((r['slot'], r['attempt']) for r in rejected):
        raise ValueError('rejection ordering differs')
    by_slot = [[] for _ in range(count)]
    for item in rejected:
        if not 0 <= item['slot'] < count or not item['reason']:
            raise ValueError('rejection slot or reason invalid')
        by_slot[item['slot']].append(item)
    panel = read_json(ROOT / read_json(stress.SUMMARY)['details'])
    selected = [g for g in panel['games'] if g['game'] == stress.GAME]
    if len(selected) != 1:
        raise ValueError('selected game differs')
    started = time.monotonic()
    results = {}
    with ProcessPoolExecutor(max_workers=10, initializer=stress.init_worker,
                             initargs=(selected[0]['selected_player'],)) as pool:
        futures = []
        for slot, (initial, final) in enumerate(zip(first, accepted, strict=True)):
            if initial['slot'] != slot or final['slot'] != slot or len(by_slot[slot]) >= 10:
                raise ValueError('slot or attempt cap differs')
            directory = original_path.parent if slot < 1000 else manifest_path.parent
            futures.append(pool.submit(audit.check, initial, final, by_slot[slot], directory, paired.BASE_SEED))
        for future in as_completed(futures):
            item = future.result()
            results[item['slot']] = item
            if len(results) % 100 == 0:
                print(f"{len(results)}/{count} slots replayed in {time.monotonic() - started:.1f}s", flush=True)
    rows = [results[i] for i in range(count)]
    if any((row['ids'], row['side'], row['available']) !=
           (rows[0]['ids'], rows[0]['side'], rows[0]['available']) for row in rows):
        raise ValueError('player identities differ')
    retry = np.array([row['retry'] for row in rows])
    continued = np.array([row['paired'] for row in rows])
    differences = retry - continued
    rng = np.random.default_rng(20261123)
    boot = np.empty((5000, differences.shape[1]))
    for i in range(len(boot)):
        boot[i] = differences[rng.integers(0, count, count)].mean(axis=0)
    intervals = np.quantile(boot, [0.025, 0.975], axis=0)
    ids, side, available = (np.array(rows[0][key]) for key in ('ids', 'side', 'available'))
    home = ids[(side == 0) & available]
    labels = (['home_points', 'away_points', 'total_points', 'home_margin']
              + [f'home_player_{pid}_points' for pid in home]
              + [f'home_player_{pid}_minutes' for pid in home])
    metrics = {label: {'retry_mean': float(retry[:, i].mean()),
                       'continuation_mean': float(continued[:, i].mean()),
                       'difference': float(differences[:, i].mean()),
                       'ci_95': intervals[:, i].tolist()} for i, label in enumerate(labels)}
    verify()
    write_json(args.output, {
        'kind': 'independent replay of scaled paired real retries and continuation',
        'report': str(args.report), 'report_sha256': sha256_file(args.report),
        'worlds': count, 'rejections_replayed': len(rejected),
        'first_exhaustions': sum(f['status'] == 'exhausted' for f in first),
        'retry_fives_checked': sum(row['retry_fives'] for row in rows),
        'paired_fives_checked': sum(row['paired_fives'] for row in rows),
        'technical_events': sum(row['technicals'] for row in rows), 'metrics': metrics,
        'bootstrap': {'replicates': 5000, 'seed': 20261123, 'unit': 'slot',
                      'interval': '95% percentile, unadjusted'},
        'elapsed_seconds': round(time.monotonic() - started, 3), 'limitations': report['limitations'],
    }, pretty=True)


if __name__ == '__main__':
    main()
