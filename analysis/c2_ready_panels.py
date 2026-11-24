#!/usr/bin/env python3
"""Freeze input-ready C2 panels before nominee selection or F4 arm outcomes."""
from datetime import datetime,timezone
import hashlib
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pandas as pd
import pyarrow as pa
from basketball_common import read_json,write_json,sha256_file
from scripts import backtest
from scripts.features import known_group


def order(key,ids):
    return sorted(ids,key=lambda gid:hashlib.sha256(f'{key}|{gid}'.encode()).hexdigest())


def inspect(fold):
    cut,lo,hi=backtest.FOLDS[fold]
    year=int(hi[:4])+(hi[5:7]>'06')
    pre=ROOT/f'data/derived/variants/a1_scheduled_{fold}_20261122_v3/features/pregame.parquet'
    stpath=ROOT/f'data/derived/history/{year}/stints.parquet'
    segpath=ROOT/f'data/derived/history/{year}/segments.parquet'
    p=pd.read_parquet(pre,columns=['game_id','date_et','team','player','pos'])
    p=p[p.date_et.between(lo,hi)]
    st=pd.read_parquet(stpath,columns=['game_id','date_et','team','player','pos','start_t'])
    st=st[st.start_t<2880].groupby(['game_id','player'],sort=False).head(1)
    templates={}
    for team,rows in st.groupby('team'):
        templates[team]=[(str(part.date_et.iloc[0]),str(gid),bool(part.pos.map(known_group).notna().all()))
                         for gid,part in rows.groupby('game_id')]
        templates[team].sort()
    seg=pd.read_parquet(segpath,columns=['game_id','date_et','season_type','offense','game_ok'])
    eligible=backtest.eligible_games(seg[seg.date_et.between(lo,hi)]).tolist()
    rosters={gid:part for gid,part in p.groupby('game_id')};records=[]
    reference_path=ROOT/'data/derived/variants/matchup/features/pregame.parquet'
    reference_rosters=None
    if fold=='F4':
        reference=pd.read_parquet(reference_path,columns=['game_id','team','player'])
        reference_rosters={gid:set(zip(part.team,part.player)) for gid,part in reference.groupby('game_id')}
    for gid in eligible:
        part=rosters.get(gid);reasons=[];bad=[]
        if part is None or part.team.nunique()!=2 or part.groupby('team').size().min()<5:
            reasons.append('missing two five-player dated rosters')
        else:
            if reference_rosters is not None and set(zip(part.team,part.player))!=reference_rosters.get(gid,set()):reasons.append('reference roster membership differs')
            if not part.pos.map(known_group).notna().all():reasons.append('missing dated player position')
            for team,rows in part.groupby('team'):
                before=str(rows.date_et.iloc[0]);prior=[v for v in templates.get(team,[]) if v[0]<before][-10:]
                bad.extend(g for d,g,known in prior if not known)
            if bad:reasons.append('missing prior-template position')
        records.append({'game_id':gid,'supported':not reasons,'reasons':reasons,'bad_template_games':sorted(set(bad))})
    paths=[pre,stpath,segpath]+([reference_path] if fold=='F4' else [])
    return records,{str(path.relative_to(ROOT)):sha256_file(path) for path in paths}


def fill(original,ready,forbidden,key):
    picked=[gid for gid in original if gid in ready and gid not in forbidden]
    rest=order(key,set(ready)-set(picked)-set(forbidden))
    picked+=rest[:200-len(picked)]
    if len(picked)!=200 or len(set(picked))!=200:raise ValueError('fewer than200 supported fixed-panel games')
    return picked


def main():
    pa.set_cpu_count(1)
    out=ROOT/'analysis/experiments/20261124_c2_ready_panels_v1.json'
    work=ROOT/'data/derived/experiments/c2_readiness_v1'
    if out.exists() or work.exists():raise FileExistsError('readiness namespace is immutable')
    work.mkdir(parents=True)
    plan=read_json(ROOT/'analysis/experiments/20261124_c2_frozen_recipe_v2.json')
    original=plan['panels'];earlier={};sources={};audits={}
    for fold in ['F1','F2','F3','F4']:
        rows,hashes=inspect(fold);sources.update(hashes)
        ready={r['game_id'] for r in rows if r['supported']}
        write_json(work/f'{fold}.json',rows,pretty=False)
        prior=(original['development_F4']+original['reserved_confirmation_F4'] if fold=='F4' else original['earlier_fixed200'][fold])
        audits[fold]={'eligible_games':len(rows),'supported_games':len(ready),'unsupported_original_ids':sorted(set(prior)-ready),
                      'audit_sha256':sha256_file(work/f'{fold}.json'),'season_stints':int(backtest.FOLDS[fold][2][:4])+(backtest.FOLDS[fold][2][5:7]>'06')}
        if fold=='F4':
            development=fill(original['development_F4'],ready,set(original['reserved_confirmation_F4']),'c2-ready-development-v1')
            confirmation=fill(original['reserved_confirmation_F4'],ready,set(development),'c2-ready-confirmation-v1')
            all_f4=sorted(ready)
        else:earlier[fold]=fill(prior,ready,set(),f'c2-ready-{fold}-v1')
        print(fold,audits[fold],flush=True)
    assert not set(development)&set(confirmation)
    write_json(out,{'frozen_at':datetime.now(timezone.utc).isoformat(),'kind':'input-only readiness before nominee selection and F4 outcomes',
                   'selection':'Keep every supported original ID in original order; fill to200 from remaining supported fold population by declared SHA256 keys. Reserve original confirmation IDs during development fill; panels remain disjoint.',
                   'training_recipe_sha256':sha256_file(ROOT/'analysis/experiments/20261124_c2_frozen_recipe_v2.json'),
                   'development_F4':development,'reserved_confirmation_F4':confirmation,'earlier_fixed200':earlier,
                   'all_eligible_F4':all_f4,'independent_stream200':order('c2-independent-stream-v1',development+confirmation)[:200],
                   'stress20':order('c2-stress-v1',development+confirmation)[:20],'readiness':audits,'input_sha256':sources,
                   'limits':'Original r3 controls may be reused only for unchanged inputs/seeds with default-off raw parity. Earlier-fold outcomes inform node selection and are broader confirmation, not independent primary evidence.'},pretty=True)

if __name__=='__main__':main()
