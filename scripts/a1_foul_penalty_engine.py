#!/usr/bin/env python3
"""Opt-in S06 player-foul-penalty exception; not the serving rotation policy."""
from __future__ import annotations

import numpy as np

from scripts import a1_substitution_engine, engine, projection


class PlayerFoulPenaltyPolicy(a1_substitution_engine.SelectedTimeoutPolicy):
    def begin(self, g: engine.Game, worlds: int, available: np.ndarray, seed: int) -> None:
        super().begin(g, worlds, available, seed)
        self.previous_fouls = np.zeros((worlds, g.n), dtype=float)
        self.technical_rng = np.random.default_rng(projection.seed_for('a1_s06_foul_penalty', seed))
        self.technical_events: list[dict[str, int | float]] = []
        self.counts['foul_penalty_attempts'] = 0
        self.counts['foul_penalty_makes'] = 0

    def _legal_plan(self, g: engine.Game, st: engine.Worlds, w: int, side: int,
                    desired: np.ndarray) -> np.ndarray:
        eligible = (g.side == side) & self.available[w] & (st.ingame['pf_so_far'][w] < 6)
        if eligible.sum() >= 5:
            return super()._legal_plan(g, st, w, side, desired)
        desired = np.asarray(desired, dtype=int).copy()
        if (len(desired) != 5 or len(set(desired.tolist())) != 5
                or (desired < 0).any() or (desired >= g.n).any() or (g.side[desired] != side).any()):
            raise ValueError(f'world {w} side {side}: scheduled lineup is not a distinct five')
        current = self.current[w, side]
        current = current[current >= 0]
        exempt = current[self.available[w, current] & (st.ingame['pf_so_far'][w, current] >= 6)]
        needed = 5 - int(eligible.sum())
        if len(exempt) < needed:
            raise ValueError(f'world {w} side {side}: fewer than five legal or retained players')
        eligible[exempt[:needed]] = True
        for slot in np.flatnonzero(~eligible[desired]):
            bench = np.flatnonzero(eligible & ~np.isin(np.arange(g.n), desired))
            if not len(bench):
                raise ValueError(f'world {w} side {side}: no legal retained-player replacement')
            desired[slot] = bench[np.argmax(g.expected[bench])]
        return desired

    def before_segment(self, g: engine.Game, st: engine.Worlds, active: np.ndarray,
                       scheduled: np.ndarray) -> np.ndarray:
        self.previous_fouls[active] = st.ingame['pf_so_far'][active]
        return super().before_segment(g, st, active, scheduled)

    def _record_trace(self, st: engine.Worlds, active: np.ndarray, lineups: np.ndarray, phase: int) -> None:
        super()._record_trace(st, active, lineups, phase)
        self.trace[-1]['all_fouls'] = st.ingame['pf_so_far'][active].copy()

    def after_fouls(self, g: engine.Game, st: engine.Worlds, active: np.ndarray,
                    offense: np.ndarray, defense: np.ndarray) -> bool:
        delta = st.ingame['pf_so_far'][active] - self.previous_fouls[active]
        if not np.isfinite(delta).all() or ((delta < 0) | (delta > 1)).any():
            raise ValueError('personal fouls changed by an invalid amount within a segment')
        changed = super().after_fouls(g, st, active, offense, defense)
        violations = np.argwhere((delta == 1) & (st.ingame['pf_so_far'][active] >= 6))
        for row, fouler in violations:
            w, side, fouler = int(active[row]), int(g.side[fouler]), int(fouler)
            if fouler not in self.current[w, side]:
                continue
            eligible = (g.side == side) & self.available[w] & (st.ingame['pf_so_far'][w] < 6)
            if eligible.sum() >= 5:
                raise ValueError('a foul-out remained on court with five eligible players')
            opponents = self.current[w, 1 - side]
            percentages = np.asarray(g.P['ft_pct'][opponents], dtype=float)
            if np.isinf(percentages).any() or ((percentages < 0) | (percentages > 1)).any():
                raise ValueError('technical shooter has an invalid earlier FT percentage')
            known = np.flatnonzero(np.isfinite(percentages))
            if not len(known):
                raise ValueError('no opposing on-court player has a known earlier FT percentage')
            slot = int(known[np.argmax(percentages[known])])
            shooter, probability = int(opponents[slot]), float(percentages[slot])
            made = int(self.technical_rng.random() < probability)
            period = min(int(st.period[w]) - 1, 4)
            st.box['fta'][w, shooter, period] += 1
            st.box['ftm'][w, shooter, period] += made
            st.box['pts'][w, shooter, period] += made
            st.pts[w, 1 - side, period] += made
            st.score[w, 1 - side] += made
            st.ingame['pts_so_far'][w, shooter] += made
            self.counts['foul_penalty_attempts'] += 1
            self.counts['foul_penalty_makes'] += made
            if self.capture_trace:
                self.technical_events.append({
                    'world': w, 'period': int(st.period[w]), 'clock': float(st.clock[w]),
                    'fouler': fouler, 'shooter': shooter, 'made': made, 'probability': probability,
                })
        return changed
