#!/usr/bin/env python3
"""Training data for the decision chain (ENGINE_PLAN D20; TRAINING_PLAN §1–§2).

Builds, from M2 segments and M4 point-in-time profiles, one dataset per decision:

  stage 1  duration (time to the event, 2-second bins) · event (action / defensive foul / violation / team turnover)
  stage 2  who (of five) · what (5 zones, turnover, fouled on a 2 or a 3) · location (distance band within the zone)
           · shot result (miss/make/and-one)
  stage 3  assisted · assister (of four) · blocked · blocker (of five) · turnover type · stealer · fouler
  stage 4  free throw · rebound (offence/defence × player/team) · rebounder (of five)

Player choices are candidate rows (one per player on the floor) grouped by segment. Every row carries the
game situation, both lineups' aggregates, and in-game counts so far (minutes, uses, makes, fouls).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, NBA_TEAM_IDS  # noqa: E402

ZONES = ['rim', 'paint', 'mid', 'corner3', 'above3']
START_TYPES = ['period_start', 'made_fg', 'made_ft', 'dreb', 'steal', 'dead_turnover', 'oreb', 'foul', 'jump_ball', 'other']
EVENT = ['action', 'def_foul', 'violation', 'team_turnover']  # team turnovers (shot clock, 8 s) credit no player
WHAT = ZONES + ['turnover', 'fouled_2', 'fouled_3']
RESULT = ['miss', 'make', 'and_one']
REBOUND = ['off', 'team_off', 'def', 'team_def']
TOV_TYPE = ['live', 'offensive_foul', 'dead_other']
# Shot location (node 16): distance bands within each zone, feet from the basket (FINDINGS §3h). The engine samples a
# band after "what"; later nodes see the band's mean distance and lateral offset.
LOCATION_EDGES = {'rim': [1, 2, 3], 'paint': [5, 7, 10, 14], 'mid': [12, 16, 19], 'corner3': [23.5, 24.5], 'above3': [25.5, 26.5, 28, 31]}
LOCATION_OFFSET = dict(zip(ZONES, np.cumsum([0] + [len(LOCATION_EDGES[z]) + 1 for z in ZONES[:-1]]).tolist()))
LOCATION_BANDS = sum(len(e) + 1 for e in LOCATION_EDGES.values())  # 21
LOCATION_MASK = np.zeros((len(ZONES), LOCATION_BANDS), dtype=bool)  # zone → its bands
for _i, _z in enumerate(ZONES):
    LOCATION_MASK[_i, LOCATION_OFFSET[_z]:LOCATION_OFFSET[_z] + len(LOCATION_EDGES[_z]) + 1] = True


def location_band(zone, distance) -> np.ndarray:
    """Global band index (0–20) for each shot from its zone name and distance; -1 when either is missing."""
    zone, distance = np.asarray(zone, dtype=object), np.asarray(distance, dtype=float)
    out = np.full(len(zone), -1, dtype=int)
    for z in ZONES:
        m = (zone == z) & ~np.isnan(distance)
        out[m] = LOCATION_OFFSET[z] + np.digitize(distance[m], LOCATION_EDGES[z])
    return out


DURATION_EDGES = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24]  # 13 bins: <2, 2–4, …, 22–24, ≥24
PROFILE = ['games_eff', 'min_avg', 'start_share', 'off_segs_eff', 'usage', 'shot_share', 'tov_share', 'foul_drawn_share',
           'live_tov_share', 'assisted_share', 'ft_pct', 'fta_per_use', 'ast_rate', 'oreb_pct', 'dreb_pct', 'stl_rate',
           'blk_rate', 'pf_rate', 'shots_eff'] + [f'mix_{z}' for z in ZONES] + [f'fg_{z}' for z in ZONES] \
          + [f'usage_mult_q{q}' for q in (1, 2, 3, 4)] + [f'min_share_q{q}' for q in (1, 2, 3, 4)]
IN_GAME = ['sec_so_far', 'uses_so_far', 'fga_so_far', 'made_so_far', 'pts_so_far', 'pf_so_far', 'ast_so_far']
CONTEXT = ['period', 'start_clock', 'sec_left_game', 'margin', 'fouls_def', 'fouls_off', 'off_home', 'season_type', 'season',
           'start_code']
# Candidate inputs added in M5 tuning; each group must earn its place by ablation (train.py --drop @group).
TEAM_STYLE = [f'team_o_{c}' for c in ('pace', 'three', 'rim', 'tov', 'foul', 'oreb')] + \
             [f'team_d_{c}' for c in ('pace', 'three', 'rim', 'tov', 'foul', 'oreb')]  # style, never strength (D18)
SCHEDULE = ['off_rest', 'def_rest', 'season_day']
GROUPS = {'team': TEAM_STYLE, 'schedule': SCHEDULE, 'clutch': ['clutch'], 'heat': ['made_so_far', 'fga_so_far', 'pts_so_far']}
CONTEXT = CONTEXT + TEAM_STYLE + SCHEDULE + ['clutch']
LINEUP = ['off_usage_sum', 'off_usage_max', 'off_ast_sum', 'off_three_sum', 'off_oreb_sum', 'off_bigs', 'off_min_mean',
          'def_blk_sum', 'def_blk_max', 'def_stl_sum', 'def_dreb_sum', 'def_pf_sum', 'def_bigs', 'def_min_mean']
# Optional profile inputs (owner, 19 Nov: size and defence): used only when the features file carries them
# (features.py --body/--archetypes/--defence), so datasets built from features without them are unchanged.
BODY = ['height_in', 'weight_lb', 'arch_code']
DEFENCE = ['d_fg_rim', 'd_fg_paint', 'd_fg_mid', 'd_fg_three', 'd_tov_rate', 'd_rim_share', 'd_three_share', 'd_segs_eff']
# D30 (20 Nov): defence columns are defender-side only — lineup aggregates, help at the rim and the actor's
# assignment-weighted matchup (MU) — never the actor's own defence on offensive rows (noise in §3l). Shot-type shares
# from the play text (features.py --shot-types) are offensive style.
MATCHUP_PROFILE = ['m_fg_rim', 'm_fg_paint', 'm_fg_mid', 'm_fg_three', 'm_tov_rate', 'm_foul_rate', 'm_uses_eff']
DEF_SIDE = DEFENCE + MATCHUP_PROFILE
STYLE_COLS = [f'st_{k}' for k in ('self', 'drive', 'cut', 'putback', 'catch')]
OPTIONAL_PROFILE = BODY + STYLE_COLS
MU = ['mu_fg_rim', 'mu_fg_paint', 'mu_fg_mid', 'mu_fg_three', 'mu_tov', 'mu_foul', 'mu_height_gap']  # actor v his likely defenders
MU_SHOT = ['mu_fg_shot']  # the zone of the shot, once known
SHOT_TYPES = ['catch', 'pullup', 'stepback', 'iso', 'drive', 'cut', 'putback', 'other']  # ablation only (engine samples no type yet)
OPTIONAL_LINEUP = {  # column: (side, profile column, aggregate)
    'off_height_mean': ('off', 'height_in', 'mean'), 'off_weight_mean': ('off', 'weight_lb', 'mean'),
    'def_height_mean': ('def', 'height_in', 'mean'), 'def_weight_mean': ('def', 'weight_lb', 'mean'),
    'def_height_max': ('def', 'height_in', 'max'),
    'def_d_fg_rim_mean': ('def', 'd_fg_rim', 'mean'), 'def_d_fg_paint_mean': ('def', 'd_fg_paint', 'mean'),
    'def_d_fg_mid_mean': ('def', 'd_fg_mid', 'mean'), 'def_d_fg_three_mean': ('def', 'd_fg_three', 'mean'),
    'def_d_tov_sum': ('def', 'd_tov_rate', 'sum'), 'def_d_rim_mean': ('def', 'd_rim_share', 'mean'),
    'def_d_three_mean': ('def', 'd_three_share', 'mean'),
    'def_d_fg_rim_min': ('def', 'd_fg_rim', 'min'),  # help: the best rim protector on the floor
    'def_m_fg_rim_mean': ('def', 'm_fg_rim', 'mean'), 'def_m_fg_paint_mean': ('def', 'm_fg_paint', 'mean'),
    'def_m_fg_mid_mean': ('def', 'm_fg_mid', 'mean'), 'def_m_fg_three_mean': ('def', 'm_fg_three', 'mean'),
    'def_m_tov_mean': ('def', 'm_tov_rate', 'mean'), 'def_m_foul_mean': ('def', 'm_foul_rate', 'mean'),
}
GROUPS['body'] = BODY + [c for c, (_, src, _) in OPTIONAL_LINEUP.items() if src in BODY]
GROUPS['defence'] = DEF_SIDE + [c for c, (_, src, _) in OPTIONAL_LINEUP.items() if src in DEF_SIDE] + MU + MU_SHOT
GROUPS['style'] = STYLE_COLS
GROUPS['stype'] = ['stype_code']


def group(pos) -> str:
    p = str(pos or '').upper()
    return 'C' if p.startswith('C') else 'G' if p.startswith('G') or p in ('PG', 'SG') else 'F'


def segment_files(include_current: bool = False, segments: Path | None = None) -> list:
    """History (and optionally current-season) segment files under a root: data/derived, or a variant written by
    `possessions.py --out` (e.g. the 2026-27 rebound convention, FINDINGS §3k)."""
    root = Path(segments or DERIVED)
    paths = sorted((root / 'history').glob('*/segments.parquet'))
    if include_current and (root / 'segments.parquet').exists():
        paths.append(root / 'segments.parquet')
    return paths


def load_segments(include_current: bool = False, segments: Path | None = None) -> pd.DataFrame:
    paths = segment_files(include_current, segments)
    seg = pd.concat([pd.read_parquet(p) for p in paths], ignore_index=True)
    seg = seg[seg['game_ok'] & seg['offense'].astype(str).isin(NBA_TEAM_IDS) & seg['defense'].astype(str).isin(NBA_TEAM_IDS)].reset_index(drop=True)  # reconciled NBA games, in game order
    seg['seg_id'] = np.arange(len(seg))
    seg['start_code'] = seg['start_type'].map({s: i for i, s in enumerate(START_TYPES)}).fillna(len(START_TYPES) - 1).astype(int)
    seg['margin'] = seg['score_off'] - seg['score_def']
    seg['sec_left_game'] = np.where(seg['period'] <= 4, (4 - seg['period']) * 720 + seg['start_clock'], seg['start_clock'])
    seg['off_home'] = seg['off_home'].astype(int)
    seg['shot_time'] = seg['shot_time'].clip(lower=0)
    seg['distance'] = np.sqrt((seg['x'] - 25) ** 2 + seg['y'] ** 2)
    seg['lateral'] = (seg['x'] - 25).abs()
    seg['made'] = seg['made'].astype(float)
    seg['clutch'] = ((seg['period'] >= 4) & (seg['sec_left_game'] <= 300) & (seg['margin'].abs() <= 5)).astype(np.int8)
    return seg


def attach_teams(seg: pd.DataFrame, teams: pd.DataFrame) -> pd.DataFrame:
    """Offence team's offensive style, defence team's defensive style, and both teams' rest (features.team_profiles)."""
    o = teams[['game_id', 'team', 'rest_days', 'season_day'] + [f'off_{c}' for c in ('pace', 'three', 'rim', 'tov', 'foul', 'oreb')]]
    o = o.rename(columns={'team': 'offense', 'rest_days': 'off_rest', **{f'off_{c}': f'team_o_{c}' for c in ('pace', 'three', 'rim', 'tov', 'foul', 'oreb')}})
    d = teams[['game_id', 'team', 'rest_days'] + [f'def_{c}' for c in ('pace', 'three', 'rim', 'tov', 'foul', 'oreb')]]
    d = d.rename(columns={'team': 'defense', 'rest_days': 'def_rest', **{f'def_{c}': f'team_d_{c}' for c in ('pace', 'three', 'rim', 'tov', 'foul', 'oreb')}})
    out = seg.merge(o, on=['game_id', 'offense'], how='left').merge(d, on=['game_id', 'defense'], how='left')
    assert len(out) == len(seg)
    return out


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

    def __init__(self, include_current: bool = False, pregame: Path | None = None, segments: Path | None = None):
        pregame = Path(pregame or DERIVED / 'features' / 'pregame.parquet')
        seg = attach_teams(load_segments(include_current, segments), pd.read_parquet(pregame.parent / 'team_pregame.parquet'))
        pre = pd.read_parquet(pregame)
        pre['grp'] = pre['pos'].map(group)
        present = [c for c in OPTIONAL_PROFILE if c in pre.columns]
        def_present = [c for c in DEF_SIDE if c in pre.columns]
        self.profile = PROFILE + present
        self.lineup = LINEUP + [c for c, (side, src, _) in OPTIONAL_LINEUP.items() if src in present or (side == 'def' and src in def_present)]
        report = pregame.parent / 'features_report.json'
        report = json.loads(report.read_text()) if report.exists() else {}
        self.seg = seg
        self.off = self._side(seg, pre, 'off', self.profile)
        self.dfn = self._side(seg, pre, 'def', self.profile + def_present)
        self.mu_cols, self.mu_shot = [], []
        if def_present and report.get('matchup'):
            self._matchup(json.loads((ROOT / report['matchup']).read_text()) if not Path(report['matchup']).is_absolute()
                          else json.loads(Path(report['matchup']).read_text()))
        self.stype = False
        if report.get('shot_types'):
            from scripts import matchups
            st = matchups.attach_shot_types(self.seg, matchups.shot_types(include_current=include_current))
            self.seg['stype_code'] = st.map({k: i for i, k in enumerate(SHOT_TYPES)}).astype(np.float32)
            self.stype = True
        self._in_game()
        self._relative()
        self._lineups()
        for table in (self.off, self.dfn):  # halves memory; models train on float32 anyway
            wide = table.select_dtypes('float64').columns
            table[wide] = table[wide].astype(np.float32)

    def _matchup(self, theta: dict):
        """Per segment with an actor: his likely defenders' quality, weighted by the soft assignment (scripts/matchups.py)."""
        from scripts import matchups
        rows = self.seg[self.seg['actor'].notna()][['seg_id', 'actor']]
        body = pd.read_parquet(DERIVED / 'athletes.parquet', columns=['player', 'height_in', 'weight_lb'])
        body['player'] = body['player'].astype(str)
        cols = matchups.MU_SOURCES
        dfn = self.dfn[['seg_id', 'player', 'grp_code', 'min_avg'] + [c for c in cols if c in self.dfn.columns]].merge(body, on='player', how='left')
        dfn = dfn[dfn['seg_id'].isin(rows['seg_id'])]
        dfn['slot'] = dfn.groupby('seg_id').cumcount()
        dfn = dfn[dfn['slot'] < 5]
        full = dfn.groupby('seg_id')['slot'].transform('size') == 5
        dfn = dfn[full]
        segs = np.sort(dfn['seg_id'].unique())
        D = {c: dfn.pivot(index='seg_id', columns='slot', values=c).reindex(segs).to_numpy(float)
             for c in ['grp_code', 'min_avg', 'height_in', 'weight_lb'] + [c for c in cols if c in dfn.columns]}
        act = rows.set_index('seg_id').loc[segs, 'actor'].astype(str).to_numpy()
        o = self.off[['seg_id', 'player', 'grp_code', 'min_avg']].merge(body, on='player', how='left')
        o = o.set_index(['seg_id', 'player']).reindex(pd.MultiIndex.from_arrays([segs, act]))
        A = {c: o[c].to_numpy(float) for c in ['grp_code', 'min_avg', 'height_in', 'weight_lb']}
        mu = matchups.mu_columns(theta, A, D)
        frame = pd.DataFrame({k: v.astype(np.float32) for k, v in mu.items()}, index=segs)
        self.seg = self.seg.merge(frame, left_on='seg_id', right_index=True, how='left')
        self.mu_cols = list(mu)
        zone = self.seg['zone'].replace({'corner3': 'three', 'above3': 'three'})
        shot = np.full(len(self.seg), np.nan, dtype=np.float32)
        for z in ('rim', 'paint', 'mid', 'three'):
            if f'mu_fg_{z}' in self.seg:
                sel = (zone == z).to_numpy()
                shot[sel] = self.seg.loc[sel, f'mu_fg_{z}'].to_numpy()
        self.seg['mu_fg_shot'] = shot
        self.mu_shot = ['mu_fg_shot']

    @staticmethod
    def _side(seg, pre, side, profile=PROFILE):
        cols = [f'{side}_{i}' for i in range(1, 6)]
        long = seg[['seg_id', 'game_id', 'period'] + cols].melt(id_vars=['seg_id', 'game_id', 'period'], value_vars=cols,
                                                               value_name='player').dropna(subset=['player'])
        long = long.drop(columns='variable').merge(pre[['game_id', 'player', 'grp'] + profile], on=['game_id', 'player'], how='left')
        long[profile] = long[profile].astype(np.float32)
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
        for col, (side, src, how) in OPTIONAL_LINEUP.items():
            if col in self.lineup:
                agg[col] = (o if side == 'off' else d)[src].agg(how)
        self.seg = self.seg.merge(agg, left_on='seg_id', right_index=True, how='left')

    # ------------------------------------------------------------------ datasets
    def _frame(self, rows, extra=()):
        cols = list(dict.fromkeys(CONTEXT + self.lineup + list(extra)))
        return rows[cols].astype(np.float32)

    def _actor(self, rows, prefix='actor'):
        """Profile and in-game columns of the segment's actor, prefixed."""
        a = self.off[['seg_id', 'player'] + self.profile + IN_GAME + ['grp_code', 'usage_share', 'usage_rank', 'usage_mult_now']]
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
            team_tov = (rows['end_type'] == 'turnover') & rows['actor'].isna()
            y = np.select([rows['end_type'] == 'foul', rows['end_type'].isin(['violation', 'jump_ball']), team_tov], [1, 2, 3], 0)
            return self._pack(name, 'multiclass', self._frame(rows, ['shot_time']), y, rows, classes=len(EVENT), profile=('start_code', None))
        usage = s[s['actor'].notna() & s['end_type'].isin(['shot', 'fouled', 'turnover', 'foul']) & ~s['heave']]
        usage = usage[((usage['end_type'] != 'foul') | (usage['fta'] > 0)) & ((usage['end_type'] != 'shot') | usage['zone'].isin(ZONES))]
        if name == 'who':
            ctx = usage[['seg_id', 'actor', 'end_type', 'shot_time', 'date_et'] + CONTEXT + self.lineup].copy()
            ctx['foul_event'] = (ctx['end_type'] == 'foul').astype(np.float32)
            cand = self.off[self.off['seg_id'].isin(ctx['seg_id'])]
            cand = cand.merge(ctx, on='seg_id', how='inner')
            y = (cand['player'] == cand['actor']).astype(int).to_numpy()
            cols = self.profile + IN_GAME + ['grp_code', 'usage_mult_now'] + [c for c in cand.columns if c.endswith('_share') or c.endswith('_rank')] \
                   + CONTEXT + self.lineup + ['shot_time', 'foul_event']
            return self._candidates(name, cand, cols, y, 'usage_share')
        if name == 'what':
            rows = usage[usage['end_type'] != 'foul']
            label = np.where(rows['end_type'] == 'shot', rows['zone'], np.where(rows['end_type'] == 'turnover', 'turnover',
                             np.where(rows['fta'] >= 3, 'fouled_3', 'fouled_2')))
            y = pd.Series(label).map({c: i for i, c in enumerate(WHAT)}).to_numpy()
            X = pd.concat([self._frame(rows, ['shot_time'] + self.mu_cols), self._actor(rows)], axis=1)
            return self._pack(name, 'multiclass', X, y, rows, classes=len(WHAT), profile=('what', X))
        shots = s[(s['end_type'] == 'shot') & ~s['heave'] & s['zone'].isin(ZONES)]
        if name == 'shot_result':
            y = np.where(shots['made'] == 1, np.where(shots['and_one'], 2, 1), 0)
            X = pd.concat([self._frame(shots, ['shot_time', 'distance', 'lateral'] + self.mu_cols + self.mu_shot + (['stype_code'] if self.stype else [])),
                           self._actor(shots),
                           shots[['zone']].assign(zone=shots['zone'].map({z: i for i, z in enumerate(ZONES)})).astype(np.float32)], axis=1)
            return self._pack(name, 'multiclass', X, y, shots, classes=3, profile=('shot_result', X))
        if name == 'location':
            rows = shots[shots['distance'].notna()]
            y = location_band(rows['zone'].to_numpy(), rows['distance'].to_numpy())
            zone = rows['zone'].map({z: i for i, z in enumerate(ZONES)})
            X = pd.concat([self._frame(rows, ['shot_time'] + self.mu_cols + self.mu_shot), self._actor(rows), zone.rename('zone').astype(np.float32).to_frame()], axis=1)
            d = self._pack(name, 'multiclass', X, y, rows, classes=LOCATION_BANDS, profile=('location', None))
            d['class_mask'] = LOCATION_MASK[zone.to_numpy()]  # the model chooses only among the zone's bands
            return d
        made = shots[shots['made'] == 1]
        if name == 'assisted':
            y = made['assister'].notna().astype(int).to_numpy()
            X = pd.concat([self._frame(made, ['shot_time', 'distance', 'lateral'] + self.mu_cols + self.mu_shot + (['stype_code'] if self.stype else [])),
                           self._actor(made),
                           made[['zone']].assign(zone=made['zone'].map({z: i for i, z in enumerate(ZONES)})).astype(np.float32)], axis=1)
            return self._pack(name, 'binary', X, y, made, profile=('actor_assisted_share', X))
        if name == 'assister':
            rows = made[made['assister'].notna()]
            ctx = rows[['seg_id', 'actor', 'assister', 'shot_time', 'distance', 'zone', 'date_et'] + CONTEXT + self.lineup].copy()
            ctx['zone'] = ctx['zone'].map({z: i for i, z in enumerate(ZONES)})
            cand = self.off[self.off['seg_id'].isin(ctx['seg_id'])].merge(ctx, on='seg_id')
            cand = cand[cand['player'] != cand['actor']]
            y = (cand['player'] == cand['assister']).astype(int).to_numpy()
            cols = self.profile + IN_GAME + ['grp_code', 'ast_rate_share', 'ast_rate_rank', 'usage_share', 'usage_rank'] + CONTEXT + self.lineup + ['shot_time', 'distance', 'zone']
            return self._candidates(name, cand, cols, y, 'ast_rate')
        missed = shots[shots['made'] == 0]
        if name == 'blocked':
            y = missed['blocker'].notna().astype(int).to_numpy()
            X = pd.concat([self._frame(missed, ['shot_time', 'distance', 'lateral'] + self.mu_cols + self.mu_shot + (['stype_code'] if self.stype else [])),
                           self._actor(missed),
                           missed[['zone']].assign(zone=missed['zone'].map({z: i for i, z in enumerate(ZONES)})).astype(np.float32)], axis=1)
            return self._pack(name, 'binary', X, y, missed, profile=('zone_rate', X))
        if name == 'blocker':
            rows = missed[missed['blocker'].notna()]
            ctx = rows[['seg_id', 'blocker', 'distance', 'zone', 'date_et'] + CONTEXT + self.lineup].copy()
            ctx['zone'] = ctx['zone'].map({z: i for i, z in enumerate(ZONES)})
            cand = self.dfn[self.dfn['seg_id'].isin(ctx['seg_id'])].merge(ctx, on='seg_id')
            y = (cand['player'] == cand['blocker']).astype(int).to_numpy()
            cols = self.profile + IN_GAME + ['grp_code', 'blk_rate_share', 'blk_rate_rank'] + CONTEXT + self.lineup + ['distance', 'zone']
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
            ctx = rows[['seg_id', 'rebound', 'rebounder', 'actor', 'distance', 'zone', 'date_et'] + CONTEXT + self.lineup].copy()
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
            cols = self.profile + IN_GAME + ['grp_code', 'reb_side_pct', 'reb_share', 'reb_rank', 'offensive', 'is_shooter'] + CONTEXT + self.lineup + ['distance', 'zone']
            return self._candidates(name, cand, cols, y, 'reb_side_pct')
        tov = s[(s['end_type'] == 'turnover') & s['actor'].notna()]
        if name == 'turnover_type':
            y = np.select([tov['turnover'] == 'live', tov['fouler'] == tov['actor']], [0, 1], 2)
            X = pd.concat([self._frame(tov, ['shot_time'] + self.mu_cols), self._actor(tov)], axis=1)
            return self._pack(name, 'multiclass', X, y, tov, classes=3, profile=('turnover_type', X))
        if name == 'stealer':
            rows = tov[(tov['turnover'] == 'live') & tov['stealer'].notna()]
            ctx = rows[['seg_id', 'stealer', 'shot_time', 'date_et'] + CONTEXT + self.lineup]
            cand = self.dfn[self.dfn['seg_id'].isin(ctx['seg_id'])].merge(ctx, on='seg_id')
            y = (cand['player'] == cand['stealer']).astype(int).to_numpy()
            cols = self.profile + IN_GAME + ['grp_code', 'stl_rate_share', 'stl_rate_rank'] + CONTEXT + self.lineup + ['shot_time']
            return self._candidates(name, cand, cols, y, 'stl_rate')
        if name == 'fouler':
            rows = s[s['fouler'].notna() & (s['end_type'].isin(['fouled', 'foul']) | (s['and_one'] == True))]
            ctx = rows[['seg_id', 'fouler', 'end_type', 'shot_time', 'date_et'] + CONTEXT + self.lineup].copy()
            ctx['shooting'] = (ctx['end_type'] != 'foul').astype(float)
            cand = self.dfn[self.dfn['seg_id'].isin(ctx['seg_id'])].merge(ctx, on='seg_id')
            y = (cand['player'] == cand['fouler']).astype(int).to_numpy()
            cols = self.profile + IN_GAME + ['grp_code', 'pf_rate_share', 'pf_rate_rank'] + CONTEXT + self.lineup + ['shot_time', 'shooting']
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

    @staticmethod
    def _meta(rows):
        """Per-row identifiers for paired comparisons, sample weights and calibration breakdowns."""
        return {'date': rows['date_et'].to_numpy(), 'game': rows['game_id'].to_numpy(), 'season_type': rows['season_type'].to_numpy(),
                'period': rows['period'].to_numpy(), 'margin': rows['margin'].to_numpy()}

    def _pack(self, name, kind, X, y, rows, classes=None, profile=None):
        return {'name': name, 'kind': kind, 'X': X.reset_index(drop=True), 'y': np.asarray(y, dtype=int),
                'classes': classes, 'profile': profile, **self._meta(rows),
                'zone': rows['zone'].to_numpy() if 'zone' in rows else None, 'start_code': rows['start_code'].to_numpy()}

    def _candidates(self, name, cand, cols, y, profile_col):
        groups = cand['seg_id'].to_numpy()
        chosen = pd.Series(y).groupby(groups).transform('sum').to_numpy()
        keep = chosen == 1  # exactly one chosen candidate per segment (lineup glitches dropped)
        cand, y, groups = cand[keep], y[keep], groups[keep]
        X = cand[list(dict.fromkeys(cols))].astype(np.float32).reset_index(drop=True)
        return {'name': name, 'kind': 'candidate', 'X': X, 'y': y, 'group': groups, **self._meta(cand),
                'profile_score': cand[profile_col].fillna(cand[profile_col].median()).to_numpy(dtype=float)}


# ---------------------------------------------------------------------- dataset cache
# Building the chain takes ~50 s and ~14 GB; experiments that only change training (weights, ablations, model
# settings) reuse cached datasets. Each cache folder is named by a hash of this module's source and the input files
# (path, size, modification time), so a change to segments, profiles or feature code starts a new folder and never
# disturbs runs still reading an older one. Old folders stay until `nodes.py --prune`.
CACHE = DERIVED / 'nodes'
ARRAYS = ('y', 'date', 'game', 'season_type', 'period', 'margin', 'zone', 'start_code', 'group', 'profile_score', 'class_mask')


def signature(pregame: Path | None = None, segments: Path | None = None) -> dict:
    import hashlib
    pregame = Path(pregame or DERIVED / 'features' / 'pregame.parquet')
    files = segment_files(False, segments) + [pregame, pregame.parent / 'team_pregame.parquet']
    return {'code': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16],
            'inputs': {str(f): [f.stat().st_size, int(f.stat().st_mtime)] for f in files}}


def cache_dir(pregame: Path | None = None, segments: Path | None = None) -> Path:
    import hashlib
    import json
    key = hashlib.sha256(json.dumps(signature(pregame, segments), sort_keys=True).encode()).hexdigest()[:12]
    return CACHE / f"{'default' if pregame is None and segments is None else 'variant'}_{key}"


def _save(d: dict, path: Path):
    arrays = {k: d[k] for k in ARRAYS if d.get(k) is not None}
    for k in ('date', 'game', 'zone'):
        if k in arrays:
            arrays[k] = arrays[k].astype(str)
    np.savez(path, X=d['X'].to_numpy(np.float32), columns=np.array([str(c) for c in d['X'].columns], dtype=str), kind=d['kind'],
             classes=d.get('classes') or 0, profile=(d['profile'][0] if d.get('profile') else ''), **arrays)


def _load(path: Path, name: str) -> dict:
    z = np.load(path, allow_pickle=False)
    d = {'name': name, 'kind': str(z['kind']), 'classes': int(z['classes']) or None,
         'X': pd.DataFrame(z['X'], columns=[str(c) for c in z['columns']])}
    d['profile'] = (str(z['profile']), None) if str(z['profile']) else None
    for k in ARRAYS:
        d[k] = z[k] if k in z.files else None
    if d['zone'] is not None:
        d['zone'] = np.where(d['zone'] == 'None', None, d['zone']).astype(object)
    return d


def datasets(names, pregame: Path | None = None, include_current: bool = False, segments: Path | None = None):
    """Yield the named datasets: from this signature's cache folder when present, else built (and cached)."""
    import json
    import os
    folder = None if include_current else cache_dir(pregame, segments)
    if folder is not None:
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'signature.json').write_text(json.dumps(signature(pregame, segments), sort_keys=True))
    chain = None
    for name in names:
        path = folder / f'{name}.npz' if folder is not None else None
        if path is not None and path.exists():
            yield _load(path, name)
            continue
        if chain is None:
            chain = Chain(include_current=include_current, pregame=pregame, segments=segments)
        d = chain.dataset(name)
        if path is not None:
            tmp = path.with_name(f'{name}.tmp{os.getpid()}.npz')
            _save(d, tmp)
            os.replace(tmp, path)
        yield d


def main():
    import argparse
    import time
    ap = argparse.ArgumentParser(description='Build (or refresh) the cached datasets for every decision.')
    ap.add_argument('--features', type=Path, default=None, help='a pregame.parquet variant (scripts/features.py --out)')
    ap.add_argument('--segments', type=Path, default=None, help='segments root variant (scripts/possessions.py --out)')
    ap.add_argument('--prune', action='store_true', help='delete every cache folder except the current default one')
    args = ap.parse_args()
    if args.prune:
        import shutil
        keep = cache_dir(None)
        for folder in CACHE.glob('*/'):
            if folder != keep:
                shutil.rmtree(folder)
                print(f'removed {folder}')
        return
    names = ['duration', 'event', 'who', 'what', 'location', 'shot_result', 'assisted', 'assister', 'blocked', 'blocker', 'rebound',
             'rebounder', 'turnover_type', 'stealer', 'fouler', 'free_throw']
    start = time.time()
    for d in datasets(names, pregame=args.features, segments=args.segments):
        print(f"{d['name']:14} {len(d['y']):>9,} rows  {d['X'].shape[1]:>3} columns  {time.time() - start:6.0f}s", flush=True)
    print(f'cache: {cache_dir(args.features, args.segments)}')


if __name__ == '__main__':
    main()
