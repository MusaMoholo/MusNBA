#!/usr/bin/env python3
"""First12-origin selection, then locked independent/all16 B2 assessment."""
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import argparse
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import pyarrow as pa
from basketball_common import read_json,write_json,sha256_file
from scripts.aggregate import crps_samples
from analysis.rule3_confirmation import expected_coverage
from analysis.b2_prepare import PLAN,VARIANTS,frame_for
from analysis.b2_runner import RUNS,MANIFEST

CACHE=RUNS/'metrics'
SELECTION=ROOT/'analysis/experiments/20261124_b2_selection_v1.json'
DECISION=ROOT/'analysis/experiments/20261124_b2_decision_v1.json'


def histogram_crps(hist,truth):
    """Exact empirical integer CRPS with no score bound/clipping."""
    n=hist.sum(-1)
    if np.any(n<=0):raise ValueError('missing score support')
    width=max(hist.shape[-1],int(np.max(truth))+1)
    padded=np.pad(hist,[(0,0)]*(hist.ndim-1)+[(0,width-hist.shape[-1])])
    cdf=np.cumsum(padded,axis=-1)/n[...,None]
    step=np.arange(width)>=np.asarray(truth)[...,None]
    return np.square(cdf-step).sum(-1)


def compile_origin(job):
    pa.set_cpu_count(1)
    day,arm=job;path=CACHE/day/(arm+'.json')
    if path.exists():return read_json(path)
    rows=[];arrays=[]
    for chunk in range(10):
        p=RUNS/'screen'/day/arm/f'{chunk:03d}.json';row=read_json(p)
        if row['worlds']!=1000 or sha256_file(ROOT/row['path'])!=row['sha256']:raise ValueError('score source changed')
        with np.load(ROOT/row['path'],allow_pickle=False) as raw:arrays.append({k:raw[k] for k in raw.files})
        rows.append(row)
    ids=sorted(read_json(ROOT/'data/derived/teams.json'),key=int)
    year=int(day[:4])+(day[5:7]>='07');frame=frame_for(year)
    truth=frame.groupby('team').win.sum().reindex(ids).to_numpy(float)
    future=frame[frame.date.ge(day)];past=frame[frame.date.lt(day)]
    actual_points=future.groupby('team').pts.sum().reindex(ids).to_numpy(float)
    past_wins=past.groupby('team').win.sum().reindex(ids,fill_value=0).to_numpy(float)
    wins=np.concatenate([a['wins'] for a in arrays]);points=np.concatenate([a['remaining_points'] for a in arrays])
    first=np.concatenate([a['first_wins'] for a in arrays]).astype(float);remaining=wins-past_wins
    second=remaining-first;means=wins.mean(0);sd=wins.std(0)
    if np.any(sd<=0):raise ValueError('zero season dispersion')
    error=means-truth;crps=crps_samples(wins,truth)
    coverage=np.array([expected_coverage(wins[:,i],truth[i]) for i in range(30)])
    chunk_crps=[]
    for a in arrays:
        w=a['wins'].astype(float);n=len(w);absolute=np.abs(w-truth).mean(0)
        empirical=crps_samples(w,truth)
        chunk_crps.append(float((absolute-(absolute-empirical)*n/(n-1)).mean()))
    names=arrays[0]['known_ids'].tolist()
    if any(a['known_ids'].tolist()!=names for a in arrays):raise ValueError('known future fixtures differ')
    width=max(a['known_hist'].shape[-1] for a in arrays)
    hist=sum((np.pad(a['known_hist'].astype(np.int64),((0,0),(0,0),(0,width-a['known_hist'].shape[-1]))) for a in arrays))
    if not np.equal(hist.sum(-1),10000).all():raise ValueError('not10k samples per known future team-game')
    lookup=frame[frame.home].copy();lookup['game_id']=lookup.game_id.astype(str);lookup=lookup.set_index('game_id')
    known_truth=np.array([[lookup.loc[gid].pts,lookup.loc[gid].opp_pts] for gid in names],float)
    known_mean=(hist*np.arange(width)).sum(-1)/10000
    known_error=known_mean-known_truth
    # Surprise persistence is descriptive; all team/world dependence remains explicit.
    future_home=future[future.home].sort_values(['date','game_id']);split=str(future_home.date.iloc[len(future_home)//2])
    real_first=future[future.date.lt(split)].groupby('team').win.sum().reindex(ids,fill_value=0).to_numpy(float)
    real_remaining=truth-past_wins
    real_s1=real_first-first.mean(0);real_s2=real_remaining-real_first-second.mean(0)
    centered1=first-first.mean(0);centered2=second-second.mean(0)
    centered1-=centered1.mean(1)[:,None];centered2-=centered2.mean(1)[:,None]
    denominator=np.sqrt((centered1**2).sum(1)*(centered2**2).sum(1));supported=denominator>0
    result={'origin':day,'season':year,'arm':arm,'worlds':len(wins),'crps':float(crps.mean()),
        'mae':float(np.abs(error).mean()),'rmse':float(np.sqrt((error**2).mean())),
        'coverage80':float(coverage.mean()),'dispersion':float(((truth-means)/sd).std()),'mean_sd':float(sd.mean()),
        'remaining_points_crps':float(crps_samples(points,actual_points).mean()),
        'known_future_team_games':int(known_truth.size),'known_game_points_crps':float(histogram_crps(hist,known_truth).mean()),
        'known_game_points_bias':float(known_error.mean()),'known_game_points_mae':float(np.abs(known_error).mean()),
        'known_game_points_rmse':float(np.sqrt((known_error**2).mean())),
        'persistence_real':float(np.corrcoef(real_s1,real_s2)[0,1]),
        'persistence_sim':float(((centered1*centered2).sum(1)[supported]/denominator[supported]).mean()),
        'chunk_crps_u':chunk_crps,'unknown_game_points':'Unassigned November Cup slots lack fixed opponent IDs; their points remain in complete team-season totals.',
        'source_sha256':{str((RUNS/'screen'/day/arm/f'{k:03d}.json').relative_to(ROOT)):sha256_file(RUNS/'screen'/day/arm/f'{k:03d}.json') for k in range(10)}}
    path.parent.mkdir(parents=True,exist_ok=True);write_json(path,result,pretty=False)
    return result


def collect(origins,jobs):
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        rows=list(pool.map(compile_origin,[(d,a) for d in origins for a in ['reference','persistence',*VARIANTS]]))
    return {(r['origin'],r['arm']):r for r in rows}


def select(jobs):
    if SELECTION.exists():raise FileExistsError(SELECTION)
    manifest=read_json(MANIFEST);origins=manifest['development_origins'];data=collect(origins,jobs)
    scores={a:float(np.mean([data[d,a]['crps'] for d in origins])) for a in ['reference','persistence',*VARIANTS]}
    eligibility={}
    for a in VARIANTS:
        harms={md:float(np.mean([data[d,a]['crps']-data[d,'reference']['crps'] for d in origins if d.endswith(md)])) for md in ['11-20','12-25','02-01','03-10']}
        eligibility[a]={'gain':scores['reference']-scores[a],'date_harm':harms,
                        'qualified':scores['reference']-scores[a]>=.05 and max(harms.values())<=.10}
    eligible=[a for a in VARIANTS if eligibility[a]['qualified']]
    nominee=min(eligible,key=lambda a:(scores[a],a)) if eligible else None
    loso={}
    for year in [2023,2024,2025]:
        training=[d for d in origins if data[d,'reference']['season']!=year];held=[d for d in origins if d not in training]
        chosen=min(['reference',*VARIANTS],key=lambda a:(np.mean([data[d,a]['crps'] for d in training]),a))
        loso[str(year)]={'chosen':chosen,'held_crps':float(np.mean([data[d,chosen]['crps'] for d in held])),
                        'held_control_crps':float(np.mean([data[d,'reference']['crps'] for d in held]))}
    write_json(SELECTION,{'kind':'B2 unchanged nomination frozen before independent season accuracy',
        'nominee':nominee,'scores':scores,'eligibility':eligibility,'leave_one_season_out':loso,
        'development_origins':origins,'held_out_origins':manifest['independent_origins'],
        'independent_outcomes_opened':False,'recipe_sha256':sha256_file(PLAN),
        'no_rescue':'No replacement nominee after held-out scores, including when nomination is None.',
        'metrics':[{k:v for k,v in r.items() if k not in ['chunk_crps_u','source_sha256']} for r in data.values()],
        'source_sha256':sha256_file(Path(__file__))},pretty=True)
    print('Frozen nominee',nominee,'development CRPS',scores,flush=True)


def assess(jobs):
    if DECISION.exists():raise FileExistsError(DECISION)
    selection=read_json(SELECTION);manifest=read_json(MANIFEST);origins=manifest['origins'];data=collect(origins,jobs)
    bootstrap=np.random.default_rng(20261124).multinomial(4,[.25]*4,size=10000)
    reports={}
    for arm in VARIANTS:
        by_season=np.array([np.mean([data[d,'reference']['crps']-data[d,arm]['crps'] for d in origins if data[d,arm]['season']==year]) for year in range(2023,2027)])
        draws=bootstrap@by_season/4;gain=float(by_season.mean());dates={};origin_precision={}
        for md in ['11-20','12-25','02-01','03-10']:
            days=sorted([d for d in origins if d.endswith(md)])
            delta=np.array([data[d,'reference']['crps']-data[d,arm]['crps'] for d in days])
            dates[md]={'gain':float(delta.mean()),'ci95_seasons':np.quantile(bootstrap@delta/4,[.025,.975]).tolist(),
                'coverage80_control':float(np.mean([data[d,'reference']['coverage80'] for d in days])),
                'coverage80_candidate':float(np.mean([data[d,arm]['coverage80'] for d in days])),
                'dispersion_distance_control':float(np.mean([abs(data[d,'reference']['dispersion']-1) for d in days])),
                'dispersion_distance_candidate':float(np.mean([abs(data[d,arm]['dispersion']-1) for d in days]))}
        held=manifest['independent_origins'];held_gain=float(np.mean([data[d,'reference']['crps']-data[d,arm]['crps'] for d in held]))
        for day in origins:
            delta=np.array(data[day,'reference']['chunk_crps_u'])-data[day,arm]['chunk_crps_u']
            weights=np.random.default_rng(20261124).multinomial(10,[.1]*10,size=10000)
            origin_precision[day]={'gain':data[day,'reference']['crps']-data[day,arm]['crps'],
                'ci95_monte_carlo_only':np.quantile(weights@delta/10,[.025,.975]).tolist()}
        bounds=np.quantile(draws,[.05/6,1-.05/6]).tolist()
        checks={'mean_gain_at_least_point05':gain>=.05,'familywise_lower_above_zero':bounds[0]>0,
                'held_out_season_gain_positive':held_gain>0,
                'no_date_crps_harm_above_point10':all(v['gain']>=-.10 for v in dates.values()),
                'no_date_coverage_shortfall_increase_above_point03':all(max(0.,.8-v['coverage80_candidate'])-max(0.,.8-v['coverage80_control'])<=.03 for v in dates.values()),
                'no_date_dispersion_distance_increase_above_point10':all(v['dispersion_distance_candidate']-v['dispersion_distance_control']<=.10 for v in dates.values())}
        reports[arm]={'mean_gain':gain,'familywise_ci95':bounds,'season_mean_gains':by_season.tolist(),
            'independent2025_26_gain':held_gain,'checks':checks,'dates':dates,'origin_monte_carlo_precision':origin_precision}
    nominee=selection['nominee'];qualified=bool(nominee and all(reports[nominee]['checks'].values()))
    write_json(DECISION,{'kind':'B2 fixed historical study decision; unchanged nominee only',
        'policy':read_json(PLAN)['policy'],'nominee':nominee,'qualified':qualified,
        'decision':'qualified_for_B3_integration' if qualified else 'retain_pathway_v1',
        'reports':reports,'origins':origins,'metrics':[{k:v for k,v in r.items() if k not in ['chunk_crps_u','source_sha256']} for r in data.values()],
        'scope':'Conditional regular-season schedule evaluation; not a title/playoff/full-calendar calibration certification.',
        'inference_limits':['Four adjacent seasons are sparse and potentially dependent. Season-block intervals do not create960 independent observations.',
          'Independent held-out2025-26 is one season: its gain is a point check, not an independently estimable between-season confidence interval.',
          'Per-origin intervals quantify simulation precision only; original schedule-revision/neutral metadata limits remain.',
          'Historical near-term possession Expected is unavailable(D40); no forecasts or absences were fabricated.'],
        'production_changed':False,'protected_scoring':False,'selection_sha256':sha256_file(SELECTION),
        'recipe_sha256':sha256_file(PLAN),'source_sha256':sha256_file(Path(__file__))},pretty=True)
    print({'nominee':nominee,'qualified':qualified,'reports':{a:{k:r[k] for k in ['mean_gain','familywise_ci95','independent2025_26_gain','checks']} for a,r in reports.items()}},flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['select','assess']);p.add_argument('--jobs',type=int,default=10,choices=range(1,11));a=p.parse_args()
    {'select':select,'assess':assess}[a.action](a.jobs)
