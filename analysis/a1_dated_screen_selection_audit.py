#!/usr/bin/env python3
"""Independently reconstruct the saved-screen selection estimates."""
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

NAMES = {'F1': '20261122_a1_dated_f1_screen_v2',
         'F2': '20261122_a1_dated_f2_screen_v1',
         'F3': '20261122_a1_dated_f3_screen_v1'}
LABELS = ('home_points', 'away_points', 'total_points', 'home_margin')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an audit')
    start = time.monotonic()
    result = read_json(args.report)
    if any(sha256_file(ROOT / name) != digest for name, digest in result['fingerprints'].items()):
        raise ValueError('report source fingerprint differs')
    matched_report = read_json(ROOT / 'analysis/experiments/20261122_a1_dated_matched_f1_full_v1.json')
    matched_path = ROOT / matched_report['manifest']
    if sha256_file(matched_path) != matched_report['manifest_sha256']:
        raise ValueError('matched manifest differs')
    matched = read_json(matched_path)
    panel = read_json(ROOT / 'analysis/experiments/20261122_a1_pre_candidate_manifest.json')
    totals = []
    for fold, expected in zip(NAMES, result['folds'], strict=True):
        screen_path = ROOT / f'analysis/experiments/{NAMES[fold]}.json'
        screen, screen_audit = read_json(screen_path), read_json(screen_path.with_name(screen_path.stem + '_audit.json'))
        if screen_audit['summary_sha256'] != sha256_file(screen_path):
            raise ValueError('screen audit differs')
        detail_path = ROOT / screen['details']
        if sha256_file(detail_path) != screen['details_sha256']:
            raise ValueError('screen manifest differs')
        games = read_json(detail_path)['games']
        declared = panel['confirmation'][fold]['games']
        if (len(games) != 200 or [g['game'] for g in games] != [g['game_id'] for g in declared]
                or any(g['day'] != d['date_et'] for g, d in zip(games, declared, strict=True))):
            raise ValueError('frozen game panel differs')
        sums = np.zeros((200, 2, 4))
        counts = np.zeros((200, 2), dtype=int)
        failed = None
        failures = 0
        for i, game in enumerate(games):
            if [b['branch'] for b in game['branches']] != ['plays', 'sits']:
                raise ValueError('branch coverage differs')
            for branch in game['branches']:
                if branch['status'] != 'simulated':
                    if branch['status'] not in ('invalid initial roster or allocation',
                                                 'unsupported missing position') or branch['attempts']:
                        raise ValueError('unsupported branch differs')
                    continue
                if len(branch['attempts']) != 5:
                    raise ValueError('attempt count differs')
                branch_players = []
                for draw, attempt in enumerate(branch['attempts']):
                    seed = str(seed_for('a1-dated-fold-exhaustion-v1', fold, game['game'], branch['branch'], draw))
                    if attempt['draw'] != draw or attempt['seed'] != seed:
                        raise ValueError('attempt identity differs')
                    success = attempt['status'] == 'complete'
                    if success:
                        path, digest = ROOT / attempt['capture'], attempt['capture_sha256']
                    elif attempt['status'] == 'exhausted' and fold == 'F1' and game['game'] == matched['game'] \
                            and branch['branch'] == 'sits':
                        record = matched['worlds'][draw]
                        if (record['draw'] != draw or record['seed'] != seed or record['status'] != 'exhausted'
                                or record['failure']['reason'] != attempt['reason']):
                            raise ValueError('continuation identity differs')
                        path, digest = ROOT / record['capture'], record['capture_sha256']
                        failures += 1
                    else:
                        raise ValueError('unmatched failure or unknown status')
                    if sha256_file(path) != digest:
                        raise ValueError('capture hash differs')
                    with np.load(path, allow_pickle=False) as data:
                        if str(data['game_id']) != game['game']:
                            raise ValueError('capture game differs')
                        score = data['final_score'][0]
                        side, available = data['side'], data['available'][0]
                        points, minutes = data['player_points'][0].sum(axis=1), data['minutes'][0].sum(axis=1)
                        selected = np.flatnonzero(data['player_ids'] == game['selected_player'])
                        if (len(selected) != 1 or side[selected[0]] != 0
                                or bool(available[selected[0]]) != (branch['branch'] == 'plays')
                                or not np.array_equal(score, data['team_points'][0].sum(axis=1))
                                or any(points[side == j].sum() != score[j] for j in (0, 1))):
                            raise ValueError('capture availability or points differ')
                        values = np.array([score[0], score[1], score.sum(), score[0] - score[1]])
                        home = (side == 0) & available
                        branch_players.append((success, {str(pid): (float(p), float(m)) for pid, p, m in
                                                zip(data['player_ids'][home], points[home], minutes[home], strict=True)}))
                    sums[i, 1] += values
                    counts[i, 1] += 1
                    if success:
                        sums[i, 0] += values
                        counts[i, 0] += 1
                if any(not success for success, _ in branch_players):
                    if failed is not None:
                        raise ValueError('multiple affected branches')
                    failed = (game['game'], branch['branch'], branch_players)
            if (i + 1) % 20 == 0:
                print(f'{fold}: {i + 1}/200 games independently checked', flush=True)
        if (expected['fold'] != fold or expected['games'] != 200 or expected['attempts'] != counts[:, 1].sum()
                or expected['survivors'] != counts[:, 0].sum() or expected['exhausted'] != failures
                or failures != screen['exhausted']):
            raise ValueError('aggregate counts differ')
        random = np.random.default_rng(20261122).integers(0, 200, (5000, 200))
        aggregate = sums.sum(axis=0) / counts.sum(axis=0)[:, None]
        sampled = sums[random].sum(axis=1) / counts[random].sum(axis=1)[:, :, None]
        intervals = np.quantile(sampled[:, 0] - sampled[:, 1], [0.025, 0.975], axis=0)
        for k, label in enumerate(LABELS):
            observed = expected['metrics'][label]
            np.testing.assert_allclose([observed['survivor_mean'], observed['continuation_mean'],
                                        observed['difference'], *observed['ci_95']],
                                       [aggregate[0, k], aggregate[1, k], aggregate[0, k] - aggregate[1, k],
                                        *intervals[:, k]], rtol=0, atol=1e-10)
        if failed is None:
            if expected['affected_branch'] is not None:
                raise ValueError('unexpected affected branch')
        else:
            game, branch, rows = failed
            affected = expected['affected_branch']
            ids = set(rows[0][1])
            if (affected['game'] != game or affected['branch'] != branch or set(affected['players']) != ids
                    or any(set(players) != ids for _, players in rows)):
                raise ValueError('affected player identities differ')
            for pid in ids:
                for column, stat in enumerate(('points', 'minutes')):
                    valid = [players[pid][column] for success, players in rows if success]
                    all_values = [players[pid][column] for _, players in rows]
                    first, second = np.mean(valid), np.mean(all_values)
                    actual = affected['players'][pid][stat]
                    np.testing.assert_allclose([actual['survivor_mean'], actual['continuation_mean'],
                                                actual['difference']], [first, second, first - second],
                                               rtol=0, atol=1e-10)
        totals.append({'fold': fold, 'games': len(games), 'attempts': int(counts[:, 1].sum()),
                       'exhausted': failures, 'checked_metrics': len(LABELS),
                       'checked_affected_players': len(failed[2][0][1]) if failed else 0})
    if any(sha256_file(ROOT / name) != digest for name, digest in result['fingerprints'].items()):
        raise ValueError('report source changed during audit')
    write_json(args.output, {'kind': 'independent saved-screen selection accounting',
                             'report': str(args.report), 'report_sha256': sha256_file(args.report),
                             'folds': totals, 'elapsed_seconds': round(time.monotonic() - start, 3),
                             'limitations': result['limitations']}, pretty=True)


if __name__ == '__main__':
    main()
