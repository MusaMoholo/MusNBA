"""Dual-reference C06 player/team decision with full-slate selection accounting."""
from __future__ import annotations
import numpy as np
import pandas as pd
from analysis import c06_data as data,c03_evaluate as ev,c01_metrics as metrics
from analysis.c01_workbench import read


def interval(frame,count=6):
    r=ev.interval(frame);g=frame.groupby('game_id',sort=True).change.agg(['sum','count']);days=frame.groupby('game_id').date_et.first().reindex(g.index);num=g['sum'].to_numpy();den=g['count'].to_numpy();n=len(g);w=np.random.default_rng(20261125).multinomial(n,[1/n]*n,size=10000);q=[.05/(2*count),1-.05/(2*count)];r['familywise_game']=np.quantile((w@num)/(w@den),q).tolist();block=pd.to_datetime(days).map(lambda d:d.date().toordinal()//7).to_numpy();_,code=np.unique(block,return_inverse=True);nb=code.max()+1;bn=np.bincount(code,weights=num);bd=np.bincount(code,weights=den);w=np.random.default_rng(20261125).multinomial(nb,[1/nb]*nb,size=10000);r['familywise_week']=np.quantile((w@bn)/(w@bd),q).tolist();r['families_counted']=count;return r

def coverage(reference,candidate):
    keys=['game_id','entity','stat','player','side'];r=reference.set_index(keys).sort_index();c=candidate.set_index(keys).sort_index();a=r.reset_index();a['r']=r.covered80.to_numpy();a['c']=c.covered80.to_numpy();g=a.groupby('game_id',sort=True).agg(r=('r','sum'),c=('c','sum'),n=('r','size'),date_et=('date_et','first'));n=len(g);q=[.05/12,1-.05/12]
    def draw(num_r,num_c,den):
        k=len(den);w=np.random.default_rng(20261125).multinomial(k,[1/k]*k,size=10000);return np.abs((w@num_c)/(w@den)-.8)-np.abs((w@num_r)/(w@den)-.8)
    game=draw(g.r.to_numpy(),g.c.to_numpy(),g.n.to_numpy());blocks=pd.to_datetime(g.date_et).map(lambda d:d.date().toordinal()//7).to_numpy();_,code=np.unique(blocks,return_inverse=True);week=draw(np.bincount(code,weights=g.r),np.bincount(code,weights=g.c),np.bincount(code,weights=g.n))
    return {'change':float(abs(c.covered80.mean()-.8)-abs(r.covered80.mean()-.8)),'familywise_game':np.quantile(game,q).tolist(),'familywise_week':np.quantile(week,q).tolist()}

def summarise(ids,families):
    rows=pd.concat([pd.read_parquet(data.WORK/'games'/g/'scores.parquet') for g in ids],ignore_index=True);joint=pd.concat([pd.read_parquet(data.WORK/'games'/g/'joint.parquet') for g in ids],ignore_index=True);full=len(ids)==200;result={'models':{},'comparisons':{},'eligible':{},'runtime':{},'shortlist':[]}
    for f,q in rows.groupby('model'):
        result['models'][f]={f'{ent}/{stat}':{'rows':len(g),'crps':float(g.crps.mean()),'mae':float(g.absolute_error.mean()),'bias':float(g.bias.mean()),'coverage80':float(g.covered80.mean()),'width80':float(g.width80.mean()),'half1':float(g.crps_half1.mean()),'half2':float(g.crps_half2.mean())} for (ent,stat),g in q.groupby(['entity','stat'])}
    limits=read(data.CONTRACT)['game_shortlist']['harm_point_limits']
    for f in families:
        q=rows[rows.model.eq(f)];checks={};comparisons={}
        for reference in ('native','control'):
            r=rows[rows.model.eq(reference)];changes={};critical={};cov={}
            def upper(x):return max(x['familywise_game'][1],x['familywise_week'][1]) if full else x['change']
            for (ent,stat),c in q.groupby(['entity','stat']):
                ref=r[r.entity.eq(ent)&r.stat.eq(stat)];key=f'{ent}/{stat}';changes[key]=interval(metrics.paired_frame(ref,c))
                if ent=='player' and stat in ('pts','fg3m'):
                    cr=ref[ref.role.eq('star')];cc=c[c.role.eq('star')];z=interval(metrics.paired_frame(cr,cc));z['relative_change']=z['change']/cr.crps.mean();z['relative_upper']=max(z['familywise_game'][1],z['familywise_week'][1])/cr.crps.mean();z['context_support']=z['games']>=30 and len(cr)>=200;critical[stat]=z
                if key in ('player/pts','team/points','game/total','game/margin'):cov[key]=coverage(ref,c)
            base=result['models'][reference]['player/pts'];cand=result['models'][f]['player/pts'];relative=changes['player/pts']['change']/base['crps'];checks[f'{reference}/primary']=relative<=(-.01 if full else -.005) and (not full or upper(changes['player/pts'])<0);checks[f'{reference}/halves']=cand['half1']<base['half1'] and cand['half2']<base['half2']
            for key in ('team/points','game/total','game/margin','player/min','player/reb','player/ast','player/fg3m'):checks[f'{reference}/{key}']=upper(changes[key])<=limits[key]
            for stat,z in critical.items():checks[f'{reference}/critical/{stat}']=(z['context_support'] and z['relative_upper']<=limits[f'critical_{stat}_relative']) if full else z['relative_change']<=limits[f'critical_{stat}_relative']
            checks[f'{reference}/coverage80']=all(upper(z)<=.03 for z in cov.values())
            j=joint[joint.model.eq(f)].set_index('game_id').sort_index();jr=joint[joint.model.eq(reference)].set_index('game_id').sort_index();jc={field:interval(j[['date_et']].assign(game_id=j.index,change=j[field]-jr[field]).reset_index(drop=True)) for field in ('win_brier','energy','win_log_loss_smoothed')};checks[f'{reference}/win_brier']=upper(jc['win_brier'])<=.01
            comparisons[reference]={'changes':changes,'critical':critical,'coverage80':cov,'joint':jc,'player_pts_relative_change':relative}
        timing=[read(data.WORK/'games'/gid/'receipt.json')['seconds_by_arm'] for gid in ids];paired=[t[f]/t['control'] for t in timing if t.get('control') is not None];ratio=float(np.median(paired));checks['runtime']=bool(paired) and ratio<=8;result['runtime'][f]={'median_control_ratio':ratio};result['comparisons'][f]=comparisons;result['eligible'][f]={'eligible':bool(all(checks.values())),'checks':{k:bool(v) for k,v in checks.items()}}
    result['shortlist']=sorted([f for f in families if result['eligible'][f]['eligible']],key=lambda f:result['comparisons'][f]['native']['player_pts_relative_change'])[:2];return result
