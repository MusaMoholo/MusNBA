"""Causal possession feature view; accepts current state, never full-game targets.

Separate from legacy features so the unchanged control/conversion path remains
identical. The same named features train and serve each C02 probability head.
"""
from __future__ import annotations
import numpy as np
from scripts import nodes
from scripts.features import known_group
from analysis.c01_core import ContractError
from analysis.c02_data import COLS

PREFIX='c02__'

class View:
    def __init__(self,g,profiles,teams):
        p=profiles[profiles.game_id.eq(str(g.game['game_id']))].set_index('player')
        if not p.index.is_unique:raise ContractError('duplicate causal player profile')
        if set(g.ids)-set(p.index):raise ContractError('missing causal player profile')
        p=p.reindex(g.ids)
        if p.date_et.ne(g.day).any():raise ContractError('causal profile origin differs')
        self.P={c:p[c].to_numpy(np.float32) for c in nodes.PROFILE}
        group=p.pos.map(known_group)
        self.P['grp_code']=group.map({'G':0,'F':1,'C':2}).to_numpy(np.float32)
        self.P['is_big']=np.where(group.notna(),group.eq('C').astype(float),np.nan).astype(np.float32)
        t=teams[teams.game_id.eq(str(g.game['game_id']))].set_index('team')
        if not t.index.is_unique:raise ContractError('duplicate causal team profile')
        self.style={};self.rest={}
        for i,label in enumerate(('home','away')):
            row=t.loc[g.game[f'{label}_id']]
            if row.date_et!=g.day:raise ContractError('causal team profile origin differs')
            self.style[i]={k:float(row[k]) for k in t.columns if k.startswith(('off_','def_'))}
            self.rest[i]=float(row.rest_days)
        self.season_day=float(t.season_day.min())

    def context(self,g,st,A,lo,ld):
        off=st.off[A];dfn=1-off;period=st.period[A];clock=st.clock[A]
        margin=st.score[A,off]-st.score[A,dfn]
        left=np.where(period<=4,(4-period)*720+clock,clock)
        c={'period':period,'start_clock':clock,'sec_left_game':left,'margin':margin,
           'fouls_def':st.tfouls[A,dfn],'fouls_off':st.tfouls[A,off],'off_home':off==0,
           'season_type':np.full(len(A),2),'start_code':st.start[A],
           'off_rest':np.where(off==0,self.rest[0],self.rest[1]),'def_rest':np.where(dfn==0,self.rest[0],self.rest[1]),
           'season_day':np.full(len(A),self.season_day),'clutch':(period>=4)&(left<=300)&(np.abs(margin)<=5)}
        for k in ('pace','three','rim','tov','foul','oreb'):
            c[f'team_o_{k}']=np.where(off==0,self.style[0][f'off_{k}'],self.style[1][f'off_{k}'])
            c[f'team_d_{k}']=np.where(dfn==0,self.style[0][f'def_{k}'],self.style[1][f'def_{k}'])
        p=self.P;o=lambda k:p[k][lo];d=lambda k:p[k][ld]
        c.update(off_usage_sum=np.nansum(o('usage'),1),off_usage_max=np.nanmax(o('usage'),1),off_ast_sum=np.nansum(o('ast_rate'),1),
            off_three_sum=np.nansum(o('mix_corner3')+o('mix_above3'),1),off_oreb_sum=np.nansum(o('oreb_pct'),1),
            off_bigs=np.sum(o('is_big'),1),off_min_mean=np.nanmean(o('min_avg'),1),
            def_blk_sum=np.nansum(d('blk_rate'),1),def_blk_max=np.nanmax(d('blk_rate'),1),def_stl_sum=np.nansum(d('stl_rate'),1),
            def_dreb_sum=np.nansum(d('dreb_pct'),1),def_pf_sum=np.nansum(d('pf_rate'),1),def_bigs=np.sum(d('is_big'),1),def_min_mean=np.nanmean(d('min_avg'),1))
        return {k:np.asarray(v,np.float32) for k,v in c.items()}

    def five(self,st,A,lineup,relative=('usage','ast_rate','oreb_pct','shot_share')):
        c={k:v[lineup] for k,v in self.P.items() if k!='is_big'}
        for k in nodes.IN_GAME:c[k]=np.take_along_axis(st.ingame[k][A],lineup,1)
        q=np.clip(st.period[A],1,4)
        c['usage_mult_now']=np.choose(q[:,None]-1,[self.P[f'usage_mult_q{k}'][lineup] for k in (1,2,3,4)])
        for k in relative:
            share,rank=nodes.relative_lineup(c[k]);c[k+'_share']=share.astype(np.float32);c[k+'_rank']=rank.astype(np.float32)
        return c

    @staticmethod
    def actor(five,slot):
        keys=nodes.PROFILE+nodes.IN_GAME+['grp_code','usage_share','usage_rank','usage_mult_now']
        return {'actor_'+k:five[k][np.arange(len(slot)),slot] for k in keys}


def selected(name,cols):
    """Whitelist is the full inference interface; no metadata or targets enter."""
    missing=set(COLS[name])-set(cols)
    if missing:raise ContractError('missing causal runtime features: '+','.join(sorted(missing)))
    return {k:cols[k] for k in COLS[name]}
