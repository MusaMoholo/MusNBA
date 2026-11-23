#!/usr/bin/env python3
"""Versioned D51 statistical compatibility; never publishes or promotes a model."""
from __future__ import annotations

import argparse
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from basketball_common import read_json, sha256_file, write_json  # noqa: E402
from scripts.a1_minutes_gate import GAME_CRPS, PLAYER_BIAS, PLAYER_CRPS, interval  # noqa: E402


def assess(report: dict, change_class: str, primary: str | None = None, *, policy: str = 'v2') -> dict:
    if policy not in ('v2','v3'):
        raise ValueError('known versioned acceptance policy required')
    if change_class not in ('mechanics', 'learned'):
        raise ValueError('empirical score gate applies to mechanics or learned changes')
    if change_class == 'learned' and primary is None:
        raise ValueError('learned changes need a preregistered primary path')
    core, diagnostics = [], []

    def check(label, data, metric, bound, diagnostic=False):
        values = data.get(metric, {})
        bounds = interval(values)
        supported = data.get('status') == 'ok' and bounds is not None
        delta = values.get('change')
        if delta is not None and (type(delta) not in (int, float) or not math.isfinite(delta)):
            raise ValueError(f'{label} {metric}: non-finite harm needs explicit resolution')
        status = 'unsupported'
        if supported:
            status = ('material_harm' if bounds[0] > bound else
                      'established' if bounds[1] < bound else 'unresolved')
        result = {'outcome': label, 'metric': metric, 'margin': bound,
                  'change': delta, 'ci_95': bounds, 'status': status}
        (diagnostics if diagnostic else core).append(result)

    for tier, stats in PLAYER_CRPS.items():
        for stat, bound in stats.items():
            data = report['players'][tier][stat]
            check(f'{tier} {stat}', data, 'crps', bound)
            check(f'{tier} {stat}', data, 'bias', PLAYER_BIAS[stat])
            check(f'{tier} {stat}', data, 'coverage', .03, True)
    if set(report['games']) != set(GAME_CRPS):
        raise ValueError('comparison lacks the registered game outcomes')
    for stat, bound in GAME_CRPS.items():
        check(stat, report['games'][stat], 'crps', bound)
        check(stat, report['games'][stat], 'coverage', .03, True)
    for stat, bound in (('margin', .50), ('total', 1.00)):
        check(stat, report['games'][stat], 'bias', bound)
    for stat, bound in (('brier', .005), ('log_loss', .010)):
        check('win', report['win'], stat, bound)
    primary_result = None
    if primary is not None:
        data = report
        for key in primary.split('/'):
            data = data[key]
        bounds = interval(data)
        primary_result = {'path': primary, 'change': data.get('change'), 'ci_95': bounds,
                          'improvement_established': bounds is not None and bounds[1] < 0,
                          'multiplicity': 'uncorrected; only one frozen benefit claim can use this directly'}
    bias = [row for row in core if row['metric']=='bias'] if policy=='v3' else []
    if policy=='v3':
        core = [row for row in core if row['metric']!='bias']
    harms = [row for row in core + diagnostics if row['status'] == 'material_harm']
    incomplete = [row for row in core if row['status'] != 'established']
    compatible = not harms and not incomplete
    benefit = change_class == 'mechanics' or bool(primary_result and primary_result['improvement_established'])
    decision = ('material_harm' if harms else 'more_precision_or_coverage_needed' if incomplete else
                'primary_benefit_not_established' if not benefit else 'development_scores_compatible')
    return {'policy': f'promotion-{policy}-20261123', 'change_class': change_class, 'runs': report['runs'],
            'population': {key: report['population'][key] for key in ('fold', 'games', 'player_games')},
            'core': {'checks': len(core), 'established': len(core) - len(incomplete), 'details': core},
            'coverage': {'checks': len(diagnostics), 'details': diagnostics,
                         'unresolved': sum(row['status'] in ('unresolved', 'unsupported') for row in diagnostics)},
            **({'bias_diagnostics':{'checks':len(bias),'details':bias,
                 'interpretation':'Cohort signed-mean calibration; never silently treated as individual prediction error or a universal veto.'}}
               if policy=='v3' else {}),
            'primary': primary_result, 'statistical_compatibility': compatible,
            'decision': decision,
            'release_requirements': 'This is development score evidence only. Rule correctness, independent '
                                    'confirmation, provenance, accounting, stress, runtime and delivery manifest '
                                    'remain required; no automatic promotion or publication.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('comparison', type=Path)
    parser.add_argument('--class', dest='change_class', choices=('mechanics', 'learned'), required=True)
    parser.add_argument('--primary')
    parser.add_argument('--policy',choices=('v2','v3'),default='v2')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite a versioned assessment')
    result = assess(read_json(args.comparison), args.change_class, args.primary,policy=args.policy)
    result['input_sha256'] = {str(p): sha256_file(p) for p in
                              (args.comparison, Path(__file__), ROOT / 'scripts/a1_minutes_gate.py',
                               ROOT / f'docs/protocols/promotion_{args.policy}_20261123.md')}
    write_json(args.output, result, pretty=True)
    print(result['decision'], result['core']['established'], '/', result['core']['checks'])


if __name__ == '__main__':
    main()
