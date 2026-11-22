#!/usr/bin/env python3
"""Compare the S06 penalty policy on seeds rejected by the artificial retry stress."""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import read_json, sha256_file, write_json  # noqa: E402
from scripts import (a1_lineup_branches, a1_substitution_world_audit, a1_substitution_world_capture,  # noqa: E402
                     backtest, engine)


class CapturedGame(Exception):
    pass


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stress', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--worlds-dir', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.worlds_dir.exists():
        raise FileExistsError('refusing to overwrite an experiment')
    stress = read_json(args.stress)
    if (stress['game'] != '401810327' or stress['model'] != 'folds/v1.2d_F4_all'
            or stress['result']['status'] != 'complete' or not stress['result']['rejections']):
        raise ValueError('expected completed fixed-game artificial stress with real rejections')
    provenance = Path(stress['provenance'])
    if (sha256_file(provenance) != stress['provenance_sha256']
            or sha256_file(ROOT / 'analysis/a1_world_retry_stress.py') != stress['analysis_sha256']):
        raise ValueError('stress source fingerprint differs')
    earlier = read_json(provenance)
    fingerprints = {**earlier['input_sha256'], **earlier['sha256']}
    if any(sha256_file(ROOT / name) != digest for name, digest in fingerprints.items()):
        raise ValueError('stress inputs or sources differ')
    backtest._init('folds/v1.2d_F4_all', str(ROOT / 'models/v1.2d.json'), 'F4', 1,
                   rotation='targets', pool=0, substitution_report=str(args.candidate),
                   capture_substitution_worlds=True, substitution_foul_penalty=True)
    eng = backtest._W['engine']
    policy = eng.rotation_policy
    if policy is None:
        raise ValueError('S06 foul-penalty policy did not initialize')
    simulate = eng.simulate
    result = []
    args.worlds_dir.mkdir(parents=True)

    def run(g: engine.Game, _worlds: int, _seed: int) -> dict:
        if g.mstate is None:
            raise ValueError('stress game needs minute states')
        indices = np.flatnonzero(g.side == 1)
        selected = sorted(indices, key=lambda i: (-g.expected[i], str(g.ids[i])))[:5]
        if [str(g.ids[i]) for i in selected] != stress['result']['kept_away_player_ids']:
            raise ValueError('five-player synthetic roster differs from stress')
        kept = set(selected)
        side_start = int(indices[0])
        for index in indices:
            available = 1.0 if index in kept else 0.0
            g.avail[index] = available
            g.players['away'][index - side_start]['availability'] = available
            if index in kept:
                g.mstate[index].update(healthy=48.0, cap=48.0, priority=48.0, ramp=1.0, rotation=1.0)
        focal = int(selected[0])
        g.avail[focal] = g.players['away'][focal - side_start]['availability'] = 0.5
        branch = a1_lineup_branches.one_player(g, str(g.game['away_id']), str(g.ids[focal]), True)
        for rejection in stress['result']['rejections']:
            eng.rotation_policy = policy
            simulate(branch, 1, int(rejection['seed']))
            capture = a1_substitution_world_capture.capture(branch, eng.last, policy)
            audit = a1_substitution_world_audit.audit_worlds(capture, foul_penalty=True)
            path = args.worlds_dir / f'world-{len(result):03d}.npz'
            np.savez_compressed(path, **capture)
            result.append({'world': rejection['world'], 'attempt': rejection['attempt'],
                           'seed': rejection['seed'], 'original_rejection': rejection['reason'],
                           'capture': str(path), 'capture_sha256': sha256_file(path),
                           'audit': audit, 'technical_events': policy.technical_events.copy()})
            print(f"S06 seed {len(result)}/{len(stress['result']['rejections'])}: "
                  f"{len(policy.technical_events)} technicals", flush=True)
        raise CapturedGame()

    start = time.monotonic()
    try:
        with patch.object(eng, 'simulate', side_effect=run):
            backtest.run_game(stress['game'])
    except CapturedGame:
        pass
    if len(result) != len(stress['result']['rejections']):
        raise ValueError('not all rejected seeds were audited')
    if any(sha256_file(ROOT / name) != digest for name, digest in fingerprints.items()):
        raise ValueError('stress inputs or sources changed during comparison')
    write_json(args.output, {
        'kind': 'artificial five-player stress comparison; not an NBA rate or accuracy test',
        'stress': str(args.stress), 'stress_sha256': sha256_file(args.stress),
        'candidate': str(args.candidate), 'candidate_sha256': sha256_file(args.candidate),
        'analysis_sha256': sha256_file(Path(__file__)), 'game': stress['game'],
        'elapsed_seconds': round(time.monotonic() - start, 3), 'worlds': result,
        'limitations': ['Synthetic 48-minute roles on a deliberately restricted five-player roster.',
                        'S06 changes substitutions and random streams, so matching seeds are not matched game states.',
                        'Not a retry-versus-penalty bias or predictive accuracy comparison.',
                        'Neither policy is promoted or connected to production.'],
    }, pretty=True)
    print(f'{len(result)} S06 worlds audited', flush=True)


if __name__ == '__main__':
    main()
