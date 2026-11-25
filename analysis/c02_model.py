"""Chronological pure-possession learners, profile baseline and frozen screen."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import gc
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import lightgbm as lgb
import numpy as np
import pandas as pd
import pyarrow as pa
from analysis import c02_data as data,c01_contexts as context,c01_metrics as metrics
from analysis.c01_core import ContractError
from analysis.c01_workbench import read,create_json
from basketball_common import sha256_file

WORK=data.WORK

def softmax(raw,k=5):
    z=np.asarray(raw,float).reshape(-1,k);z=z-z.max(1,keepdims=True);p=np.exp(z);return p/p.sum(1,keepdims=True)

def check_prob(p):
    p=np.asarray(p,float)
    if p.ndim!=2 or not np.isfinite(p).all() or (p<0).any() or not np.allclose(p.sum(1),1,atol=1e-7):raise ContractError('invalid possession probability law')
    return p

def objective(pred,ds):
    y=ds.get_label();p=softmax(pred).ravel();w=ds.get_weight()
    if w is None:w=np.ones(len(y))
    return (p-y)*w,2*np.maximum(p*(1-p),1e-6)*w

def actor_metric(pred,ds):
    y=ds.get_label().reshape(-1,5);p=softmax(pred);w=ds.get_weight()
    loss=-np.log(p[y.astype(bool)])
    return 'conditional_nll',float(np.average(loss,weights=None if w is None else w[::5])),False

def baseline_fit(training):
    f=training['what'];p=profile_what(f,None)
    return {'what_fallback':np.nanmean(p,axis=0).tolist(),'training_through':str(f.date_et.max()),'floor':1e-6}

def profile_what(f,fallback):
    cols=[f.actor_shot_share.to_numpy()*f[f'actor_mix_{z}'].to_numpy() for z in context.nodes.ZONES]
    three=f.actor_mix_corner3.to_numpy()+f.actor_mix_above3.to_numpy();foul=f.actor_foul_drawn_share.to_numpy()
    p=np.column_stack(cols+[f.actor_tov_share.to_numpy(),foul*(1-.1*three),foul*.1*three]).astype(float)
    if fallback is None:return p
    p=np.where(np.isnan(p),np.asarray(fallback),p)
    p=np.maximum(p,1e-6);return check_prob(p/p.sum(1,keepdims=True))

def profile_predict(name,f,fit):
    if name=='what':return profile_what(f,fit['what_fallback'])
    p=f.usage_share.to_numpy(float).reshape(-1,5)
    p=np.where(np.isnan(p),1.,p);p=np.maximum(p,1e-6);return check_prob(p/p.sum(1,keepdims=True))

def params(name,threads=10):
    c=read(data.CONTRACT)['candidate']
    p={k:c[k] for k in ('learning_rate','num_leaves','min_data_in_leaf','lambda_l2','max_bin','seed','feature_fraction','bagging_fraction')}
    p.update(objective=objective if name=='who' else 'multiclass',metric='None' if name=='who' else 'multi_logloss',
             num_threads=threads,verbosity=-1,deterministic=True,force_col_wise=True,feature_pre_filter=False)
    if name=='what':p['num_class']=8
    return p

def weights(f,origin):
    if f.date_et.ge(origin).any():raise ContractError('future possession fit/calibration origin')
    return np.exp2(-(pd.Timestamp(origin)-pd.to_datetime(f.date_et)).dt.days.to_numpy()/365)

def train_head(f,name,folder,threads=10,fixed_rounds=None):
    data.validate(f,name,True);c=read(data.CONTRACT)['candidate'];cols=data.COLS[name]
    if fixed_rounds is None:
        tr=f.date_et.le('2025-09-30').to_numpy();va=~tr
        if not tr.any() or not va.any():raise ContractError('empty chronological training/selection block')
        a=lgb.Dataset(f.loc[tr,cols],label=f.loc[tr,'y'],weight=weights(f[tr],'2025-10-01'),free_raw_data=True)
        b=lgb.Dataset(f.loc[va,cols],label=f.loc[va,'y'],weight=weights(f[va],'2026-01-01'),reference=a,free_raw_data=True)
        selected=lgb.train(params(name,threads),a,num_boost_round=c['rounds_max'],valid_sets=[b],feval=actor_metric if name=='who' else None,
                    callbacks=[lgb.early_stopping(c['early_stopping_rounds'],verbose=False),lgb.log_evaluation(50)])
        rounds=selected.best_iteration
        selection={'best_rounds':rounds,'validation_score':selected.best_score['valid_0'],'training_rows':int(tr.sum()),'selection_rows':int(va.sum())}
        del selected,a,b;gc.collect()
    else:rounds=int(fixed_rounds);selection={'best_rounds':rounds}
    fit=lgb.Dataset(f[cols],label=f.y,weight=weights(f,'2026-01-01'),free_raw_data=True)
    booster=lgb.train(params(name,threads),fit,num_boost_round=rounds)
    path=folder/f'{name}.txt'
    if path.exists():raise FileExistsError(path)
    booster.save_model(str(path))
    return booster,selection

def fit():
    data.verify();folder=WORK/'models';folder.mkdir(exist_ok=False)
    started=time.monotonic();info={};training={}
    for name in ('who','what'):training[name]=pd.read_parquet(WORK/f'training_{name}.parquet')
    base=baseline_fit(training);create_json(folder/'baseline.json',base)
    for name in ('who','what'):
        print('Fit pure possession head',name,flush=True)
        _,info[name]=train_head(training[name],name,folder)
        del training[name];gc.collect();print(name,info[name],flush=True)
    meta={'kind':'C02 fitted pure possession probability heads','created_at':datetime.now(timezone.utc).isoformat(),'heads':info,'features':data.COLS,
          'training_through':'2025-12-31','source_sha256':sha256_file(Path(__file__)),'contract_sha256':sha256_file(data.CONTRACT),
          'data_manifest_sha256':sha256_file(WORK/'data.json'),'hashes':{n:sha256_file(folder/n) for n in ('who.txt','what.txt','baseline.json')},'seconds':time.monotonic()-started,
          'selection':'earlier chronological block only; no development tuning','production_changed':False}
    create_json(folder/'fit.json',meta);print('Fit complete',meta['seconds'],flush=True)

class Predictor:
    def __init__(self,folder=None):
        self.folder=Path(folder or WORK/'models');self.meta=read(self.folder/'fit.json')
        if self.meta['features']!=data.COLS:raise ContractError('unapproved possession feature interface')
        for n,h in self.meta['hashes'].items():
            if sha256_file(self.folder/n)!=h:raise ContractError('fitted head changed')
        self.models={n:lgb.Booster(model_file=str(self.folder/f'{n}.txt')) for n in ('who','what')}
        self.baseline=read(self.folder/'baseline.json')
    def predict(self,name,f,raw=False):
        if set(data.COLS[name])-set(f):raise ContractError('missing runtime possession features')
        x=f[data.COLS[name]].to_numpy(np.float32) if isinstance(f,pd.DataFrame) else np.column_stack([f[c] for c in data.COLS[name]]).astype(np.float32)
        out=self.models[name].predict(x,raw_score=name=='who',num_threads=1)
        if name=='who':return out if raw else check_prob(softmax(out))
        return check_prob(out)


def rows_for(name,f,p,model):
    if name=='who':
        y=f.y.to_numpy().reshape(-1,5);chosen=p[y.astype(bool)];br=((p-y)**2).sum(1);keys=f.iloc[::5]
    else:
        y=f.y.to_numpy();chosen=p[np.arange(len(y)),y];br=((p-np.eye(8)[y])**2).sum(1);keys=f
    if (chosen<=0).any():raise ContractError('zero true-class probability')
    return pd.DataFrame({'seg_id':keys.seg_id.to_numpy(),'game_id':keys.game_id.to_numpy(),'date_et':keys.date_et.to_numpy(),
                         'node':name,'model':model,'loss':-np.log(chosen),'brier':br})

def screen():
    data.verify();predictor=Predictor();plan=read(WORK/'data.json');output=WORK/'screen.json'
    if output.exists():raise FileExistsError(output)
    records=[]
    for name in ('who','what'):
        f=pd.read_parquet(WORK/f'panel_{name}.parquet')
        for model,p in (('candidate',predictor.predict(name,f)),('profile',profile_predict(name,f,predictor.baseline))):records.append(rows_for(name,f,p,model))
    chain,ds,_=context.load_chain(plan['game_ids']);e,_=context.load_engine(plan['game_ids'])
    # Only paired source-supported keys are scored; no outcome-defined exclusions.
    for name in ('who','what'):
        d=ds[name];p,brier,_,pick=context.predict_node(e,name,d)
        groups=d.get('group',d.get('seg_id'))[pick]
        records.append(pd.DataFrame({'seg_id':groups,'game_id':d['game'][pick],'date_et':d['date'][pick],
                         'node':name,'model':'incumbent','loss':-np.log(p),'brier':brier}))
    all_rows=pd.concat(records,ignore_index=True);full=[];summary={}
    common_keys=set(all_rows[all_rows.model.eq('candidate')&all_rows.node.eq('what')].seg_id)
    for model in ('incumbent','candidate','profile'):
        a=all_rows[all_rows.model.eq(model)&all_rows.node.eq('who')].set_index('seg_id')
        b=all_rows[all_rows.model.eq(model)&all_rows.node.eq('what')].set_index('seg_id')
        if common_keys-set(a.index) or common_keys-set(b.index):raise ContractError('recorded action support differs')
        keys=sorted(common_keys);a=a.loc[keys];b=b.loc[keys]
        if not np.array_equal(a.game_id.to_numpy(),b.game_id.to_numpy()):raise ContractError('event keys differ')
        f=pd.DataFrame({'seg_id':keys,'game_id':a.game_id.to_numpy(),'date_et':a.date_et.to_numpy(),'model':model,
                        'loss':a.loss.to_numpy()+b.loss.to_numpy(),'brier':a.brier.to_numpy()+b.brier.to_numpy()})
        full.append(f);summary[model]={'events':len(f),'games':f.game_id.nunique(),'joint_log_loss_nats':float(f.loss.mean()),'conditional_head_brier_sum':float(f.brier.mean()),
                   'who_loss':float(a.loss.mean()),'what_loss':float(b.loss.mean())}
    rows=pd.concat(full,ignore_index=True);ref=full[0].set_index('seg_id');changes={}
    for f in full[1:]:
        name=f.model.iloc[0];q=f.set_index('seg_id').loc[ref.index];changes[name]={}
        for field in ('loss','brier'):
            pair=q[['game_id','date_et']].assign(change=q[field]-ref[field]).reset_index(drop=True)
            changes[name][field]=metrics.bootstrap_change(pair)
    c=read(data.CONTRACT)['screen'];r=changes['candidate'];relative=-r['loss']['change']/summary['incumbent']['joint_log_loss_nats']
    passed=(summary['candidate']['games']>=c['minimum_games'] and len(ref)>=c['minimum_events'] and relative>=c['minimum_relative_gain']
        and max(r['loss']['ci95_game'][1],r['loss']['ci95_calendar_week'][1])<0
        and max(r['brier']['ci95_game'][1],r['brier']['ci95_calendar_week'][1])<=c['brier_max_harm'])
    all_rows.to_parquet(WORK/'event_scores.parquet',index=False);rows.to_parquet(WORK/'joint_event_scores.parquet',index=False)
    result={'kind':'C02 frozen recorded-context screen; known development only','models':summary,'changes_vs_incumbent':changes,'candidate_relative_log_loss_gain':relative,
            'screen_passed':bool(passed),'next_rollout_games':200 if passed else 20,'composite_brier_definition':'sum of actor and observed-actor conditional action Brier scores; not a flat40-class Brier',
            'population':'same supported actor/action keys, actual participants and recorded histories; no operational skill claim',
            'fit_sha256':sha256_file(WORK/'models/fit.json'),'scorer_sha256':sha256_file(Path(__file__)),'production_changed':False}
    create_json(output,result);create_json(ROOT/'analysis/experiments/20261125_c02_screen_v1.json',result)
    print(result,flush=True)

if __name__=='__main__':
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    a=argparse.ArgumentParser();a.add_argument('stage',choices=['fit','screen']);args=a.parse_args()
    fit() if args.stage=='fit' else screen()
