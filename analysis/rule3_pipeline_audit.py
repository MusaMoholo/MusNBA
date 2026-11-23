#!/usr/bin/env python3
"""Audit completed paired games while the frozen simulation continues; resumable by content hash."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import os
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from basketball_common import read_json, sha256_file, write_json
from analysis import rule3_capture_audit as audit


def audit_pair(task):
    meta, cache = map(Path, task)
    entry = read_json(meta)
    if set(entry['outputs']) != {'control', 'candidate'}:
        raise ValueError('incomplete saved pair')
    reports, captures = [], {}
    for label, output in entry['outputs'].items():
        capture = ROOT / output['capture']
        if sha256_file(capture) != output['sha256']:
            raise ValueError('changed capture')
        with np.load(capture, allow_pickle=False) as packed:
            data = {key: packed[key] for key in packed.files}
        if audit.capture_digest(data) != output['world_sha256']:
            raise ValueError('canonical captured worlds differ')
        compatible = {**data, 'trace_phase': data['trace_phase'].astype(np.int16)}
        corrected = label == 'candidate' or entry.get('control_corrected', False)
        result = audit.audit_worlds(compatible, foul_penalty=True) if corrected else audit.accounting(data)
        result.update(audit.team_fouls(data, corrected))
        audit.audit_metrics(data, output['result'])
        reports.append({'game': entry['game'], 'label': label, **result})
        captures[output['capture']] = output['sha256']
    result = {'game': entry['game'], 'meta_sha256': sha256_file(meta), 'captures': captures, 'audits': reports}
    if cache.exists():
        raise FileExistsError(cache)
    write_json(cache, result, pretty=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run')
    parser.add_argument('--jobs', type=int, default=1)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if not args.run.isidentifier() or not args.run.isascii() or not 1 <= args.jobs <= 10:
        raise ValueError('ASCII run and 1–10 single-thread audit workers required')
    if any(os.environ.get(n) != '1' for n in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS')):
        raise ValueError('set OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1')
    folder = ROOT / 'data/derived/experiments' / args.run
    plan = read_json(folder / 'plan.json')
    ids = plan['game_ids']
    cache = folder.with_name(folder.name + '_independent_audits')
    if args.output.exists() or (cache.exists() and not args.resume):
        raise FileExistsError('fresh output/cache required; use resume only for an incomplete audit')
    source = {'plan_sha256': sha256_file(folder / 'plan.json'), 'auditor_sha256': sha256_file(Path(audit.__file__)),
              'pipeline_sha256': sha256_file(Path(__file__))}
    if args.resume:
        if read_json(cache / 'plan.json') != source:
            raise ValueError('audit source/plan differs')
    else:
        cache.mkdir()
        write_json(cache / 'plan.json', source, pretty=True)
    done = {gid: read_json(cache / f'{gid}.json') for gid in ids if (cache / f'{gid}.json').exists()}
    queued = set(done)
    started = time.monotonic()
    last_mark = len(done) * 10 // len(ids)
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        futures = {}
        while len(done) < len(ids):
            for gid in ids:
                if gid not in queued and (folder / f'{gid}.json').exists():
                    futures[pool.submit(audit_pair, (str(folder / f'{gid}.json'), str(cache / f'{gid}.json')))] = gid
                    queued.add(gid)
            for future in list(futures):
                if future.done():
                    gid = futures.pop(future)
                    result = future.result()
                    if result['game'] != gid:
                        raise ValueError('audit game identity differs')
                    done[gid] = result
                    mark = len(done) * 10 // len(ids)
                    if mark > last_mark:
                        print(f'audited {len(done)}/{len(ids)} complete pairs in {time.monotonic() - started:.1f}s', flush=True)
                        last_mark = mark
            time.sleep(1)
    run_path = ROOT / f'analysis/experiments/{args.run}.json'
    while not run_path.exists():
        time.sleep(1)
    run = read_json(run_path)
    if run['game_ids'] != ids or source != {'plan_sha256': sha256_file(folder / 'plan.json'),
                                         'auditor_sha256': sha256_file(Path(audit.__file__)), 'pipeline_sha256': sha256_file(Path(__file__))}:
        raise ValueError('audit/run inputs changed')
    metas = {row['game']: row['meta_sha256'] for row in run['captures']}
    for gid, item in done.items():
        if item['meta_sha256'] != metas[gid] or sha256_file(folder / f'{gid}.json') != metas[gid]:
            raise ValueError('changed completed metadata')
        for path, digest in item['captures'].items():
            if sha256_file(ROOT / path) != digest:
                raise ValueError('changed independently audited capture')
    write_json(args.output, {'run': args.run, 'pairs': len(ids), 'worlds_per_branch_game': run['worlds'],
                            'source_sha256': source['auditor_sha256'], 'pipeline_sha256': source['pipeline_sha256'],
                            'run_sha256': sha256_file(run_path), 'legacy_fields_equal_1e_12': None, 'same_worlds_as': None,
                            'audits': [row for gid in ids for row in done[gid]['audits']],
                            'status': 'pass; accounting only, no accuracy claim', 'overlapped_generation': True}, pretty=True)
    print('all audited captures match final run manifest', flush=True)


if __name__ == '__main__':
    main()
