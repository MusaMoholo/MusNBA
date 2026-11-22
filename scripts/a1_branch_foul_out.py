"""Opt-in branch-only foul-out substitutions; not connected to production."""
from __future__ import annotations

import numpy as np

from scripts import a1_lineup_branches, engine


class BranchFoulOutPolicy:
    def __init__(self) -> None:
        self.guard = a1_lineup_branches.BranchLegalityGuard()
        self.available = np.empty((0, 0), dtype=bool)
        self.counts: dict[str, int] = {}

    def begin(self, g: engine.Game, worlds: int, available: np.ndarray, seed: int) -> None:
        self.guard.begin(g, worlds, available, seed)
        self.available = self.guard.available
        if not np.isfinite(g.expected).all():
            raise a1_lineup_branches.BranchLegalityError('branch player minute targets must be finite')
        self.counts = {'scheduled_replacements': 0, 'foul_out_replacements': 0}

    def _repair(self, g: engine.Game, st: engine.Worlds, world: int, side: int,
                lineup: np.ndarray) -> tuple[np.ndarray, int]:
        desired = lineup.copy()
        if (desired.shape != (5,) or (desired < 0).any() or (desired >= g.n).any()
                or len(np.unique(desired)) != 5 or (g.side[desired] != side).any()):
            raise a1_lineup_branches.BranchLegalityError(
                f'branch game {g.game["game_id"]} world {world} side {side}: invalid scheduled five')
        legal = (g.side == side) & self.available[world] & (st.ingame['pf_so_far'][world] < 6)
        if legal.sum() < 5:
            raise a1_lineup_branches.BranchLegalityError(
                f'branch game {g.game["game_id"]} world {world} side {side}: '
                f'fewer than five eligible players at period {st.period[world]} clock {st.clock[world]:.1f}')
        bad = np.flatnonzero(~legal[desired])
        for slot in bad:
            bench = np.flatnonzero(legal & ~np.isin(np.arange(g.n), desired))
            if not len(bench):
                raise a1_lineup_branches.BranchLegalityError(
                    f'branch game {g.game["game_id"]} world {world} side {side}: no legal replacement')
            desired[slot] = bench[np.argmax(g.expected[bench])]
        return desired, len(bad)

    def _repair_fives(self, g: engine.Game, st: engine.Worlds, active: np.ndarray,
                      scheduled: np.ndarray) -> tuple[np.ndarray, np.ndarray, int]:
        if scheduled.shape != (len(active), 2, 5):
            raise a1_lineup_branches.BranchLegalityError('branch lineup dimensions do not match active worlds')
        lineups = scheduled.copy()
        if ((lineups < 0) | (lineups >= g.n)).any():
            raise a1_lineup_branches.BranchLegalityError('branch scheduled lineup has invalid player indices')
        invalid = ((np.diff(np.sort(lineups, axis=2), axis=2) == 0).any(axis=2)
                   | (g.side[lineups] != np.arange(2)[None, :, None]).any(axis=2))
        if invalid.any():
            row, side = np.argwhere(invalid)[0]
            raise a1_lineup_branches.BranchLegalityError(
                f'branch game {g.game["game_id"]} world {active[row]} side {side}: invalid scheduled five')
        illegal = (~self.available[active[:, None, None], lineups]
                   | (st.ingame['pf_so_far'][active[:, None, None], lineups] >= 6))
        changed = np.zeros(len(active), dtype=bool)
        total = 0
        for row, side in np.argwhere(illegal.any(axis=2)):
            lineups[row, side], replacements = self._repair(g, st, int(active[row]), int(side), lineups[row, side])
            changed[row] = replacements > 0
            total += replacements
        self.guard._check(g, st, active, lineups)
        return lineups, changed, total

    def before_segment(self, g: engine.Game, st: engine.Worlds, active: np.ndarray,
                       scheduled: np.ndarray) -> np.ndarray:
        lineups, _, replacements = self._repair_fives(g, st, active, scheduled)
        self.counts['scheduled_replacements'] += replacements
        return lineups

    def after_fouls(self, g: engine.Game, st: engine.Worlds, active: np.ndarray,
                    offense: np.ndarray, defense: np.ndarray) -> np.ndarray:
        if offense.shape != (len(active), 5) or defense.shape != (len(active), 5):
            raise a1_lineup_branches.BranchLegalityError('branch lineup dimensions do not match active worlds')
        lineups = np.empty((len(active), 2, 5), dtype=int)
        off = st.off[active]
        lineups[np.arange(len(active)), off] = offense
        lineups[np.arange(len(active)), 1 - off] = defense
        lineups, changed, replacements = self._repair_fives(g, st, active, lineups)
        self.counts['foul_out_replacements'] += replacements
        offense[:] = lineups[np.arange(len(active)), off]
        defense[:] = lineups[np.arange(len(active)), 1 - off]
        return changed

    def finish(self, g: engine.Game, st: engine.Worlds) -> None:
        self.guard.finish(g, st)
