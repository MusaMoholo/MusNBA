#!/usr/bin/env python3
"""Count roster and foul-out pressure in completed research branch captures."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from analysis.a1_branch_persist_audit import audit  # noqa: E402
from basketball_common import read_json, sha256_file, write_json  # noqa: E402


def pressure(available: np.ndarray, fouls: np.ndarray, side: np.ndarray) -> dict:
    if (available.ndim != 2 or available.dtype != bool or side.shape != (available.shape[1],)
            or not np.isin(side, (0, 1)).all() or fouls.shape != (*available.shape, 5)
            or not np.isfinite(fouls).all() or (fouls < 0).any()
            or (fouls[~available] != 0).any()):
        raise ValueError('invalid roster, availability or foul dimensions')
    totals = fouls.sum(axis=2)
    if (totals > 6).any():
        raise ValueError('foul count exceeds the repaired-policy limit')
    rows = []
    for team in (0, 1):
        on_team = side == team
        initial = available[:, on_team].sum(axis=1)
        disqualified = ((totals[:, on_team] >= 6) & available[:, on_team]).sum(axis=1)
        eligible = initial - disqualified
        if (initial < 5).any() or (eligible < 5).any():
            raise ValueError('completed world has fewer than five eligible players')
        pairs, counts = np.unique(np.stack((initial, disqualified), axis=1), axis=0, return_counts=True)
        rows.append({
            'side': 'home' if team == 0 else 'away',
            'team_worlds': len(initial),
            'exactly_five_initial': int((initial == 5).sum()),
            'exactly_five_final_eligible': int((eligible == 5).sum()),
            'any_six_foul_player': int((disqualified > 0).sum()),
            'counts_by_initial_and_six_fouls': [
                {'initial': int(pair[0]), 'six_foul_players': int(pair[1]), 'worlds': int(count)}
                for pair, count in zip(pairs, counts, strict=True)
            ],
        })
    return {'worlds': len(available), 'sides': rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifests', type=Path, nargs='+')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an experiment')
    results = []
    for path in args.manifests:
        manifest_hash = sha256_file(path)
        report = read_json(path)
        audit(report)
        branches = []
        for index, record in enumerate(report['branches']):
            capture = Path(record['capture'])
            if sha256_file(capture) != record['capture_sha256']:
                raise ValueError('capture changed since manifest audit')
            with np.load(capture, allow_pickle=False) as data:
                counts = pressure(data['available'], data['player_fouls'], data['side'])
            if counts['worlds'] != record['worlds'] or sha256_file(capture) != record['capture_sha256']:
                raise ValueError('capture changed or world count differs')
            branches.append({'index': index, 'weight': record['weight'],
                             'capture_sha256': record['capture_sha256'], **counts})
        if sha256_file(path) != manifest_hash:
            raise ValueError('manifest changed during audit')
        results.append({'game': report['game'], 'origin': report['origin'], 'manifest': str(path),
                        'manifest_sha256': manifest_hash, 'branches': branches})
    if len({item['game'] for item in results}) != len(results):
        raise ValueError('duplicate games')
    write_json(args.output, {
        'kind': 'completed research-branch roster pressure; not a forecast or failure-rate estimate',
        'script_sha256': sha256_file(Path(__file__)),
        'manifest_auditor_sha256': sha256_file(ROOT / 'analysis/a1_branch_persist_audit.py'),
        'games': results,
        'limitations': ['Completed batches only; failed or missing attempts cannot be counted.',
                        'Branch probabilities are uncalibrated assumptions, not actual injury rates.',
                        'Three selected games are not representative development folds or NBA outcomes.'],
    }, pretty=True)
    print(f"Audited {sum(b['worlds'] for game in results for b in game['branches']):,} completed worlds")


if __name__ == '__main__':
    main()
