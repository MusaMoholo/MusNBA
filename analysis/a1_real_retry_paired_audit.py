#!/usr/bin/env python3
"""Replay actual retries and independently check paired continuation outcomes."""
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
from analysis import a1_f4_six_roster_full_audit as comparison, a1_f4_six_roster_stress as stress  # noqa: E402
from analysis import a1_matched_penalty_repair as repair, a1_matched_penalty_run as matched  # noqa: E402
from analysis.a1_parallel_world_probe import capture_digest  # noqa: E402
from basketball_common import read_json, sha256_file, write_json  # noqa: E402
from scripts import a1_branch_foul_out, a1_substitution_world_audit, projection  # noqa: E402


def load(saved, game, penalty):
    path = ROOT / saved['path']
    if sha256_file(path) != saved['sha256']:
        raise ValueError('capture hash differs')
    with np.load(path, allow_pickle=False) as data:
        capture = dict(data)
    if str(capture['game_id']) != game:
        raise ValueError('capture game differs')
    audit = a1_substitution_world_audit.audit_worlds(capture, foul_penalty=penalty)
    if audit != saved['audit'] or audit['worlds'] != 1:
        raise ValueError('saved world accounting differs')
    return capture


def check(first, accepted, rejected, directory, base_seed):
    slot = first['slot']
    batch, world = divmod(slot, 100)
    batch_seed = projection.seed_for('a1-real-retry-paired-batch-v1', base_seed, batch)
    if read_json(ROOT / directory / f'first-{slot:04d}.json') != first:
        raise ValueError('first attempt record differs')
    if accepted['slot'] != slot or accepted['attempt'] != len(rejected):
        raise ValueError('accepted attempt index differs')
    for number, item in enumerate([*rejected, accepted]):
        seed = projection.seed_for('a1-isolated-world-v1', batch_seed, world, number)
        if int(item['seed']) != seed or (number < len(rejected)
                                         and (item['slot'] != slot or item['attempt'] != number)):
            raise ValueError('retry seed or ordering differs')
    if first['seed'] != str(projection.seed_for('a1-isolated-world-v1', batch_seed, world, 0)):
        raise ValueError('first seed differs')
    expected_accepted = ROOT / directory / f'accepted-{slot:04d}.npz'
    expected_first = ROOT / directory / f'first-{slot:04d}.npz' if rejected else expected_accepted
    if ROOT / accepted['capture']['path'] != expected_accepted or ROOT / first['capture']['path'] != expected_first:
        raise ValueError('capture path differs from slot')
    eng, branch = stress._WORKER['engine'], stress._WORKER['branch']
    first_failure = None
    for item in rejected:
        policy = matched.FailureTrace()
        eng.rotation_policy = policy
        try:
            stress._WORKER['simulate'](branch, 1, int(item['seed']))
        except a1_branch_foul_out.ExhaustedEligiblePlayers as exc:
            if str(exc) != item['reason']:
                raise ValueError('replayed rejection reason differs') from exc
            if item['attempt'] == 0:
                first_failure = policy.failure
        else:
            raise ValueError('recorded rejection did not exhaust')
    if (first['status'] != ('exhausted' if rejected else 'complete')
            or first['failure'] != first_failure):
        raise ValueError('first failure state differs')
    policy = matched.FailureTrace()
    eng.rotation_policy = policy
    stress._WORKER['simulate'](branch, 1, int(accepted['seed']))
    replayed = policy.capture(branch, eng.last)
    saved = load(accepted['capture'], stress.GAME, False)
    if capture_digest(replayed) != capture_digest(saved):
        raise ValueError('accepted world replay differs')
    first_capture = load(first['capture'], stress.GAME, bool(rejected))
    if rejected:
        policy = repair.MatchedPenaltyTrace()
        eng.rotation_policy = policy
        stress._WORKER['simulate'](branch, 1, int(first['seed']))
        if (policy.first_exhaustion.get(0) != first_failure
                or capture_digest(policy.capture(branch, eng.last)) != capture_digest(first_capture)):
            raise ValueError('matched continuation replay differs')
    elif capture_digest(first_capture) != capture_digest(saved):
        raise ValueError('unchanged first-seed survivor differs')
    values, ids, available = comparison.metrics(saved)
    paired, _, _ = comparison.metrics(first_capture, ids, available, saved['side'])
    return {'slot': slot, 'retry': values, 'paired': paired, 'ids': ids.tolist(),
            'side': saved['side'].tolist(), 'available': available.tolist(),
            'retry_fives': accepted['capture']['audit']['lineup_fives_checked'],
            'paired_fives': first['capture']['audit']['lineup_fives_checked'],
            'technicals': first['capture']['audit'].get('foul_penalty_events', 0)}


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
    manifest_path = ROOT / report['manifest']
    if sha256_file(manifest_path) != report['manifest_sha256']:
        raise ValueError('manifest differs')
    manifest = read_json(manifest_path)
    count = 20 if report['pilot'] else 1000
    if (report['game'] != stress.GAME or manifest['game'] != stress.GAME or report['worlds'] != count
            or len(manifest['accepted']) != count or len(manifest['first']) != count
            or report['rejections'] != len(manifest['rejections']) or report['rejections'] > 500):
        raise ValueError('population or cap differs')

    def verify():
        if any(sha256_file(ROOT / name) != digest for name, digest in manifest['fingerprints'].items()):
            raise ValueError('source, input or model changed')

    verify()
    panel = read_json(ROOT / read_json(stress.SUMMARY)['details'])
    selected = [g for g in panel['games'] if g['game'] == stress.GAME]
    if len(selected) != 1:
        raise ValueError('selected game differs')
    by_slot = [[] for _ in range(count)]
    for item in manifest['rejections']:
        if not 0 <= item['slot'] < count or not item['reason']:
            raise ValueError('rejection slot or reason invalid')
        by_slot[item['slot']].append(item)
    started = time.monotonic()
    results = {}
    with ProcessPoolExecutor(max_workers=8, initializer=stress.init_worker,
                             initargs=(selected[0]['selected_player'],)) as pool:
        futures = []
        for slot, (first, accepted) in enumerate(zip(manifest['first'], manifest['accepted'], strict=True)):
            if first['slot'] != slot or accepted['slot'] != slot or len(by_slot[slot]) >= 10:
                raise ValueError('slot or attempt cap differs')
            futures.append(pool.submit(check, first, accepted, by_slot[slot], manifest_path.parent,
                                       report['base_seed']))
        for future in as_completed(futures):
            item = future.result()
            results[item['slot']] = item
            if len(results) % (1 if report['pilot'] else 100) == 0:
                print(f"{len(results)}/{count} retry slots independently replayed", flush=True)
    rows = [results[i] for i in range(count)]
    if any((row['ids'], row['side'], row['available']) !=
           (rows[0]['ids'], rows[0]['side'], rows[0]['available']) for row in rows):
        raise ValueError('player identities differ')
    metrics = None
    if not report['pilot']:
        retry = np.array([row['retry'] for row in rows])
        paired = np.array([row['paired'] for row in rows])
        draws = np.random.default_rng(20261123).integers(0, count, (5000, count))
        delta = retry[draws].mean(axis=1) - paired[draws].mean(axis=1)
        ci = np.quantile(delta, [0.025, 0.975], axis=0)
        ids = np.array(rows[0]['ids'])
        side, available = np.array(rows[0]['side']), np.array(rows[0]['available'])
        home = ids[(side == 0) & available]
        labels = (['home_points', 'away_points', 'total_points', 'home_margin']
                  + [f'home_player_{pid}_points' for pid in home]
                  + [f'home_player_{pid}_minutes' for pid in home])
        metrics = {label: {'retry_mean': float(retry[:, i].mean()), 'continuation_mean': float(paired[:, i].mean()),
                           'difference': float(retry[:, i].mean() - paired[:, i].mean()),
                           'ci_95': ci[:, i].tolist()} for i, label in enumerate(labels)}
    verify()
    write_json(args.output, {
        'kind': 'independent replay of paired real retry and continuation',
        'report': str(args.report), 'report_sha256': sha256_file(args.report),
        'worlds': count, 'rejections_replayed': len(manifest['rejections']),
        'first_exhaustions': sum(f['status'] == 'exhausted' for f in manifest['first']),
        'retry_fives_checked': sum(row['retry_fives'] for row in rows),
        'paired_fives_checked': sum(row['paired_fives'] for row in rows),
        'technical_events': sum(row['technicals'] for row in rows), 'metrics': metrics,
        'bootstrap': {'replicates': 5000, 'seed': 20261123, 'unit': 'slot',
                      'interval': '95% percentile, unadjusted'} if metrics else None,
        'elapsed_seconds': round(time.monotonic() - started, 3), 'limitations': report['limitations'],
    }, pretty=True)


if __name__ == '__main__':
    main()
