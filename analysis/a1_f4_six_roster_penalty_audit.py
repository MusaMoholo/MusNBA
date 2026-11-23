#!/usr/bin/env python3
"""Independently replay saved S06 captures for the selected six-player stress."""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import read_json, sha256_file, write_json  # noqa: E402
from scripts import a1_substitution_world_audit, projection  # noqa: E402


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
    rejected = [r for r in read_json(source_detail)['attempts'] if r['status'] == 'exhausted']
    manifest_path = Path(report['manifest'])
    if sha256_file(manifest_path) != report['manifest_sha256']:
        raise ValueError('comparison manifest differs')
    manifest = read_json(manifest_path)
    if manifest['game'] != source['game'] or len(rejected) != report['worlds'] or len(rejected) != len(manifest['worlds']):
        raise ValueError('game or world count differs')
    if any(sha256_file(ROOT / name) != digest for name, digest in manifest['fingerprints'].items()):
        raise ValueError('source, model or input changed')
    started = time.monotonic()
    technicals = event_worlds = fives = 0
    for previous, current in zip(rejected, manifest['worlds'], strict=True):
        draw = previous['draw']
        if (current['draw'] != draw or current['seed'] != previous['seed']
                or int(current['seed']) != projection.seed_for('a1-f4-six-roster-v1', source['game'], draw)
                or current['original_rejection'] != previous['reason']
                or read_json(manifest_path.parent / f'world-{draw:04d}.json') != current):
            raise ValueError('rejected draw, seed or record differs')
        path = Path(current['capture'])
        if path != manifest_path.parent / f'world-{draw:04d}.npz' or sha256_file(path) != current['capture_sha256']:
            raise ValueError('capture path or hash differs')
        with np.load(path, allow_pickle=False) as data:
            if (str(data['game_id']) != source['game']
                    or (data['available'][:, data['side'] == 0].sum(axis=1) != 6).any()):
                raise ValueError('game or six-player branch differs')
            audit = a1_substitution_world_audit.audit_worlds(data, foul_penalty=True)
            if audit != current['audit'] or audit['worlds'] != 1:
                raise ValueError('saved-world accounting differs')
            for key in ('world', 'period', 'clock', 'fouler', 'shooter', 'made', 'probability'):
                actual = data[f'technical_{key}']
                expected = np.asarray([event[key] for event in current['technical_events']], dtype=actual.dtype)
                if not np.array_equal(actual, expected):
                    raise ValueError('technical-event record differs')
        technicals += audit['foul_penalty_events']
        event_worlds += audit['foul_penalty_events'] > 0
        fives += audit['lineup_fives_checked']
    if technicals != report['technical_events'] or event_worlds != report['worlds_with_technical']:
        raise ValueError('technical totals differ')
    if any(sha256_file(ROOT / name) != digest for name, digest in manifest['fingerprints'].items()):
        raise ValueError('source or input changed during audit')
    write_json(args.output, {
        'kind': 'independent selected six-player S06 saved-world accounting',
        'report': str(args.report), 'report_sha256': sha256_file(args.report),
        'audit_sha256': sha256_file(Path(__file__)), 'worlds': len(rejected),
        'technical_events': technicals, 'worlds_with_technical': event_worlds,
        'lineup_fives_checked': fives, 'elapsed_seconds': round(time.monotonic() - started, 3),
        'limitations': ['Selected oracle-roster game with a synthetic absence and D29-rejected seeds.',
                        'Different policies and random paths; same seeds do not establish matched states or bias.'],
    }, pretty=True)
    print(f'{len(rejected)} saved worlds, {fives} fives and {technicals} technicals reconciled', flush=True)


if __name__ == '__main__':
    main()
