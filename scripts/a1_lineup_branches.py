"""Isolated lineup-branch preparation; not connected to the nightly or serving."""
from __future__ import annotations

from copy import deepcopy

import numpy as np

from scripts import engine, minutes, rotations


def one_player(game: engine.Game, team_id: str, player_id: str, plays: bool) -> engine.Game:
    """Prepare a separate conditional game without changing the original inputs."""
    if not isinstance(plays, bool):
        raise ValueError('plays must be a boolean')
    if not all(isinstance(value, str) and value.isascii() and value.isdigit()
               for value in (team_id, player_id)):
        raise ValueError('team and player IDs must be ASCII digits')
    if game.mstate is None or game.strict_minute_targets:
        raise ValueError('one-player branches require the default D29 target rotation')
    ids = [str(pid) for pid in game.ids]
    if len(set(ids)) != len(ids):
        raise ValueError('duplicate player IDs in game')
    sides = [i for i, side in enumerate(game.sides) if str(game.game[f'{side}_id']) == team_id]
    if len(sides) != 1 or player_id not in ids:
        raise ValueError('player and team must identify one game roster')
    index = ids.index(player_id)
    if int(game.side[index]) != sides[0]:
        raise ValueError('player does not belong to that team')
    if not np.isfinite(game.avail).all() or not ((game.avail >= 0) & (game.avail <= 1)).all():
        raise ValueError('availability must be finite and between zero and one')
    if not 0 < game.avail[index] < 1:
        raise ValueError('branch player must have uncertain availability')

    branch = deepcopy(game)
    if branch.mstate is None:
        raise ValueError('copied game has no D29 minute states')
    branch.avail[index] = float(plays)
    local_index = index - int(np.flatnonzero(branch.side == sides[0])[0])
    branch.players[branch.sides[sides[0]]][local_index]['availability'] = float(plays)
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
