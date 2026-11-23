#!/usr/bin/env python3
"""Independently replay matched continuation captures and failure states."""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from analysis import a1_f4_six_roster_full_audit as comparisons, a1_f4_six_roster_stress as stress  # noqa: E402
from analysis import a1_matched_penalty_run as runner  # noqa: E402
from analysis.a1_parallel_world_probe import capture_digest  # noqa: E402
from basketball_common import read_json, sha256_file, write_json  # noqa: E402
from scripts import a1_substitution_world_audit, projection  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an audit')
    report = read_json(args.report)
    source_path, manifest_path = ROOT / report['stress'], ROOT / report['manifest']
    if sha256_file(source_path) != report['stress_sha256'] or sha256_file(manifest_path) != report['manifest_sha256']:
        raise ValueError('source or manifest differs')
    source, manifest = read_json(source_path), read_json(manifest_path)
    details_path = ROOT / source['details']
    if sha256_file(details_path) != source['details_sha256']:
        raise ValueError('original manifest differs')
    prior = read_json(details_path)['attempts']
    selected = (sorted([r for r in prior if r['status'] == 'complete'][:5]
                       + [r for r in prior if r['status'] == 'exhausted'][:5], key=lambda r: r['draw'])
                if report['pilot'] else prior)
    if len(selected) != report['worlds'] or len(selected) != len(manifest['worlds']) or manifest['game'] != source['game']:
        raise ValueError('selected world population differs')
    fingerprints = manifest['fingerprints']

    def verify():
        if any(sha256_file(ROOT / name) != digest for name, digest in fingerprints.items()):
            raise ValueError('source or input changed')

    verify()
    panel = read_json(ROOT / read_json(stress.SUMMARY)['details'])
    game = [row for row in panel['games'] if row['game'] == stress.GAME]
    if len(game) != 1:
        raise ValueError('selected game is missing from panel')
    started = time.monotonic()
    stress.init_worker(game[0]['selected_player'])
    d29, continued = [], []
    identities = availability = sides = None
    legal_fives = technicals = failures = 0
    for previous, current in zip(selected, manifest['worlds'], strict=True):
        draw = previous['draw']
        if (current['draw'] != draw or current['seed'] != previous['seed']
                or int(current['seed']) != projection.seed_for('a1-f4-six-roster-v1', stress.GAME, draw)
                or current['original_status'] != previous['status']
                or read_json(manifest_path.parent / f'world-{draw:04d}.json') != current):
            raise ValueError('draw, seed, status or saved record differs')
        path = ROOT / current['capture']
        if path != manifest_path.parent / f'world-{draw:04d}.npz' or sha256_file(path) != current['capture_sha256']:
            raise ValueError('continuation capture path or hash differs')
        with np.load(path, allow_pickle=False) as data:
            captured = dict(data)
        if str(captured['game_id']) != stress.GAME:
            raise ValueError('game differs')
        audit = a1_substitution_world_audit.audit_worlds(captured, foul_penalty=True)
        if audit != current['audit'] or audit['worlds'] != 1:
            raise ValueError('saved continuation accounting differs')
        value, identities, availability = comparisons.metrics(captured, identities, availability, sides)
        sides = captured['side']
        continued.append(value)
        legal_fives += audit['lineup_fives_checked']
        technicals += audit['foul_penalty_events']
        if previous['status'] == 'exhausted':
            if runner.original_failure(previous) != current['first_exhaustion']:
                raise ValueError('independent original failure replay differs')
            d29.append(np.full(len(value), np.nan))
            failures += 1
        elif previous['status'] == 'complete':
            if current['first_exhaustion'] is not None:
                raise ValueError('survivor was marked exhausted')
            original_path = ROOT / previous['capture']
            if sha256_file(original_path) != previous['capture_sha256']:
                raise ValueError('original survivor hash differs')
            with np.load(original_path, allow_pickle=False) as data:
                original = dict(data)
            if (capture_digest(original) != previous['world_sha256']
                    or capture_digest({key: captured[key] for key in original}) != previous['world_sha256']):
                raise ValueError('saved survivor trajectory differs')
            d29.append(comparisons.metrics(original, identities, availability, sides)[0])
        else:
            raise ValueError('unknown original outcome')
    results = None
    if not report['pilot']:
        d29, continued = np.asarray(d29), np.asarray(continued)
        if len(d29) != 1000 or failures != 202:
            raise ValueError('full continuation population differs')
        draws = np.random.default_rng(20261122).integers(0, 1000, (5000, 1000))
        difference, intervals = comparisons.estimates(d29, continued, draws)
        home_ids = identities[(sides == 0) & availability]
        labels = ['home_points', 'away_points', 'total_points', 'home_margin']
        labels += [f'home_player_{pid}_points' for pid in home_ids]
        labels += [f'home_player_{pid}_minutes' for pid in home_ids]
        results = {label: {'d29_survivor_mean': float(np.nanmean(d29[:, i])),
                           'continuation_mean': float(continued[:, i].mean()),
                           'difference': float(difference[i]), 'ci_95': intervals[i].tolist()}
                   for i, label in enumerate(labels)}
    verify()
    write_json(args.output, {
        'kind': 'independent selected matched D29 continuation accounting',
        'report': str(args.report), 'report_sha256': sha256_file(args.report),
        'audit_sha256': sha256_file(Path(__file__)), 'pilot': report['pilot'],
        'worlds': len(selected), 'original_failures_replayed': failures,
        'survivor_trajectories_matched': len(selected) - failures,
        'lineup_fives_checked': legal_fives, 'technical_events': technicals, 'metrics': results,
        'bootstrap': {'replicates': 5000, 'seed': 20261122, 'unit': 'original seed',
                      'interval': '95% percentile, unadjusted across metrics'} if results else None,
        'elapsed_seconds': round(time.monotonic() - started, 3), 'limitations': report['limitations'],
    }, pretty=True)
    print(f'{len(selected)} worlds audited, {failures} first-failure states independently replayed', flush=True)


if __name__ == '__main__':
    main()
