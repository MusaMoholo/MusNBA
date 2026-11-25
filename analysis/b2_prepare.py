#!/usr/bin/env python3
"""Freeze three B2 starting-strength/memory candidates and strictly prior auxiliaries."""
from pathlib import Path
from datetime import datetime,timezone
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import pyarrow as pa
from basketball_common import read_json,write_json,sha256_file
from scripts import pathway,season_backtest
from analysis.b2_calendar_audit import WORK as CALENDAR

PLAN=ROOT/'analysis/experiments/20261124_b2_frozen_recipe_v1.json'
WORK=ROOT/'data/derived/experiments/d42_b2_strength_v1'
VARIANTS={
 'carry8':{'starting':'carry','n_cap':20,'scale':1.},
 'opponent8':{'starting':'opponent','n_cap':20,'scale':1.},
 'opponent40':{'starting':'opponent','n_cap':40,'scale':1.}}


def opponent_offsets(frame,league,ids,prior=None):
    """Ridge eight game-equivalents per offence/defence; home effect remains accepted2pts."""
    index={t:i for i,t in enumerate(ids)};n=len(ids)
    X=np.zeros((len(frame),2*n),float)
    row=np.arange(len(frame));X[row,[index[t] for t in frame.team]]=1
    X[row,n+np.array([index[t] for t in frame.opp])]=1
    y=100*frame.pts.to_numpy(float)/frame.poss.to_numpy(float)-league['ortg']
    # Known neutral Cup semifinals carry no home-court term; other designated-home games retain v1's assumption.
    hca=np.where(frame.get('neutral',pd.Series(False,index=frame.index)),0.,np.where(frame.home,1.,-1.))
    y-=100*hca/frame.poss.to_numpy(float)
    target=np.zeros(2*n) if prior is None else np.asarray(prior,float)
    return np.linalg.solve(X.T@X+8*np.eye(2*n),X.T@y+8*target)


def starts(frame,day,previous,variant,ids):
    past=frame[frame.date.lt(day)].copy()
    if past.empty or past.date.max()>=day:raise ValueError('starting fit must precede origin')
    T,lg=season_backtest.state_before(frame,day)
    off,dfn,pace,gp=pathway.start_ratings(T,lg,ids,8)
    if variant=='reference' or variant=='persistence':
        return {'off':off.tolist(),'def':dfn.tolist(),'pace':pace.tolist(),'gp':gp.tolist(),
                'T':T,'league':lg,'latest_fit_date':str(past.date.max()),'previous_latest_fit_date':None}
    prior=np.zeros(2*len(ids))
    prior_date=None
    if previous is not None:
        if previous.date.max()>=day:raise ValueError('future carry-over source')
        _,prior_lg=season_backtest.state_before(previous,'9999-12-31')
        prior=.5*opponent_offsets(previous,prior_lg,ids)
        prior_date=str(previous.date.max())
    if VARIANTS[variant]['starting']=='carry':
        off+=8*prior[:len(ids)]/(gp+8);dfn+=8*prior[len(ids):]/(gp+8)
    else:
        offsets=opponent_offsets(past,lg,ids,prior)
        off=lg['ortg']+offsets[:len(ids)];dfn=lg['ortg']+offsets[len(ids):]
    return {'off':off.tolist(),'def':dfn.tolist(),'pace':pace.tolist(),'gp':gp.tolist(),
            'T':T,'league':lg,'latest_fit_date':str(past.date.max()),'previous_latest_fit_date':prior_date}


def frame_for(year):
    frame=pd.read_parquet(CALENDAR/f'{year}.parquet')
    from analysis.b2_calendar_audit import POLICIES
    policy=POLICIES[year];frame['neutral']=False
    if policy['cup_final']:
        frame.loc[frame.date.eq(f'{year-1}-{policy["sf"]}'),'neutral']=True
    return frame


def freeze():
    if PLAN.exists() or WORK.exists():raise FileExistsError('immutable B2 freeze required')
    origins=read_json(ROOT/'analysis/experiments/20261124_chunk_b_successor_v4.json')['historical_pathway_panel']['origins']
    policy={'version':'pathway-b2-v1-20261124','primary':'mean final-team-wins CRPS across all16 origins; each season/origin/team equal',
       'candidates':3,'development':'First12 origins/seasons ending2023-25; leave-one-season-out selection within these three only.',
       'independent':'All four2025-26 origins withheld until unchanged nominee selected on development. Other candidates cannot replace a failed nominee.',
       'nominee':'Minimum development mean CRPS among candidates with mean gain>=.05 and no date mean CRPS harm>.10; deterministic lexical ties. No development survivor means retain v1.',
       'uncertainty':'10000 paired complete-season block resamples, seed20261124; retain all four dates and30 teams in each season block. Four seasons are sparse/dependent evidence, not independent960 team-starts.',
       'multiplicity':'All16 inference uses simultaneous Bonferroni95% intervals for three frozen candidates (quantiles .0083333/.9916667). No switched primary.',
       'acceptance':'Unchanged nominee: all16 mean CRPS gain>=.05 and familywise lower>0; independent2025-26 mean gain>0; no MM-DD mean CRPS harm>.10, no coverage80 shortfall increase>.03, dispersion-distance-to1 not worse by>.10. Report persistence and team-points CRPS/bias; no pooled cancellation hides dates.',
       'per_origin_uncertainty':'Paired canonical1k-world chunk bootstrap describes Monte Carlo precision only; generalisation intervals use whole historical seasons. No team or world iid claim.',
       'promotion_limit':'Only conditional regular-season calibration from reconstructed schedules; no historical title/postseason certification. Unknown schedule revision timestamps, neutral metadata and absent injury history remain explicit.',
       'release':'No new production parameter until all16/source/accounting/cutoff/exact-mixture/runtime gates and B3 integration pass. Failure closes this fixed study, retains pathway-v1 and records unmet objectives.'}
    WORK.mkdir(parents=True)
    write_json(PLAN,{'kind':'B2 prospectively frozen starting-strength/memory study; no candidate results opened',
        'frozen_at':datetime.now(timezone.utc).isoformat(),'variants':VARIANTS,
        'reference':pathway.PATHWAY,'persistence_control':{'starting':'reference','scale':0.,'n_cap':20},
        'fixed_auxiliary':{'prior_equivalent_games':8,'offseason_retention':.5,'ridge':8,
            'home_court':2,'posterior_scale_unchanged':.4,'sigma_unchanged':11,
            'early2022':'Common league-centred zero offsets; no2021-22 data is invented.'},
        'policy':policy,'origins':origins,'worlds':10000,'chunk_worlds':1000,
        'historical_calendar':'20261124_b2_calendar_audit_v1.json; unknown November Cup matchups drawn inside each world; Cup finals excluded from regular counts.',
        'absence':'No supported dated future injury process; no hazard in every arm.',
        'near_term':'No original possession forecasts retained at these historical origins (D40). Do not backfill/fabricate Expected. Historical paths use no engine atoms; exact live Expected coupling remains independently checked on current saved branches, without outcome scoring.',
        'inference':'Season ratings use only sources/fits before each origin. Cross-validation selects frozen hyperparameters, never an origin-specific future input.',
        'format_sources':['https://www.nba.com/news/2023-in-season-tournament-debut-official-release',
                          'https://www.nba.com/grizzlies/emiratesnbacup',
                          'https://cdn-uat.nba.com/news/board-of-governors-in-game-flopping-penalty-permanent',
                          'https://www.nba.com/news/2025-nba-cup-group-draw-results'],
        'protected_scoring':False,'production_changed':False,
        'source_sha256':{str(p.relative_to(ROOT)):sha256_file(p) for p in [Path(__file__),ROOT/'analysis/b2_calendar_audit.py',ROOT/'analysis/experiments/20261124_b2_calendar_audit_v1.json',ROOT/'scripts/pathway.py',ROOT/'scripts/competitions.py',ROOT/'scripts/competition_rules.py']}},pretty=True)
    print('Frozen3 variants, first12 development/4 independent origins, policy and no-hazard/missing-Expected limits',flush=True)


def build():
    plan=read_json(PLAN);path=WORK/'starts.json'
    if path.exists():raise FileExistsError(path)
    frames={y:frame_for(y) for y in (2023,2024,2025,2026)}
    ids=sorted(frames[2023].team.unique(),key=int);out={}
    for day in plan['origins']:
        year=int(day[:4])+(day[5:7]>='07');out[day]={}
        for variant in ['reference','persistence',*VARIANTS]:
            out[day][variant]=starts(frames[year],day,frames.get(year-1),variant,ids)
            check=starts(pd.concat([frames[year],frames[year].assign(date='2099-01-01',pts=999999)]),day,
                         frames.get(year-1),variant,ids)
            if out[day][variant]!=check:raise ValueError('future injection changed starting fit')
        print(f'{day}:5 strictly prior starts; future injection has no effect',flush=True)
    write_json(path,{'ids':ids,'origins':out,'recipe_sha256':sha256_file(PLAN)},pretty=False)
    report=ROOT/'analysis/experiments/20261124_b2_prior_fits_v1.json'
    if report.exists():raise FileExistsError(report)
    write_json(report,{'kind':'B2 prior-only ratings/auxiliaries; no forecast outcomes',
        'origins':16,'arms':5,'fit_rows':80,'future_injection_checks':80,
        'latest_dates':{day:{arm:{k:r[k] for k in ['latest_fit_date','previous_latest_fit_date']} for arm,r in arms.items()} for day,arms in out.items()},
        'path':str(path.relative_to(ROOT)),'sha256':sha256_file(path),'recipe_sha256':sha256_file(PLAN),
        'candidate_results_opened':False,'protected_scoring':False},pretty=True)


if __name__=='__main__':
    pa.set_cpu_count(1)
    {'freeze':freeze,'build':build}[sys.argv[1]]()
