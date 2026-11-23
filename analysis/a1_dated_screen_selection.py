#!/usr/bin/env python3
"""Reconcile saved earlier-fold screens with their one matched continuation."""
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

SCREENS = {'F1': '20261122_a1_dated_f1_screen_v2',
           'F2': '20261122_a1_dated_f2_screen_v1',
           'F3': '20261122_a1_dated_f3_screen_v1'}
MATCHED = '20261122_a1_dated_matched_f1_full_v1'
LABELS = ('home_points', 'away_points', 'total_points', 'home_margin')


def sources(fold):
    base = ROOT / 'analysis/experiments'
    screen_path = base / f'{SCREENS[fold]}.json'
    screen, audit = read_json(screen_path), read_json(base / f'{SCREENS[fold]}_audit.json')
    if audit['summary_sha256'] != sha256_file(screen_path):
        raise ValueError('screen audit does not match summary')
    detail_path = ROOT / screen['details']
    if sha256_file(detail_path) != screen['details_sha256']:
        raise ValueError('screen manifest differs')
    detail = read_json(detail_path)
    if screen['fold'] != fold or detail['fold'] != fold or len(detail['games']) != 200:
        raise ValueError('screen fold or game count differs')
    matched_path = base / f'{MATCHED}.json'
    matched, matched_audit = read_json(matched_path), read_json(base / f'{MATCHED}_audit.json')
    if matched_audit['report_sha256'] != sha256_file(matched_path):
        raise ValueError('matched audit does not match report')
    manifest_path = ROOT / matched['manifest']
    if sha256_file(manifest_path) != matched['manifest_sha256']:
        raise ValueError('matched manifest differs')
    manifest = read_json(manifest_path)
    return screen, detail, manifest


def load_capture(path, digest, game):
    if sha256_file(path) != digest:
        raise ValueError('capture hash differs')
    with np.load(path, allow_pickle=False) as data:
        if str(data['game_id']) != game:
            raise ValueError('capture game differs')
        score = np.asarray(data['final_score'][0], dtype=float)
        if score.shape != (2,) or not np.array_equal(score, data['team_points'][0].sum(axis=1)):
            raise ValueError('saved team scores do not reconcile')
        side = data['side']
        points = data['player_points'][0].sum(axis=1)
        if any(points[side == i].sum() != score[i] for i in (0, 1)):
            raise ValueError('saved player points do not reconcile')
        home = (side == 0) & data['available'][0]
        players = {str(pid): [float(pts), float(minutes)] for pid, pts, minutes in zip(
            data['player_ids'][home], points[home], data['minutes'][0, home].sum(axis=1), strict=True)}
        if len(players) != int(home.sum()):
            raise ValueError('duplicate home player IDs')
        return np.array([score[0], score[1], score.sum(), score[0] - score[1]]), players


def compare(original_sum, original_count, continued_sum, continued_count, draws):
    if (original_sum.shape != continued_sum.shape or original_sum.ndim != 2
            or original_sum.shape[1] != len(LABELS) or original_count.shape != continued_count.shape
            or original_count.shape != (len(original_sum),) or draws.ndim != 2
            or draws.shape[1] != len(original_sum)):
        raise ValueError('invalid game-cluster dimensions')
    oc, cc = original_count.sum(), continued_count.sum()
    if not oc or not cc:
        raise ValueError('comparison has no worlds')
    bo, bc = original_count[draws].sum(axis=1), continued_count[draws].sum(axis=1)
    if (bo == 0).any() or (bc == 0).any():
        raise ValueError('bootstrap sample has no worlds')
    original = original_sum.sum(axis=0) / oc
    continued = continued_sum.sum(axis=0) / cc
    boot = original_sum[draws].sum(axis=1) / bo[:, None] - continued_sum[draws].sum(axis=1) / bc[:, None]
    return {key: {'survivor_mean': float(original[i]), 'continuation_mean': float(continued[i]),
                  'difference': float(original[i] - continued[i]),
                  'ci_95': np.quantile(boot[:, i], [0.025, 0.975]).tolist()}
            for i, key in enumerate(LABELS)}


def calculate(fold):
    screen, detail, matched = sources(fold)
    original_sum = np.zeros((200, 4))
    continued_sum = np.zeros((200, 4))
    original_count = np.zeros(200, dtype=int)
    continued_count = np.zeros(200, dtype=int)
    affected = None
    exhausted = completed = 0
    for index, game in enumerate(detail['games']):
        for branch in game['branches']:
            if branch['status'] != 'simulated':
                if branch['status'] not in ('invalid initial roster or allocation', 'unsupported missing position') \
                        or branch['attempts']:
                    raise ValueError('unsupported branch has attempts or unknown status')
                continue
            if len(branch['attempts']) != 5:
                raise ValueError('screen branch does not have five attempts')
            player_rows = []
            for draw, attempt in enumerate(branch['attempts']):
                seed = str(seed_for('a1-dated-fold-exhaustion-v1', fold, game['game'], branch['branch'], draw))
                if attempt['draw'] != draw or attempt['seed'] != seed:
                    raise ValueError('screen draw or seed differs')
                if attempt['status'] == 'complete':
                    path, digest = ROOT / attempt['capture'], attempt['capture_sha256']
                    completed += 1
                elif attempt['status'] == 'exhausted':
                    if fold != 'F1' or game['game'] != matched['game'] or branch['branch'] != 'sits':
                        raise ValueError('no audited continuation for exhausted attempt')
                    record = matched['worlds'][draw]
                    if (record['draw'] != draw or record['seed'] != seed or record['status'] != 'exhausted'
                            or record['failure']['reason'] != attempt['reason']):
                        raise ValueError('matched continuation identity differs')
                    path, digest = ROOT / record['capture'], record['capture_sha256']
                    exhausted += 1
                else:
                    raise ValueError('unknown attempt status')
                score, players = load_capture(path, digest, game['game'])
                player_rows.append((attempt['status'], players))
                continued_sum[index] += score
                continued_count[index] += 1
                if attempt['status'] == 'complete':
                    original_sum[index] += score
                    original_count[index] += 1
            if any(status == 'exhausted' for status, _ in player_rows):
                ids = set(player_rows[0][1])
                if any(set(players) != ids for _, players in player_rows) or affected is not None:
                    raise ValueError('affected branch identities or count differ')
                affected = {'game': game['game'], 'branch': branch['branch'], 'players': {}}
                for pid in sorted(ids):
                    survivor = np.array([players[pid] for status, players in player_rows if status == 'complete'])
                    all_values = np.array([players[pid] for _, players in player_rows])
                    affected['players'][pid] = {
                        stat: {'survivor_mean': float(survivor[:, i].mean()),
                               'continuation_mean': float(all_values[:, i].mean()),
                               'difference': float(survivor[:, i].mean() - all_values[:, i].mean())}
                        for i, stat in enumerate(('points', 'minutes'))}
        if (index + 1) % 20 == 0:
            print(f'{fold}: {index + 1}/200 games reconciled', flush=True)
    if (completed != screen['attempts'] - screen['exhausted'] or exhausted != screen['exhausted']
            or int(continued_count.sum()) != screen['attempts']):
        raise ValueError('screen attempt counts differ')
    rng = np.random.default_rng(20261122)
    draws = rng.integers(0, 200, (5000, 200))
    return {'fold': fold, 'games': 200, 'attempts': int(continued_count.sum()), 'survivors': completed,
            'exhausted': exhausted, 'metrics': compare(original_sum, original_count, continued_sum,
                                                        continued_count, draws), 'affected_branch': affected}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an experiment')
    start = time.monotonic()
    folds = [calculate(fold) for fold in SCREENS]
    paths = [ROOT / f'analysis/experiments/{name}{suffix}.json'
             for name in (*SCREENS.values(), MATCHED) for suffix in ('', '_audit')]
    paths += [Path(__file__), ROOT / 'analysis/a1_dated_screen_selection_audit.py']
    write_json(args.output, {
        'kind': 'retrospective screen matched-continuation accounting; research only',
        'folds': folds, 'fingerprints': {str(p.relative_to(ROOT)): sha256_file(p) for p in paths},
        'bootstrap': {'replicates': 5000, 'seed': 20261122, 'unit': 'game',
                      'interval': '95% percentile, unadjusted'},
        'elapsed_seconds': round(time.monotonic() - start, 3),
        'limitations': ['Oracle actual-participant rosters, synthetic absences and five attempts per branch.',
                        'One explicit continuation assumption; no real-outcome or predictive comparison.',
                        'One exhausted attempt makes intervals fragile; zero is not proof of no population risk.'],
    }, pretty=True)


if __name__ == '__main__':
    main()
