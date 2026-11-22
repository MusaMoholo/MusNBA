#!/usr/bin/env python3
"""Re-audit saved S06 worlds from the artificial retry-policy comparison."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import read_json, sha256_file, write_json  # noqa: E402
from scripts import a1_substitution_world_audit  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an experiment')
    report = read_json(args.report)
    stress_path = Path(report['stress'])
    if sha256_file(stress_path) != report['stress_sha256']:
        raise ValueError('stress report fingerprint differs')
    stress = read_json(stress_path)
    rejected = stress['result']['rejections']
    if len(rejected) != len(report['worlds']):
        raise ValueError('rejected seed count differs')
    events = event_worlds = fives = 0
    for previous, current in zip(rejected, report['worlds'], strict=True):
        if any(previous[key] != current[key] for key in ('world', 'attempt', 'seed')):
            raise ValueError('failed seed identity differs')
        if previous['reason'] != current['original_rejection']:
            raise ValueError('original failure reason differs')
        path = Path(current['capture'])
        if sha256_file(path) != current['capture_sha256']:
            raise ValueError('saved world fingerprint differs')
        with np.load(path, allow_pickle=False) as data:
            audit = a1_substitution_world_audit.audit_worlds(data, foul_penalty=True)
            if audit != current['audit']:
                raise ValueError('independent saved-world audit differs')
            for key in ('world', 'period', 'clock', 'fouler', 'shooter', 'made', 'probability'):
                actual = data[f'technical_{key}']
                expected = np.asarray([event[key] for event in current['technical_events']], dtype=actual.dtype)
                if not np.array_equal(actual, expected):
                    raise ValueError('technical-event output differs from saved trace')
        events += audit['foul_penalty_events']
        event_worlds += audit['foul_penalty_events'] > 0
        fives += audit['lineup_fives_checked']
    write_json(args.output, {
        'kind': 'independent saved-world accounting; artificial stress only',
        'report': str(args.report), 'report_sha256': sha256_file(args.report),
        'audit_sha256': sha256_file(Path(__file__)), 'worlds': len(rejected),
        'technical_events': events, 'worlds_with_technical': event_worlds,
        'lineup_fives_checked': fives,
        'limitations': ['Artificial five-player roster and synthetic 48-minute roles.',
                        'S06 and D29 repair differ in policy and streams; seed matching is not a matched-state comparison.',
                        'Not an NBA failure rate or a predictive test.'],
    }, pretty=True)
    print(f'{len(rejected)} saved worlds, {fives} fives and {events} technicals reconciled')


if __name__ == '__main__':
    main()
