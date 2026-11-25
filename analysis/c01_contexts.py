"""Source-bound observed histories and read-only diagnostic replay for C01.

Legacy loaders are confined here with parquet predicates BEFORE deserialisation.
No reserved outcomes, current-season outcomes, fitting, or production hooks.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pandas as pd

from analysis.c01_core import ContractError
from analysis.c01_baselines import CUTOFF
from analysis.c01_workbench import ROOT, FEATURES, TEAMS, SEGMENTS
from scripts import engine, nodes, rotations

ORIGINAL_PARQUET = pd.read_parquet
MODEL = "folds/v1.2d_F4_all"
CLOCK = "data/derived/experiments/20261123_a2_late_clock_confirmation_v1/F4_pools.json"
CLOCK_REPORT = "analysis/experiments/20261123_a2_late_clock_confirmation_v1.json"


def and_filters(existing, clause):
    if not existing:
        return clause
    left = [existing] if isinstance(existing[0], tuple) else existing
    right = [clause] if isinstance(clause[0], tuple) else clause
    return [a+b for a in left for b in right]


class SourceBoundary:
    def __init__(self, ids, mode):
        if mode not in ("panel", "training") or not ids or len(ids)!=len(set(ids)):
            raise ContractError("invalid source boundary")
        self.ids, self.mode, self.reads = list(ids), mode, []

    def read(self,path,*args,**kwargs):
        path=Path(path)
        name=path.name
        text=str(path)
        if name=="athletes.parquet":
            # Legacy physical-profile source, explicitly not certified pre-tip.
            clause=None
        elif name in ("segments.parquet","pregame.parquet","team_pregame.parquet"):
            clause=[("game_id","in",self.ids)] if self.mode=="panel" else [("date_et","<=",CUTOFF)]
        elif name.startswith("play_by_play_") and name.endswith(".parquet"):
            clause=[("game_id","in",list(map(int,self.ids)))] if self.mode=="panel" else [("game_date","<=",date.fromisoformat(CUTOFF))]
        else:
            raise ContractError(f"unapproved legacy source read: {path.name}")
        if clause is not None:
            kwargs["filters"]=and_filters(kwargs.get("filters"),clause)
        result=ORIGINAL_PARQUET(path,*args,**kwargs)
        if self.mode=="panel" and "game_id" in result and not set(result.game_id.astype(str)).issubset(self.ids):
            raise ContractError("source reader crossed development boundary")
        if self.mode=="training" and "date_et" in result and result.date_et.gt(CUTOFF).any():
            raise ContractError("source reader crossed training cutoff")
        self.reads.append({"path":text,"rows":len(result),"mode":self.mode,"predicate":str(clause)})
        return result

    @contextmanager
    def installed(self):
        with patch.object(pd,"read_parquet",side_effect=self.read):
            yield self


def load_engine(ids):
    boundary=SourceBoundary(ids,"training")
    with boundary.installed():
        e=engine.Engine(MODEL,runtime={**engine.ENGINE,"models":MODEL,"clock_recipe":None})
    if e.m.cfg["train_through"]!=CUTOFF:
        raise ContractError("observed-context model cutoff differs")
    import json
    from scripts.late_clock import ContextClock
    report=json.loads((ROOT/CLOCK_REPORT).read_text())["folds"]["F4"]["training"]
    if report["latest_training_date"]>CUTOFF:
        raise ContractError("future replay clock")
    e.clock_policy=ContextClock(json.loads((ROOT/CLOCK).read_text()),report["cells"])
    e.clock_policy.train_through=CUTOFF
    def capped_predict(name,cols,n):
        x=np.empty((n,len(e.m.nodes[name]["columns"])),np.float32)
        for j,col in enumerate(e.m.nodes[name]["columns"]):x[:,j]=cols[col]
        return e.m.boosters[name].predict(x,raw_score=e.m.nodes[name]["kind"]=="candidate",num_threads=1)
    e.m.predict=capped_predict
    return e,boundary.reads


def load_chain(ids):
    boundary=SourceBoundary(ids,"panel")
    original_pack=nodes.Chain._pack
    def packed(self,name,kind,X,y,rows,classes=None,profile=None):
        out=original_pack(self,name,kind,X,y,rows,classes,profile)
        out["seg_id"]=rows.seg_id.to_numpy()
        return out
    with boundary.installed(),patch.object(nodes,"segment_files",return_value=[ROOT/SEGMENTS]),patch.object(nodes.Chain,"_pack",packed):
        chain=nodes.Chain(pregame=ROOT/FEATURES)
        datasets={name:chain.dataset(name) for name in ("duration","event","who","what","location","shot_result","assisted","assister","blocked","blocker","turnover_type","stealer","fouler","free_throw","rebound","rebounder")}
    return chain,datasets,boundary.reads


def make_game(ref,pre,teams):
    """Identical retained IDs/profiles; no source minutes fitted or reconstructed."""
    ids=ref["captured_player_ids"]
    side=np.array(ref["captured_sides"])
    p=pre[pre.game_id.eq(ref["game_id"])].copy()
    t=teams[teams.game_id.eq(ref["game_id"])].copy()
    if set(ids)-set(p.player):raise ContractError("game missing pinned prior players")
    lookup=p.set_index("player")
    players={label:[{"id":pid,"name":pid,"pos":lookup.loc[pid,"pos"],"jersey":"","starter":False,"projected_starter":False,
                      "status":"Active","injury":None,"availability":1.,"base_min":float(lookup.loc[pid,"min_avg"])} for pid,s in zip(ids,side) if s==i]
             for i,label in enumerate(("home","away"))}
    t["last_game"]=(pd.to_datetime(t.date_et)-pd.to_timedelta(t.rest_days,unit="D")).dt.strftime("%Y-%m-%d")
    t["season_start"]=(pd.to_datetime(t.date_et)-pd.to_timedelta(t.season_day,unit="D")).dt.strftime("%Y-%m-%d")
    with patch.object(rotations,"templates_for",return_value=[]),SourceBoundary([ref["game_id"]],"panel").installed():
        g=engine.Game({"game_id":ref["game_id"],"home_id":ref["home"],"away_id":ref["away"]},players,p.drop(columns="game_id"),t.drop(columns="game_id"),pd.DataFrame(),ref["date_et"])
    if g.ids!=ids:raise ContractError("recorded player index order changed")
    g.season=2026
    return g


def recorded_runtime(e,g,chain):
    """Both paths receive exactly the same recorded start-of-segment history.

    Separately return the runtime actor timing phase: the engine increments clock
    exposure before evaluating actor nodes; Chain uses preceding segments only.
    No correction is applied here.
    """
    s=chain.seg[chain.seg.game_id.eq(str(g.game["game_id"]))].copy()
    index={pid:i for i,pid in enumerate(g.ids)}
    known=s[[f"{side}_{j}" for side in ("off","def") for j in range(1,6)]].isin(list(index)).all(axis=1)
    s=s[known].copy()
    n=len(s);A=np.arange(n)
    lo=np.array([[index[r[f"off_{j}"]] for j in range(1,6)] for r in s.to_dict("records")])
    ld=np.array([[index[r[f"def_{j}"]] for j in range(1,6)] for r in s.to_dict("records")])
    off=np.where(s.off_home,0,1)
    scores=np.zeros((n,2));fouls=np.zeros((n,2))
    scores[A,off]=s.score_off;scores[A,1-off]=s.score_def
    fouls[A,off]=s.fouls_off;fouls[A,1-off]=s.fouls_def
    st=SimpleNamespace(off=off,period=s.period.to_numpy(),clock=s.start_clock.to_numpy(),score=scores,tfouls=fouls,start=s.start_code.to_numpy(),
                       ingame={key:np.zeros((n,g.n),np.float32) for key in nodes.IN_GAME})
    for table in (chain.off,chain.dfn):
        part=table[table.seg_id.isin(s.seg_id)].set_index(["seg_id","player"])
        for lineup in (lo,ld):
            player=np.asarray(g.ids)[lineup].ravel()
            idx=pd.MultiIndex.from_arrays([np.repeat(s.seg_id.to_numpy(),5),player])
            found=part.reindex(idx)
            present=idx.isin(part.index)
            for col in nodes.IN_GAME:
                st.ingame[col][np.repeat(A,5)[present],lineup.ravel()[present]]=found[col].to_numpy()[present]
    ctx=e._context(g,st,A,lo,ld)
    five=e._five(g,st,A,lo,engine.OFF_REL)
    actor=np.array([list(lo[i]).index(index[pid]) if pid in index and index[pid] in lo[i] else -1 for i,pid in enumerate(s.actor)])
    keep=actor>=0
    slot=np.maximum(actor,0)
    actor_cols=e._actor(five,slot)
    mu=e._mu(g,ld,lo[A,slot],A,lo,slot) if e.m.mu else {}
    common={**ctx,**actor_cols,**mu,"shot_time":s.shot_time.to_numpy(np.float32),"distance":s.distance.to_numpy(np.float32),"lateral":s.lateral.to_numpy(np.float32),
            "zone":s.zone.map({z:i for i,z in enumerate(nodes.ZONES)}).to_numpy(np.float32)}
    zone=s.zone.replace({"corner3":"three","above3":"three"}).to_numpy()
    for pre in ("mu","mu1","mu2"):
        if f"{pre}_fg_rim" in mu:
            common[f"{pre}_fg_shot"]=np.select([zone==z for z in ("rim","paint","mid","three")],[mu[f"{pre}_fg_{z}"] for z in ("rim","paint","mid","three")],default=np.nan).astype(np.float32)
    differences=[]
    # Compare shared context, actor and assignment inputs directly to Chain.
    actor_training=chain._actor(s)
    for col,value in common.items():
        expected=s[col].map({z:i for i,z in enumerate(nodes.ZONES)}).to_numpy(np.float32) if col=="zone" else s[col].to_numpy(np.float32) if col in s else actor_training[col].to_numpy(np.float32) if col in actor_training else None
        if expected is None:continue
        mask=keep if col.startswith(("actor_","mu")) else np.ones(n,bool)
        a,b=np.asarray(value)[mask],expected[mask]
        same=np.isclose(a,b,atol=1e-5,rtol=1e-5,equal_nan=True)
        err=np.abs(a-b);finite=np.isfinite(err)
        differences.append({"game_id":str(g.game["game_id"]),"feature":col,"rows":int(mask.sum()),"mismatches":int((~same).sum()),
                            "max_abs_error":float(err[finite].max()) if finite.any() else 0.})
    # Actor nodes receive elapsed time in runtime; this is a phase diagnostic,
    # not parity on different input histories disguised as the same comparison.
    elapsed=s.shot_time.to_numpy(float)
    for lineup in (lo,ld):st.ingame["sec_so_far"][A[:,None],lineup]+=elapsed[:,None]
    after=e._actor(e._five(g,st,A,lo,engine.OFF_REL),slot)
    time_delta=after["actor_sec_so_far"]-actor_cols["actor_sec_so_far"]
    return s,common,keep,differences,{"eligible_actor_rows":int(keep.sum()),"phase_changed_rows":int((keep&(time_delta!=0)).sum()),
             "sum_elapsed_seconds":float(time_delta[keep].sum()),"max_elapsed_seconds":float(time_delta[keep].max()) if keep.any() else None}


def predict_node(e,name,dataset):
    X=dataset["X"]
    cols=e.m.nodes[name]["columns"]
    if set(cols)-set(X):raise ContractError(f"unsupported observed columns: {name}")
    raw=e.m.boosters[name].predict(X[cols].to_numpy(np.float32),raw_score=dataset["kind"]=="candidate",num_threads=1)
    y=dataset["y"]
    if dataset["kind"]=="candidate":
        groups=dataset["group"]
        unique=np.unique(groups)
        p=np.empty(len(y));brier=[];uniform=[];chosen=[]
        pick=[]
        for group in unique:
            indices=np.flatnonzero(groups==group);count=len(indices);pick.append(indices[0])
            z=raw[indices]/e.m.nodes[name]["temperature"]
            prob=engine.softmax(z[None,:])[0]
            truth=y[indices]
            if truth.sum()!=1:raise ContractError("unsupported candidate label")
            p[indices]=prob
            chosen.append(float(prob[truth.astype(bool)][0]));brier.append(float(((prob-truth)**2).sum()));uniform.append(np.log(count))
        return np.asarray(chosen),np.asarray(brier),np.asarray(uniform),np.asarray(pick)
    if dataset["kind"]=="binary":
        p=np.column_stack([1-raw,raw])
    else:
        p=np.asarray(raw)
        if name=="location":
            z=X.zone.astype(int).to_numpy();p=p*nodes.LOCATION_MASK[z];p=p/p.sum(1,keepdims=True)
    if not np.isfinite(p).all() or (p<0).any() or not np.allclose(p.sum(1),1,atol=1e-6):raise ContractError("invalid observed class law")
    truth=np.eye(p.shape[1])[y]
    return p[np.arange(len(y)),y],((p-truth)**2).sum(1),np.full(len(y),np.log(p.shape[1])),np.arange(len(y))


def duration_scores(probabilities,bin_seconds,truth):
    """Exact empirical within-bin timing mixture, in seconds, without MC draws."""
    p=np.asarray(probabilities,float);y=np.asarray(truth,float)
    if p.ndim!=2 or p.shape[1]!=len(bin_seconds) or not np.isfinite(p).all() or (p<0).any() or not np.allclose(p.sum(1),1):raise ContractError("invalid timing probabilities")
    times=np.unique(np.concatenate(bin_seconds)).astype(float)
    conditional=np.zeros((len(bin_seconds),len(times)))
    for i,values in enumerate(bin_seconds):
        if not len(values):raise ContractError("unsupported duration bin")
        conditional[i]=np.bincount(np.searchsorted(times,values),minlength=len(times))/len(values)
    mass=p@conditional;cdf=np.cumsum(mass,axis=1)[:,:-1]
    proper=(mass*np.abs(times[None,:]-y[:,None])).sum(1)-(cdf*(1-cdf)*np.diff(times)).sum(1)
    absolute=np.abs(mass@times-y)
    return proper,absolute


class ZoneObserver:
    """Read-only generated zone counts; no RNG use or engine mutation."""
    def begin(self,g,st):
        self.attempts=np.zeros((st.W,2,5),np.int64)
        self.makes=np.zeros_like(self.attempts)
    def before_segment(self,g,st,A,L):
        if ((st.clock[A]<0)|(st.clock[A]>np.where(st.period[A]<=4,720,300))).any():raise ContractError("replay clock boundary")
        for side in (0,1):
            five=L[:,side]
            if (np.diff(np.sort(five,axis=1),axis=1)==0).any() or (g.side[five]!=side).any():raise ContractError("replay illegal five")
            eligible=((st.ingame["pf_so_far"][A]<6)&(g.side[None,:]==side)).sum(1)
            bad=st.ingame["pf_so_far"][A[:,None],five]>=6
            if (bad.any(1)&(eligible>=5)).any():raise ContractError("replay illegal disqualified player")
    def after_segment(self,g,st,A,info):
        k=info["shot"]
        np.add.at(self.attempts,(A[k],info["off"][k],info["zone"][k]),1)
        made=k[info["res"][k]>=1]
        np.add.at(self.makes,(A[made],info["off"][made],info["zone"][made]),1)
    def finish(self,g,st):
        if not st.done.all():raise ContractError("replay unfinished worlds")
        for side in (0,1):
            target=240+25*(st.period-4)
            if np.max(np.abs(st.minutes[:,g.side==side].sum((1,2))-target))>1e-8:raise ContractError("replay minute identity")
            if not np.array_equal(self.attempts[:,side].sum(1),st.box["fga"][:,g.side==side].sum((1,2))):raise ContractError("zone attempt identity")
            fg3=st.box["fg3m"][:,g.side==side].sum((1,2));ftm=st.box["ftm"][:,g.side==side].sum((1,2))
            pts=2*self.makes[:,side].sum(1)+fg3+ftm
            if not np.array_equal(pts,st.pts[:,side].sum(1)):raise ContractError("zone scoring identity")
            if not np.array_equal(self.makes[:,side,3:].sum(1),fg3):raise ContractError("zone three identity")


def stored_schedules(capture):
    """One-second schedule adapter from STORED SIMULATED fives, not NBA tracking.

    This holds a sampled forecast schedule fixed for a separate event replay.
    New foul outcomes still receive the legal Rule 3 response. It is explicitly
    not a bit-for-bit regeneration or primary incumbent accuracy comparison.
    """
    with np.load(capture,allow_pickle=False) as z:
        keep=(z["trace_phase"]==0)&(z["trace_period"]<=4)
        world=z["trace_world"][keep].astype(int);period=z["trace_period"][keep].astype(int)
        clock=z["trace_clock"][keep];fives=z["trace_lineups"][keep]
        n=len(z["final_period"]);players=z["player_ids"].tolist();side=z["side"].copy()
        minutes=z["minutes"][:,:,:4].sum(2)
    tables=np.empty((n*2,2880,5),np.int16)
    elapsed=(period-1)*720+720-clock
    order=np.lexsort((elapsed,world))
    world,elapsed,fives=world[order],elapsed[order],fives[order]
    for w in range(n):
        mask=world==w;t=elapsed[mask];line=fives[mask]
        if not len(t) or t[0]>.1:raise ContractError("stored schedule lacks start")
        # Engine consults the schedule at integer elapsed seconds.
        choice=np.searchsorted(t,np.arange(2880),side="right")-1
        for s in (0,1):tables[2*w+s]=line[choice,s]
    if (tables<0).any() or (tables>=len(players)).any() or any((np.diff(np.sort(tables,axis=2),axis=2)==0).ravel()):raise ContractError("illegal stored schedule five")
    reconstructed=np.zeros_like(minutes)
    for i in range(len(players)):
        s=side[i]
        reconstructed[:,i]=(tables[s::2]==i).sum((1,2))/60
    return tables,np.column_stack([2*np.arange(n),2*np.arange(n)+1]),float(np.abs(reconstructed-minutes).max())
