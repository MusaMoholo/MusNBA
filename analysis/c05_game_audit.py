"""Independent short-panel eligibility arithmetic using audited returned-world scores."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from analysis import c05_data as data,c05_audit as audit
from analysis.c01_workbench import read,create_json
from analysis.c01_core import ContractError


def run():
    report=read(data.WORK/'short.json');ids=data.verify()['game_ids'][:20];account=audit.world_audit(ids);rows=pd.concat([pd.read_parquet(data.WORK/'games'/g/'scores.parquet') for g in ids]);joint=pd.concat([pd.read_parquet(data.WORK/'games'/g/'joint.parquet') for g in ids]);limits=read(data.CONTRACT)['game_shortlist']['harm_point_limits'];results={}
    for f in report['families']:
        q=rows[rows.model.eq(f)];checks={};effects={}
        for baseline in ('native','bridge'):
            r=rows[rows.model.eq(baseline)];c=q[q.entity.eq('player')&q.stat.eq('pts')];ref=r[r.entity.eq('player')&r.stat.eq('pts')];relative=c.crps.mean()/ref.crps.mean()-1;effects[baseline]=float(relative);checks[f'{baseline}/primary']=relative<=-.005;checks[f'{baseline}/halves']=all(c[f'crps_half{k}'].mean()<ref[f'crps_half{k}'].mean() for k in (1,2))
            for key in ('team/points','game/total','game/margin','player/min','player/reb','player/ast','player/fg3m'):
                ent,stat=key.split('/');a=q[q.entity.eq(ent)&q.stat.eq(stat)];b=r[r.entity.eq(ent)&r.stat.eq(stat)];checks[f'{baseline}/{key}']=a.crps.mean()-b.crps.mean()<=limits[key]
            for stat in ('pts','fg3m'):
                a=q[q.role.eq('star')&q.stat.eq(stat)];b=r[r.role.eq('star')&r.stat.eq(stat)];checks[f'{baseline}/critical/{stat}']=a.crps.mean()/b.crps.mean()-1<=.02
            coverage=[]
            for ent,stat in [('player','pts'),('team','points'),('game','total'),('game','margin')]:
                a=q[q.entity.eq(ent)&q.stat.eq(stat)];b=r[r.entity.eq(ent)&r.stat.eq(stat)];coverage.append(abs(a.covered80.mean()-.8)-abs(b.covered80.mean()-.8)<=.03)
            checks[f'{baseline}/coverage80']=all(coverage);checks[f'{baseline}/win_brier']=joint[joint.model.eq(f)].win_brier.mean()-joint[joint.model.eq(baseline)].win_brier.mean()<=.01
        timing=[read(data.WORK/'games'/g/'receipt.json')['seconds_by_arm'] for g in ids];checks['runtime']=np.median([t[f]/t['bridge'] for t in timing])<=2
        if any(bool(v)!=report['eligible'][f]['checks'][k] for k,v in checks.items()):raise ContractError('independent game decision mismatch')
        results[f]={'eligible':bool(all(checks.values())),'player_points_relative_effect':effects,'failed_checks':[k for k,v in checks.items() if not v],'all_checks_independently_match':True}
    out={'known_games':20,'world_accounting':account,'decisions':results,'accuracy_scope':'development selection only, no independent chronological confirmation','production_changed':False};create_json(data.WORK/'short_independent.json',out);create_json(ROOT/'analysis/experiments/20261126_c05_short_independent_v1.json',out);print(out)

if __name__=='__main__':run()
