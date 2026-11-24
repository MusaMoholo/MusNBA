"""Persist the frozen court decoder's training-only geometry/compatibility fits."""
import numpy as np
import pandas as pd
from scripts import court_zones as cz,train,nodes
from scripts.court_runtime import SCHEMA
from analysis.c2_node_screen import source_rows


def prepare(fold,variant):
    rows,band=source_rows('location');cut=train.FOLDS[fold]
    date=rows.date_et.to_numpy();train_all=(date>=train.BURN_IN)&(date<=cut[0])
    ns=pd.to_datetime(rows.date_et).astype('int64').to_numpy()
    tr=train_all & (ns<np.quantile(ns[train_all],.9))
    spec=cz.layout(variant!='zone');label=cz.encode(spec,rows.x,rows.y,rows.value)
    coarse,cell,mask=cz.decoder(spec);centroids=[]
    for col in ['distance','lateral']:
        means=pd.Series(rows[col].to_numpy()[tr]).groupby(label[tr]).mean().reindex(range(len(cell)))
        centroids.append([float(x) if np.isfinite(x) else None for x in means])
    compat=None
    if variant=='zone':
        counts=np.zeros((len(cell),nodes.LOCATION_BANDS),float)
        np.add.at(counts,(label[tr],band[tr]),1)
        zone=rows.zone.map(dict(zip(nodes.ZONES,range(5)))).to_numpy()
        for k in range(len(cell)):
            if not counts[k].sum():
                counts[k]=np.bincount(band[tr & (zone==coarse[k])],minlength=nodes.LOCATION_BANDS)
            if not counts[k].sum():counts[k]=nodes.LOCATION_MASK[coarse[k]]
            counts[k]/=counts[k].sum()
        compat=counts.tolist()
    return {'schema':SCHEMA,'variant':variant,'layout':spec,'training_through':cut[0],
            'latest_fit_date':str(max(date[tr].tolist())),'fit_rows':int(tr.sum()),
            'fit_precision':'Same strict training90% centroid transform as frozen node fit; last10% early stopping excluded',
            'distance':centroids[0],'lateral':centroids[1],'compatibility_band_probabilities':compat}
