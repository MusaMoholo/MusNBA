"""Versioned exact zone storage, browser encoding and stored-world summaries."""
import base64
import numpy as np
from scripts.world_mass import WorldMass

KEYS=('rim','paint','mid','corner3','above3')
SCHEMA=1

def validate(raw):
    fields=('zone_fga','zone_fgm')
    if not any(k in raw for k in fields):return False
    if not all(k in raw for k in fields):raise ValueError('incomplete zone capture')
    a,m=(np.asarray(raw[k]) for k in fields)
    shape=raw['minutes'].shape+(5,)
    if a.shape!=shape or m.shape!=shape or a.dtype!=np.uint16 or m.dtype!=np.uint16 or (m>a).any():raise ValueError('invalid exact zone arrays')
    for values,stat in ((a,'fga'),(m,'fgm')):
        if not np.array_equal(values.sum(3),raw['box_'+stat]):raise ValueError('zone/player/period totals differ')
    for values,stat in ((a,'fg3a'),(m,'fg3m')):
        if not np.array_equal(values[:,:,:,3:].sum(3),raw['box_'+stat]):raise ValueError('zone/player/period three-point totals differ')
    return True

def encode_arrays(attempts,makes):
    if (attempts.ndim!=4 or attempts.shape[2:]!=(5,5) or makes.shape!=attempts.shape
        or attempts.dtype!=np.uint16 or makes.dtype!=np.uint16 or (makes>attempts).any()):
        raise ValueError('invalid zone array encoding')
    result={'zone_schema':SCHEMA,'zone_keys':list(KEYS)}
    for name,counts in [('attempts',attempts),('makes',makes)]:
        values=counts.sum(2,dtype=np.uint64)
        if (values>np.iinfo(np.uint16).max).any():raise ValueError('full-game zone counts exceed u16; no clipping')
        result['zone_'+name+'_u16_le']=base64.b64encode(np.ascontiguousarray(values,dtype='<u2').tobytes()).decode('ascii')
    return result

def encode(raw):
    if not validate(raw):return {}
    return encode_arrays(raw['zone_fga'],raw['zone_fgm'])


def summaries(raw,weights=None):
    if not validate(raw):return None
    return summaries_arrays(raw['zone_fga'],raw['zone_fgm'],raw['player_ids'],raw['side'],weights)

def summaries_arrays(attempts,makes,ids,side,weights=None):
    n=len(attempts);mass=WorldMass(n,weights)
    a=attempts.sum(2,dtype=np.uint64);m=makes.sum(2,dtype=np.uint64)
    def result(attempts,makes):
        probability=[mass.mean(attempts[:,i]>0) for i in range(5)]
        return {'attempts':mass.mean(attempts).tolist(),'makes':mass.mean(makes).tolist(),
                'attempt_worlds':[(attempts[:,i]>0).sum().item() for i in range(5)],
                'attempt_probability':list(map(float,probability)),
                'worlds':n,'probability_mass':mass.total,'weighted':weights is not None}
    return {'home':result(a[:,side==0].sum(1),m[:,side==0].sum(1)),
            'away':result(a[:,side==1].sum(1),m[:,side==1].sum(1)),
            'players':{str(pid):result(a[:,i],m[:,i]) for i,pid in enumerate(ids)}}
