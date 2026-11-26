"""Final engine-returned law diagnostics, including minute translation and calibration."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from analysis.c05_models import WORK
from analysis.c01_workbench import read,create_json
from analysis.c01_core import ContractError
from basketball_common import sha256_file


def summarise(ids):
    records=[];translation={}
    for gid in ids:
        folder=WORK/'games'/gid;r=read(folder/'receipt.json')
        if any(sha256_file(folder/n)!=h for n,h in r['hashes'].items()):raise ContractError('delivered game artifact changed')
        records.append(pd.read_parquet(folder/'scores.parquet'))
        for model in r['arms']:
            if model=='native':continue
            with np.load(folder/f'{model}.npz',allow_pickle=False) as z:
                schedule=abs(z['scheduled_minutes']-z['target_minutes'])
                if schedule.max()>1/60+1e-8:raise ContractError('delivered schedule violates target bound')
                # Engine minutes include generated OT/fouls/substitution timing: retain all differences.
                actual=abs(z['minutes']-z['scheduled_minutes']);reg=z['final_period']==4
                entry=translation.setdefault(model,{'schedule_error_sum':0.,'schedule_error_values':0,'schedule_error_max':0.,'returned_vs_schedule_sum':0.,'regulation_only_difference_sum':0.,'regulation_only_values':0})
                entry['schedule_error_sum']+=float(schedule.sum());entry['schedule_error_values']+=schedule.size;entry['schedule_error_max']=max(entry['schedule_error_max'],float(schedule.max()));entry['returned_vs_schedule_sum']+=float(actual.sum());entry['regulation_only_difference_sum']+=float(actual[reg].sum());entry['regulation_only_values']+=int(actual[reg].size)
    rows=pd.concat(records,ignore_index=True);out={'games':len(ids),'returned_distributions':{},'translation':translation,'scope':'Exact scheduled targets do not imply exact returned game minutes: event-boundary substitutions, fouls and OT remain explicit. No result-selected trimming.'}
    for f,q in rows.groupby('model'):
        out['returned_distributions'][f]={f'{entity}/{stat}':{'rows':len(v),'crps':float(v.crps.mean()),'mae':float(v.absolute_error.mean()),**{f'coverage{level}':float(v[f'covered{level}'].mean()) for level in (50,80,95)}} for (entity,stat),v in q.groupby(['entity','stat'])}
    for v in translation.values():
        v['schedule_error_mean']=v['schedule_error_sum']/v['schedule_error_values'];v['returned_vs_schedule_mean']=v['returned_vs_schedule_sum']/v['schedule_error_values'];v['regulation_only_difference_mean']=v['regulation_only_difference_sum']/v['regulation_only_values'] if v['regulation_only_values'] else None
    return out

if __name__=='__main__':
    from analysis.c05_data import verify
    p=verify();n=200 if (WORK/'final.json').exists() else 20 if (WORK/'short.json').exists() else 2;r=summarise(p['game_ids'][:n]);create_json(WORK/f'delivered{n}.json',r);create_json(ROOT/f'analysis/experiments/20261126_c05_delivered{n}_v1.json',r);print(r)
