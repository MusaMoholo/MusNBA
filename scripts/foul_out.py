"""Opt-in NBA Rule 3-I foul-outs; unchanged fitted nodes and D29 targets. Not enabled by default."""
from __future__ import annotations

import numpy as np

from scripts import projection


class Rule3Policy:
    def __init__(self, capture_events: bool = False):
        self.capture_events = capture_events
        self.counts = {}
        self.technical_events = []

    def begin(self, g, worlds, available, seed):
        if available.shape != (worlds, g.n) or available.dtype != np.bool_:
            raise ValueError('rule3 availability does not match worlds/players')
        if not np.isfinite(g.expected).all() or (g.expected < 0).any():
            raise ValueError('rule3 requires valid D29 target priorities')
        if any((available[:, g.side == side].sum(axis=1) < 5).any() for side in (0, 1)):
            raise ValueError('rule3 cannot repair an invalid initial roster')
        self.available = available.copy()
        self.exempt = np.zeros_like(available)
        self.previous_fouls = np.zeros_like(available, dtype=np.float64)
        self.technical_rng = np.random.default_rng(projection.seed_for('a1_s06_foul_penalty', seed))
        self.technical_events = []
        self.counts = {'scheduled_replacements': 0, 'foul_out_replacements': 0,
                       'technical_attempts': 0, 'technical_makes': 0, 'retained_offensive_team_fouls': 0}

    def _repair(self, g, st, active, scheduled):
        if scheduled.shape != (len(active), 2, 5):
            raise ValueError('rule3 scheduled lineups have invalid dimensions')
        if ((scheduled < 0) | (scheduled >= g.n)).any():
            raise ValueError('rule3 scheduled lineup has invalid player index')
        if ((np.diff(np.sort(scheduled, axis=2), axis=2) == 0).any() or
                (g.side[scheduled] != np.arange(2)[None, :, None]).any()):
            raise ValueError('rule3 requires five distinct same-team players')
        lineups = scheduled.copy()
        allowed = self.available & ((st.ingame['pf_so_far'] < 6) | self.exempt)
        illegal = ~allowed[active[:, None, None], lineups]
        changed = np.zeros(len(active), dtype=bool)
        replacements = 0
        for row, side in np.argwhere(illegal.any(axis=2)):
            world = int(active[row])
            eligible = allowed[world] & (g.side == side)
            if eligible.sum() < 5:
                raise ValueError('rule3 has fewer than five legal/currently-retained players')
            for slot in np.flatnonzero(illegal[row, side]):
                bench = np.flatnonzero(eligible & ~np.isin(np.arange(g.n), lineups[row, side]))
                if not len(bench):
                    raise ValueError('rule3 has no eligible replacement')
                lineups[row, side, slot] = bench[np.argmax(g.expected[bench])]
                replacements += 1
            changed[row] = True
        return lineups, changed, replacements

    def before_segment(self, g, st, active, scheduled):
        self.previous_fouls[active] = st.ingame['pf_so_far'][active]
        lineups, _, count = self._repair(g, st, active, scheduled)
        self.counts['scheduled_replacements'] += count
        return lineups

    def after_fouls(self, g, st, active, offense, defense):
        off = st.off[active]
        current = np.empty((len(active), 2, 5), dtype=int)
        current[np.arange(len(active)), off] = offense
        current[np.arange(len(active)), 1 - off] = defense
        fouls = st.ingame['pf_so_far'][active]
        delta = fouls - self.previous_fouls[active]
        if not np.isfinite(delta).all() or ((delta < 0) | (delta > 1)).any():
            raise ValueError('rule3 personal-foul transition is invalid')
        for row, fouler in np.argwhere((delta == 1) & (fouls == 6)):
            world, side = int(active[row]), int(g.side[fouler])
            ordinary = self.available[world] & (g.side == side) & (fouls[row] < 6)
            if ordinary.sum() < 5:
                if fouler not in current[row, side]:
                    raise ValueError('rule3 can only retain the currently playing offender')
                self.exempt[world, fouler] = True
                if self.exempt[world, g.side == side].sum() != 5 - ordinary.sum():
                    raise ValueError('rule3 would revive a previously removed disqualified player')
        lineups, changed, count = self._repair(g, st, active, current)
        self.counts['foul_out_replacements'] += count
        offense[:] = lineups[np.arange(len(active)), off]
        defense[:] = lineups[np.arange(len(active)), 1 - off]
        for row, fouler in np.argwhere((delta == 1) & (fouls >= 6)):
            world, side = int(active[row]), int(g.side[fouler])
            if not self.exempt[world, fouler]:
                continue
            if fouler not in lineups[row, side]:
                raise ValueError('rule3 retained offender left the current five')
            if side == off[row]:  # Rule 12B-VII exception; defensive team foul is already counted.
                st.tfouls[world, side] += 1
                self.counts['retained_offensive_team_fouls'] += 1
            opponents = lineups[row, 1 - side]
            percentages = np.asarray(g.P['ft_pct'][opponents], dtype=float)
            if np.isinf(percentages).any() or ((percentages < 0) | (percentages > 1)).any():
                raise ValueError('rule3 technical-shooter FT profile is invalid')
            known = np.flatnonzero(np.isfinite(percentages))
            if not len(known):
                raise ValueError('rule3 technical needs a known opposing on-court FT profile')
            shooter = int(opponents[known[np.argmax(percentages[known])]])
            probability = float(g.P['ft_pct'][shooter])
            made = int(self.technical_rng.random() < probability)
            period = min(int(st.period[world]) - 1, 4)
            for key, value in (('fta', 1), ('ftm', made), ('pts', made)):
                st.box[key][world, shooter, period] += value
            st.pts[world, 1 - side, period] += made
            st.score[world, 1 - side] += made
            st.ingame['pts_so_far'][world, shooter] += made
            self.counts['technical_attempts'] += 1
            self.counts['technical_makes'] += made
            if self.capture_events:
                self.technical_events.append({'world': world, 'period': int(st.period[world]),
                                              'clock': float(st.clock[world]), 'fouler': int(fouler),
                                              'shooter': shooter, 'made': made, 'probability': probability,
                                              'offensive': bool(side == off[row])})
        return changed

    def finish(self, g, st):
        if not st.done.all():
            raise ValueError('rule3 simulation did not complete')
