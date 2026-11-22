#!/usr/bin/env python3
"""Demonstrate rejection bias on a synthetic, known-outcome population."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import sha256_file, write_json  # noqa: E402
from scripts.a1_world_retry import RecoverableWorldError, simulate_isolated  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worlds', type=int, default=10000)
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an experiment')
    threshold = 0.05

    def draw(world: int, attempt: int, seed: int) -> float:
        return float(np.random.default_rng(seed).random())

    def rejected_draw(world: int, attempt: int, seed: int) -> float:
        value = draw(world, attempt, seed)
        if value < threshold:
            raise RecoverableWorldError('synthetic outcome below 0.05')
        return value

    control = simulate_isolated(draw, worlds=args.worlds, seed=args.seed, attempts_per_world=10,
                                max_rejections=args.worlds)
    result = simulate_isolated(rejected_draw, worlds=args.worlds, seed=args.seed, attempts_per_world=10,
                               max_rejections=args.worlds)
    affected = {r.world for r in result.rejections}
    if (len(result.worlds) != args.worlds or any(v < threshold for v in result.worlds)
            or any(control.worlds[i] != result.worlds[i] for i in range(args.worlds) if i not in affected)):
        raise ValueError('synthetic retry accounting failed')
    write_json(args.output, {
        'kind': 'synthetic rejection-bias demonstration; not an NBA estimate',
        'worlds': args.worlds, 'seed': str(args.seed), 'threshold': threshold,
        'control_mean': float(np.mean(control.worlds)), 'accepted_mean': float(np.mean(result.worlds)),
        'theoretical_unconditional_mean': 0.5, 'theoretical_conditional_mean': (1 + threshold) / 2,
        'rejected_attempts': len(result.rejections), 'affected_worlds': len(affected),
        'rejection_rate_over_attempts': len(result.rejections) / (args.worlds + len(result.rejections)),
        'rejections': [{'world': r.world, 'attempt': r.attempt, 'seed': str(r.seed), 'reason': r.reason}
                       for r in result.rejections],
        'analysis_sha256': sha256_file(Path(__file__)),
        'coordinator_sha256': sha256_file(ROOT / 'scripts/a1_world_retry.py'),
        'seed_algorithm_sha256': sha256_file(ROOT / 'scripts/projection.py'),
        'limitations': ['Synthetic uniform outcome; not an NBA failure rate or measured game-forecast bias.',
                        'Retry cap and failure criterion are deliberately chosen for this demonstration.'],
    }, pretty=True)
    print(f'{args.worlds} worlds, {len(result.rejections)} rejected attempts; '
          f'mean {np.mean(control.worlds):.5f} -> {np.mean(result.worlds):.5f}', flush=True)


if __name__ == '__main__':
    main()
