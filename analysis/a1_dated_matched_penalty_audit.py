#!/usr/bin/env python3
"""Independently replay dated original attempts and audit continuation captures."""
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
from analysis import a1_dated_matched_penalty as run, a1_f4_six_roster_full_audit as comparisons  # noqa: E402
from analysis.a1_parallel_world_probe import capture_digest  # noqa: E402
from basketball_common import read_json, sha256_file, write_json  # noqa: E402
from scripts import a1_substitution_world_audit  # noqa: E402


def metrics(data):
    ids, side, available = data['player_ids'], data['side'], data['available'][0]
    home = np.flatnonzero((side == 0) & available)
    if len(home) != 7:
        raise ValueError('continuation does not have seven available home players')
    score = data['final_score'][0]
    labels = ['home_points', 'away_points', 'total_points', 'home_margin']
    labels += [f'home_player_{pid}_points' for pid in ids[home]]
    labels += [f'home_player_{pid}_minutes' for pid in ids[home]]
    values = np.concatenate((score, [score.sum(), score[0] - score[1]],
                             data['player_points'][0, home].sum(axis=1),
                             data['minutes'][0, home].sum(axis=1)))
    return labels, values


def check(previous, spec, directory):
    draw, fold, gid = previous['draw'], spec['fold'], spec['game']['game']
    seed, status, failure, original = run.simulate_original(draw, gid, fold)
    if (previous['seed'] != seed or previous['status'] != status or previous['failure'] != failure
            or previous['original_world_sha256'] != (capture_digest(original) if original is not None else None)):
        raise ValueError('independently replayed original trajectory differs')
    if draw < 5:
        old = spec['branch']['attempts'][draw]
        if old['seed'] != seed or old['status'] != status:
            raise ValueError('original screen seed or status differs')
        if status == 'exhausted' and old['reason'] != failure['reason']:
            raise ValueError('original screen rejection differs')
        if status == 'complete' and old['world_sha256'] != capture_digest(original):
            raise ValueError('original screen capture differs')
    path = ROOT / previous['capture']
    if path != ROOT / directory / f'world-{draw:04d}.npz' or sha256_file(path) != previous['capture_sha256']:
        raise ValueError('continuation capture path or hash differs')
    with np.load(path, allow_pickle=False) as data:
        saved = dict(data)
    if str(saved['game_id']) != gid:
        raise ValueError('continuation game differs')
    audit = a1_substitution_world_audit.audit_worlds(saved, foul_penalty=True)
    if audit != previous['audit'] or audit['worlds'] != 1:
        raise ValueError('continuation accounting differs')
    if original is not None and capture_digest({key: saved[key] for key in original}) != capture_digest(original):
        raise ValueError('continuation survivor trajectory differs')
    labels, values = metrics(saved)
    if original is not None:
        old_labels, original_values = metrics(original)
        if old_labels != labels or not np.array_equal(values, original_values):
            raise ValueError('survivor metrics differ')
    else:
        original_values = np.full(len(values), np.nan)
    return {'draw': draw, 'status': status, 'labels': labels, 'original': original_values,
            'continued': values, 'fives': audit['lineup_fives_checked'],
            'technicals': audit['foul_penalty_events']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an audit')
    if any(os.environ.get(name) != '1' for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS')):
        raise ValueError('set OMP_NUM_THREADS=1 and OPENBLAS_NUM_THREADS=1')
    report = read_json(args.report)
    spec = run.sources(report['fold'])
    manifest_path = ROOT / report['manifest']
    if sha256_file(manifest_path) != report['manifest_sha256']:
        raise ValueError('continuation manifest differs')
    manifest = read_json(manifest_path)
    if (manifest['fold'] != report['fold'] or manifest['game'] != report['game']
            or report['game'] != spec['game']['game'] or manifest['fingerprints'] != spec['fingerprints']
            or len(manifest['worlds']) != report['worlds']
            or report['worlds'] != (5 if report['pilot'] else 1000)):
        raise ValueError('manifest or selected population differs')

    def verify():
        if any(sha256_file(ROOT / name) != digest for name, digest in manifest['fingerprints'].items()):
            raise ValueError('source, fold model or input changed')

    verify()
    directory = Path(report['manifest']).parent
    for draw, record in enumerate(manifest['worlds']):
        if record['draw'] != draw or read_json(ROOT / directory / f'world-{draw:04d}.json') != record:
            raise ValueError('per-world record differs')
    started = time.monotonic()
    results = {}
    with ProcessPoolExecutor(max_workers=8, initializer=run.init_worker, initargs=(spec,)) as pool:
        futures = {pool.submit(check, record, spec, directory): record['draw'] for record in manifest['worlds']}
        try:
            for future in as_completed(futures):
                result = future.result()
                results[result['draw']] = result
                if len(results) % (1 if report['pilot'] else 100) == 0:
                    print(f"{report['fold']} audited {len(results)}/{len(futures)}", flush=True)
        except BaseException:
            for future in futures:
                future.cancel()
            raise
    ordered = [results[draw] for draw in range(report['worlds'])]
    labels = ordered[0]['labels']
    if any(row['labels'] != labels for row in ordered):
        raise ValueError('player identities differ across worlds')
    original = np.asarray([row['original'] for row in ordered])
    continued = np.asarray([row['continued'] for row in ordered])
    failures = sum(row['status'] == 'exhausted' for row in ordered)
    outcome = None
    if not report['pilot'] and failures < report['worlds']:
        draws = np.random.default_rng(20261122).integers(0, len(ordered), (5000, len(ordered)))
        difference, intervals = comparisons.estimates(original, continued, draws)
        outcome = {label: {'d29_survivor_mean': float(np.nanmean(original[:, i])),
                           'continuation_mean': float(continued[:, i].mean()),
                           'difference': float(difference[i]), 'ci_95': intervals[i].tolist()}
                   for i, label in enumerate(labels)}
    verify()
    write_json(args.output, {
        'kind': 'independent selected earlier-fold matched continuation accounting',
        'report': str(args.report), 'report_sha256': sha256_file(args.report),
        'audit_sha256': sha256_file(Path(__file__)), 'fold': report['fold'], 'game': report['game'],
        'pilot': report['pilot'], 'worlds': len(ordered), 'exhausted': failures,
        'lineup_fives_checked': sum(row['fives'] for row in ordered),
        'technical_events': sum(row['technicals'] for row in ordered),
        'metrics': outcome, 'bootstrap': {'replicates': 5000, 'seed': 20261122,
                                          'unit': 'original seed', 'interval': '95% percentile, unadjusted'}
        if outcome else None,
        'elapsed_seconds': round(time.monotonic() - started, 3), 'limitations': report['limitations'],
    }, pretty=True)
    print(f"{report['fold']}: audited {len(ordered)} worlds and replayed {failures} failures", flush=True)


if __name__ == '__main__':
    main()
