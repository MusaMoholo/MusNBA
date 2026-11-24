"""Strictly prior derived-court profiles; isolated research, never serving work.

Each day is read before its outcomes are added. Defence means on-court exposure,
not an observed or inferred primary defender. Unknown coordinates retain a bin.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from scripts import court_zones as zones

PARENT = np.array([0] + [1]*4 + [2]*8 + [3]*2 + [4]*5 + [2,4])
K = np.array([30,40,50,80,150],float)
COLS = ([f'court_mix_{i}' for i in range(22)] + [f'court_fg_{i}' for i in range(22)] +
        [f'court_d_mix_{i}' for i in range(22)] + [f'court_d_fg_{i}' for i in range(22)] +
        ['court_uses_eff','court_shots_eff','court_d_uses_eff','court_d_shots_eff'] +
        [f'court_rate_{i}' for i in range(22)] + [f'court_d_rate_{i}' for i in range(22)])


def pool(freq, conv, league, defence=False):
    """Return normalized shot mix and conversion with explicit parent support."""
    attempts, makes = conv[:22], conv[22:]
    la, lm = league[:22], league[22:]
    lp_a = np.bincount(PARENT, weights=la, minlength=5)
    lp_m = np.bincount(PARENT, weights=lm, minlength=5)
    # Uniform initial cell mass; only past outcomes move this cold-start prior.
    league_mix = (la+1)/(la.sum()+22)
    league_fg = (lp_m+1)/(lp_a+2)
    parent_a = np.bincount(PARENT,weights=attempts,minlength=5)
    parent_m = np.bincount(PARENT,weights=makes,minlength=5)
    strength = np.full(5,60.) if defence else K
    parent_fg = (parent_m+strength*league_fg)/(parent_a+strength)
    fg = (makes+strength[PARENT]*parent_fg[PARENT])/(attempts+strength[PARENT])
    f = freq[1:]
    parent_f = np.bincount(PARENT,weights=f,minlength=5)
    league_pm = np.bincount(PARENT,weights=league_mix,minlength=5)
    mix_k = 60. if defence else 50.
    parent_mix = (parent_f+mix_k*league_pm)/(f.sum()+mix_k)
    conditional = (f+mix_k*league_mix/league_pm[PARENT])/(parent_f[PARENT]+mix_k)
    mix = parent_mix[PARENT]*conditional
    return mix,fg


def covered_events(seg):
    """Retain exact source indices; compute explicit legal exposure eligibility."""
    ons=[f'{side}_{i}' for side in ['off','def'] for i in range(1,6)]
    s=seg.copy()
    s['court_cell']=zones.derive(s.x,s.y,s.value)
    players=s[ons].to_numpy(float)
    legal=np.isfinite(players).all(axis=1)
    legal &= np.all(np.diff(np.sort(players,axis=1),axis=1)!=0,axis=1)
    actor=s.actor.to_numpy(float)
    legal &= np.any(players[:,:5]==actor[:,None],axis=1)
    use=s.end_type.isin(['shot','fouled','turnover']).to_numpy() & ~s.heave.fillna(False).to_numpy(bool)
    legal &= s.game_ok.to_numpy(bool)
    s['court_use']=legal & use
    s['court_attempt']=s.court_use & s.end_type.eq('shot') & s.court_cell.ge(0)
    s['court_make']=s.court_attempt & s.made.eq(1)
    return s


def build(seg,roster,progress=None):
    """Emit one row per dated roster player, with no outcomes from that ET day."""
    s=covered_events(seg)
    # Numerators and denominators use the same covered-use population.
    use=s[s.court_use]
    events=[]
    for side in ['off','def']:
        slots=['actor'] if side=='off' else [f'def_{i}' for i in range(1,6)]
        for slot in slots:
            r=use[['game_id','date_et','season','court_cell','court_attempt','court_make',slot]].rename(columns={slot:'player'}).copy()
            r['side']=side
            events.append(r)
    e=pd.concat(events,ignore_index=True)
    # Per game/player additive sufficient statistics: uses, attempts22, makes22.
    keys=['date_et','season','game_id','player','side']
    e['cell']=np.where(e.court_attempt,e.court_cell,-1)
    counts=e.groupby(keys+['cell'],sort=False).agg(uses=('cell','size'),made=('court_make','sum')).reset_index()
    by_day={d:g for d,g in counts.groupby('date_et',sort=False)}
    roster=roster[['game_id','date_et','season','player']].drop_duplicates().sort_values(['date_et','game_id','player'])
    if roster.duplicated(['game_id','player']).any():raise ValueError('duplicate roster identity')
    states={};last_season={};league=np.zeros(44);league_uses=0.;out=[]
    groups=list(roster.groupby('date_et',sort=True))
    for n,(day,rows) in enumerate(groups):
        # Season carry occurs before reads, without adding current-day observations.
        for player,season in rows[['player','season']].drop_duplicates().itertuples(index=False,name=None):
            if player not in states:states[player]=[np.zeros(23),np.zeros(44),np.zeros(45)]
            if player in last_season and last_season[player]!=season:
                for st,carry in zip(states[player],[.6,.8,.6]):st*=carry
            last_season[player]=season
        for game,date,season,player in rows.itertuples(index=False,name=None):
            f,c,d=states[player]
            mix,fg=pool(f,c,league)
            dmix,dfg=pool(d[:23],d[1:],league,True)
            league_rate=league[:22].sum()/league_uses if league_uses else .5
            rate=(f[1:].sum()+200*league_rate)/(f[0]+200)
            drate=(d[1:23].sum()+60*league_rate)/(d[0]+60)
            out.append([game,date,season,player,*mix,*fg,*dmix,*dfg,f[0],c[:22].sum(),d[0],d[1:23].sum(),*(mix*rate),*(dmix*drate)])
        updates=by_day.get(day)
        if updates is not None:
            league_add=np.zeros(44)
            # All covered participants age once per game, even with zero actor uses.
            today=use[use.date_et.eq(day)]
            participants=pd.concat([today[['game_id',col]].rename(columns={col:'player'}) for col in [f'{side}_{i}' for side in ['off','def'] for i in range(1,6)]],ignore_index=True).drop_duplicates().sort_values(['game_id','player'])
            for game,player in participants.itertuples(index=False,name=None):
                if player not in states:raise ValueError('covered participant absent from source roster')
                for state,half in zip(states[player],[15,40,30]):state*=2**(-1/half)
            league_uses+=float(updates[updates.side.eq('off')].uses.sum())
            for (game,player,side),r in updates.groupby(['game_id','player','side'],sort=False):
                if player not in states:raise ValueError('covered player absent from source roster')
                a=np.zeros(45);a[0]=r.uses.sum()
                shot=r.cell.ge(0)
                cells=r.loc[shot,'cell'].to_numpy(int)
                a[1+cells]=r.loc[shot,'uses'].to_numpy()
                a[23+cells]=r.loc[shot,'made'].to_numpy()
                if side=='off':
                    states[player][0]+=a[:23]
                    states[player][1]+=a[1:]
                    league_add+=a[1:]
                else:
                    states[player][2]+=a
            league+=league_add
        if progress and (n+1)%100==0:progress(n+1,len(groups))
    frame=pd.DataFrame(out,columns=['game_id','date_et','season','player']+COLS)
    for c in COLS:frame[c]=frame[c].astype(np.float32)
    audit={'source_segments':len(s),'covered_uses':int(s.court_use.sum()),'covered_attempts':int(s.court_attempt.sum()),
           'covered_makes':int(s.court_make.sum()),'uncovered_uses':int((s.end_type.isin(['shot','fouled','turnover']) & ~s.heave.fillna(False) & ~s.court_use).sum()),
           'unknown_attempts':int((s.court_attempt & s.court_cell.ge(20)).sum()),'defender_uses':int((e.side=='def').sum()),
           'defender_attempts':int(((e.side=='def') & e.court_attempt).sum()),'rows':len(frame),'days':len(groups),
           'latest_source_date':str(s.date_et.max()),'league_uses':int(league_uses),'league_attempts':int(league[:22].sum()),'league_makes':int(league[22:].sum())}
    assert audit['league_uses']==audit['covered_uses']
    assert audit['defender_uses']==5*audit['covered_uses']
    assert audit['defender_attempts']==5*audit['covered_attempts']
    assert audit['league_attempts']==audit['covered_attempts']
    assert audit['league_makes']==audit['covered_makes']
    assert np.allclose(frame[[f'court_mix_{i}' for i in range(22)]].sum(axis=1),1)
    assert np.allclose(frame[[f'court_d_mix_{i}' for i in range(22)]].sum(axis=1),1)
    assert (frame[[f'court_rate_{i}' for i in range(22)]].sum(axis=1)<=1.000001).all()
    assert (frame[[f'court_d_rate_{i}' for i in range(22)]].sum(axis=1)<=1.000001).all()
    return frame,audit
