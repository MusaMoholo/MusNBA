#!/usr/bin/env python3
"""Independently audit earlier-fold branch exhaustion captures."""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from analysis.a1_parallel_world_probe import capture_digest  # noqa: E402
from basketball_common import read_json, sha256_file, write_json  # noqa: E402
from scripts import evaluate, projection  # noqa: E402
from scripts.a1_substitution_world_audit import audit_worlds  # noqa: E402

MANIFEST = ROOT / 'analysis/experiments/20261122_a1_pre_candidate_manifest.json'


def totals(games: list[dict]) -> dict:
    clusters = []
    invalid = 0
    for game in games:
        branches = game['branches']
        invalid += sum(b['status'] != 'simulated' for b in branches)
        attempts = [a for branch in branches for a in branch['attempts']]
        clusters.append((len(attempts), sum(a['status'] == 'exhausted' for a in attempts)))
    rows = np.asarray(clusters, dtype=int)
    attempts, exhausted = rows.sum(axis=0)
    interval = None
    if exhausted and attempts:
        rng = np.random.default_rng(20261122)
        rates = []
        for _ in range(5000):
            sampled = rows[rng.integers(0, len(rows), size=len(rows))].sum(axis=0)
            if sampled[0] == 0:
                raise ValueError('bootstrap sample has no attempts')
            rates.append(sampled[1] / sampled[0])
        interval = np.quantile(rates, [0.025, 0.975]).tolist()
    return {'games': len(games), 'attempts': int(attempts), 'exhausted': int(exhausted),
            'invalid_initial_branches': int(invalid),
            'exhaustion_fraction': float(exhausted / attempts) if attempts else None,
            'game_cluster_bootstrap_95': interval,
            'interval_note': '5000 game-cluster bootstrap replicates, seed 20261122; '
                             'not calculated for zero observed exhaustions'}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('summary', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an audit')
    summary = read_json(args.summary)
    detail_path = Path(summary['details'])
    if sha256_file(detail_path) != summary['details_sha256']:
        raise ValueError('detailed manifest differs')
    details = read_json(detail_path)
    fold = summary['fold']
    if details['fold'] != fold or fold not in ('F1', 'F2', 'F3'):
        raise ValueError('fold differs')
    if any(sha256_file(ROOT / name) != digest for name, digest in details['fingerprints'].items()):
        raise ValueError('source, model or input differs')
    declared = read_json(MANIFEST)['confirmation'][fold]['games']
    if ([game['game'] for game in details['games']] != [g['game_id'] for g in declared]
            or len(declared) != 200):
        raise ValueError('fixed game panel differs')
    started = time.monotonic()
    completed = exhausted = snapshots = 0
    paths = set()
    for game, expected_game in zip(details['games'], declared, strict=True):
        if (game['day'] != expected_game['date_et']
                or not evaluate.FOLDS[fold][1] <= game['day'] <= evaluate.FOLDS[fold][2]
                or read_json(detail_path.parent / f"{game['game']}.json") != game):
            raise ValueError('game, date or record differs')
        if [b['branch'] for b in game['branches']] != ['plays', 'sits']:
            raise ValueError('branch coverage differs')
        for branch in game['branches']:
            if branch['status'] == 'invalid initial roster or allocation':
                if branch['attempts'] or not branch['reason']:
                    raise ValueError('invalid branch has attempts or no reason')
                continue
            if branch['status'] != 'simulated' or len(branch['attempts']) != 5:
                raise ValueError('branch did not record five attempts')
            for draw, attempt in enumerate(branch['attempts']):
                seed = projection.seed_for('a1-dated-fold-exhaustion-v1', fold, game['game'], branch['branch'], draw)
                if attempt['draw'] != draw or int(attempt['seed']) != seed:
                    raise ValueError('draw or seed differs')
                if attempt['status'] == 'exhausted':
                    if 'fewer than five eligible players' not in attempt['reason']:
                        raise ValueError('unclassified world rejection')
                    exhausted += 1
                    continue
                if attempt['status'] != 'complete':
                    raise ValueError('unknown attempt status')
                path = Path(attempt['capture'])
                if path in paths or path.parent != detail_path.parent or sha256_file(path) != attempt['capture_sha256']:
                    raise ValueError('capture path or hash differs')
                paths.add(path)
                with np.load(path, allow_pickle=False) as data:
                    capture = {key: data[key] for key in data.files}
                    if str(capture['game_id']) != game['game'] or capture_digest(capture) != attempt['world_sha256']:
                        raise ValueError('captured world identity differs')
                    selected = np.flatnonzero(capture['player_ids'] == game['selected_player'])
                    if (len(selected) != 1 or capture['side'][selected[0]] != 0
                            or bool(capture['available'][0, selected[0]]) != (branch['branch'] == 'plays')):
                        raise ValueError('selected player or fixed branch availability differs')
                    result = audit_worlds(capture)
                if result != attempt['audit'] or result['worlds'] != 1:
                    raise ValueError('world accounting differs')
                completed += 1
                snapshots += result['lineup_snapshots']
    aggregate = totals(details['games'])
    if any(summary[key] != value for key, value in aggregate.items()) or exhausted != aggregate['exhausted']:
        raise ValueError('aggregate accounting differs')
    if completed + exhausted != aggregate['attempts']:
        raise ValueError('attempt counts do not reconcile')
    if any(sha256_file(ROOT / name) != digest for name, digest in details['fingerprints'].items()):
        raise ValueError('source or input changed during audit')
    write_json(args.output, {'kind': 'independent fixed earlier-fold saved-world accounting',
                             'summary': str(args.summary), 'summary_sha256': sha256_file(args.summary),
                             'audit_sha256': sha256_file(Path(__file__)), **aggregate,
                             'completed_worlds': completed, 'lineup_snapshots': snapshots,
                             'elapsed_seconds': round(time.monotonic() - started, 3),
                             'limitations': summary['limitations']}, pretty=True)
    print(f'{fold}: {completed} completed worlds, {exhausted} exhaustions audited', flush=True)


if __name__ == '__main__':
    main()
