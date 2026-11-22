#!/usr/bin/env python3
"""Fit a dated assignment in isolation and compare old versus training-only holdout preprocessing.

  .venv/bin/python -u -m scripts.a1_assignment_audit --through 2025-12-31 --holdout-to 2026-04-30 \\
      --output analysis/experiments/new-assignment.json --model-output data/derived/variants/new-assignment.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, sha256_file, write_json  # noqa: E402
from scripts import history, matchups, nodes  # noqa: E402

BASE = DERIVED / 'variants' / 'a1_causal_base_20261122_v2' / 'features' / 'pregame.parquet'
FINAL_TEST = '2026-07-01'


def audit(through: str, holdout_to: str, include_body: bool = True) -> tuple[dict, dict]:
    if not through < holdout_to < FINAL_TEST:
        raise ValueError('holdout must follow training and remain before the protected final test')
    provenance = json.loads((BASE.parent / 'features_report.json').read_text())
    if not provenance.get('causal_first_priors') or not provenance.get('history_only'):
        raise ValueError('expected the pinned historical causal-base profiles')
    for path, digest in provenance['input_sha256'].items():
        if sha256_file(Path(path)) != digest:
            raise ValueError(f'causal feature input changed: {path}')
    started = time.monotonic()
    seg = nodes.load_segments(False)
    if seg['date_et'].max() >= FINAL_TEST:
        raise ValueError('protected final-test segment present')
    print(f'loaded {len(seg)} historical segments in {time.monotonic() - started:.1f}s', flush=True)
    types = matchups.attach_shot_types(seg, matchups.shot_types(include_current=False))
    pre = matchups._players(through, BASE, include_body=include_body)
    ev = matchups.events(seg, types).merge(seg[['seg_id', 'date_et']], on='seg_id', validate='many_to_one')
    train = ev[ev['date_et'].le(through)]
    holdout = ev[ev['date_et'].gt(through) & ev['date_et'].le(holdout_to)]
    if train.empty or holdout.empty:
        raise ValueError('training or held-out assignment events are empty')
    print(f'assignment events: {len(train)} training, {len(holdout)} held out', flush=True)
    X, y, w, kind, prep = matchups.design(seg, train, pre, return_preprocessing=True)
    fixed, yf, wf, kf, _ = matchups.design(seg, holdout, pre, preprocessing=prep)
    legacy, yl, wl, kl, _ = matchups.design(seg, holdout, pre)
    if not (np.array_equal(yf, yl) and np.array_equal(wf, wl) and np.array_equal(kf, kl)):
        raise ValueError('legacy and corrected holdout populations differ')
    print(f'fitting on {len(y)} usable events; {len(yf)} usable held-out events', flush=True)
    theta = matchups.fit_clogit(X, y, w)
    nk = len(matchups.MATCH)
    propensity = np.r_[np.zeros(nk), matchups.fit_clogit(X[:, :, nk:], y, w)]
    on_ball = np.isin(kf, ['foul3', 'block_jump', 'and1_jump'])
    def metrics(matrix):
        rank = matrix[on_ball][:, :, :nk] @ theta[:nk]
        return {'full_loglik': matchups.loglik(matrix, yf, wf, theta),
                'propensity_only_loglik': matchups.loglik(matrix, yf, wf, propensity),
                'on_ball_top1': float((rank.argmax(1) == yf[on_ball]).mean()) if on_ball.any() else None}
    old_metrics, new_metrics = metrics(legacy), metrics(fixed)
    valid_from = str(np.datetime64(through) + np.timedelta64(1, 'D'))
    model = {'through': through, 'valid_from': valid_from, 'match': dict(zip(matchups.MATCH, theta[:nk].tolist())),
             'prop': dict(zip(matchups.PROP, theta[nk:].tolist())), 'fill': prep['fill'],
             'body_policy': 'include' if include_body else 'omit',
             'missing_policy': 'retain_missing', 'events': len(y), 'preprocessing': prep,
             'status': 'research candidate; do not apply before valid_from or promote without full gates'}
    paths = [BASE, BASE.parent / 'features_report.json', ROOT / 'scripts' / 'matchups.py', ROOT / 'scripts' / 'nodes.py']
    if include_body:
        paths.append(DERIVED / 'athletes.parquet')
    paths += nodes.segment_files(False) + sorted(history.RAW_DIR.glob('play_by_play_*.parquet'))
    result = {'experiment': 'a1_assignment_holdout_preprocessing', 'through': through, 'holdout_to': holdout_to,
              'train_events': len(y), 'holdout_events': len(yf), 'on_ball_events': int(on_ball.sum()),
              'train_kinds': {str(k): int((kind == k).sum()) for k in np.unique(kind)},
              'legacy_holdout': old_metrics, 'training_preprocessed_holdout': new_metrics,
              'changed_holdout_feature_values': int((~np.isclose(legacy, fixed, rtol=1e-12, atol=1e-12,
                                                                   equal_nan=True)).sum()),
              'elapsed_s': round(time.monotonic() - started, 2),
              'body_policy': model['body_policy'],
              'limitations': 'candidate uses first-season-causal base priors; historical position provenance remains '
                             'unverified; ' + ('static body publication timing is unproven; ' if include_body else
                                                'static body measurements are omitted; ') +
                             'assignment is unavailable before valid_from and is not a promoted model',
              'input_sha256': {str(p.relative_to(ROOT)): sha256_file(p) for p in paths}}
    return result, model


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--through', required=True, help='last training ET date, inclusive')
    parser.add_argument('--holdout-to', required=True, help='last held-out ET date, inclusive')
    parser.add_argument('--output', type=Path, required=True, help='new report path')
    parser.add_argument('--model-output', type=Path, required=True, help='new isolated data/derived/variants model path')
    parser.add_argument('--without-body', action='store_true', help='omit unverified historical height and weight')
    args = parser.parse_args()
    variant_root = (DERIVED / 'variants').resolve()
    if not args.model_output.resolve().is_relative_to(variant_root):
        raise ValueError('candidate model must remain inside data/derived/variants')
    if args.output.exists() or args.model_output.exists():
        raise FileExistsError('refusing to overwrite an assignment report or candidate model')
    result, model = audit(args.through, args.holdout_to, include_body=not args.without_body)
    write_json(args.model_output, model, pretty=True)
    result['candidate_model'] = str(args.model_output)
    result['candidate_model_sha256'] = sha256_file(args.model_output)
    write_json(args.output, result, pretty=True)
    print(f'saved {args.output} and isolated {args.model_output}', flush=True)


if __name__ == '__main__':
    main()
