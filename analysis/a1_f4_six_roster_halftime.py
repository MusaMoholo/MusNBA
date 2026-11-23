#!/usr/bin/env python3
"""Replay selected six-player attempts and observe states before any recorded failure."""
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
from analysis import a1_f4_six_roster_halftime_audit as auditor, a1_f4_six_roster_stress as stress  # noqa: E402
from analysis.a1_parallel_world_probe import capture_digest  # noqa: E402
from basketball_common import read_json, sha256_file, write_json  # noqa: E402
from scripts import a1_branch_foul_out, a1_branch_world_probe, projection  # noqa: E402

SUMMARY = ROOT / 'analysis/experiments/20261122_a1_f4_six_roster_v1.json'
AUDIT = ROOT / 'analysis/experiments/20261122_a1_f4_six_roster_v1_audit.json'


class HalftimeTrace(a1_branch_world_probe.RepairedTrace):
    def __init__(self) -> None:
        super().__init__()
        self.halftime = None

    def before_segment(self, g, st, active, scheduled):
        if self.halftime is None and len(active) == 1 and st.period[active[0]] == 3:
            w = int(active[0])
            if st.clock[w] != 720:
                raise ValueError('first observed third-period clock is not 720 seconds')
            self.halftime = {'side': g.side.copy(), 'available': self.available[w].copy(),
                             'minutes': st.minutes[w].copy(), 'player_points': st.box['pts'][w].copy(),
                             'player_fouls': st.box['pf'][w].copy(), 'team_points': st.pts[w].copy(),
                             'score': st.score[w].copy()}
        return super().before_segment(g, st, active, scheduled)


def attempt(previous: dict, directory: str) -> dict:
    draw = previous['draw']
    if int(previous['seed']) != projection.seed_for('a1-f4-six-roster-v1', stress.GAME, draw):
        raise ValueError('original seed differs')
    eng, branch = stress._WORKER['engine'], stress._WORKER['branch']
    policy = HalftimeTrace()
    eng.rotation_policy = policy
    try:
        stress._WORKER['simulate'](branch, 1, int(previous['seed']))
    except a1_branch_foul_out.ExhaustedEligiblePlayers as exc:
        if previous['status'] != 'exhausted' or str(exc) != previous['reason']:
            raise ValueError('failure differs from original') from exc
        outcome = {'status': 'exhausted', 'reason': str(exc)}
    else:
        digest = capture_digest(policy.capture(branch, eng.last))
        if previous['status'] != 'complete' or digest != previous['world_sha256']:
            raise ValueError('complete world differs from original')
        outcome = {'status': 'complete', 'world_sha256': digest}
    if policy.halftime is None:
        raise ValueError('no halftime state was captured')
    auditor.metrics(policy.halftime)
    path = Path(directory) / f'world-{draw:04d}.npz'
    if path.exists():
        raise FileExistsError(f'{path}: refusing to overwrite capture')
    np.savez_compressed(path, **policy.halftime)
    return {'draw': draw, 'seed': previous['seed'], **outcome, 'capture': str(path),
            'capture_sha256': sha256_file(path)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worlds-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.worlds_dir.exists() or args.output.exists():
        raise FileExistsError('refusing to overwrite an experiment')
    if any(os.environ.get(name) != '1' for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS')):
        raise ValueError('set OMP_NUM_THREADS=1 and OPENBLAS_NUM_THREADS=1')
    original, audit = read_json(SUMMARY), read_json(AUDIT)
    if audit['summary_sha256'] != sha256_file(SUMMARY) or audit['exhausted'] != original['exhausted']:
        raise ValueError('independent source audit differs')
    detail_path = ROOT / original['details']
    if sha256_file(detail_path) != original['details_sha256']:
        raise ValueError('stress manifest differs')
    previous = read_json(detail_path)['attempts']
    if len(previous) != 1000:
        raise ValueError('expected 1000 original attempts')
    panel = read_json(ROOT / read_json(stress.SUMMARY)['details'])
    selected = [game for game in panel['games'] if game['game'] == stress.GAME]
    if len(selected) != 1:
        raise ValueError('selected game is missing from panel')
    fingerprints = dict(original['fingerprints'])
    for path in (SUMMARY, AUDIT, Path(__file__), ROOT / 'analysis/a1_f4_six_roster_halftime_audit.py'):
        fingerprints[str(path.relative_to(ROOT))] = sha256_file(path)

    def verify_inputs() -> None:
        if any(sha256_file(ROOT / name) != digest for name, digest in fingerprints.items()):
            raise ValueError('stress, source, model or input changed')

    verify_inputs()
    args.worlds_dir.mkdir(parents=True)
    started = time.monotonic()
    records = {}
    with ProcessPoolExecutor(max_workers=6, initializer=stress.init_worker,
                             initargs=(selected[0]['selected_player'],)) as pool:
        futures = {pool.submit(attempt, record, str(args.worlds_dir)): record['draw'] for record in previous}
        for future in as_completed(futures):
            draw = futures[future]
            record = future.result()
            write_json(args.worlds_dir / f'world-{draw:04d}.json', record, pretty=True)
            records[draw] = record
            if len(records) % 100 == 0:
                elapsed = time.monotonic() - started
                print(f'{len(records)}/1000 attempts in {elapsed:.1f}s '
                      f'({len(records) / elapsed:.2f} attempts/s)', flush=True)
    ordered = [records[draw] for draw in range(1000)]
    values = []
    for record in ordered:
        with np.load(record['capture'], allow_pickle=False) as data:
            values.append(auditor.metrics(data))
    results = auditor.summary(np.asarray(values), np.array([r['status'] == 'complete' for r in ordered]))
    verify_inputs()
    manifest = args.worlds_dir / 'manifest.json'
    write_json(manifest, {'game': stress.GAME, 'fingerprints': fingerprints, 'worlds': ordered}, pretty=True)
    write_json(args.output, {
        'kind': 'selected six-player F4 halftime survivor-conditioning diagnostic',
        'stress': str(SUMMARY.relative_to(ROOT)), 'stress_sha256': sha256_file(SUMMARY),
        'manifest': str(manifest), 'manifest_sha256': sha256_file(manifest),
        'attempts': len(ordered), 'workers': 6, 'threads': 'OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1',
        'elapsed_seconds': round(time.monotonic() - started, 3), 'metrics': results,
        'bootstrap': {'replicates': 5000, 'seed': 20261122, 'unit': 'attempt', 'interval': '95% percentile'},
        'limitations': ['One selected oracle-roster game with synthetic absence; not an NBA rate.',
                        'Halftime selection only; rejected final outcomes and full-game predictive bias are unknown.',
                        'Does not promote any retry or foul-penalty policy.'],
    }, pretty=True)


if __name__ == '__main__':
    main()
