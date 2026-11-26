"""Actor-only probability adapter; all other event decisions remain incumbent."""
from contextlib import contextmanager
import numpy as np
from analysis.c06_core import CONTEXT,PLAYER
from analysis.c01_core import ContractError
PREFIX='c06__'

@contextmanager
def attached(e,g,view,predictor):
    if predictor.meta['training_through']>=g.day:raise ContractError('future C06 runtime fit')
    old_context,old_five,old_predict=e._context,e._five,e.m.predict;temperature=e.m.nodes['who']['temperature'];counts={'who':0}
    def ctx(game,st,A,lo,ld):
        return {**old_context(game,st,A,lo,ld),**{PREFIX+k:v for k,v in view.context(game,st,A,lo,ld).items()}}
    def five(game,st,A,lineup,relative):
        return {**old_five(game,st,A,lineup,relative),**{PREFIX+k:v for k,v in view.five(st,A,lineup,relative).items()}}
    def predict(name,cols,n):
        if name!='who':return old_predict(name,cols,n)
        if np.any(cols['foul_event']):return old_predict(name,cols,n)/temperature
        c={k:np.asarray(cols[PREFIX+k] if k!='shot_time' else cols[k]).reshape(-1,5)[:,0] for k in CONTEXT};p={k:np.asarray(cols[PREFIX+k]).reshape(-1,5) for k in PLAYER};law=predictor.predict(c,p);counts['who']+=len(law);return np.log(law).ravel()
    e._context,e._five,e.m.predict=ctx,five,predict;e.m.nodes['who']['temperature']=1.
    try:yield counts
    finally:e._context,e._five,e.m.predict=old_context,old_five,old_predict;e.m.nodes['who']['temperature']=temperature
