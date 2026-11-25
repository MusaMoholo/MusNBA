"""Frozen cheap200 joint-minute test; exact native player support, no simulations."""
from __future__ import annotations
import sys,hashlib,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from analysis import c04_data as data,c04_models as models,c03_evaluate as ev,c01_metrics as metrics
from analysis.c01_workbench import read,create_json
from analysis.c01_core import ContractError
from basketball_common import sha256_file

def seed(gid,side):return int.from_bytes(hashlib.sha256(f'c04-minute-v1|{gid}|{side}'.encode()).digest()[:8],'little')

def run():
    p=data.verify();out=data.WORK/'minute_screen.json'
    if out.exists():raise FileExistsError(out)
    allrows=pd.read_parquet(data.WORK/'rows.parquet');predictors={f:models.Predictor(f) for f in 'ABC'};records=[];hashes={};folder=data.WORK/'minute_draws';folder.mkdir(exist_ok=False)
    for j,ref in enumerate(p['references']):
        gid=ref['game_id'];ids=ref['captured_player_ids'];part=allrows[allrows.game_id.eq(gid)].set_index('player').loc[ids].reset_index();n=len(ids)
        if sha256_file(ROOT/ref['capture'])!=ref['capture_sha256']:raise ContractError('native minute capture changed')
        with np.load(ROOT/ref['capture'],allow_pickle=False) as z:native=z['minutes'][:1000,:,:4].sum(2);side=z['side']
        a={'native':native,'player_ids':np.array(ids),'side':side}
        for f,model in predictors.items():
            x=np.zeros((1000,n))
            for s in (0,1):
                take=np.flatnonzero(side==s);x[:,take]=model.draw(part.iloc[take],1000,np.random.default_rng(seed(gid,s)))
            a[f]=x
        path=folder/f'{gid}.npz'
        with path.open('xb') as stream:np.savez_compressed(stream,**a)
        hashes[gid]=sha256_file(path)
        # Critical-player definition is the pinned dated usage, never current outcome.
        with np.load(ROOT/ref['capture'],allow_pickle=False) as z:usage=z['prior_usage']
        for f in ('native','A','B','C'):
            for i,r in enumerate(part.itertuples()):records.append({'game_id':gid,'date_et':ref['date_et'],'model':f,'entity':'player','stat':'regmin','player':r.player,'side':str(side[i]),'critical':bool(usage[i]>=.25),'roster_n':r.roster_n,**metrics.scalar_record(a[f][:,i],r.reg)})
        if (j+1)%25==0:print('C04 minute forecasts',j+1,'/200',flush=True)
    rows=pd.DataFrame(records);rows.to_parquet(data.WORK/'minute_scores.parquet',index=False);ref=rows[rows.model.eq('native')];report={'models':{},'changes':{},'eligible':{},'draw_hashes':hashes,'games':200,'worlds':1000,'training_credibility':{f:m.meta['training_credibility'] for f,m in predictors.items()},'production_changed':False}
    for f,g in rows.groupby('model'):report['models'][f]={'player_games':len(g),'regulation_minute_crps':float(g.crps.mean()),'mae':float(g.absolute_error.mean()),'coverage80':float(g.covered80.mean()),'width80':float(g.width80.mean())}
    for f in 'ABC':
        q=rows[rows.model.eq(f)];change=ev.interval(metrics.paired_frame(ref,q));relative=change['change']/ref.crps.mean();r=ref[ref.critical];c=q[q.critical];critical=ev.interval(metrics.paired_frame(r,c));critical['relative_change']=critical['change']/r.crps.mean()
        coverage=abs(q.covered80.mean()-.8)-abs(ref.covered80.mean()-.8);checks={'minute_gain':relative<=-.02,'game_week_support':max(change['familywise_game'][1],change['familywise_week'][1])<0,'critical_harm':critical['relative_change']<=.02,'coverage80':coverage<=.03}
        report['changes'][f]={'overall':change,'relative_change':relative,'critical':critical,'coverage80_distance_deterioration':float(coverage)};report['eligible'][f]={'eligible':bool(all(checks.values())),'checks':{k:bool(v) for k,v in checks.items()}}
    report['shortlist']=sorted([f for f in 'ABC' if report['eligible'][f]['eligible']],key=lambda f:report['changes'][f]['relative_change'])[:2]
    create_json(out,report);create_json(ROOT/'analysis/experiments/20261125_c04_minute_screen_v1.json',{k:v for k,v in report.items() if k!='draw_hashes'});print('C04 minute shortlist',report['shortlist'],report['models'],report['eligible'],flush=True);return report

if __name__=='__main__':run()
