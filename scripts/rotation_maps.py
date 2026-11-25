"""Stored all-world regulation presence, separate from continuous playing-time forecasts."""
import numpy as np
from scripts.world_mass import WorldMass
SCHEMA='rotation-midpoints-v1'
SECONDS=list(range(30,2880,60))

def validate(raw):
    if 'rotation_presence' not in raw:return False
    values=np.asarray(raw['rotation_presence']);n,p=raw['available'].shape
    if values.shape!=(n,p,48) or values.dtype!=np.uint8 or (values>1).any():raise ValueError('invalid rotation presence')
    if (values*~raw['available'][:,:,None]).any():raise ValueError('unavailable player in rotation map')
    for side in (0,1):
        if not (values[:,raw['side']==side].sum(1)==5).all():raise ValueError('rotation map must have five per team/time')
    return True

def summarise(raw,weights=None):
    if not validate(raw):return None
    values=raw['rotation_presence'];mass=WorldMass(len(values),weights)
    counts=np.einsum('w,wpt->pt',np.ones(len(values),dtype=np.int64) if weights is None else weights,values,dtype=np.int64)
    return {'schema':SCHEMA,'seconds':SECONDS,'worlds':len(values),'probability_mass':mass.total,
            'players':{str(pid):{'side':int(raw['side'][i]),'on_court_mass':counts[i].tolist(),
                                'probability':(counts[i]/mass.total).tolist()} for i,pid in enumerate(raw['player_ids'])},
            'definition':'Chance of being on court at each regulation minute midpoint; all saved worlds with exact weights. Includes worlds where the player sits. Not an estimate of continuous minutes; overtime excluded.'}
