#!/usr/bin/env python3
"""Apply the frozen A1 minute-screen and non-inferiority bounds to paired reports."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import sha256_file, write_json  # noqa: E402
from scripts import a1_manifest  # noqa: E402

PLAYER_CRPS = {
    'star': {'min': 0.0578, 'pts': 0.0898, 'reb': 0.0304, 'ast': 0.0261, 'fg3m': 0.0200},
    'starter': {'min': 0.0605, 'pts': 0.0711, 'reb': 0.0290, 'ast': 0.0207, 'fg3m': 0.0200},
    'bench': {'min': 0.0796, 'pts': 0.0553, 'reb': 0.0237, 'ast': 0.0155, 'fg3m': 0.0200},
}
PLAYER_BIAS = {'min': 0.30, 'pts': 0.30, 'reb': 0.10, 'ast': 0.10, 'fg3m': 0.05}
GAME_CRPS = {'margin': 0.20, 'total': 0.20, **{
    f'q{quarter}_{stat}': 0.10 for quarter in range(1, 5) for stat in ('margin', 'total')
}}


def interval(metric: dict) -> list[float] | None:
    bounds = metric.get('ci_95')
    if bounds is None:
        return None
    if (len(bounds) != 2 or not all(type(v) in (int, float) and math.isfinite(v) for v in bounds)
            or bounds[0] > bounds[1]):
        raise ValueError('paired 95% interval must contain two ordered finite bounds')
    return [float(bounds[0]), float(bounds[1])]


def assess(report: dict, noise_report: dict) -> dict:
    if (report['runs']['control'] != noise_report['runs']['control']
            or report['population']['fold'] != noise_report['population']['fold']
            or report['population']['game_ids'] != noise_report['population']['game_ids']):
        raise ValueError('comparison and seed-noise reports do not share the frozen control and games')
    if set(report['games']) != set(GAME_CRPS):
        raise ValueError('paired report does not contain exactly the registered game outcomes')
    seed_result = noise_report['players']['all']['min']
    seed = interval(seed_result['crps'])
    if seed is None or seed_result['status'] != 'ok':
        raise ValueError('pooled minute seed-noise interval is unavailable')
    floor = a1_manifest.noise_floors(noise_report)['players']['all']['min']['crps']
    if floor is None or not math.isfinite(floor):
        raise ValueError('pooled minute seed-noise floor is unavailable')
    primary = report['players']['all']['min']
    primary_ci = interval(primary['crps'])
    change = float(primary['crps']['change'])
    if not math.isfinite(change):
        raise ValueError('pooled minute CRPS change must be finite')
    preliminary = (primary['status'] == 'ok' and primary_ci is not None
                   and primary_ci[1] < 0 and -change > floor)
    checks = []

    def check(label: str, data: dict, metric: str, bound: float) -> None:
        metric_data = data.get(metric, {})
        ci = interval(metric_data)
        supported = data.get('status') == 'ok' or (label == 'win' and data.get('status') == 'infinite_log_loss')
        established = supported and ci is not None and ci[1] < bound
        checks.append({'outcome': label, 'metric': metric, 'bound': bound,
                       'change': metric_data.get('change'), 'ci_95': ci, 'established': established})

    for tier, stats in PLAYER_CRPS.items():
        for stat, bound in stats.items():
            data = report['players'][tier][stat]
            check(f'{tier} {stat}', data, 'crps', bound)
            check(f'{tier} {stat}', data, 'bias', PLAYER_BIAS[stat])
            check(f'{tier} {stat}', data, 'coverage', 0.03)
    for stat, bound in GAME_CRPS.items():
        data = report['games'][stat]
        check(stat, data, 'crps', bound)
        check(stat, data, 'coverage', 0.03)
    for stat, bound in (('margin', 0.50), ('total', 1.00)):
        check(stat, report['games'][stat], 'bias', bound)
    for stat, bound in (('brier', 0.005), ('log_loss', 0.010)):
        check('win', report['win'], stat, bound)
    failed = [row for row in checks if not row['established']]
    return {
        'experiment': 'a1_minutes_preliminary_gate',
        'runs': report['runs'],
        'population': {key: report['population'][key] for key in ('fold', 'games', 'player_games')},
        'pooled_minute_crps': {'change': change, 'ci_95': primary_ci, 'seed_noise_floor': floor,
                               'passes_uncorrected_screen': preliminary},
        'non_inferiority': {'checks': len(checks), 'established': len(checks) - len(failed),
                            'not_established': failed},
        'limitations': 'Preliminary uncorrected 95% screen, not Holm-adjusted confirmation or a promotion decision; '
                       'actual-participant diagnostics are not availability forecasts.',
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('comparison', type=Path)
    parser.add_argument('seed_noise', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f'refusing to overwrite {args.output}')
    report = assess(json.loads(args.comparison.read_text()), json.loads(args.seed_noise.read_text()))
    inputs = [path.resolve() for path in (args.comparison, args.seed_noise, Path(__file__), Path(a1_manifest.__file__))]
    if any(not path.is_relative_to(ROOT) for path in inputs):
        raise ValueError('gate inputs must be inside the repository')
    report['input_sha256'] = {str(path.relative_to(ROOT)): sha256_file(path) for path in inputs}
    write_json(args.output, report, pretty=True)
    print(f"pooled minutes screen: {report['pooled_minute_crps']['passes_uncorrected_screen']}; "
          f"non-inferiority: {report['non_inferiority']['established']}/"
          f"{report['non_inferiority']['checks']} bounds established")


if __name__ == '__main__':
    main()
