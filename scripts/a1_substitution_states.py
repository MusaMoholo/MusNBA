#!/usr/bin/env python3
"""Describe observed timeout substitution decisions by pre-game role and current state."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import atomic_bytes, sha256_file, write_json  # noqa: E402
from scripts import a1_compare  # noqa: E402

TIERS = ('star', 'starter', 'bench', 'unknown')


def player_states(windows: pd.DataFrame, roles: pd.DataFrame) -> pd.DataFrame:
    if roles.duplicated(['game_id', 'player']).any() or windows['window_id'].duplicated().any():
        raise ValueError('duplicate player-game role or timeout window')
    mapping = {(str(row.game_id), str(row.player)):
               (str(row.tier), str(row.team_control), str(row.date_et_control), bool(row.role_missing))
               for row in roles.itertuples(index=False)}
    states = []
    for window in windows.to_dict('records'):
        changes = json.loads(window['changes_json'])
        for side in ('home', 'away'):
            team = window[side]
            margin = window['margin_home'] if side == 'home' else -window['margin_home']
            if margin <= -15:
                margin_bin = 'behind_15_plus'
            elif margin >= 15:
                margin_bin = 'ahead_15_plus'
            elif abs(margin) <= 5:
                margin_bin = 'close_5_or_less'
            else:
                margin_bin = 'intermediate'
            before = set(window[f'{side}_five_before'])
            outgoing = {change['player_out'] for change in changes if change['team'] == team}
            incoming = {change['player_in'] for change in changes if change['team'] == team}
            if len(before) != 5 or not outgoing.issubset(before) or incoming & before:
                raise ValueError(f"{window['window_id']}: invalid labelled lineup transition")
            fields = ('players', 'fouls_before', 'stint_before', 'rest_before')
            values = [window[f'{side}_{field}'] for field in fields]
            if len({len(value) for value in values}) != 1:
                raise ValueError(f"{window['window_id']}: player state vectors are misaligned")
            for player, fouls, stint, rest in zip(*values):
                role = mapping.get((str(window['game_id']), player))
                if role is not None and (role[1] != team or role[2] != window['date_et'] or role[0] not in TIERS):
                    raise ValueError(f"{window['window_id']}: pre-game role team, date or tier is invalid")
                on = player in before
                elapsed = float(stint if on else rest)
                if not np.isfinite(elapsed) or elapsed < 0:
                    raise ValueError(f"{window['window_id']}: missing or negative stint/rest duration")
                duration = 'under_4' if elapsed < 240 else ('4_to_under_8' if elapsed < 480 else '8_plus')
                states.append({
                    'window_id': window['window_id'], 'game_id': window['game_id'], 'player': player,
                    'team': team, 'tier': role[0] if role is not None else 'unknown',
                    'role_missing': role is None or role[3], 'decision': 'out' if on else 'in',
                    'changed': player in (outgoing if on else incoming), 'margin': margin_bin,
                    'period': str(window['period']) if window['period'] <= 4 else 'OT',
                    'foul_trouble': 'yes' if fouls >= min(5, window['period'] + 1) else 'no',
                    'duration': duration,
                })
    result = pd.DataFrame(states)
    if result.empty or result.duplicated(['window_id', 'team', 'player']).any():
        raise ValueError('player-state population is empty or duplicated')
    return result


def summarize(states: pd.DataFrame) -> dict:
    ids = sorted(states['game_id'].unique().tolist())
    draws = np.random.default_rng(a1_compare.BOOTSTRAP_SEED).integers(
        0, len(ids), (a1_compare.BOOTSTRAP_REPLICATES, len(ids)))
    weights = np.zeros(draws.shape, dtype=np.int16)
    np.add.at(weights, (np.arange(len(draws))[:, None], draws), 1)
    cells = {}
    started = time.monotonic()
    completed = 0
    for decision in ('out', 'in'):
        for tier in ('all', *TIERS):
            part = states[states['decision'].eq(decision)]
            if tier != 'all':
                part = part[part['tier'].eq(tier)]
            for dimension in ('margin', 'period', 'foul_trouble', 'duration'):
                for value, group in part.groupby(dimension, sort=True):
                    n_games = int(group['game_id'].nunique())
                    n_player_games = len(group[['game_id', 'player']].drop_duplicates())
                    supported = n_player_games >= 100 and n_games >= 30
                    per_game = group.groupby('game_id')['changed'].agg(['sum', 'count']).reindex(ids, fill_value=0)
                    n = len(group)
                    changed = int(group['changed'].sum())
                    interval = None
                    if supported:
                        totals = weights @ per_game['count'].to_numpy(dtype=float)
                        successes = weights @ per_game['sum'].to_numpy(dtype=float)
                        if (totals == 0).any():
                            raise ValueError('supported bootstrap cell has an empty replicate')
                        interval = [float(x) for x in np.quantile(successes / totals, [0.025, 0.975])]
                    key = f'{decision}/{tier}/{dimension}/{value}'
                    cells[key] = {'observations': n, 'player_games': n_player_games, 'games': n_games,
                                  'changed': changed, 'rate': changed / n, 'supported': supported, 'ci_95': interval}
            completed += 1
            print(f'role-decision groups {completed}/10 {time.monotonic() - started:.1f}s', flush=True)
    return {'games': len(ids), 'player_decisions': len(states),
            'missing_role_decisions': int(states['role_missing'].sum()), 'cells': cells}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('opportunities', type=Path)
    parser.add_argument('--rows', type=Path, required=True)
    parser.add_argument('--pregame', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--rows-output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.rows_output.exists():
        raise FileExistsError('refusing to overwrite an existing state-response report')
    paths = [args.opportunities.resolve(), args.rows.resolve(), args.pregame.resolve(), Path(__file__),
             ROOT / 'scripts/a1_compare.py']
    if any(not path.is_relative_to(ROOT) for path in paths + [args.rows_output.resolve()]):
        raise ValueError('state-response inputs and output must be inside the repository')
    source = json.loads(args.opportunities.read_text())
    for path, digest in source['input_sha256'].items():
        if sha256_file(ROOT / path) != digest:
            raise ValueError(f'opportunity input changed: {path}')
    rows_key = str(args.rows.resolve().relative_to(ROOT))
    if source['output_sha256'].get(rows_key) != sha256_file(args.rows):
        raise ValueError('supplied rows do not match the recorded opportunity output')
    windows = pd.read_parquet(args.rows)
    if len(windows) != source['retained_windows'] or windows['game_id'].nunique() != source['retained_games']:
        raise ValueError('opportunity rows do not match the recorded population')
    roster = {}
    for window in windows.to_dict('records'):
        for side in ('home', 'away'):
            for player in window[f'{side}_players']:
                key = (window['game_id'], player)
                value = (window[side], window['date_et'])
                if key in roster and roster[key] != value:
                    raise ValueError(f'{key}: inconsistent game team or date')
                roster[key] = value
    roles = pd.DataFrame([(game, player, team, date) for (game, player), (team, date) in roster.items()],
                         columns=['game_id', 'player', 'team_control', 'date_et_control'])
    pregame = pd.read_parquet(args.pregame, columns=['game_id', 'player', 'date_et', 'usage', 'start_share'])
    games = windows[['game_id', 'date_et']].drop_duplicates()
    tiers = a1_compare.roles(roles[['game_id', 'player']], pregame, games)
    roles = roles.merge(tiers, on=['game_id', 'player'], validate='one_to_one')
    coverage = roles[['game_id', 'player']].merge(pregame[['game_id', 'player']], on=['game_id', 'player'],
                                                how='left', validate='one_to_one', indicator=True)
    roles['role_missing'] = coverage['_merge'].eq('left_only')
    states = player_states(windows, roles)
    if int(states['decision'].eq('out').sum()) != 10 * len(windows):
        raise ValueError('timeout windows do not each have five on-court players per team')
    expected_changes = int((windows['home_subs'] + windows['away_subs']).sum())
    for decision in ('out', 'in'):
        if int(states.loc[states['decision'].eq(decision), 'changed'].sum()) != expected_changes:
            raise ValueError(f'{decision} player labels do not reconcile with substitutions')
    accounting = summarize(states)
    result = {
        'experiment': 'a1_s06_timeout_state_response_diagnostic',
        **accounting,
        'method': 'Describe outgoing and incoming frequencies at independently reconciled full-timeout windows '
                  'by S01 pre-game role and current score, fouls, period and stint/rest. Supported intervals '
                  'resample complete games 10,000 times with the S01 seed.',
        'limitations': 'Actual-participant rosters, inferred period lineups and outcome-dependent exclusion of '
                       'ambiguous same-clock decisions make these descriptive selected-window rates, not '
                       'pre-game forecasts, causal effects or calibrated substitution hazards.',
        'input_sha256': {str(path.relative_to(ROOT)): sha256_file(path) for path in paths},
    }
    atomic_bytes(args.rows_output, states.to_parquet(index=False))
    result['output_sha256'] = {str(args.rows_output.resolve().relative_to(ROOT)): sha256_file(args.rows_output)}
    write_json(args.output, result, pretty=True)
    print(f"described {accounting['player_decisions']} player decisions across {accounting['games']} games; "
          f"{accounting['missing_role_decisions']} lack the matched pre-game role record", flush=True)


if __name__ == '__main__':
    main()
