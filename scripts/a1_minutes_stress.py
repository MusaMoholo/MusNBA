#!/usr/bin/env python3
"""Audit candidate D29 regulation allocation and redraw invariants on fixed and stress rosters."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, sha256_file, write_json  # noqa: E402
from scripts import a1_minutes_candidate as candidate, a1_minutes_diagnose, a1_signal, minutes  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS  # noqa: E402


def audit() -> dict:
    stress_rng = np.random.default_rng(20261122)
    synthetic = {}
    for n in (5, 6, 7, 10, 15):
        h, cap, sd = np.full(n, 240 / n), np.full(n, 48.0), np.full(n, 7.0)
        original = minutes.redraw(h, cap, sd, 10000, np.random.default_rng(11))
        corrected = candidate.redraw(h, cap, sd, 10000, np.random.default_rng(11))
        repeated = candidate.redraw(h, cap, sd, 10000, np.random.default_rng(11))
        if not np.array_equal(corrected, repeated):
            raise ValueError(f'{n}-player candidate redraw is not deterministic')
        allocation_errors = 0
        max_allocated = 0.0
        for _ in range(1000):
            role = stress_rng.uniform(0, 40, n)
            maximum = stress_rng.uniform(6, 46, n)
            old = minutes.allocate(role, maximum, role, gamma=0, room=1)
            fixed = candidate.allocate(role, maximum, role, gamma=0, room=1)
            allocation_errors += int((old > 48).any() or (old < 0).any() or abs(old.sum() - 240) > 1e-10)
            max_allocated = max(max_allocated, float(fixed.max()))
            if (fixed < 0).any() or (fixed > 48).any() or abs(fixed.sum() - 240) > 1e-10:
                raise ValueError(f'{n}-player candidate mean allocation is illegal')
        synthetic[str(n)] = {
            'worlds': len(corrected),
            'legacy_worlds_not_240_at_1e_6': int((np.abs(original.sum(axis=1) - 240) > 1e-6).sum()),
            'legacy_max_deficit': float(np.max(240 - original.sum(axis=1))),
            'candidate_max_team_error': float(np.abs(corrected.sum(axis=1) - 240).max()),
            'candidate_min_player_minutes': float(corrected.min()),
            'candidate_max_player_minutes': float(corrected.max()),
            'legacy_illegal_mean_allocations': allocation_errors,
            'candidate_max_mean_allocation': max_allocated,
        }

    manifest = json.loads(a1_signal.MANIFEST.read_text())
    games_path = DERIVED / 'experiments' / f'{a1_minutes_diagnose.CONTROL}.parquet'
    games = a1_signal.fixed_games(pd.read_parquet(games_path), manifest)
    print('building candidate states for real-roster accounting', flush=True)
    model = candidate.build(FOLDS['F4'][1], include_current=False)
    rows = model['rows'].loc[model['rows']['game_id'].isin(games['game_id'])]
    team_games = 0
    absent_cases = 0
    infeasible_after_absence = 0
    max_team_error = 0.0
    max_cascade_error = 0.0
    max_world_error = 0.0
    for (_, _), part in rows.groupby(['game_id', 'team'], sort=True):
        states = [{'healthy': row.healthy, 'cap': row.cap, 'ramp': row.ramp, 'rotation': 1.0,
                   'priority': row.priority} for row in part.itertuples(index=False)]
        target = candidate.game_targets(states)
        max_team_error = max(max_team_error, abs(float(target.sum()) - 240))
        maxes = np.array([s['cap'] for s in states], dtype=float)
        spread = minutes.sd_for(model['sd'], target)
        worlds = candidate.redraw(target, maxes, spread, 20, np.random.default_rng(team_games))
        max_world_error = max(max_world_error, float(np.abs(worlds.sum(axis=1) - 240).max()))
        if len(states) <= 5:
            infeasible_after_absence += 1
        else:
            removed = int(np.argmax(target))
            remainder = candidate.game_targets([s for i, s in enumerate(states) if i != removed])
            expected = target[removed]
            observed = (remainder - np.delete(target, removed)).sum()
            max_cascade_error = max(max_cascade_error, abs(float(observed - expected)))
            absent_cases += 1
        team_games += 1
    if team_games != 2 * len(games) or max(max_team_error, max_cascade_error, max_world_error) > 1e-10:
        raise ValueError('fixed-panel regulation or absence-cascade accounting failed')
    paths = [a1_signal.MANIFEST, games_path, ROOT / 'scripts/minutes.py', Path(candidate.__file__),
             Path(__file__), DERIVED / 'teams.json']
    paths += sorted((DERIVED / 'history').glob('*/on_court.parquet'))
    paths += sorted((ROOT / 'data/raw/hoopr').glob('player_box_*.parquet'))
    return {
        'experiment': 'a1_s05_minutes_candidate_stress',
        'method': 'Repeat 10,000 same-seed draws and 1,000 mean allocations for each roster size; compare original '
                  'D29 with the candidate hard-48 regulation correction. Rebuild F4 candidate states, allocate each '
                  'team and remove its largest target to test redistribution.',
        'limitations': 'Synthetic stress is not a forecast or an engine-accuracy test. Historical state learning '
                       'still uses the original D29 allocator; the strict correction is an isolated runtime candidate. '
                       'Observed player caps remain soft when they cannot cover 240; 48 is the hard regulation limit.',
        'synthetic': synthetic,
        'fixed_panel': {'games': len(games), 'team_games': team_games, 'absence_cascades': absent_cases,
                        'infeasible_after_removal': infeasible_after_absence,
                        'max_target_team_error': max_team_error, 'max_world_team_error': max_world_error,
                        'max_cascade_error': max_cascade_error},
        'input_sha256': {str(p.relative_to(ROOT)): sha256_file(p) for p in paths},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=EXPERIMENTS / '20261122_a1_s05_minutes_candidate_stress.json')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f'refusing to overwrite {args.output}')
    report = audit()
    write_json(args.output, report, pretty=True)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
