#!/usr/bin/env python3
"""Capture raw simulated worlds for an independent S06 lineup and accounting audit."""
from __future__ import annotations

import numpy as np

from scripts import a1_foul_penalty_engine, a1_substitution_engine, engine


def capture(g: engine.Game, st: engine.Worlds, policy: a1_substitution_engine.SelectedTimeoutPolicy) -> dict[str, np.ndarray]:
    if not policy.capture_trace or not policy.trace:
        raise ValueError('world accounting requested without a complete lineup trace')
    result = {
        'game_id': np.asarray(str(g.game['game_id'])),
        'player_ids': np.asarray(g.ids, dtype=str),
        'side': np.asarray(g.side).copy(),
        'available': policy.available.copy(),
        'final_period': st.period.copy(),
        'final_score': st.score.copy(),
        'minutes': st.minutes.copy(),
        'player_points': st.box['pts'].copy(),
        'player_fouls': st.box['pf'].copy(),
        'team_points': st.pts.copy(),
        **{f'trace_{key}': np.concatenate([entry[key] for entry in policy.trace], axis=0)
           for key in ('world', 'period', 'clock', 'lineups', 'fouls', 'phase')},
    }
    if isinstance(policy, a1_foul_penalty_engine.PlayerFoulPenaltyPolicy):
        result['trace_all_fouls'] = np.concatenate([entry['all_fouls'] for entry in policy.trace], axis=0)
        result['player_ft_pct'] = np.asarray(g.P['ft_pct']).copy()
        result['player_fta'] = st.box['fta'].copy()
        result['player_ftm'] = st.box['ftm'].copy()
        for key in ('world', 'period', 'clock', 'fouler', 'shooter', 'made', 'probability'):
            dtype = float if key in ('clock', 'probability') else int
            result[f'technical_{key}'] = np.asarray([event[key] for event in policy.technical_events], dtype=dtype)
    return result
