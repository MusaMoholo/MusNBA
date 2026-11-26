"""Frozen final legal/quantised joint-minute comparison, all exposed200 games."""
from __future__ import annotations
import sys,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from analysis import c04_data as source,c05_data as data,c05_models as models,c01_metrics as metrics
from analysis.c04_compare import interval
from analysis.c01_workbench import read,create_json
from basketball_common import sha256_file
from analysis.c01_core import ContractError

def seed(gid,s):return int.from_bytes(hashlib.sha256(f'c05-law-v1|{gid}|{s}'.encode()).digest()[:8],'little')

def run():
    p=data.verify();out=data.WORK/'minute_screen.json'
    if out.exists():raise FileExistsError(out)
    rows=pd.read_parquet(source.WORK/'rows.parquet');predictors={f:models.Predictor(f) for f in 'ABC'};records=[];joint=[];hashes={};folder=data.WORK/'minute_draws';folder.mkdir(exist_ok=False)
    for j,ref in enumerate(p['references']):
        gid=ref['game_id'];ids=ref['captured_player_ids'];part=rows[rows.game_id.eq(gid)].set_index('player').loc[ids].reset_index()
        if sha256_file(ROOT/ref['capture'])!=ref['capture_sha256']:raise ContractError('native changed')
        with np.load(ROOT/ref['capture'],allow_pickle=False) as z:native=z['minutes'][:1000,:,:4].sum(2);side=z['side'];usage=z['prior_usage']
        a={'native':native,'player_ids':np.array(ids),'side':side}
        for f,model in predictors.items():
            x=np.zeros_like(native)
            for s in (0,1):
                take=np.flatnonzero(side==s);x[:,take]=model.draw(part.iloc[take],1000,np.random.default_rng(seed(gid,s)))
            a[f]=x
        with (folder/f'{gid}.npz').open('xb') as stream:np.savez_compressed(stream,**a)
        hashes[gid]=sha256_file(folder/f'{gid}.npz')
        for f in ('native','A','B','C'):
            for i,r in enumerate(part.itertuples()):records.append({'game_id':gid,'date_et':ref['date_et'],'model':f,'entity':'player','stat':'regmin','player':r.player,'side':str(side[i]),'critical':bool(usage[i]>=.25),'roster_n':r.roster_n,**metrics.scalar_record(a[f][:,i],r.reg)})
            joint.append({'game_id':gid,'date_et':ref['date_et'],'model':f,'energy':float(np.linalg.norm(a[f]-part.reg.to_numpy(),axis=1).mean()-.5*np.mean([np.linalg.norm(a[f]-np.roll(a[f],shift,axis=0),axis=1).mean() for shift in range(1,33)]))})
        if (j+1)%25==0:print('C05 legal minute laws',j+1,'/200',flush=True)
    scores=pd.DataFrame(records);scores.to_parquet(data.WORK/'minute_scores.parquet',index=False);pd.DataFrame(joint).to_parquet(data.WORK/'minute_joint.parquet',index=False);report={'models':{},'changes':{},'eligible':{},'draw_hashes':hashes,'games':200,'worlds':1000,'production_changed':False};native=scores[scores.model.eq('native')]
    for f,g in scores.groupby('model'):
        report['models'][f]={'player_games':len(g),'crps':float(g.crps.mean()),'mae':float(g.absolute_error.mean()),'half1':float(g.crps_half1.mean()),'half2':float(g.crps_half2.mean()),**{f'coverage{level}':float(g[f'covered{level}'].mean()) for level in (50,80,95)},'width80':float(g.width80.mean()),'energy':float(pd.DataFrame(joint).query('model==@f').energy.mean())}
    for f in 'ABC':
        g=scores[scores.model.eq(f)];z=interval(metrics.paired_frame(native,g),3);critical=g[g.critical];cr=native[native.critical];cz=interval(metrics.paired_frame(cr,critical),3);relative=z['change']/native.crps.mean();checks={'minute_gain':relative<=-.02,'game_week_support':max(z['familywise_game'][1],z['familywise_week'][1])<0,'halves':all(g[f'crps_half{k}'].mean()<native[f'crps_half{k}'].mean() for k in (1,2)),'support':z['games']>=100 and len(g)>=2000,'critical_harm':cz['change']/cr.crps.mean()<=.02,'coverage50':.45<=g.covered50.mean()<=.55,'coverage80':.76<=g.covered80.mean()<=.84,'coverage95':.92<=g.covered95.mean()<=.98,'critical_coverage80':.73<=critical.covered80.mean()<=.87}
        report['changes'][f]={'overall':z,'relative_change':relative,'critical':cz,'critical_coverage80':float(critical.covered80.mean()),'equal_game_change':float(metrics.paired_frame(native,g).groupby('game_id').change.mean().mean()),'by_roster_size':{str(n):{'rows':len(v),'crps':float(v.crps.mean()),'coverage80':float(v.covered80.mean())} for n,v in g.groupby('roster_n')}};report['eligible'][f]={'eligible':bool(all(checks.values())),'checks':{k:bool(v) for k,v in checks.items()}}
    report['shortlist']=sorted([f for f in 'ABC' if report['eligible'][f]['eligible']],key=lambda f:report['models'][f]['crps'])[:2];create_json(out,report);create_json(ROOT/'analysis/experiments/20261126_c05_minute_screen_v1.json',{k:v for k,v in report.items() if k!='draw_hashes'});print(report['models'],report['eligible'],report['shortlist'],flush=True)

if __name__=='__main__':run()
