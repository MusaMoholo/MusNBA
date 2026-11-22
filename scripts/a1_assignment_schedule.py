#!/usr/bin/env python3
"""Fit resumable, body-free monthly matchup assignments and freeze one schedule per historical fold.

  .venv/bin/python -u -m scripts.a1_assignment_schedule \\
      --base data/derived/variants/a1_causal_base_20261122_v4/features/pregame.parquet \\
      --out data/derived/variants/a1_assignment_schedule_20261122_v2 \\
      --report analysis/experiments/20261122_a1_assignment_monthly_schedule_v2.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, sha256_file, write_json  # noqa: E402
from scripts import history, matchups, nodes  # noqa: E402
from scripts.evaluate import FOLDS, TEST_FROM  # noqa: E402

MIN_EVENTS = 1000


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    write_json(temporary, value, pretty=True)
    os.replace(temporary, path)


def build(base: Path, out: Path, report: Path) -> None:
    if not out.resolve().is_relative_to((DERIVED / 'variants').resolve()):
        raise ValueError('assignment schedule must remain under data/derived/variants')
    provenance_path = base.parent / 'features_report.json'
    provenance = json.loads(provenance_path.read_text())
    if (not provenance.get('causal_first_priors') or not provenance.get('causal_positions') or
            not provenance.get('history_only') or provenance.get('matchup')):
        raise ValueError('expected isolated history-only base profiles with causal priors and prior-observed positions')
    for path, digest in provenance['input_sha256'].items():
        if sha256_file(Path(path)) != digest:
            raise ValueError(f'causal feature input changed: {path}')
    inputs = [base, provenance_path, Path(__file__), ROOT / 'scripts' / 'matchups.py', ROOT / 'scripts' / 'nodes.py']
    inputs += nodes.segment_files(False) + sorted(history.RAW_DIR.glob('play_by_play_*.parquet'))
    hashes = {str(path): sha256_file(path) for path in inputs}
    signature = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    if report.exists():
        raise FileExistsError(f'refusing to overwrite schedule report: {report}')

    started = time.monotonic()
    seg = nodes.load_segments(False)
    if seg['date_et'].max() >= TEST_FROM:
        raise ValueError('protected final-test segment present')
    types = matchups.attach_shot_types(seg, matchups.shot_types(include_current=False))
    pre = matchups._players(None, base, include_body=False)
    ev = matchups.events(seg, types).merge(seg[['seg_id', 'date_et']], on='seg_id', validate='many_to_one')
    last_cutoff = max(fold[0] for fold in FOLDS.values())
    ev = ev[ev['date_et'].le(last_cutoff)]
    periods = sorted(pd.to_datetime(ev['date_et']).dt.to_period('M').unique())
    cutoffs = [str(period.end_time.date()) for period in periods if str(period.end_time.date()) <= last_cutoff]
    cold = {'through': None, 'valid_from': '1900-01-01', 'match': {name: 0.0 for name in matchups.MATCH},
            'fill': {}, 'body_policy': 'omit', 'missing_policy': 'retain_missing', 'events': 0}
    models, skipped = [], []
    model_dir = out / 'monthly'
    model_dir.mkdir(parents=True, exist_ok=True)
    print(f'assignment schedule: {len(seg)} segments, {len(ev)} eligible credits, {len(cutoffs)} months', flush=True)
    for i, cutoff in enumerate(cutoffs, 1):
        train = ev[ev['date_et'].le(cutoff)]
        path = model_dir / f'{cutoff}.json'
        if path.exists():
            model = json.loads(path.read_text())
            if model.get('input_signature') != signature or model.get('through') != cutoff:
                raise ValueError(f'cannot resume model with changed inputs: {path}')
            state = 'reused'
        else:
            if len(train) < MIN_EVENTS:
                skipped.append({'through': cutoff, 'eligible_events': len(train), 'reason': 'below fixed minimum'})
                print(f'assignment month {i}/{len(cutoffs)}: {cutoff}, {len(train)} credits, cold start', flush=True)
                continue
            X, y, w, kind, prep = matchups.design(seg, train, pre, return_preprocessing=True)
            if len(y) < MIN_EVENTS:
                skipped.append({'through': cutoff, 'usable_events': len(y), 'reason': 'below fixed minimum'})
                print(f'assignment month {i}/{len(cutoffs)}: {cutoff}, {len(y)} usable, cold start', flush=True)
                continue
            theta = matchups.fit_clogit(X, y, w)
            nk = len(matchups.MATCH)
            model = {'through': cutoff, 'valid_from': str(np.datetime64(cutoff) + np.timedelta64(1, 'D')),
                     'events': len(y), 'last_event_date': str(train['date_et'].max()),
                     'event_kinds': {str(k): int((kind == k).sum()) for k in np.unique(kind)},
                     'match': dict(zip(matchups.MATCH, theta[:nk].tolist())),
                     'prop': dict(zip(matchups.PROP, theta[nk:].tolist())), 'fill': prep['fill'],
                     'preprocessing': prep, 'body_policy': 'omit', 'missing_policy': 'retain_missing',
                     'input_signature': signature}
            atomic_json(path, model)
            state = 'fitted'
        models.append(model)
        print(f'assignment month {i}/{len(cutoffs)}: {cutoff}, {model["events"]} usable, {state}, '
              f'{time.monotonic() - started:.1f}s elapsed', flush=True)

    manifests = {}
    for fold, (through, _, _) in FOLDS.items():
        selected = [cold] + [model for model in models if model['through'] <= through]
        schedule = {'kind': 'dated_implicit_schedule', 'training_through': through, 'models': selected,
                    'base_pregame_sha256': hashes[str(base)], 'input_signature': signature,
                    'status': 'isolated research; raw revision/publication timing remains unverified'}
        matchups.dated_masks(schedule, [])
        path = out / f'{fold}.json'
        if path.exists() and json.loads(path.read_text()) != schedule:
            raise ValueError(f'existing fold schedule differs: {path}')
        if not path.exists():
            atomic_json(path, schedule)
        manifests[fold] = {'training_through': through, 'models': len(selected) - 1,
                           'last_fit_through': selected[-1]['through'], 'path': str(path),
                           'sha256': sha256_file(path)}
    result = {'experiment': 'a1_bodyfree_monthly_assignment_schedule', 'minimum_usable_events': MIN_EVENTS,
              'fit_months': len(models), 'skipped_months': skipped, 'folds': manifests,
              'input_signature': signature, 'input_sha256': hashes,
              'elapsed_s': round(time.monotonic() - started, 2),
              'limitations': 'not promoted; later body data omitted, position uses strictly earlier game records '
                             'whose original publication/revision timing is unverified; actual-participant '
                             'diagnostics are not availability forecasts'}
    atomic_json(report, result)
    print(f'saved {len(models)} monthly fits, {len(manifests)} fold schedules and {report}', flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    build(args.base, args.out, args.report)


if __name__ == '__main__':
    main()
