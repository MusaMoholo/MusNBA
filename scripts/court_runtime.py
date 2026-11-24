"""Explicit optional decoder for the frozen C2 court representation.

The accepted engine has no court decoder. This object reads fitted, dated auxiliary
parameters; it never fits or fetches during simulation or browsing.
"""
import numpy as np
from scripts import court_profiles,court_zones,nodes

SCHEMA='court-decoder-v2'


class CourtRuntime:
    def __init__(self,aux,model_cutoff):
        if aux['schema']!=SCHEMA or aux['training_through']!=model_cutoff or aux['latest_fit_date']>model_cutoff:
            raise ValueError('court auxiliary schema/cutoff differs from node model')
        self.layout=aux['layout']
        if self.layout['schema']!=court_zones.SCHEMA:raise ValueError('court geometry schema differs')
        if aux['variant'] not in ('zone','distance','defence') or self.layout['within_distance'] != (aux['variant']!='zone'):
            raise ValueError('court recipe and location interface differ')
        self.coarse,self.cell,self.mask=court_zones.decoder(self.layout)
        n=len(self.cell)
        self.defence=aux['variant']=='defence'
        self.band=np.array([p for p,c in self.layout['pairs']],int) if self.layout['within_distance'] else None
        self.compat=np.asarray(aux['compatibility_band_probabilities'],float) if self.band is None else None
        if self.compat is not None:
            if self.compat.shape!=(n,nodes.LOCATION_BANDS) or not np.isfinite(self.compat).all() or (self.compat<0).any() or not np.allclose(self.compat.sum(axis=1),1):
                raise ValueError('invalid court compatibility probabilities')
            if (self.compat*~nodes.LOCATION_MASK[self.coarse]).any():raise ValueError('court compatibility changes shot value/parent')
        self.distance=np.asarray(aux['distance'],np.float32)
        self.lateral=np.asarray(aux['lateral'],np.float32)
        if self.distance.shape!=(n,) or self.lateral.shape!=(n,):raise ValueError('court centroid dimensions differ')
        if np.isinf(self.distance).any() or np.isinf(self.lateral).any():raise ValueError('infinite court centroid')

    def context(self,P,defenders):
        if not self.defence:return {}
        cols=court_profiles.COLS[44:88]+[f'court_d_rate_{i}' for i in range(22)]
        return {'lineup_'+col:np.mean(P[col][defenders],axis=1).astype(np.float32) for col in cols}

    def decode(self,choice,actor,rng):
        from scripts.engine import draw
        cell=self.cell[choice]
        extra={'court_cell':cell.astype(np.float32)}
        fg=np.column_stack([actor[f'actor_court_fg_{i}'] for i in range(22)])
        extra['actor_court_fg_selected']=fg[np.arange(len(choice)),cell].astype(np.float32)
        if self.band is None:
            band=draw(self.compat[choice],rng)
        else:
            band=self.band[choice]
            extra.update(distance=self.distance[choice],lateral=self.lateral[choice])
        return band,extra


def attach(model,aux):
    """Configure an isolated model after its nodes load; default model is untouched."""
    court=CourtRuntime(aux,model.cfg['train_through'])
    if model.nodes['location']['classes']!=len(court.cell) or 'court_cell' not in model.nodes['shot_result']['columns']:
        raise ValueError('court LOCATION and SHOT_RESULT interfaces were not trained together')
    used={col for metadata in model.nodes.values() for col in metadata['columns']}
    model.style=list(dict.fromkeys(model.style+[col for col in court_profiles.COLS if 'actor_'+col in used]))
    model.court=court
    model.location_mask=court.mask
    return court


def attach_game(game,profiles):
    """Copy precomputed, dated player inputs into the isolated research game."""
    if not profiles.date_et.astype(str).eq(str(game.day)).all():raise ValueError('court profile day differs from game origin')
    if profiles.player.duplicated().any():raise ValueError('duplicate court player input')
    frame=profiles.set_index('player').reindex(game.ids)
    for col in court_profiles.COLS:game.P[col]=frame[col].to_numpy(np.float32)
