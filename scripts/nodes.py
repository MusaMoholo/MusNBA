#!/usr/bin/env python3
"""Training data for the decision chain (ENGINE_PLAN D20; TRAINING_PLAN §1–§2).

Builds, from M2 segments and M4 point-in-time profiles, one dataset per decision:

  stage 1  duration (time to the event, 2-second bins) · event (action / defensive foul / violation)
  stage 2  who (of five) · what (5 zones, turnover, fouled on a 2 or a 3) · shot result (miss/make/and-one)
  stage 3  assisted · assister (of four) · blocked · blocker (of five) · turnover type · stealer · fouler
  stage 4  free throw · rebound (offence/defence × player/team) · rebounder (of five)

Player choices are candidate rows (one per player on the floor) grouped by segment. Every row carries the
game situation, both lineups' aggregates, and in-game counts so far (minutes, uses, makes, fouls).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED  # noqa: E402

ZONES = ['rim', 'paint', 'mid', 'corner3', 'above3']
START_TYPES = ['period_start', 'made_fg', 'made_ft', 'dreb', 'steal', 'dead_turnover', 'oreb', 'foul', 'jump_ball', 'other']
EVENT = ['action', 'def_foul', 'violation']
WHAT = ZONES + ['turnover', 'fouled_2', 'fouled_3']
RESULT = ['miss', 'make', 'and_one']
REBOUND = ['off', 'team_off', 'def', 'team_def']
TOV_TYPE = ['live', 'offensive_foul', 'dead_other']
DURATION_EDGES = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24]  # 13 bins: <2, 2–4, …, 22–24, ≥24
PROFILE = ['games_eff', 'min_avg', 'start_share', 'off_segs_eff', 'usage', 'shot_share', 'tov_share', 'foul_drawn_share',
           'live_tov_share', 'assisted_share', 'ft_pct', 'fta_per_use', 'ast_rate', 'oreb_pct', 'dreb_pct', 'stl_rate',
           'blk_rate', 'pf_rate', 'shots_eff'] + [f'mix_{z}' for z in ZONES] + [f'fg_{z}' for z in ZONES] \
          + [f'usage_mult_q{q}' for q in (1, 2, 3, 4)] + [f'min_share_q{q}' for q in (1, 2, 3, 4)]
IN_GAME = ['sec_so_far', 'uses_so_far', 'fga_so_far', 'made_so_far', 'pts_so_far', 'pf_so_far', 'ast_so_far']
CONTEXT = ['period', 'start_clock', 'sec_left_game', 'margin', 'fouls_def', 'fouls_off', 'off_home', 'season_type', 'season',
           'start_code']
LINEUP = ['off_usage_sum', 'off_usage_max', 'off_ast_sum', 'off_three_sum', 'off_oreb_sum', 'off_bigs', 'off_min_mean',
          'def_blk_sum', 'def_blk_max', 'def_stl_sum', 'def_dreb_sum', 'def_pf_sum', 'def_bigs', 'def_min_mean']


def group(pos) -> str:
    p = str(pos or '').upper()
    return 'C' if p.startswith('C') else 'G' if p.startswith('G') or p in ('PG', 'SG') else 'F'


def load_segments(include_current: bool = False) -> pd.DataFrame:
    paths = sorted((DERIVED / 'history').glob('*/segments.parquet'))
    if include_current and (DERIVED / 'segments.parquet').exists():
        paths.append(DERIVED / 'segments.parquet')
    seg = pd.concat([pd.read_parquet(p) for p in paths], ignore_index=True)
    seg = seg[seg['game_ok']].reset_index(drop=True)  # rows stay in game order within each game
    seg['seg_id'] = np.arange(len(seg))
    seg['start_code'] = seg['start_type'].map({s: i for i, s in enumerate(START_TYPES)}).fillna(len(START_TYPES) - 1).astype(int)
    seg['margin'] = seg['score_off'] - seg['score_def']
    seg['sec_left_game'] = np.where(seg['period'] <= 4, (4 - seg['period']) * 720 + seg['start_clock'], seg['start_clock'])
    seg['off_home'] = seg['off_home'].astype(int)
    seg['shot_time'] = seg['shot_time'].clip(lower=0)
    seg['distance'] = np.sqrt((seg['x'] - 25) ** 2 + seg['y'] ** 2)
    seg['lateral'] = (seg['x'] - 25).abs()
    seg['made'] = seg['made'].astype(float)
    return seg


def _cumulative_before(left: pd.DataFrame, events: pd.DataFrame, cols) -> pd.DataFrame:
    """Per (game, player): totals of `cols` over events in earlier segments of the same game."""
    ev = events.groupby(['game_id', 'player', 'seg_id'])[cols].sum().reset_index().sort_values('seg_id')
    ev[cols] = ev.groupby(['game_id', 'player'])[cols].cumsum()
    order = left[['game_id', 'player', 'seg_id']].reset_index().sort_values('seg_id')
    merged = pd.merge_asof(order, ev, on='seg_id', by=['game_id', 'player'], allow_exact_matches=False, direction='backward')
    merged = merged.set_index('index').reindex(left.index)
    return merged[cols].fillna(0)


class Chain:
    """Segments plus offence/defence candidate tables with profiles, relative roles and in-game counts."""

    def __init__(self, include_current: bool = False):
        seg = load_segments(include_current)
        pre = pd.read_parquet(DERIVED / 'features' / 'pregame.parquet')
        pre['grp'] = pre['pos'].map(group)
        self.seg = seg
        self.off = self._side(seg, pre, 'off')
        self.dfn = self._side(seg, pre, 'def')
        self._in_game()
        self._relative()
        self._lineups()

    @staticmethod
    def _side(seg, pre, side):
        cols = [f'{side}_{i}' for i in range(1, 6)]
        long = seg[['seg_id', 'game_id', 'period'] + cols].melt(id_vars=['seg_id', 'game_id', 'period'], value_vars=cols,
                                                               value_name='player').dropna(subset=['player'])
        long = long.drop(columns='variable').merge(pre[['game_id', 'player', 'grp'] + PROFILE], on=['game_id', 'player'], how='left')
        long['is_big'] = (long['grp'] == 'C').astype(np.int8)
        long['grp_code'] = long['grp'].map({'G': 0, 'F': 1, 'C': 2}).fillna(1).astype(np.int8)
        q = long['period'].clip(upper=4).astype(int)
        long['usage_mult_now'] = np.select([q == k for k in (1, 2, 3, 4)], [long[f'usage_mult_q{k}'] for k in (1, 2, 3, 4)])
        return long.drop(columns='period').sort_values(['seg_id', 'player']).reset_index(drop=True)

    def _in_game(self):
        s = self.seg
        on = pd.concat([self.off[['game_id', 'player', 'seg_id']], self.dfn[['game_id', 'player', 'seg_id']]])
        on = on.merge(s[['seg_id', 'duration']], on='seg_id')
        actors = s[s['actor'].notna()]
        ev = pd.DataFrame({'game_id': actors['game_id'], 'player': actors['actor'], 'seg_id': actors['seg_id'],
                           'uses_so_far': 1.0, 'fga_so_far': (actors['end_type'] == 'shot').astype(float),
                           'made_so_far': ((actors['end_type'] == 'shot') & (actors['made'] == 1)).astype(float),
                           'pts_so_far': actors['points'].astype(float)})
        fouls = s[s['fouler'].notna()]
        ev_f = pd.DataFrame({'game_id': fouls['game_id'], 'player': fouls['fouler'], 'seg_id': fouls['seg_id'], 'pf_so_far': 1.0})
        asts = s[s['assister'].notna()]
        ev_a = pd.DataFrame({'game_id': asts['game_id'], 'player': asts['assister'], 'seg_id': asts['seg_id'], 'ast_so_far': 1.0})
        sec = on.rename(columns={'duration': 'sec_so_far'})
        for table in (self.off, self.dfn):
            table[['uses_so_far', 'fga_so_far', 'made_so_far', 'pts_so_far']] = _cumulative_before(
                table, ev, ['uses_so_far', 'fga_so_far', 'made_so_far', 'pts_so_far']).to_numpy()
            table['pf_so_far'] = _cumulative_before(table, ev_f, ['pf_so_far']).to_numpy()
            table['ast_so_far'] = _cumulative_before(table, ev_a, ['ast_so_far']).to_numpy()
            table['sec_so_far'] = _cumulative_before(table, sec, ['sec_so_far']).to_numpy()

    def _relative(self):
        for table, cols in ((self.off, ['usage', 'ast_rate', 'oreb_pct', 'shot_share']), (self.dfn, ['blk_rate', 'stl_rate', 'dreb_pct', 'pf_rate'])):
            g = table.groupby('seg_id')
            for c in cols:
                filled = table[c].fillna(table[c].median())
                total = filled.groupby(table['seg_id']).transform('sum')
                table[f'{c}_share'] = filled / total.where(total > 0)
                table[f'{c}_rank'] = filled.groupby(table['seg_id']).rank(ascending=False, method='first')
            del g

    def _lineups(self):
        o = self.off.assign(three=self.off['mix_corner3'] + self.off['mix_above3']).groupby('seg_id')
        d = self.dfn.groupby('seg_id')
        agg = pd.DataFrame({'off_usage_sum': o['usage'].sum(), 'off_usage_max': o['usage'].max(), 'off_ast_sum': o['ast_rate'].sum(),
                            'off_three_sum': o['three'].sum(), 'off_oreb_sum': o['oreb_pct'].sum(), 'off_bigs': o['is_big'].sum(),
                            'off_min_mean': o['min_avg'].mean(),
                            'def_blk_sum': d['blk_rate'].sum(), 'def_blk_max': d['blk_rate'].max(), 'def_stl_sum': d['stl_rate'].sum(),
                            'def_dreb_sum': d['dreb_pct'].sum(), 'def_pf_sum': d['pf_rate'].sum(), 'def_bigs': d['is_big'].sum(),
                            'def_min_mean': d['min_avg'].mean()})
        self.seg = self.seg.merge(agg, left_on='seg_id', right_index=True, how='left')

    # ------------------------------------------------------------------ datasets
    def _frame(self, rows, extra=()):
        cols = list(dict.fromkeys(CONTEXT + LINEUP + list(extra)))
        return rows[cols].astype(np.float32)

    def _actor(self, rows, prefix='actor'):
        """Profile and in-game columns of the segment's actor, prefixed."""
        a = self.off[['seg_id', 'player'] + PROFILE + IN_GAME + ['grp_code', 'usage_share', 'usage_rank', 'usage_mult_now']]
        m = rows[['seg_id', 'actor']].merge(a, left_on=['seg_id', 'actor'], right_on=['seg_id', 'player'], how='left')
        m = m.drop(columns=['seg_id', 'actor', 'player'])
        m.columns = [f'{prefix}_{c}' for c in m.columns]
        m.index = rows.index
        return m.astype(np.float32)

    def dataset(self, name: str) -> dict:
        s = self.seg
        if name == 'duration':
            rows = s[(s['start_clock'] > 24) & ~s['end_type'].isin(['end_period', 'unknown'])]
            y = np.digitize(rows['shot_time'].to_numpy(), DURATION_EDGES)
            return self._pack(name, 'multiclass', self._frame(rows), y, rows, classes=len(DURATION_EDGES) + 1,
                              profile=('start_code', None))
        if name == 'event':
            rows = s[s['end_type'].isin(['shot', 'fouled', 'turnover', 'foul', 'violation', 'jump_ball'])]
            y = np.select([rows['end_type'] == 'foul', rows['end_type'].isin(['violation', 'jump_ball'])], [1, 2], 0)
            return self._pack(name, 'multiclass', self._frame(rows, ['shot_time']), y, rows, classes=3, profile=('start_code', None))
        usage = s[s['actor'].notna() & s['end_type'].isin(['shot', 'fouled', 'turnover', 'foul']) & ~s['heave']]
        usage = usage[((usage['end_type'] != 'foul') | (usage['fta'] > 0)) & ((usage['end_type'] != 'shot') | usage['zone'].isin(ZONES))]
        if name == 'who':
            ctx = usage[['seg_id', 'actor', 'end_type', 'shot_time', 'date_et'] + CONTEXT + LINEUP].copy()
            ctx['foul_event'] = (ctx['end_type'] == 'foul').astype(np.float32)
            cand = self.off[self.off['seg_id'].isin(ctx['seg_id'])]
            cand = cand.merge(ctx, on='seg_id', how='inner')
            y = (cand['player'] == cand['actor']).astype(int).to_numpy()
            cols = PROFILE + IN_GAME + ['grp_code', 'usage_mult_now'] + [c for c in cand.columns if c.endswith('_share') or c.endswith('_rank')] \
                   + CONTEXT + LINEUP + ['shot_time', 'foul_event']
            return self._candidates(name, cand, cols, y, 'usage_share')
        if name == 'what':
            rows = usage[usage['end_type'] != 'foul']
            label = np.where(rows['end_type'] == 'shot', rows['zone'], np.where(rows['end_type'] == 'turnover', 'turnover',
                             np.where(rows['fta'] >= 3, 'fouled_3', 'fouled_2')))
            y = pd.Series(label).map({c: i for i, c in enumerate(WHAT)}).to_numpy()
            X = pd.concat([self._frame(rows, ['shot_time']), self._actor(rows)], axis=1)
            return self._pack(name, 'multiclass', X, y, rows, classes=len(WHAT), profile=('what', X))
        shots = s[(s['end_type'] == 'shot') & ~s['heave'] & s['zone'].isin(ZONES)]
        if name == 'shot_result':
            y = np.where(shots['made'] == 1, np.where(shots['and_one'], 2, 1), 0)
            X = pd.concat([self._frame(shots, ['shot_time', 'distance', 'lateral']), self._actor(shots),
                           shots[['zone']].assign(zone=shots['zone'].map({z: i for i, z in enumerate(ZONES)})).astype(np.float32)], axis=1)
            return self._pack(name, 'multiclass', X, y, shots, classes=3, profile=('shot_result', X))
        made = shots[shots['made'] == 1]
        if name == 'assisted':
            y = made['assister'].notna().astype(int).to_numpy()
            X = pd.concat([self._frame(made, ['shot_time', 'distance', 'lateral']), self._actor(made),
                           made[['zone']].assign(zone=made['zone'].map({z: i for i, z in enumerate(ZONES)})).astype(np.float32)], axis=1)
            return self._pack(name, 'binary', X, y, made, profile=('actor_assisted_share', X))
        if name == 'assister':
            rows = made[made['assister'].notna()]
            ctx = rows[['seg_id', 'actor', 'assister', 'shot_time', 'distance', 'zone', 'date_et'] + CONTEXT + LINEUP].copy()
            ctx['zone'] = ctx['zone'].map({z: i for i, z in enumerate(ZONES)})
            cand = self.off[self.off['seg_id'].isin(ctx['seg_id'])].merge(ctx, on='seg_id')
            cand = cand[cand['player'] != cand['actor']]
            y = (cand['player'] == cand['assister']).astype(int).to_numpy()
            cols = PROFILE + IN_GAME + ['grp_code', 'ast_rate_share', 'ast_rate_rank', 'usage_share', 'usage_rank'] + CONTEXT + LINEUP + ['shot_time', 'distance', 'zone']
            return self._candidates(name, cand, cols, y, 'ast_rate')
        missed = shots[shots['made'] == 0]
        if name == 'blocked':
            y = missed['blocker'].notna().astype(int).to_numpy()
            X = pd.concat([self._frame(missed, ['shot_time', 'distance', 'lateral']), self._actor(missed),
                           missed[['zone']].assign(zone=missed['zone'].map({z: i for i, z in enumerate(ZONES)})).astype(np.float32)], axis=1)
            return self._pack(name, 'binary', X, y, missed, profile=('zone_rate', X))
        if name == 'blocker':
            rows = missed[missed['blocker'].notna()]
            ctx = rows[['seg_id', 'blocker', 'distance', 'zone', 'date_et'] + CONTEXT + LINEUP].copy()
            ctx['zone'] = ctx['zone'].map({z: i for i, z in enumerate(ZONES)})
            cand = self.dfn[self.dfn['seg_id'].isin(ctx['seg_id'])].merge(ctx, on='seg_id')
            y = (cand['player'] == cand['blocker']).astype(int).to_numpy()
            cols = PROFILE + IN_GAME + ['grp_code', 'blk_rate_share', 'blk_rate_rank'] + CONTEXT + LINEUP + ['distance', 'zone']
            return self._candidates(name, cand, cols, y, 'blk_rate')
        if name == 'rebound':
            rows = s[s['rebound'].isin(REBOUND)]
            y = rows['rebound'].map({c: i for i, c in enumerate(REBOUND)}).to_numpy()
            extra = rows[['zone', 'value', 'fta']].assign(zone=rows['zone'].map({z: i for i, z in enumerate(ZONES)}),
                                                          ft_miss=(rows['end_type'] != 'shot').astype(float),
                                                          blocked=rows['blocker'].notna().astype(float)).astype(np.float32)
            X = pd.concat([self._frame(rows, ['shot_time', 'distance', 'lateral']), extra], axis=1)
            return self._pack(name, 'multiclass', X, y, rows, classes=4, profile=('rebound', X))
        if name == 'rebounder':
            rows = s[s['rebound'].isin(['off', 'def']) & s['rebounder'].notna()]
            ctx = rows[['seg_id', 'rebound', 'rebounder', 'actor', 'distance', 'zone', 'date_et'] + CONTEXT + LINEUP].copy()
            ctx['zone'] = ctx['zone'].map({z: i for i, z in enumerate(ZONES)})
            off_c = self.off[self.off['seg_id'].isin(ctx.loc[ctx['rebound'] == 'off', 'seg_id'])].merge(ctx, on='seg_id')
            def_c = self.dfn[self.dfn['seg_id'].isin(ctx.loc[ctx['rebound'] == 'def', 'seg_id'])].merge(ctx, on='seg_id')
            off_c['reb_side_pct'], def_c['reb_side_pct'] = off_c['oreb_pct'], def_c['dreb_pct']
            off_c['offensive'], def_c['offensive'] = 1.0, 0.0
            for c in ('oreb_pct_share', 'oreb_pct_rank'):
                off_c[c.replace('oreb_pct', 'reb')] = off_c[c]
            for c in ('dreb_pct_share', 'dreb_pct_rank'):
                def_c[c.replace('dreb_pct', 'reb')] = def_c[c]
            cand = pd.concat([off_c, def_c], ignore_index=True)
            cand['is_shooter'] = (cand['player'] == cand['actor']).astype(float)
            y = (cand['player'] == cand['rebounder']).astype(int).to_numpy()
            cols = PROFILE + IN_GAME + ['grp_code', 'reb_side_pct', 'reb_share', 'reb_rank', 'offensive', 'is_shooter'] + CONTEXT + LINEUP + ['distance', 'zone']
            return self._candidates(name, cand, cols, y, 'reb_side_pct')
        tov = s[(s['end_type'] == 'turnover') & s['actor'].notna()]
        if name == 'turnover_type':
            y = np.select([tov['turnover'] == 'live', tov['fouler'] == tov['actor']], [0, 1], 2)
            X = pd.concat([self._frame(tov, ['shot_time']), self._actor(tov)], axis=1)
            return self._pack(name, 'multiclass', X, y, tov, classes=3, profile=('turnover_type', X))
        if name == 'stealer':
            rows = tov[(tov['turnover'] == 'live') & tov['stealer'].notna()]
            ctx = rows[['seg_id', 'stealer', 'shot_time', 'date_et'] + CONTEXT + LINEUP]
            cand = self.dfn[self.dfn['seg_id'].isin(ctx['seg_id'])].merge(ctx, on='seg_id')
            y = (cand['player'] == cand['stealer']).astype(int).to_numpy()
            cols = PROFILE + IN_GAME + ['grp_code', 'stl_rate_share', 'stl_rate_rank'] + CONTEXT + LINEUP + ['shot_time']
            return self._candidates(name, cand, cols, y, 'stl_rate')
        if name == 'fouler':
            rows = s[s['fouler'].notna() & (s['end_type'].isin(['fouled', 'foul']) | (s['and_one'] == True))]
            ctx = rows[['seg_id', 'fouler', 'end_type', 'shot_time', 'date_et'] + CONTEXT + LINEUP].copy()
            ctx['shooting'] = (ctx['end_type'] != 'foul').astype(float)
            cand = self.dfn[self.dfn['seg_id'].isin(ctx['seg_id'])].merge(ctx, on='seg_id')
            y = (cand['player'] == cand['fouler']).astype(int).to_numpy()
            cols = PROFILE + IN_GAME + ['grp_code', 'pf_rate_share', 'pf_rate_rank'] + CONTEXT + LINEUP + ['shot_time', 'shooting']
            return self._candidates(name, cand, cols, y, 'pf_rate')
        if name == 'free_throw':
            rows = s[(s['fta'] > 0) & s['actor'].notna() & (s['ft_seq'].str.len() == s['fta'])]
            reps = rows.loc[rows.index.repeat(rows['fta'].astype(int))].copy()
            reps['attempt'] = reps.groupby(level=0).cumcount()
            # Labels from the recorded sequence: attempt order is real (an earlier version assigned makes to the first
            # attempts of each trip, which leaked the label through `attempt`; see FINDINGS §3g).
            y = np.array([int(seq[k]) for seq, k in zip(reps['ft_seq'], reps['attempt'])], dtype=int)
            X = pd.concat([self._frame(reps), self._actor(reps)], axis=1)
            X['and_one'] = reps['and_one'].astype(np.float32).to_numpy()
            X['attempt'] = reps['attempt'].astype(np.float32).to_numpy()              # first, second or third of the trip
            X['trip'] = reps['fta'].astype(np.float32).to_numpy()
            X['last_of_trip'] = (reps['attempt'] == reps['fta'] - 1).astype(np.float32).to_numpy()
            return self._pack(name, 'binary', X, y, reps, profile=('actor_ft_pct', X))
        raise KeyError(name)

    def _pack(self, name, kind, X, y, rows, classes=None, profile=None):
        return {'name': name, 'kind': kind, 'X': X.reset_index(drop=True), 'y': np.asarray(y, dtype=int),
                'date': rows['date_et'].to_numpy(), 'classes': classes, 'profile': profile,
                'zone': rows['zone'].to_numpy() if 'zone' in rows else None, 'start_code': rows['start_code'].to_numpy()}

    def _candidates(self, name, cand, cols, y, profile_col):
        groups = cand['seg_id'].to_numpy()
        chosen = pd.Series(y).groupby(groups).transform('sum').to_numpy()
        keep = chosen == 1  # exactly one chosen candidate per segment (lineup glitches dropped)
        cand, y, groups = cand[keep], y[keep], groups[keep]
        X = cand[list(dict.fromkeys(cols))].astype(np.float32).reset_index(drop=True)
        return {'name': name, 'kind': 'candidate', 'X': X, 'y': y, 'group': groups, 'date': cand['date_et'].to_numpy(),
                'profile_score': cand[profile_col].fillna(cand[profile_col].median()).to_numpy(dtype=float)}
