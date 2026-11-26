"""Independent weighted-CDF arithmetic, world accounting and decision checks."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from analysis import c07_data as data,c07_score as score,c07_members as members
from analysis.c01_workbench import read,create_json
from analysis.c01_core import ContractError
from basketball_common import sha256_file


def verify_fingerprints(tree,root=ROOT):
    import re
    checked=0
    for key,value in tree.items():
        if isinstance(value,dict):checked+=verify_fingerprints(value,root)
        elif isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value) and '/' in key:
            path=Path(root)/key
            if not path.is_file() or sha256_file(path)!=value:raise ContractError('retained source bytes changed:'+key)
            checked+=1
    return checked


def reference_crps(x,y,w):
    order=np.argsort(x);v=np.asarray(x)[order];p=np.asarray(w)[order];cuts=np.unique(np.r_[v,y]);idx=np.searchsorted(v,cuts[:-1],side='right');cdf=np.r_[0,np.cumsum(p)][idx]
    return float(np.sum((cdf-(cuts[:-1]>=y))**2*np.diff(cuts)))


def audit(ids):
    maximum=0.;count=0;worlds=0;mass=0
    for gid in ids:
        folder=data.WORK/'forecasts'/gid;r=read(folder/'receipt.json');arrays={}
        for name,h in r['hashes'].items():
            if sha256_file(folder/name)!=h:raise ContractError('expert score/archive changed')
        for f in r['families']:
            with np.load(folder/f'{f}.npz',allow_pickle=False) as z:a={k:z[k] for k in z.files}
            score.check_worlds(a);arrays[f]=a;worlds+=1000
            if 'member' in a:
                if len(set(zip(a['member'],a['member_world'])))!=1000:raise ContractError('expert source world duplicated')
                if abs(a['weight'][:500].sum()-.5)>1e-12:raise ContractError('expert half mass changed')
                names=r['member_names'];expected=np.array(r['mixture_masses'][f]);actual=np.bincount(a['member'],weights=a['weight'],minlength=len(names))
                expected=expected if len(names)==4 else expected[[0,3]]
                if not np.allclose(actual,expected,atol=1e-12,rtol=0):raise ContractError('independent component mass mismatch')
                for j,name in enumerate(names):
                    mask=a['member']==j
                    if not mask.any():continue
                    original=members.load(gid,name);ix=a['member_world'][mask]
                    for field in ('pts','team','minutes','fgm','fga','fg3m','fg3a','ftm','fta','oreb','dreb','ast','pf','final_period'):
                        if not np.array_equal(a[field][mask],original[field][ix]):raise ContractError('mixture world/source mapping mismatch')
                mass+=1
        for row in pd.read_parquet(folder/'scores.parquet').itertuples():
            a=arrays[row.model];w=a['weight']
            if row.entity=='player':x=a['minutes' if row.stat=='min' else row.stat][:,a['player_ids'].tolist().index(row.player)]
            elif row.entity=='team':x=a['team'][:,0 if row.side=='home' else 1]
            else:x=a['team'].sum(1) if row.stat=='total' else a['team'][:,0]-a['team'][:,1]
            for expected,xx,ww in [(row.crps,x,w),(row.crps_half1,x[:500],w[:500]/w[:500].sum()),(row.crps_half2,x[500:],w[500:]/w[500:].sum())]:
                delta=abs(reference_crps(xx,row.truth,ww)-expected);maximum=max(maximum,delta);count+=1
                if delta>1e-9:raise ContractError('independent weighted CRPS differs')
            order=np.argsort(x);cdf=np.cumsum(w[order]);lo=x[order][np.searchsorted(cdf,.1)];hi=x[order][min(np.searchsorted(cdf,.9),999)]
            if bool(lo<=row.truth<=hi)!=bool(row.covered80):raise ContractError('independent weighted coverage differs')
        joint=pd.read_parquet(folder/'joint.parquet')
        for row in joint.itertuples():
            a=arrays[row.model];p=float(sum(a['weight'][a['team'][:,0]>a['team'][:,1]]))
            if abs(p-row.p_home)>1e-12 or abs((p-row.home_won)**2-row.win_brier)>1e-12:raise ContractError('independent weighted win score differs')
    return {'games':len(ids),'returned_worlds_checked':worlds,'scalar_and_half_scores_checked':count,'maximum_difference':maximum,'mass_and_source_mappings_checked':mass,'all_conservation_passed':True}


def decision(stage):
    from analysis.c05_compare import interval
    from analysis.c07_evaluate import coverage
    from analysis.c01_metrics import paired_frame
    report=read(data.WORK/f'{stage}_decision.json');p=data.verify();ids=p['eval_ids'][:20] if stage=='short' else p['eval_ids'];rows=pd.concat([pd.read_parquet(data.WORK/'forecasts'/g/'scores.parquet') for g in ids]);joint=pd.concat([pd.read_parquet(data.WORK/'forecasts'/g/'joint.parquet') for g in ids]);full=stage=='final';results={};limits=read(data.CONTRACT)['harm_limits']
    for f,z in report['eligible'].items():
        q=rows[rows.model.eq(f)];r=rows[rows.model.eq('native')];checks={}
        def change(ent,stat,c=q,b=r):
            cr=c[c.entity.eq(ent)&c.stat.eq(stat)];rr=b[b.entity.eq(ent)&b.stat.eq(stat)];return interval(paired_frame(rr,cr),7),cr,rr
        def upper(v):return max(v['familywise_game'][1],v['familywise_week'][1]) if full else v['change']
        v,c,base=change('player','pts');relative=c.crps.mean()/base.crps.mean()-1;checks['primary']=relative<=(-.01 if full else -.005) and (not full or upper(v)<0);checks['halves']=all(c[f'crps_half{k}'].mean()<base[f'crps_half{k}'].mean() for k in (1,2));checks['population']=len(ids)>=100 if full else True
        for entstat in ('team/points','game/total','game/margin','player/min','player/reb','player/ast','player/fg3m'):
            ent,stat=entstat.split('/');v,cc,rr=change(ent,stat);checks[entstat]=upper(v)<=limits[entstat]
        for stat in ('pts','fg3m'):
            cr=r[r.role.eq('star')&r.stat.eq(stat)];cc=q[q.role.eq('star')&q.stat.eq(stat)];v=interval(paired_frame(cr,cc),7);checks[f'critical/{stat}']=(v['games']>=30 and len(cr)>=200 and upper(v)/cr.crps.mean()<=.02) if full else cc.crps.mean()/cr.crps.mean()-1<=.02
        covers=[]
        for ent,stat in [('player','min'),('player','pts'),('team','points'),('game','total'),('game','margin')]:
            rr=r[r.entity.eq(ent)&r.stat.eq(stat)];cc=q[q.entity.eq(ent)&q.stat.eq(stat)];covers.append(upper(coverage(rr,cc,7))<=.03)
        checks['coverage80']=all(covers);j=joint[joint.model.eq(f)].set_index('game_id').sort_index();jr=joint[joint.model.eq('native')].set_index('game_id').sort_index()
        for field,limit in [('win_brier',.01),('energy',.15)]:
            v=interval(pd.DataFrame({'game_id':j.index,'date_et':j.date_et,'change':j[field]-jr[field]}).reset_index(drop=True),7);checks[field]= (v['change'] if field=='energy' else upper(v))<=limit
        if f!='pool':
            checks['converged']=read(data.WORK/'fit.json')['training'][f]['converged']
            if full:
                poolrows=rows[rows.model.eq('pool')];v,cc,rr=change('player','pts',q,poolrows);checks['learned_pool_gain']=cc.crps.mean()/rr.crps.mean()-1<=-.0025 and upper(v)<0
        elif full:checks['shortlist']='pool' in read(data.WORK/'short_decision.json')['shortlist']
        if set(checks)!=set(z['checks']) or any(bool(value)!=z['checks'][key] for key,value in checks.items()):raise ContractError('independent expert decision differs')
        results[f]={'relative_pts_change_native':float(relative),'all_checks_independently_match':True,'eligible':bool(all(checks.values())),'failed_checks':[k for k,v in checks.items() if not v]}
    return {'game_accounting':audit(ids),'decisions':results,'shortlist':report['shortlist'],'retained_source_files_verified':verify_fingerprints(data.verify()['sources']),'independent_confirmation':False}

if __name__=='__main__':
    stage=sys.argv[1] if len(sys.argv)>1 else 'wiring';p=data.verify();r=audit(p['eval_ids'][:2]) if stage=='wiring' else decision(stage);create_json(data.WORK/f'{stage}_audit.json',r);create_json(ROOT/f'analysis/experiments/20261126_c07_{stage}_audit_v1.json',r);print(r)
