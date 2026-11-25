"""Isolated pure-possession probability adapter. No production modifications."""
from __future__ import annotations
from contextlib import contextmanager
import numpy as np
from analysis.c02_features import PREFIX,selected
from analysis.c02_model import check_prob
from analysis.c01_core import ContractError

@contextmanager
def attached(e,g,view,predictor):
    if predictor.meta['training_through']>=g.day:raise ContractError('future runtime possession model')
    old_context,old_five,old_actor,old_predict=e._context,e._five,e._actor,e.m.predict
    temperature=e.m.nodes['who']['temperature'];counts={'who':0,'what':0}
    def ctx(game,st,A,lo,ld):
        normal=old_context(game,st,A,lo,ld);causal=view.context(game,st,A,lo,ld)
        return {**normal,**{PREFIX+k:v for k,v in causal.items()}}
    def five(game,st,A,lineup,relative):
        normal=old_five(game,st,A,lineup,relative);causal=view.five(st,A,lineup,relative)
        return {**normal,**{PREFIX+k:v for k,v in causal.items()}}
    def actor(cols,slot):
        normal=old_actor(cols,slot);causal=view.actor({k[len(PREFIX):]:v for k,v in cols.items() if k.startswith(PREFIX)},slot)
        return {**normal,**{PREFIX+k:v for k,v in causal.items()}}
    def predict(name,cols,n):
        if name not in counts:return old_predict(name,cols,n)
        # Elapsed duration and the already-sampled event type are shared, causal
        # information. Every other candidate feature comes from the C02 view.
        raw={k[len(PREFIX):]:v for k,v in cols.items() if k.startswith(PREFIX)}
        for k in ('shot_time','foul_event'):
            if k in cols:raw[k]=cols[k]
        features=selected(name,raw);out=predictor.predict(name,features,raw=name=='who')
        if name=='what':check_prob(out)
        elif np.asarray(out).shape!=(n,) or not np.isfinite(out).all():raise ContractError('invalid runtime actor logits')
        counts[name]+=n if name=='what' else n//5
        return out
    e._context,e._five,e._actor,e.m.predict=ctx,five,actor,predict
    e.m.nodes['who']['temperature']=1.
    try:yield counts
    finally:
        e._context,e._five,e._actor,e.m.predict=old_context,old_five,old_actor,old_predict
        e.m.nodes['who']['temperature']=temperature


def validate_worlds(g,st):
    if not st.done.all():raise ContractError('unfinished possession worlds')
    if not np.array_equal(st.score,st.pts.sum(2)):raise ContractError('event/team score identity')
    box=st.box
    if any((v<0).any() for v in box.values()):raise ContractError('negative event count')
    if not np.array_equal(box['pts'],2*box['fgm']+box['fg3m']+box['ftm']):raise ContractError('player event scoring identity')
    if (box['fg3m']>box['fgm']).any() or (box['fgm']>box['fga']).any() or (box['fg3m']>box['fg3a']).any() or (box['fg3a']>box['fga']).any() or (box['ftm']>box['fta']).any():raise ContractError('event makes/attempts bounds')
    for side in (0,1):
        idx=g.side==side
        if not np.array_equal(box['pts'][:,idx].sum(1),st.pts[:,side]):raise ContractError('player/team period identity')
        if not np.allclose(st.minutes[:,idx].sum((1,2)),240+25*(st.period-4),atol=1e-8,rtol=0):raise ContractError('legal team minutes')
    return True
