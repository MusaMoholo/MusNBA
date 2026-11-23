#!/usr/bin/env python3
"""Audit halftime snapshots and quantify survivor conditioning in a selected stress case."""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import read_json, sha256_file, write_json  # noqa: E402
from scripts.projection import seed_for  # noqa: E402


def metrics(data) -> np.ndarray:
    side, available = data['side'], data['available']
    minutes, points, fouls = data['minutes'], data['player_points'], data['player_fouls']
    team_points, score = data['team_points'], data['score']
    n = len(side)
    if (available.shape != (n,) or minutes.shape != (n, 5) or points.shape != (n, 5)
            or fouls.shape != (n, 5) or team_points.shape != (2, 5) or score.shape != (2,)
            or set(side.tolist()) != {0, 1} or int(available[side == 0].sum()) != 6):
        raise ValueError('invalid halftime dimensions, teams or roster')
    if (not np.isfinite(minutes).all() or (minutes < 0).any() or (points < 0).any() or (fouls < 0).any()
            or (minutes[~available] != 0).any() or (points[~available] != 0).any()
            or (fouls[~available] != 0).any() or (minutes[:, 2:] != 0).any()
            or (points[:, 2:] != 0).any() or (fouls[:, 2:] != 0).any()):
        raise ValueError('invalid halftime player accounting')
    for team in (0, 1):
        if (not np.allclose(minutes[side == team, :2].sum(axis=0), [60, 60], atol=1e-8, rtol=0)
                or not np.array_equal(points[side == team].sum(axis=0), team_points[team])
                or team_points[team].sum() != score[team]):
            raise ValueError('halftime minutes or points do not reconcile')
    home_fouls = fouls[side == 0].sum(axis=1)
    return np.array([score[0], score[1], home_fouls.sum(), (home_fouls >= 3).sum()], dtype=float)


def summary(values: np.ndarray, succeeded: np.ndarray) -> dict:
    if values.shape != (1000, 4) or succeeded.shape != (1000,) or succeeded.sum() != 798:
        raise ValueError('unexpected sample or success count')
    generator = np.random.default_rng(20261122)
    differences = np.empty((5000, 4))
    for i in range(len(differences)):
        sample = generator.integers(0, len(values), size=len(values))
        chosen = succeeded[sample]
        if not chosen.any():
            raise ValueError('bootstrap sample has no survivors')
        differences[i] = values[sample][chosen].mean(axis=0) - values[sample].mean(axis=0)
    names = ('home_score', 'away_score', 'home_personal_fouls', 'home_players_three_plus_fouls')
    result = {}
    for index, name in enumerate(names):
        all_mean = values[:, index].mean()
        survivor_mean = values[succeeded, index].mean()
        failed_mean = values[~succeeded, index].mean()
        result[name] = {'all_attempts_mean': float(all_mean), 'survivors_mean': float(survivor_mean),
                        'failed_mean': float(failed_mean), 'survivor_minus_all': float(survivor_mean - all_mean),
                        'bootstrap_95_percentile': np.quantile(differences[:, index], [0.025, 0.975]).tolist()}
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an audit')
    report = read_json(args.report)
    source_path = ROOT / report['stress']
    if sha256_file(source_path) != report['stress_sha256']:
        raise ValueError('stress summary differs')
    source = read_json(source_path)
    source_detail = ROOT / source['details']
    if sha256_file(source_detail) != source['details_sha256']:
        raise ValueError('stress manifest differs')
    previous = read_json(source_detail)['attempts']
    manifest_path = Path(report['manifest'])
    if sha256_file(manifest_path) != report['manifest_sha256']:
        raise ValueError('halftime manifest differs')
    manifest = read_json(manifest_path)
    if len(previous) != 1000 or len(manifest['worlds']) != 1000 or manifest['game'] != source['game']:
        raise ValueError('sample or game differs')
    fingerprints = manifest['fingerprints']
    if any(sha256_file(ROOT / name) != digest for name, digest in fingerprints.items()):
        raise ValueError('source, model or input changed')
    started = time.monotonic()
    values, successes = [], []
    for draw, (old, current) in enumerate(zip(previous, manifest['worlds'], strict=True)):
        if (old['draw'] != draw or current['draw'] != draw or old['seed'] != current['seed']
                or int(current['seed']) != seed_for('a1-f4-six-roster-v1', source['game'], draw)
                or old['status'] != current['status']
                or read_json(manifest_path.parent / f'world-{draw:04d}.json') != current):
            raise ValueError('draw, seed, status or saved record differs')
        if current['status'] == 'exhausted':
            if old['reason'] != current['reason']:
                raise ValueError('rejection reason differs')
        elif current['status'] == 'complete':
            if old['world_sha256'] != current['world_sha256']:
                raise ValueError('complete world differs')
        else:
            raise ValueError('unknown status')
        path = Path(current['capture'])
        if path != manifest_path.parent / f'world-{draw:04d}.npz' or sha256_file(path) != current['capture_sha256']:
            raise ValueError('halftime capture path or hash differs')
        with np.load(path, allow_pickle=False) as data:
            values.append(metrics(data))
        successes.append(current['status'] == 'complete')
    results = summary(np.asarray(values), np.asarray(successes, dtype=bool))
    if results != report['metrics']:
        raise ValueError('halftime selection or bootstrap results differ')
    if any(sha256_file(ROOT / name) != digest for name, digest in fingerprints.items()):
        raise ValueError('source or input changed during audit')
    write_json(args.output, {'kind': 'independent selected six-player halftime accounting',
                             'report': str(args.report), 'report_sha256': sha256_file(args.report),
                             'audit_sha256': sha256_file(Path(__file__)), 'attempts': len(previous),
                             'completed': sum(successes), 'exhausted': len(successes) - sum(successes),
                             'metrics': results, 'elapsed_seconds': round(time.monotonic() - started, 3),
                             'limitations': report['limitations']}, pretty=True)
    print(f'{len(previous)} halftime snapshots, seed identities and selection estimates reconciled')


if __name__ == '__main__':
    main()
