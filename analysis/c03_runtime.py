"""Isolated joint-law adapter; conversion, clocks and foul resolution stay fixed."""
from contextlib import contextmanager
import numpy as np
from analysis.c03_choices import CONTEXT,PLAYER,decode
from analysis.c01_core import ContractError
from scripts import engine

@contextmanager
def attached(e,g,view,predictor):
    if predictor.meta['training_through']>=g.day:raise ContractError('future C03 runtime fit')
    old_context,old_five,old_actor,old_predict=e._context,e._five,e._actor,e.m.predict
    temperature=e.m.nodes['who']['temperature'];state={};counts={'event':0,'who':0,'what':0}
    def ctx(game,st,A,lo,ld):
        normal=old_context(game,st,A,lo,ld)
        state.update(st=st,A=A,lo=lo,ld=ld,ctx=view.context(game,st,A,lo,ld))
        return {**normal,'c03_row':np.arange(len(A))}
    def five(game,st,A,lineup,relative):
        return {**old_five(game,st,A,lineup,relative),'c03_slot':np.tile(np.arange(5),(len(A),1))}
    def actor(cols,slot):return {**old_actor(cols,slot),'c03_actor_slot':cols['c03_slot'][np.arange(len(slot)),slot]}
    def predict(name,cols,n):
        if name=='event':
            c={k:v for k,v in state['ctx'].items() if k in CONTEXT};c['shot_time']=cols['shot_time']
            pl=view.five(state['st'],state['A'],state['lo'],engine.OFF_REL);pl={k:pl[k] for k in PLAYER}
            state['law']=predictor.predict(c,pl);state['decoded']=decode(state['law']);counts[name]+=n
            return state['decoded'][0]
        if name=='who' and not np.any(cols['foul_event']):
            rows=cols['c03_row'].astype(int).reshape(-1,5)[:,0];counts[name]+=len(rows)
            return np.log(state['decoded'][1][rows]).ravel()
        if name=='what':
            rows=cols['c03_row'].astype(int);slot=cols['c03_actor_slot'].astype(int);counts[name]+=n
            return state['decoded'][2][rows,slot]
        return old_predict(name,cols,n)/temperature if name=='who' else old_predict(name,cols,n)
    e._context,e._five,e._actor,e.m.predict=ctx,five,actor,predict;e.m.nodes['who']['temperature']=1.
    try:yield counts
    finally:
        e._context,e._five,e._actor,e.m.predict=old_context,old_five,old_actor,old_predict;e.m.nodes['who']['temperature']=temperature
