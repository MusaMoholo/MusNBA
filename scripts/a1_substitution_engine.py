#!/usr/bin/env python3
"""Isolated S06 selected-timeout rotation policy; not an availability forecast."""
from __future__ import annotations

import json
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

from basketball_common import DERIVED, sha256_file
from scripts import (a1_minutes_fold_eval, a1_substitution_dataset, a1_substitution_in_coverage,
                     a1_substitution_in_screen, a1_substitution_out_screen, engine, projection)
from scripts.evaluate import EXPERIMENTS, FOLDS

ROOT = Path(__file__).resolve().parent.parent
TIERS = a1_substitution_in_screen.TIERS
POSITIONS = a1_substitution_in_screen.POSITIONS
DEAD_BALLS = tuple(engine.S[name] for name in
                   ('period_start', 'made_fg', 'made_ft', 'dead_turnover', 'foul', 'jump_ball'))
MASKS = ((np.arange(32)[:, None] >> np.arange(5)) & 1).astype(bool)


def conditional_exits(probability: np.ndarray, bench: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Draw independent exits conditional on enough eligible replacements."""
    probability = np.asarray(probability, dtype=float)
    bench = np.asarray(bench)
    if (probability.ndim != 2 or probability.shape[1] != 5 or bench.shape != (len(probability),)
            or not np.isfinite(probability).all() or ((probability < 0) | (probability > 1)).any()
            or (bench < 0).any()):
        raise ValueError('invalid outgoing probabilities or available-bench counts')
    weights = np.where(MASKS[None, :, :], probability[:, None, :], 1 - probability[:, None, :]).prod(axis=2)
    weights = np.where(MASKS.sum(axis=1)[None, :] <= bench[:, None], weights, 0)
    total = weights.sum(axis=1)
    if not np.isfinite(total).all() or (total <= 0).any():
        raise ValueError('outgoing distribution has no legal probability mass')
    choice = (rng.random(len(total))[:, None] * total[:, None] >= weights.cumsum(axis=1)).sum(axis=1)
    if (choice >= len(MASKS)).any():
        raise ValueError('outgoing conditional draw exceeded its support')
    return MASKS[choice]


def load_features(fold: str) -> pd.DataFrame:
    if fold not in FOLDS:
        raise ValueError('unsupported substitution candidate fold')
    path = DERIVED / f'experiments/20261122_a1_s05_unconditional_{fold}_corrected.parquet'
    audit = json.loads((EXPERIMENTS / '20261122_a1_s05_minutes_screen_accounting_corrected.json').read_text())
    if audit['output_sha256'].get(str(path.relative_to(ROOT))) != sha256_file(path):
        raise ValueError('pregame target proxies differ from their independently audited fingerprint')
    rows = pd.read_parquet(path, columns=a1_substitution_dataset.TARGET_COLUMNS)
    if rows.duplicated(['game_id', 'player']).any() or rows['prior_day'].ge(rows['date_et']).any():
        raise ValueError('candidate targets contain duplicate or non-prior roster dates')
    profile_dates = pd.to_datetime(rows['prior_profile_date'], errors='raise')
    dates = pd.to_datetime(rows['date_et'], errors='raise')
    if (profile_dates.notna() & profile_dates.ge(dates)).any():
        raise ValueError('candidate profile dates must precede the game')
    rows['prior_profile_date'] = profile_dates.dt.strftime('%Y-%m-%d')
    profiles = pd.read_parquet(a1_minutes_fold_eval.CAUSAL_PROFILES, columns=['date_et', 'player', 'pos'])
    rows = a1_substitution_in_coverage.attach_positions(rows, profiles)
    if not rows['tier'].isin(TIERS).all():
        raise ValueError('candidate target tiers are invalid')
    values = pd.to_numeric(rows['control_mean'], errors='raise').to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError('candidate target proxies are invalid')
    return rows


def load_candidate(report_path: Path, fold: str) -> tuple[lgb.Booster, lgb.Booster, dict]:
    report = json.loads(report_path.read_text())
    if report['fold'] != fold or report['training_through'] >= FOLDS[fold][1]:
        raise ValueError('substitution model training is not before the requested fold')
    for section in ('input_sha256', 'output_sha256'):
        for path, digest in report[section].items():
            if sha256_file(ROOT / path) != digest:
                raise ValueError(f'substitution artifact fingerprint differs: {path}')
    outputs = {Path(path).name: ROOT / path for path in report['output_sha256']}
    if set(outputs) != {'outgoing.txt', 'incoming.txt', 'templates.json'}:
        raise ValueError('substitution model artifacts are incomplete')
    outgoing = lgb.Booster(model_file=str(outputs['outgoing.txt']))
    incoming = lgb.Booster(model_file=str(outputs['incoming.txt']))
    if (tuple(outgoing.feature_name()) != a1_substitution_out_screen.FEATURES
            or tuple(incoming.feature_name()) != a1_substitution_in_screen.FEATURES):
        raise ValueError('substitution model feature order differs from its frozen screens')
    timing = json.loads(outputs['templates.json'].read_text())
    if timing['training_through'] != report['training_through']:
        raise ValueError('timeout template and model cutoffs differ')
    return outgoing, incoming, timing


def elapsed(period: np.ndarray, clock: np.ndarray) -> np.ndarray:
    period = np.asarray(period)
    clock = np.asarray(clock, dtype=float)
    length = np.where(period <= 4, 720, 300)
    if (period < 1).any() or not np.isfinite(clock).all() or ((clock < 0) | (clock > length)).any():
        raise ValueError('world period or clock is invalid')
    return np.where(period <= 4, (period - 1) * 720 + 720 - clock,
                    2880 + (period - 5) * 300 + 300 - clock)


class SelectedTimeoutPolicy:
    def __init__(self, outgoing: lgb.Booster, incoming: lgb.Booster, timing: dict, features: pd.DataFrame):
        self.outgoing, self.incoming, self.timing = outgoing, incoming, timing
        if not timing.get('regulation') or not timing.get('overtime'):
            raise ValueError('selected-timeout policy needs earlier regulation and overtime templates')
        keys = ['game_id', 'team', 'player']
        if features.duplicated(keys).any():
            raise ValueError('candidate game features contain duplicate player/team/game keys')
        self.features = {tuple(str(row[key]) for key in keys): row for row in features.to_dict('records')}
        self.counts: dict[str, int] = {}

    def begin(self, g: engine.Game, worlds: int, available: np.ndarray, seed: int) -> None:
        self.available = np.asarray(available, dtype=bool).copy()
        if self.available.shape != (worlds, g.n):
            raise ValueError('availability does not match the game worlds')
        if not np.isfinite(g.expected).all() or (g.expected < 0).any():
            raise ValueError('planned player minutes must be finite and non-negative')
        for side in range(2):
            if (self.available[:, g.side == side].sum(axis=1) < 5).any():
                raise ValueError(f'side {side} has fewer than five explicitly available players')
        self.rng = np.random.default_rng(projection.seed_for('a1_s06_timeout_policy', seed))
        self.current = np.full((worlds, 2, 5), -1, dtype=int)
        self.last_plan = np.full((worlds, 2, 5), -1, dtype=int)
        self.last_period = np.zeros(worlds, dtype=int)
        self.on_since = np.full((worlds, g.n), np.nan)
        self.off_since = np.full((worlds, g.n), np.nan)
        self.seen = np.zeros((worlds, g.n), dtype=bool)
        self.target = np.full(g.n, np.nan)
        self.tier = np.full(g.n, 'unknown', dtype=object)
        self.position = np.full(g.n, 'unknown', dtype=object)
        gid = str(g.game.get('game_id', g.game.get('id', '')))
        for index, player in enumerate(g.ids):
            side = g.sides[int(g.side[index])]
            key = (gid, str(g.game[f'{side}_id']), str(player))
            row = self.features.get(key)
            if row is None:
                continue
            self.target[index] = float(row['control_mean'])
            self.tier[index] = row['tier']
            if pd.notna(row['prior_position']):
                self.position[index] = row['prior_position']
        if not np.isin(self.tier, TIERS).all() or not np.isin(self.position, POSITIONS).all():
            raise ValueError('candidate game features contain invalid roles or positions')
        reg = self.timing['regulation']
        self.reg_templates = [reg[int(i)] for i in self.rng.integers(0, len(reg), size=worlds)]
        self.reg_index = np.zeros(worlds, dtype=int)
        self.ot_templates: list[list[float]] = [[] for _ in range(worlds)]
        self.ot_index = np.zeros(worlds, dtype=int)
        self.ot_period = np.zeros(worlds, dtype=int)
        self.counts = {
            'worlds': worlds, 'missing_target_players': int(np.isnan(self.target).sum()),
            'unknown_position_players': int((self.position == 'unknown').sum()),
            'timeout_worlds': 0, 'timeout_team_windows': 0, 'timeout_outgoing': 0,
            'coalesced_timeout_clocks': 0, 'expired_timeout_clocks': 0,
            'plan_resets': 0, 'foul_out_replacements': 0, 'scheduled_disqualified_replacements': 0,
            'overtime_timeout_worlds': 0,
        }

    def _legal_plan(self, g: engine.Game, st: engine.Worlds, w: int, side: int,
                    desired: np.ndarray) -> np.ndarray:
        desired = np.asarray(desired, dtype=int).copy()
        if (len(desired) != 5 or len(set(desired.tolist())) != 5
                or (desired < 0).any() or (desired >= g.n).any() or (g.side[desired] != side).any()):
            raise ValueError(f'world {w} side {side}: scheduled lineup is not a distinct five')
        legal = (g.side == side) & self.available[w] & (st.ingame['pf_so_far'][w] < 6)
        if legal.sum() < 5:
            raise ValueError(f'world {w} side {side}: fewer than five eligible players after foul-out')
        bad = np.flatnonzero(~legal[desired])
        for slot in bad:
            bench = np.flatnonzero(legal & ~np.isin(np.arange(g.n), desired))
            if not len(bench):
                raise ValueError(f'world {w} side {side}: no eligible foul-out replacement')
            desired[slot] = bench[np.argmax(g.expected[bench])]
        return desired

    def _set(self, g: engine.Game, st: engine.Worlds, w: int, side: int,
             desired: np.ndarray, now: float) -> None:
        legal = self._legal_plan(g, st, w, side, desired)
        if not np.array_equal(legal, desired):
            raise ValueError('attempted to set an unavailable or disqualified player')
        old = set(self.current[w, side].tolist()) - {-1}
        new = set(desired.tolist())
        for player in old - new:
            self.off_since[w, player] = now
        for player in new - old:
            self.on_since[w, player] = now
            self.seen[w, player] = True
        self.current[w, side] = desired

    def _timeout_due(self, w: int, period: int, clock: float, legal: bool) -> bool:
        template = self.reg_templates[w]
        index = int(self.reg_index[w])
        while index < len(template) and int(template[index][0]) < period:
            self.counts['expired_timeout_clocks'] += 1
            index += 1
        self.reg_index[w] = index
        if period <= 4:
            pending = template
            index = int(self.reg_index[w])
            local = 720 - clock
            if not legal or index >= len(pending) or int(pending[index][0]) != period:
                return False
            count = 0
            while index < len(pending) and int(pending[index][0]) == period and float(pending[index][1]) <= local:
                count += 1
                index += 1
            self.reg_index[w] = index
        else:
            if self.ot_period[w] != period:
                if self.ot_period[w] >= 5:
                    self.counts['expired_timeout_clocks'] += len(self.ot_templates[w]) - int(self.ot_index[w])
                template_id = int(self.rng.integers(len(self.timing['overtime'])))
                self.ot_templates[w] = self.timing['overtime'][template_id]
                self.ot_index[w] = 0
                self.ot_period[w] = period
            pending = self.ot_templates[w]
            index = int(self.ot_index[w])
            local = 300 - clock
            if not legal:
                return False
            count = 0
            while index < len(pending) and float(pending[index]) <= local:
                count += 1
                index += 1
            self.ot_index[w] = index
        if count:
            self.counts['timeout_worlds'] += 1
            self.counts['coalesced_timeout_clocks'] += count - 1
            self.counts['overtime_timeout_worlds'] += int(period > 4)
        return bool(count)

    def _numeric(self, st: engine.Worlds, worlds: np.ndarray, sides: np.ndarray,
                 players: np.ndarray, now: np.ndarray, rest: bool) -> list[np.ndarray]:
        period, clock = st.period[worlds], st.clock[worlds]
        seconds = st.ingame['sec_so_far'][worlds, players].astype(float)
        target = self.target[players]
        deficit = np.where(period <= 4, target * now / 2880 - seconds / 60, np.nan)
        since = self.off_since[worlds, players] if rest else self.on_since[worlds, players]
        duration = now - since
        if rest:
            duration = np.where(self.seen[worlds, players], duration, np.nan)
        if np.isinf(duration).any() or (duration[np.isfinite(duration)] < 0).any():
            raise ValueError('substitution stint or rest is invalid')
        if not rest and not np.isfinite(duration).all():
            raise ValueError('on-court player has no recorded stint start')
        margin = st.score[worlds, sides] - st.score[worlds, 1 - sides]
        return [period, clock, margin, st.ingame['pf_so_far'][worlds, players], seconds, duration, target, deficit]

    def _apply_timeouts(self, g: engine.Game, st: engine.Worlds, due: np.ndarray) -> None:
        worlds = np.repeat(due, 2)
        sides = np.tile(np.arange(2), len(due))
        fives = self.current[worlds, sides]
        n = len(worlds)
        flat_worlds = np.repeat(worlds, 5)
        flat_sides = np.repeat(sides, 5)
        players = fives.reshape(-1)
        now = elapsed(st.period[flat_worlds], st.clock[flat_worlds])
        cols = self._numeric(st, flat_worlds, flat_sides, players, now, rest=False)
        cols.extend((self.tier[players] == tier).astype(float) for tier in TIERS)
        probabilities = np.asarray(self.outgoing.predict(np.column_stack(cols), num_threads=1), dtype=float).reshape(n, 5)
        eligible = ((g.side[None, :] == sides[:, None]) & self.available[worlds]
                    & (st.ingame['pf_so_far'][worlds] < 6))
        eligible[np.arange(n)[:, None], fives] = False
        exits = conditional_exits(probabilities, eligible.sum(axis=1), self.rng)
        changing = np.flatnonzero(exits.any(axis=1))
        self.counts['timeout_team_windows'] += n
        self.counts['timeout_outgoing'] += int(exits.sum())
        if not len(changing):
            return
        candidate_groups, candidate_players, remaining = [], [], []
        for group in changing:
            bench = np.flatnonzero(eligible[group])
            candidate_groups.extend([int(group)] * len(bench))
            candidate_players.extend(bench.tolist())
            survivors = fives[group][~exits[group]]
            counts = [(self.position[survivors] == pos).sum() for pos in POSITIONS]
            remaining.extend([counts] * len(bench))
        groups = np.asarray(candidate_groups, dtype=int)
        candidate = np.asarray(candidate_players, dtype=int)
        candidate_worlds, candidate_sides = worlds[groups], sides[groups]
        now = elapsed(st.period[candidate_worlds], st.clock[candidate_worlds])
        cols = self._numeric(st, candidate_worlds, candidate_sides, candidate, now, rest=True)
        cols.extend((self.tier[candidate] == tier).astype(float) for tier in TIERS)
        cols.extend((self.position[candidate] == pos).astype(float) for pos in POSITIONS)
        position_counts = np.asarray(remaining, dtype=float)
        cols.extend(position_counts[:, index] for index in range(len(POSITIONS)))
        scores = np.asarray(self.incoming.predict(np.column_stack(cols), raw_score=True, num_threads=1), dtype=float)
        if scores.shape != (len(candidate),) or not np.isfinite(scores).all():
            raise ValueError('incoming model produced invalid relative scores')
        scores += self.rng.gumbel(size=len(scores))
        for group in changing:
            choices = np.flatnonzero(groups == group)
            count = int(exits[group].sum())
            if len(choices) < count:
                raise ValueError('conditional exits exceed the eligible incoming pool')
            chosen = choices[np.argsort(-scores[choices], kind='stable')[:count]]
            w, side = int(worlds[group]), int(sides[group])
            desired = fives[group].copy()
            desired[exits[group]] = candidate[chosen]
            time = float(elapsed(st.period[w:w + 1], st.clock[w:w + 1])[0])
            self._set(g, st, w, side, desired, time)

    def before_segment(self, g: engine.Game, st: engine.Worlds, active: np.ndarray,
                       scheduled: np.ndarray) -> np.ndarray:
        if scheduled.shape != (len(active), 2, 5):
            raise ValueError('scheduled lineups do not match active worlds')
        periods = st.period[active]
        legal = np.isin(st.start[active], DEAD_BALLS)
        first = self.last_period[active] == 0
        changed_period = (self.last_period[active] != periods) & ~first
        if (changed_period & (st.start[active] != engine.S['period_start'])).any():
            raise ValueError('world entered a period without a period-start boundary')
        plan = np.sort(scheduled, axis=2)
        changed = np.any(plan != self.last_plan[active], axis=2)
        reset = first[:, None] | (legal[:, None] & (changed | changed_period[:, None]))
        for row, side in zip(*np.nonzero(reset)):
            w = int(active[row])
            now = float(elapsed(st.period[w:w + 1], st.clock[w:w + 1])[0])
            desired = self._legal_plan(g, st, w, int(side), scheduled[row, side])
            self.counts['scheduled_disqualified_replacements'] += int(np.sum(desired != scheduled[row, side]))
            self._set(g, st, w, int(side), desired, now)
            self.last_plan[w, side] = plan[row, side]
            self.counts['plan_resets'] += int(not first[row])
        self.last_period[active] = periods
        due = [int(w) for row, w in enumerate(active)
               if self._timeout_due(int(w), int(periods[row]), float(st.clock[w]), bool(legal[row]))]
        if due:
            self._apply_timeouts(g, st, np.asarray(due, dtype=int))
        return self.current[active].copy()

    def after_fouls(self, g: engine.Game, st: engine.Worlds, active: np.ndarray,
                    offense: np.ndarray, defense: np.ndarray) -> bool:
        fives = self.current[active]
        fouls = st.ingame['pf_so_far'][active[:, None, None], fives]
        affected = np.any(fouls >= 6, axis=2)
        for row, side in zip(*np.nonzero(affected)):
            w = int(active[row])
            desired = self._legal_plan(g, st, w, int(side), fives[row, side])
            now = float(elapsed(st.period[w:w + 1], st.clock[w:w + 1])[0])
            self.counts['foul_out_replacements'] += int(np.sum(desired != fives[row, side]))
            self._set(g, st, w, int(side), desired, now)
            if int(st.off[w]) == side:
                offense[row] = desired
            else:
                defense[row] = desired
        return bool(affected.any())

    def finish(self, g: engine.Game, st: engine.Worlds) -> None:
        if not st.done.all():
            raise ValueError('candidate engine stopped before all worlds completed')
        for w in range(st.W):
            self.counts['expired_timeout_clocks'] += len(self.reg_templates[w]) - int(self.reg_index[w])
            if self.ot_period[w] >= 5:
                self.counts['expired_timeout_clocks'] += len(self.ot_templates[w]) - int(self.ot_index[w])
        expected = 240 + 25 * np.maximum(st.period - 4, 0)
        for side in range(2):
            player = g.side == side
            actual = st.minutes[:, player].sum(axis=(1, 2))
            if not np.allclose(actual, expected, rtol=0, atol=1e-5):
                raise ValueError(f'side {side}: simulated minutes do not equal five-player game time')
            points = st.box['pts'][:, player].sum(axis=(1, 2))
            if not np.array_equal(points, st.pts[:, side].sum(axis=1)):
                raise ValueError(f'side {side}: simulated player points do not sum to team points')
