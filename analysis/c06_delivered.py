"""Final returned player/team distribution summary, all scored coverage levels."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pandas as pd
from analysis.c06_data import WORK,verify
from analysis.c01_workbench import create_json


def run():
    n=200 if (WORK/'final.json').exists() else 20 if (WORK/'short.json').exists() else 2
    ids=verify()['game_ids'][:n];rows=pd.concat([pd.read_parquet(WORK/'games'/g/'scores.parquet') for g in ids]);out={'games':n,'models':{},'scope':'Final returned worlds, including generated foul substitutions and overtime; first2 wiring is mechanical only, no game-skill claim. Native schedules fixed across C06 arms; actual realised minutes may vary.'}
    for family,q in rows.groupby('model'):
        out['models'][family]={f'{entity}/{stat}':{'rows':len(v),'crps':float(v.crps.mean()),'mae':float(v.absolute_error.mean()),'bias':float(v.bias.mean()),**{f'coverage{level}':float(v[f'covered{level}'].mean()) for level in (50,80,95)}} for (entity,stat),v in q.groupby(['entity','stat'])}
    create_json(WORK/f'delivered{n}.json',out);create_json(ROOT/f'analysis/experiments/20261126_c06_delivered{n}_v1.json',out);return out

if __name__=='__main__':print(run())
