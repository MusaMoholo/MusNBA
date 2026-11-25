#!/usr/bin/env python3
"""Reconcile historical regulation/final scores from retained original scoreboards."""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pandas as pd
import pyarrow as pa
from basketball_common import read_json,write_json,sha256_file

WORK=ROOT/'data/derived/experiments/d42_b2_score_truth_v3'
REPORT=ROOT/'analysis/experiments/20261124_b2_score_truth_v3.json'


def one(year):
    pa.set_cpu_count(1)
    regular=pd.read_parquet(ROOT/f'data/derived/experiments/d42_b2_calendar_audit_v1/{year}.parquet')
    path=ROOT/f'data/raw/hoopr/play_by_play_{year}.parquet'
    columns=['game_id','sequence_number','period_number','clock_display_value','home_score','away_score','home_team_id','away_team_id']
    p=pd.read_parquet(path,columns=columns,filters=[('game_id','in',regular.game_id.astype('int64').unique().tolist())])
    clock=p.clock_display_value.str.split(':',expand=True)
    p['remaining']=pd.to_numeric(clock[0],errors='coerce')*60+pd.to_numeric(clock[1],errors='coerce')
    p=p.sort_values(['game_id','period_number','remaining','sequence_number'],ascending=[True,True,False,True],kind='stable')
    ends=p.groupby(['game_id','period_number'],sort=False).tail(1)
    final=ends.groupby('game_id',sort=False).tail(1).set_index('game_id')
    reg=ends[ends.period_number.eq(4)].set_index('game_id')
    rows=[];summary_used=[]
    summary_root=ROOT/'data/raw/b2_score_summaries_20261124_v1'
    summaries={r['game']:r for r in read_json(summary_root/'manifest.json')}
    for r in regular[regular.home].itertuples():
        gid=int(r.game_id)
        incomplete=gid not in final.index or gid not in reg.index
        if not incomplete:
            f=final.loc[gid];q=reg.loc[gid];recorded=[int(f.home_score),int(f.away_score)]
            incomplete=recorded!=[int(r.pts),int(r.opp_pts)]
        if incomplete:
            descriptor=summaries[str(gid)];source=ROOT/descriptor['path']
            if sha256_file(source)!=descriptor['sha256']:raise ValueError('retained summary changed')
            game=read_json(source)['header']['competitions'][0]
            sides={x['homeAway']:x for x in game['competitors']}
            recorded=[int(sides[s]['score']) for s in ('home','away')]
            lines=[sides[s].get('linescores',[]) for s in ('home','away')]
            if len(lines[0])!=len(lines[1]) or len(lines[0])<4:raise ValueError('missing paired summary period support')
            period=len(lines[0]);ot=period-4
            if all(len(x)>=4 for x in lines):
                regulation=[sum(int(float(x.get('displayValue',x.get('value')))) for x in side[:4]) for side in lines]
            elif period==4:
                regulation=recorded.copy()  # Known four-period final equals regulation by identity.
            else:raise ValueError(f'{gid}: missing supported OT period truth')
            summary_used.append(str(gid))
        else:
            regulation=[int(q.home_score),int(q.away_score)];ot=int(f.period_number)-4
        if recorded!=[int(r.pts),int(r.opp_pts)]:raise ValueError(f'{gid}: final scoreboard/box mismatch')
        if not all(a<=b for a,b in zip(regulation,recorded)) or ((regulation[0]==regulation[1])!=(ot>0)):
            raise ValueError(f'{gid}: unsupported regulation/OT score')
        rows.append({'game_id':str(r.game_id),'home':r.team,'away':r.opp,'reg_home':regulation[0],
                     'reg_away':regulation[1],'final_home':recorded[0],'final_away':recorded[1],'ot':ot})
    result=pd.DataFrame(rows);output=WORK/f'{year}.parquet';result.to_parquet(output,index=False)
    derived=ROOT/f'data/derived/history/{year}/player_periods.csv.gz'
    old=pd.read_csv(derived,dtype={'game_id':str,'team_id':str})
    old=old[old.period.le(4)].groupby(['game_id','team_id']).pts.sum()
    mismatches=[]
    for r in result.itertuples():
        for label in ('home','away'):
            key=(r.game_id,getattr(r,label));actual=getattr(r,'reg_'+label)
            if key not in old or old[key]!=actual:
                mismatches.append({'game':r.game_id,'side':label,'derived':None if key not in old else int(old[key]),'original_scoreboard':actual})
    return {'season':year,'games':len(result),'regulation_period_end_differences':mismatches,
            'truth':str(output.relative_to(ROOT)),'sha256':sha256_file(output),
            'summary_games':summary_used,
            'source_sha256':{str(path.relative_to(ROOT)):sha256_file(path),str(derived.relative_to(ROOT)):sha256_file(derived),
                             **{summaries[gid]['path']:summaries[gid]['sha256'] for gid in summary_used}}}


if __name__=='__main__':
    if WORK.exists() or REPORT.exists():raise FileExistsError('new immutable source truth namespace required')
    WORK.mkdir(parents=True)
    with ProcessPoolExecutor(max_workers=4) as pool:rows=list(pool.map(one,range(2023,2027)))
    write_json(REPORT,{'kind':'B2 original-scoreboard score reconciliation; no forecast outcomes',
        'seasons':rows,'regular_games':sum(r['games'] for r in rows),
        'derived_period_differences':sum(len(r['regulation_period_end_differences']) for r in rows),
        'method':'Order original scoreboards by period/clock/sequence (late-logged earlier plays cannot overwrite period ends). Q4/final checked against final box totals. Six incomplete feeds use retained ESPN summaries; a verified four-period final equals regulation. No clamping, imputation or outcome-driven exclusions.',
        'setup_repair':'Initial audit sorted by feed sequence alone; incomplete V1 namespace/source retained. No candidate results were opened.',
        'old_source_preserved':True,'workers':4,'inner_threads':1,'protected_scoring':False,
        'source_sha256':sha256_file(Path(__file__))},pretty=True)
    print('Reconciled',sum(r['games'] for r in rows),'games;',sum(len(r['regulation_period_end_differences']) for r in rows),'derived period differences',flush=True)
