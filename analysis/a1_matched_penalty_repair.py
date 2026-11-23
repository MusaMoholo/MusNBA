#!/usr/bin/env python3
"""Research-only D29 repair with an on-court foul-penalty continuation."""
from __future__ import annotations

import numpy as np

from analysis.a1_parallel_world_probe import capture_digest
from scripts import a1_branch_foul_out, a1_branch_world_probe, a1_lineup_branches, projection


def state_digest(st, offense, defense, trace):
    arrays = {key: np.asarray(getattr(st, key)) for key in
              ('period', 'clock', 'first', 'off', 'start', 'score', 'tfouls', 'done', 'minutes', 'pts', 'poss')}
    arrays.update({f'ingame_{key}': value for key, value in st.ingame.items()})
    arrays.update({f'box_{key}': value for key, value in st.box.items()})
    arrays.update({'offense': offense.copy(), 'defense': defense.copy()})
    arrays.update({f'trace_{key}': np.concatenate([entry[key] for entry in trace])
                   for key in ('world', 'period', 'clock', 'lineups', 'fouls', 'phase')})
    return capture_digest(arrays)


class ContinuationRepair(a1_branch_foul_out.BranchFoulOutPolicy):
    def begin(self, g, worlds, available, seed):
        if worlds != 1:
            raise ValueError('matched-state diagnostic requires isolated single-world simulation')
        super().begin(g, worlds, available, seed)
        self.exempt = np.zeros_like(available)

    def _repair(self, g, st, world, side, lineup):
        if not self.exempt[world, g.side == side].any():
            return super()._repair(g, st, world, side, lineup)
        desired = lineup.copy()
        legal = (g.side == side) & self.available[world] & (
            (st.ingame['pf_so_far'][world] < 6) | self.exempt[world])
        if legal.sum() != 5:
            raise a1_lineup_branches.BranchLegalityError('continuation must retain exactly five players')
        bad = np.flatnonzero(~legal[desired])
        for slot in bad:
            bench = np.flatnonzero(legal & ~np.isin(np.arange(g.n), desired))
            if not len(bench):
                raise a1_lineup_branches.BranchLegalityError('continuation has no legal replacement')
            desired[slot] = bench[np.argmax(g.expected[bench])]
        return desired, len(bad)

    def _repair_fives(self, g, st, active, scheduled):
        if not self.exempt[active].any():
            return super()._repair_fives(g, st, active, scheduled)
        if scheduled.shape != (len(active), 2, 5):
            raise a1_lineup_branches.BranchLegalityError('branch lineup dimensions do not match active worlds')
        lineups = scheduled.copy()
        if ((lineups < 0) | (lineups >= g.n)).any():
            raise a1_lineup_branches.BranchLegalityError('branch scheduled lineup has invalid player indices')
        invalid = ((np.diff(np.sort(lineups, axis=2), axis=2) == 0).any(axis=2)
                   | (g.side[lineups] != np.arange(2)[None, :, None]).any(axis=2))
        if invalid.any():
            raise a1_lineup_branches.BranchLegalityError('continuation scheduled lineup is not a valid five')
        legal = (self.available[active[:, None, None], lineups]
                 & ((st.ingame['pf_so_far'][active[:, None, None], lineups] < 6)
                    | self.exempt[active[:, None, None], lineups]))
        changed = np.zeros(len(active), dtype=bool)
        total = 0
        for row, side in np.argwhere(~legal.all(axis=2)):
            lineups[row, side], replacements = self._repair(g, st, int(active[row]), int(side), lineups[row, side])
            changed[row] |= replacements > 0
            total += replacements
        return lineups, changed, total


class MatchedPenaltyTrace(a1_branch_world_probe.RepairedTrace):
    def __init__(self):
        super().__init__()
        self.repair = ContinuationRepair()

    def begin(self, g, worlds, available, seed):
        super().begin(g, worlds, available, seed)
        self.previous_fouls = np.zeros((worlds, g.n), dtype=float)
        self.technical_rng = np.random.default_rng(projection.seed_for('a1_s06_foul_penalty', seed))
        self.technical_events = []
        self.first_exhaustion = {}

    def before_segment(self, g, st, active, scheduled):
        self.previous_fouls[active] = st.ingame['pf_so_far'][active]
        lineups = super().before_segment(g, st, active, scheduled)
        self.trace[-1]['all_fouls'] = st.ingame['pf_so_far'][active].copy()
        return lineups

    def after_fouls(self, g, st, active, offense, defense):
        delta = st.ingame['pf_so_far'][active] - self.previous_fouls[active]
        if not np.isfinite(delta).all() or ((delta < 0) | (delta > 1)).any():
            raise ValueError('personal fouls changed by an invalid amount within a segment')
        off = st.off[active]
        current = np.empty((len(active), 2, 5), dtype=int)
        current[np.arange(len(active)), off] = offense
        current[np.arange(len(active)), 1 - off] = defense
        for row, fouler in np.argwhere((delta == 1) & (st.ingame['pf_so_far'][active] == 6)):
            w, side, fouler = int(active[row]), int(g.side[fouler]), int(fouler)
            eligible = (g.side == side) & self.available[w] & (st.ingame['pf_so_far'][w] < 6)
            if eligible.sum() < 5:
                if fouler not in current[row, side]:
                    raise ValueError('newly disqualified player was not on court')
                self.repair.exempt[w, fouler] = True
                needed = 5 - int(eligible.sum())
                if self.repair.exempt[w, g.side == side].sum() != needed:
                    raise ValueError('continuation would reintroduce a previously removed foul-out')
                if w not in self.first_exhaustion:
                    self.first_exhaustion[w] = {
                        'reason': (f'branch game {g.game["game_id"]} world {w} side {side}: '
                                   f'fewer than five eligible players at period {st.period[w]} clock {st.clock[w]:.1f}'),
                        'state_sha256': state_digest(st, offense, defense, self.trace),
                    }
        lineups, changed, replacements = self.repair._repair_fives(g, st, active, current)
        self.counts['foul_out_replacements'] += replacements
        offense[:] = lineups[np.arange(len(active)), off]
        defense[:] = lineups[np.arange(len(active)), 1 - off]
        technical_rows = np.zeros(len(active), dtype=bool)
        for row, fouler in np.argwhere((delta == 1) & (st.ingame['pf_so_far'][active] >= 6)):
            w, side, fouler = int(active[row]), int(g.side[fouler]), int(fouler)
            if not self.repair.exempt[w, fouler]:
                continue
            if fouler not in lineups[row, side]:
                raise ValueError('retained foul-out left the court')
            opponents = lineups[row, 1 - side]
            percentages = np.asarray(g.P['ft_pct'][opponents], dtype=float)
            if np.isinf(percentages).any() or ((percentages < 0) | (percentages > 1)).any():
                raise ValueError('technical shooter has an invalid earlier FT percentage')
            known = np.flatnonzero(np.isfinite(percentages))
            if not len(known):
                raise ValueError('no opposing on-court player has a known earlier FT percentage')
            shooter = int(opponents[known[np.argmax(percentages[known])]])
            probability = float(g.P['ft_pct'][shooter])
            made = int(self.technical_rng.random() < probability)
            period = min(int(st.period[w]) - 1, 4)
            st.box['fta'][w, shooter, period] += 1
            st.box['ftm'][w, shooter, period] += made
            st.box['pts'][w, shooter, period] += made
            st.pts[w, 1 - side, period] += made
            st.score[w, 1 - side] += made
            st.ingame['pts_so_far'][w, shooter] += made
            self.technical_events.append({'world': w, 'period': int(st.period[w]), 'clock': float(st.clock[w]),
                                          'fouler': fouler, 'shooter': shooter, 'made': made,
                                          'probability': probability})
            technical_rows[row] = True
        rows = np.flatnonzero(changed | technical_rows)
        if len(rows):
            worlds = active[rows]
            fives = lineups[rows]
            self.trace.append({
                'world': worlds.copy(), 'period': st.period[worlds].copy(), 'clock': st.clock[worlds].copy(),
                'lineups': fives.copy(), 'fouls': st.ingame['pf_so_far'][worlds[:, None, None], fives].copy(),
                'all_fouls': st.ingame['pf_so_far'][worlds].copy(), 'phase': np.ones(len(rows), dtype=np.int8),
            })
        return changed

    def capture(self, g, st):
        result = super().capture(g, st)
        result['trace_all_fouls'] = np.concatenate([entry['all_fouls'] for entry in self.trace])
        result['player_ft_pct'] = np.asarray(g.P['ft_pct']).copy()
        result['player_fta'] = st.box['fta'].copy()
        result['player_ftm'] = st.box['ftm'].copy()
        for key in ('world', 'period', 'clock', 'fouler', 'shooter', 'made', 'probability'):
            dtype = float if key in ('clock', 'probability') else int
            result[f'technical_{key}'] = np.asarray([event[key] for event in self.technical_events], dtype=dtype)
        return result
