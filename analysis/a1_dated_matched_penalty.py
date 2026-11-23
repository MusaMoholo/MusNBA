#!/usr/bin/env python3
"""Replay a selected earlier-fold branch under D29 and a matched continuation."""
from __future__ import annotations

import argparse
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from analysis import a1_dated_fold_exhaustion as screen, a1_matched_penalty_repair as repair  # noqa: E402
from analysis import a1_matched_penalty_run as matched  # noqa: E402
from analysis.a1_parallel_world_probe import capture_digest  # noqa: E402
from basketball_common import read_json, sha256_file, write_json  # noqa: E402
from scripts import a1_branch_foul_out, a1_lineup_branches, a1_substitution_world_audit, backtest, projection  # noqa: E402

CASES = {'F1': ('401585382', '20261122_a1_dated_f1_screen_v2'),
         'F2': ('401705024', '20261122_a1_dated_f2_screen_v1'),
         'F3': ('401810091', '20261122_a1_dated_f3_screen_v1')}
_WORKER = {}


def sources(fold):
    gid, name = CASES[fold]
    summary_path = ROOT / f'analysis/experiments/{name}.json'
    audit_path = ROOT / f'analysis/experiments/{name}_audit.json'
    summary, audit = read_json(summary_path), read_json(audit_path)
    if audit['summary_sha256'] != sha256_file(summary_path):
        raise ValueError('earlier-fold screen audit differs')
    detail_path = ROOT / summary['details']
    if sha256_file(detail_path) != summary['details_sha256']:
        raise ValueError('earlier-fold screen manifest differs')
    detail = read_json(detail_path)
    games = [row for row in detail['games'] if row['game'] == gid]
    if len(games) != 1:
        raise ValueError('selected game is absent')
    game = games[0]
    branches = [row for row in game['branches'] if row['branch'] == 'sits']
    if len(branches) != 1 or branches[0]['status'] != 'simulated' or game['actual_participant_counts'][0] != 8:
        raise ValueError('selected seven-player branch differs')
    if fold != 'F1':
        feasible = sorted((g['actual_participant_counts'][0], g['game'])
                          for g in detail['games'] for b in g['branches']
                          if b['branch'] == 'sits' and b['status'] == 'simulated')
        if feasible[0] != (8, gid):
            raise ValueError('fold case is not the frozen minimum-roster choice')
    preparation_path = ROOT / summary['preparation']
    if sha256_file(preparation_path) != summary['preparation_sha256']:
        raise ValueError('dated preparation differs')
    paths = (summary_path, audit_path, detail_path, preparation_path, Path(__file__),
             ROOT / 'analysis/a1_dated_matched_penalty_audit.py',
             ROOT / 'analysis/a1_matched_penalty_repair.py', ROOT / 'analysis/a1_matched_penalty_run.py')
    fingerprints = {**detail['fingerprints'], **{str(p.relative_to(ROOT)): sha256_file(p) for p in paths}}
    return {'fold': fold, 'game': game, 'branch': branches[0], 'preparation': read_json(preparation_path),
            'fingerprints': fingerprints}


def init_worker(spec):
    screen.init_worker(spec['preparation'])
    eng = screen._WORKER['engine']
    simulate = eng.simulate
    gid, fold = spec['game']['game'], spec['fold']

    def prepare(g, _worlds, _seed):
        home = np.flatnonzero(g.side == 0)
        if len(home) != 8 or g.day != spec['game']['day']:
            raise ValueError('dated game or participant count differs')
        index = min(home, key=lambda i: (-g.expected[i], str(g.ids[i])))
        if str(g.ids[index]) != spec['game']['selected_player']:
            raise ValueError('selected player differs')
        g.avail[index] = g.players['home'][int(index)]['availability'] = 0.5
        branch = a1_lineup_branches.one_player(g, str(g.game['home_id']), str(g.ids[index]), False)
        if int((branch.avail[home] > 0).sum()) != 7:
            raise ValueError('expected seven available home players')
        _WORKER.update(engine=eng, branch=branch, simulate=simulate, fold=fold)
        raise screen.CapturedGame()

    try:
        with patch.object(eng, 'simulate', side_effect=prepare):
            backtest.run_game(gid)
    except screen.CapturedGame:
        pass
    if not _WORKER:
        raise ValueError('selected dated game was not reached')


def simulate_original(draw, gid, fold):
    seed = projection.seed_for('a1-dated-fold-exhaustion-v1', fold, gid, 'sits', draw)
    policy = matched.FailureTrace()
    eng, branch = _WORKER['engine'], _WORKER['branch']
    eng.rotation_policy = policy
    try:
        _WORKER['simulate'](branch, 1, seed)
    except a1_branch_foul_out.ExhaustedEligiblePlayers:
        return str(seed), 'exhausted', policy.failure, None
    capture = policy.capture(branch, eng.last)
    a1_substitution_world_audit.audit_worlds(capture)
    return str(seed), 'complete', None, capture


def attempt(draw, spec, directory):
    gid, fold = spec['game']['game'], spec['fold']
    seed, status, failure, original = simulate_original(draw, gid, fold)
    if draw < 5:
        old = spec['branch']['attempts'][draw]
        if old['draw'] != draw or old['seed'] != seed or old['status'] != status:
            raise ValueError('original five-draw screen did not reproduce')
        if status == 'exhausted' and old['reason'] != failure['reason']:
            raise ValueError('original screen failure differs')
        if status == 'complete' and old['world_sha256'] != capture_digest(original):
            raise ValueError('original screen survivor differs')
    eng, branch = _WORKER['engine'], _WORKER['branch']
    policy = repair.MatchedPenaltyTrace()
    eng.rotation_policy = policy
    _WORKER['simulate'](branch, 1, int(seed))
    capture = policy.capture(branch, eng.last)
    if status == 'exhausted':
        if policy.first_exhaustion.get(0) != failure:
            raise ValueError('matched first-exhaustion state differs')
    elif policy.first_exhaustion or capture_digest({key: capture[key] for key in original}) != capture_digest(original):
        raise ValueError('matched survivor trajectory differs')
    audit = a1_substitution_world_audit.audit_worlds(capture, foul_penalty=True)
    path = Path(directory) / f'world-{draw:04d}.npz'
    if path.exists():
        raise FileExistsError(f'{path}: refusing to overwrite capture')
    np.savez_compressed(path, **capture)
    return {'draw': draw, 'seed': seed, 'status': status, 'failure': failure,
            'original_world_sha256': capture_digest(original) if original is not None else None,
            'capture': str(path), 'capture_sha256': sha256_file(path), 'audit': audit}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fold', choices=tuple(CASES), required=True)
    parser.add_argument('--worlds-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pilot', action='store_true', help='reproduce the five original draws only')
    args = parser.parse_args()
    if args.worlds_dir.exists() or args.output.exists():
        raise FileExistsError('refusing to overwrite an experiment')
    if any(os.environ.get(name) != '1' for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS')):
        raise ValueError('set OMP_NUM_THREADS=1 and OPENBLAS_NUM_THREADS=1')
    spec = sources(args.fold)

    def verify():
        if any(sha256_file(ROOT / name) != digest for name, digest in spec['fingerprints'].items()):
            raise ValueError('source, fold model or input changed')

    verify()
    count = 5 if args.pilot else 1000
    args.worlds_dir.mkdir(parents=True)
    start = time.monotonic()
    records = {}
    with ProcessPoolExecutor(max_workers=8, initializer=init_worker, initargs=(spec,)) as pool:
        futures = {pool.submit(attempt, draw, spec, str(args.worlds_dir)): draw for draw in range(count)}
        try:
            for future in as_completed(futures):
                result = future.result()
                write_json(args.worlds_dir / f"world-{result['draw']:04d}.json", result, pretty=True)
                records[result['draw']] = result
                if len(records) % (1 if args.pilot else 100) == 0:
                    elapsed = time.monotonic() - start
                    print(f'{args.fold} {len(records)}/{count} worlds in {elapsed:.1f}s', flush=True)
        except BaseException:
            for future in futures:
                future.cancel()
            raise
    verify()
    manifest_path = args.worlds_dir / 'manifest.json'
    write_json(manifest_path, {'fold': args.fold, 'game': spec['game']['game'],
                               'fingerprints': spec['fingerprints'],
                               'worlds': [records[draw] for draw in range(count)]}, pretty=True)
    write_json(args.output, {
        'kind': 'selected earlier-fold matched D29 continuation; diagnostic only',
        'fold': args.fold, 'game': spec['game']['game'], 'pilot': args.pilot, 'worlds': count,
        'manifest': str(manifest_path), 'manifest_sha256': sha256_file(manifest_path),
        'workers': 8, 'elapsed_seconds': round(time.monotonic() - start, 3),
        'limitations': ['Selected synthetic oracle-roster case and dated diagnostic engine.',
                        'Continuation is an explicit assumption, not the no-exception counterfactual.',
                        'Not a league rate, predictive test, or production gate.'],
    }, pretty=True)


if __name__ == '__main__':
    main()
