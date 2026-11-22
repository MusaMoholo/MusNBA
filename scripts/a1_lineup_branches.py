"""Isolated lineup-branch preparation; not connected to the nightly or serving."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from datetime import date
from fractions import Fraction
from itertools import product

import numpy as np

from scripts import engine, minutes, rotations


class BranchLegalityError(ValueError):
    """A branch cannot be completed safely with the current foul-out rules."""


class BranchLegalityGuard:
    """Reject unsupported foul-outs without changing the engine's draws or lineups."""

    def __init__(self) -> None:
        self.counts: dict[str, int] = {}
        self.available = np.empty((0, 0), dtype=bool)

    def begin(self, g: engine.Game, worlds: int, available: np.ndarray, seed: int) -> None:
        if available.shape != (worlds, g.n) or available.dtype != bool:
            raise BranchLegalityError('branch availability does not match the game worlds')
        for side in range(2):
            if (available[:, g.side == side].sum(axis=1) < 5).any():
                raise BranchLegalityError(f'branch side {side} has fewer than five available players')
        self.available = available.copy()

    def _check(self, g: engine.Game, st: engine.Worlds, active: np.ndarray, lineups: np.ndarray) -> None:
        if lineups.shape != (len(active), 2, 5):
            raise BranchLegalityError('branch lineup dimensions do not match active worlds')
        outside = ((lineups < 0) | (lineups >= g.n)).any(axis=2)
        if outside.any():
            row, side = np.argwhere(outside)[0]
            raise BranchLegalityError(f'branch game {g.game["game_id"]} world {active[row]} side {side}: invalid five')
        invalid = ((np.diff(np.sort(lineups, axis=2), axis=2) == 0).any(axis=2)
                   | (g.side[lineups] != np.arange(2)[None, :, None]).any(axis=2)
                   | (~self.available[active[:, None, None], lineups]).any(axis=2))
        if invalid.any():
            row, side = np.argwhere(invalid)[0]
            raise BranchLegalityError(f'branch game {g.game["game_id"]} world {active[row]} side {side}: invalid five')
        fouled = st.ingame['pf_so_far'][active[:, None, None], lineups] >= 6
        if fouled.any():
            row, side, slot = np.argwhere(fouled)[0]
            world = active[row]
            raise BranchLegalityError(
                f'branch game {g.game["game_id"]} world {world} side {side} '
                f'period {st.period[world]} clock {st.clock[world]:.1f}: '
                f'unsupported sixth foul for player {g.ids[int(lineups[row, side, slot])]}'
            )

    def before_segment(self, g: engine.Game, st: engine.Worlds, active: np.ndarray,
                       scheduled: np.ndarray) -> np.ndarray:
        self._check(g, st, active, scheduled)
        return scheduled

    def after_fouls(self, g: engine.Game, st: engine.Worlds, active: np.ndarray,
                    offense: np.ndarray, defense: np.ndarray) -> bool:
        lineups = np.empty((len(active), 2, 5), dtype=int)
        off = st.off[active]
        lineups[np.arange(len(active)), off] = offense
        lineups[np.arange(len(active)), 1 - off] = defense
        self._check(g, st, active, lineups)
        return False

    def finish(self, g: engine.Game, st: engine.Worlds) -> None:
        if not st.done.all():
            raise BranchLegalityError('branch engine stopped before all worlds completed')


@dataclass(frozen=True)
class Branch:
    assignments: tuple[tuple[str, str, bool], ...]
    weight: Fraction | None

    @property
    def branch_id(self) -> str:
        return 'lineup-v1:' + ','.join(
            f'{team}/{player}={"plays" if plays else "sits"}'
            for team, player, plays in self.assignments
        )


@dataclass(frozen=True)
class SelectedPlayer:
    team_id: str
    player_id: str
    probability: float
    status: str
    availability_basis: str
    status_source: str | None
    reported_status: str | None
    healthy_role: float | None
    role_basis: str
    usage: float | None
    missing: tuple[str, ...]


def select_uncertain(game: engine.Game, registry: Mapping[str, dict],
                     minutes_latest: Mapping[str, dict]) -> tuple[SelectedPlayer, ...]:
    """Select uncertain players; callers must supply the cutoff-safe origin inputs."""
    origin = date.fromisoformat(game.input_before)
    if origin > date.fromisoformat(game.day):
        raise ValueError('forecast origin must not follow the slate')
    if game.mstate is None or game.strict_minute_targets:
        raise ValueError('selection requires the default D29 target rotation')
    ids = [str(pid) for pid in game.ids]
    if len(set(ids)) != len(ids):
        raise ValueError('duplicate player IDs in game')
    if not np.isfinite(game.avail).all() or not ((game.avail >= 0) & (game.avail <= 1)).all():
        raise ValueError('availability must be finite and between zero and one')
    usage_values = game.P.get('usage')
    if usage_values is not None and len(usage_values) != len(ids):
        raise ValueError('usage profile does not match the game roster')
    chosen = []
    for index, player_id in enumerate(ids):
        probability = float(game.avail[index])
        if not 0 < probability < 1:
            continue
        side_index = int(game.side[index])
        if side_index not in (0, 1):
            raise ValueError('player has an invalid game side')
        side = game.sides[side_index]
        team_id = str(game.game[f'{side}_id'])
        local_index = index - int(np.flatnonzero(game.side == side_index)[0])
        player = game.players[side][local_index]
        record = registry.get(player_id)
        if (str(player.get('id')) != player_id or record is None or not record.get('on_roster')
                or str(record.get('team')) != team_id):
            raise ValueError(f'player {player_id} does not match the origin roster')
        status = (record.get('status') or '').strip() or 'Unknown'
        if player.get('status') != status or float(player['availability']) != probability:
            raise ValueError(f'player {player_id} availability inputs differ from the origin roster')
        state = minutes_latest.get(player_id)
        games = state.get('games') if state is not None else 0
        if not isinstance(games, int) or isinstance(games, bool) or games < 0:
            raise ValueError(f'player {player_id} has invalid prior minutes history')
        if games:
            last_date = state.get('last_date') if state is not None else None
            if not last_date or date.fromisoformat(str(last_date)) >= origin:
                raise ValueError(f'player {player_id} minutes history is not before the origin')
        raw_role = game.mstate[index].get('healthy')
        role = None if raw_role is None or np.isnan(raw_role) else float(raw_role)
        if role is not None and (not np.isfinite(role) or role < 0):
            raise ValueError(f'player {player_id} has invalid healthy role')
        raw_usage = None if usage_values is None else usage_values[index]
        usage = None if raw_usage is None or np.isnan(raw_usage) else float(raw_usage)
        if usage is not None and (not np.isfinite(usage) or not 0 <= usage <= 1):
            raise ValueError(f'player {player_id} has invalid prior usage')
        missing = tuple(name for name, unknown in (
            ('observed_role', not games or role is None), ('usage', usage is None),
        ) if unknown)
        if ((role is not None and role >= 15) or (usage is not None and usage >= 0.25) or missing):
            chosen.append(SelectedPlayer(
                team_id, player_id, probability, status, player['availability_basis'],
                record.get('status_source'), record.get('reported_status'), role,
                'history_based' if games else 'prior', usage, missing,
            ))
    if chosen:
        _selected_indices(game, [(p.team_id, p.player_id) for p in chosen])
    return tuple(sorted(chosen, key=lambda p: (p.team_id, p.player_id)))


def _selected_indices(game: engine.Game, selected: Sequence[tuple[str, str]]) -> list[tuple[str, str, int]]:
    if not selected:
        raise ValueError('at least one branch player is required')
    if game.mstate is None or game.strict_minute_targets:
        raise ValueError('branches require the default D29 target rotation')
    ids = [str(pid) for pid in game.ids]
    if len(set(ids)) != len(ids):
        raise ValueError('duplicate player IDs in game')
    if not np.isfinite(game.avail).all() or not ((game.avail >= 0) & (game.avail <= 1)).all():
        raise ValueError('availability must be finite and between zero and one')
    result = []
    seen = set()
    for team_id, player_id in selected:
        if not all(isinstance(value, str) and value.isascii() and value.isdigit()
                   for value in (team_id, player_id)):
            raise ValueError('team and player IDs must be ASCII digits')
        if player_id in seen:
            raise ValueError('duplicate selected player ID')
        seen.add(player_id)
        sides = [i for i, side in enumerate(game.sides) if str(game.game[f'{side}_id']) == team_id]
        if len(sides) != 1 or player_id not in ids:
            raise ValueError('player and team must identify one game roster')
        index = ids.index(player_id)
        if int(game.side[index]) != sides[0]:
            raise ValueError('player does not belong to that team')
        if not 0 < game.avail[index] < 1:
            raise ValueError('branch player must have uncertain availability')
        result.append((team_id, player_id, index))
    return sorted(result)


def enumerate_branches(game: engine.Game, selected: Sequence[tuple[str, str]]) -> tuple[Branch, ...]:
    """Use uncalibrated independent weights for <=2 players, else unweighted sensitivities."""
    players = _selected_indices(game, selected)
    if len(players) <= 2:
        choices = product((True, False), repeat=len(players))
    else:
        choices = [tuple(i != missing for i in range(len(players))) for missing in range(-1, len(players))]
    branches = []
    for choice in choices:
        weight = None
        if len(players) <= 2:
            weight = Fraction(1)
            for (_, _, index), plays in zip(players, choice):
                p = Fraction(str(game.avail[index]))
                weight *= p if plays else 1 - p
        assignments = tuple((team, player, plays) for (team, player, _), plays in zip(players, choice))
        branches.append(Branch(assignments, weight))
    if len(players) <= 2 and sum(branch.weight for branch in branches if branch.weight is not None) != 1:
        raise ValueError('exhaustive branch weights do not sum to one')
    return tuple(branches)


def one_player(game: engine.Game, team_id: str, player_id: str, plays: bool) -> engine.Game:
    """Prepare a separate conditional game without changing the original inputs."""
    return prepare_branch(game, ((team_id, player_id, plays),))


def prepare_branch(game: engine.Game, assignments: Sequence[tuple[str, str, bool]]) -> engine.Game:
    """Fix selected availability together, then independently re-solve both rosters."""
    if not all(isinstance(plays, bool) for _, _, plays in assignments):
        raise ValueError('plays must be a boolean')
    players = _selected_indices(game, [(team, player) for team, player, _ in assignments])
    decisions = {(team, player): plays for team, player, plays in assignments}
    branch = deepcopy(game)
    if branch.mstate is None:
        raise ValueError('copied game has no D29 minute states')
    for team, player, index in players:
        plays = decisions[(team, player)]
        side_index = int(branch.side[index])
        branch.avail[index] = float(plays)
        local_index = index - int(np.flatnonzero(branch.side == side_index)[0])
        branch.players[branch.sides[side_index]][local_index]['availability'] = float(plays)
    for i, side in enumerate(branch.sides):
        indices = np.flatnonzero(branch.side == i)
        eligible = [int(j) for j in indices if branch.avail[j] > 0]
        if len(eligible) < 5:
            raise ValueError(f'{side} has fewer than five possible available players')
        states = [branch.mstate[j] for j in eligible]
        targets = minutes.game_targets(states)
        if (not np.isfinite(targets).all() or (targets < 0).any() or (targets > 48 + 1e-8).any()
                or not np.isclose(targets.sum(), 240, rtol=0, atol=1e-6)):
            raise ValueError(f'{side} D29 targets do not form a legal 240-minute allocation')
        branch.expected[indices] = 0.0
        branch.expected[eligible] = targets
        for j in indices:
            branch.mstate[j]['target'] = float(branch.expected[j])
        sure = [j for j in eligible if branch.avail[j] >= 0.9]
        pool = sure if len(sure) >= 5 else eligible
        players = branch.players[side]
        offset = int(indices[0])
        chosen = minutes.projected_starters(
            [branch.mstate[j] for j in pool],
            [rotations.group(players[j - offset]['pos']) for j in pool],
        )
        selected = {pool[k] - offset for k in chosen}
        branch.lineup[i] = sorted(selected)
        for j, player in enumerate(players):
            player['starter'] = player['projected_starter'] = j in selected
    return branch
