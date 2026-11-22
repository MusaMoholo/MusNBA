#!/usr/bin/env python3
"""Reproduce the existing engine's six-foul substitution behaviour without changing it."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import sha256_file, write_json  # noqa: E402
from scripts import engine  # noqa: E402
from scripts.evaluate import EXPERIMENTS  # noqa: E402


class CapturedLineup(Exception):
    def __init__(self, players: list[int]):
        self.players = players


class ProbeEngine(engine.Engine):
    def __init__(self) -> None:
        self.m = SimpleNamespace(dated_candidate=False)
        self.diag = self.rotation_diag = None

    def _context(self, game, state, active, offense, defense):
        raise CapturedLineup(np.concatenate([offense[0], defense[0]]).astype(int).tolist())


class ProbeGame:
    n = 12
    avail = np.ones(12)
    side = np.array([0] * 6 + [1] * 6)
    expected = np.arange(12, dtype=float)

    def lineup_tables(self, available, rng):
        tables = np.stack([np.tile(np.arange(5), (2880, 1)), np.tile(np.arange(6, 11), (2880, 1))])
        return tables, np.array([[0, 1]])


def lineup_at_fouls(fouls: int) -> list[int]:
    class InjectedWorlds(engine.Worlds):
        def __init__(self, game, worlds, rng):
            super().__init__(game, worlds, rng)
            self.ingame['pf_so_far'][0, 0] = fouls
            self.box['pf'][0, 0, 0] = fouls

    try:
        with patch.object(engine, 'Worlds', InjectedWorlds):
            ProbeEngine().simulate(ProbeGame(), 1, 20261122)
    except CapturedLineup as result:
        return result.players
    raise RuntimeError('engine did not reach the captured segment')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=EXPERIMENTS / '20261122_a1_s06_foul_out_probe.json')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite the foul-out probe')
    five, six = lineup_at_fouls(5), lineup_at_fouls(6)
    if len(set(five)) != 10 or len(set(six)) != 10 or 0 not in five:
        raise ValueError('probe did not start with the expected two distinct fives')
    result = {
        'experiment': 'a1_s06_foul_out_state_probe',
        'worlds': 1,
        'home_roster': [0, 1, 2, 3, 4, 5],
        'scheduled_home_five': [0, 1, 2, 3, 4],
        'available_bench_player': 5,
        'five_fouls_player_on_court': 0 in five,
        'six_fouls_player_on_court': 0 in six,
        'six_fouls_bench_player_on_court': 5 in six,
        'interpretation': 'Controlled state injection before a segment, not a frequency estimate. '
                          'The currently served source initializes its foul-out mask but does not update it.',
        'input_sha256': {str(path.relative_to(ROOT)): sha256_file(path)
                         for path in (Path(__file__), ROOT / 'scripts/engine.py')},
    }
    write_json(args.output, result, pretty=True)
    print(f"six-foul player retained: {result['six_fouls_player_on_court']}; "
          f"available substitute used: {result['six_fouls_bench_player_on_court']}", flush=True)


if __name__ == '__main__':
    main()
