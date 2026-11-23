#!/usr/bin/env python3
"""Screen predeclared earlier-fold games for isolated branch exhaustion."""
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
from analysis import a1_dated_fold_exhaustion_audit as auditor  # noqa: E402
from analysis.a1_parallel_world_probe import capture_digest  # noqa: E402
from basketball_common import read_json, sha256_file, write_json  # noqa: E402
from scripts import a1_branch_foul_out, a1_branch_world_probe, a1_lineup_branches  # noqa: E402
from scripts import a1_substitution_world_audit, backtest, evaluate, projection  # noqa: E402

MANIFEST = ROOT / 'analysis/experiments/20261122_a1_pre_candidate_manifest.json'
_WORKER = {}


class CapturedGame(Exception):
    pass


def init_worker(preparation: dict) -> None:
    fold = preparation['fold']
    backtest._init(preparation['model_version'], str(ROOT / preparation['config']), fold, 1,
                   rotation='targets', pool=0)
    _WORKER.update(engine=backtest._W['engine'], fold=fold)


def screen_game(gid: str, directory: str) -> dict:
    eng, fold = _WORKER['engine'], _WORKER['fold']
    if eng.rotation_policy is not None:
        raise ValueError('worker must start with the default policy')
    simulate = eng.simulate
    result = {}

    def run(g, _worlds, _seed):
        if not evaluate.FOLDS[fold][1] <= g.day <= evaluate.FOLDS[fold][2]:
            raise ValueError(f'{gid}: outside declared development fold')
        home = np.flatnonzero(g.side == 0)
        if len(home) < 5:
            raise ValueError(f'{gid}: observed home roster has fewer than five players')
        index = min(home, key=lambda i: (-g.expected[i], str(g.ids[i])))
        player, team = str(g.ids[index]), str(g.game['home_id'])
        g.avail[index] = g.players['home'][int(index)]['availability'] = 0.5
        branches = []
        for plays in (True, False):
            label = 'plays' if plays else 'sits'
            availability = g.avail.copy()
            availability[index] = float(plays)
            missing = []
            for side_number, side_name in enumerate(g.sides):
                indices = np.flatnonzero(g.side == side_number)
                eligible = [int(j) for j in indices if availability[j] > 0]
                sure = [j for j in eligible if availability[j] >= 0.9]
                pool = sure if len(sure) >= 5 else eligible
                offset = int(indices[0])
                if any(not isinstance(g.players[side_name][j - offset]['pos'], str)
                       or not g.players[side_name][j - offset]['pos'].strip() for j in pool):
                    missing.append(side_name)
            if missing:
                branches.append({'branch': label, 'status': 'unsupported missing position',
                                 'reason': f"projected-starter pool lacks position: {', '.join(missing)}",
                                 'attempts': []})
                continue
            try:
                branch = a1_lineup_branches.one_player(g, team, player, plays)
            except ValueError as exc:
                if not any(str(exc) == f'{side} {problem}' for side in ('home', 'away') for problem in (
                        'has fewer than five possible available players',
                        'D29 targets do not form a legal 240-minute allocation')):
                    raise
                branches.append({'branch': label, 'status': 'invalid initial roster or allocation',
                                 'reason': str(exc), 'attempts': []})
                continue
            attempts = []
            for draw in range(5):
                seed = projection.seed_for('a1-dated-fold-exhaustion-v1', fold, gid, label, draw)
                policy = a1_branch_world_probe.RepairedTrace()
                eng.rotation_policy = policy
                try:
                    simulate(branch, 1, seed)
                except a1_branch_foul_out.ExhaustedEligiblePlayers as exc:
                    attempts.append({'draw': draw, 'seed': str(seed), 'status': 'exhausted',
                                     'reason': str(exc)})
                    continue
                capture = policy.capture(branch, eng.last)
                accounting = a1_substitution_world_audit.audit_worlds(capture)
                path = Path(directory) / f'{gid}-{label}-{draw}.npz'
                if path.exists():
                    raise FileExistsError(f'{path}: refusing to overwrite capture')
                np.savez_compressed(path, **capture)
                attempts.append({'draw': draw, 'seed': str(seed), 'status': 'complete',
                                 'capture': str(path), 'capture_sha256': sha256_file(path),
                                 'world_sha256': capture_digest(capture), 'audit': accounting})
            branches.append({'branch': label, 'status': 'simulated', 'attempts': attempts})
        result.update({'game': gid, 'day': g.day, 'selected_player': player,
                       'actual_participant_counts': [int((g.side == side).sum()) for side in (0, 1)],
                       'branches': branches})
        raise CapturedGame()

    try:
        with patch.object(eng, 'simulate', side_effect=run):
            backtest.run_game(gid)
    except CapturedGame:
        pass
    finally:
        eng.rotation_policy = None
    if not result:
        raise ValueError(f'{gid}: game was not reached')
    write_json(Path(directory) / f'{gid}.json', result, pretty=True)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preparation', type=Path, required=True)
    parser.add_argument('--worlds-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.worlds_dir.exists() or args.output.exists():
        raise FileExistsError('refusing to overwrite an experiment')
    if any(os.environ.get(name) != '1' for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS')):
        raise ValueError('set OMP_NUM_THREADS=1 and OPENBLAS_NUM_THREADS=1')
    preparation_path = args.preparation if args.preparation.is_absolute() else ROOT / args.preparation
    preparation = read_json(preparation_path)
    fold = preparation['fold']
    if fold not in ('F1', 'F2', 'F3') or preparation['training_through'] != evaluate.FOLDS[fold][0]:
        raise ValueError('preparation has an invalid fold cutoff')
    declared = read_json(MANIFEST)['confirmation'][fold]['games']
    ids = [row['game_id'] for row in declared]
    if len(ids) != 200 or len(set(ids)) != 200 or ids != sorted(ids):
        raise ValueError('fixed earlier-fold game IDs differ')
    fingerprints = {**preparation['input_sha256'], **preparation['model_files'],
                    preparation['config']: preparation['config_sha256'],
                    preparation['node_audit']: preparation['node_audit_sha256']}
    extra = (MANIFEST, preparation_path, Path(__file__), ROOT / 'analysis/a1_dated_fold_exhaustion_audit.py',
             ROOT / 'analysis/a1_parallel_world_probe.py', ROOT / 'scripts/a1_branch_foul_out.py',
             ROOT / 'scripts/a1_branch_world_probe.py', ROOT / 'scripts/a1_lineup_branches.py',
             ROOT / 'scripts/a1_substitution_world_audit.py', ROOT / 'scripts/projection.py',
             ROOT / 'scripts/minutes.py', ROOT / 'scripts/rotations.py', ROOT / 'scripts/matchups.py',
             ROOT / 'basketball_common.py', ROOT / 'data/derived/teams.json',
             ROOT / Path(read_json(ROOT / preparation['config'])['default']['features']).parent / 'team_pregame.parquet')
    fingerprints.update({str(p.relative_to(ROOT)): sha256_file(p) for p in extra})
    for season in range(2023, 2027):
        history = ROOT / f'data/derived/history/{season}'
        for path in (history / 'on_court.parquet', history / 'segments.parquet',
                     history / 'stints.parquet', history / 'player_periods.csv.gz',
                     ROOT / f'data/raw/hoopr/player_box_{season}.parquet'):
            fingerprints[str(path.relative_to(ROOT))] = sha256_file(path)

    def verify_inputs() -> None:
        if any(sha256_file(ROOT / name) != digest for name, digest in fingerprints.items()):
            raise ValueError('source, fold model or input changed')

    verify_inputs()
    args.worlds_dir.mkdir(parents=True)
    started = time.monotonic()
    records = {}
    pool = ProcessPoolExecutor(max_workers=8, initializer=init_worker, initargs=(preparation,))
    try:
        futures = {pool.submit(screen_game, gid, str(args.worlds_dir)): gid for gid in ids}
        for future in as_completed(futures):
            gid = futures[future]
            records[gid] = future.result()
            if len(records) % 20 == 0:
                elapsed = time.monotonic() - started
                print(f'{len(records)}/200 games in {elapsed:.1f}s ({len(records) / elapsed:.3f} games/s)',
                      flush=True)
    finally:
        pool.shutdown(wait=True, cancel_futures=True)
    ordered = [records[gid] for gid in ids]
    aggregate = auditor.totals(ordered)
    verify_inputs()
    detail_path = args.worlds_dir / 'manifest.json'
    write_json(detail_path, {'fold': fold, 'fingerprints': fingerprints, 'games': ordered}, pretty=True)
    write_json(args.output, {
        'kind': 'fixed earlier-fold oracle-roster synthetic-branch exhaustion screen',
        'fold': fold, 'preparation': str(args.preparation), 'preparation_sha256': sha256_file(args.preparation),
        'details': str(detail_path), 'details_sha256': sha256_file(detail_path),
        **aggregate, 'workers': 8, 'threads': 'OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1',
        'elapsed_seconds': round(time.monotonic() - started, 3),
        'limitations': ['Dated body-free diagnostic engine differs from accepted v1.3 and F4 screen.',
                        'Actual participant rosters and synthetic statuses are not dated pre-game availability.',
                        'Does not estimate league rate, retry bias, accuracy or promote a model.'],
    }, pretty=True)


if __name__ == '__main__':
    main()
