#!/usr/bin/env python3
"""C01 connected diagnostics. Fixed20 wiring, then200; all outputs research-only."""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor,as_completed
from datetime import datetime,timezone
import argparse
import ast
import copy
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import pyarrow as pa

from basketball_common import sha256_file
from analysis import c01_baselines as base,c01_benchmark as bench,c01_contexts as context,c01_metrics as metrics
from analysis.c01_core import ContractError
from analysis.c01_workbench import WORK as FOUNDATION,read,create_json,read_panel,FEATURES,TEAMS,SEGMENTS

WORK=ROOT/"data/derived/experiments/c01_diagnostics_v2"
RECIPE=ROOT/"analysis/c01_diagnostic_recipe_v1.json"
STATE={}


def sources():
    paths=[Path(__file__),ROOT/"analysis/c01_contexts.py",ROOT/"tests/test_c01_diagnostics.py",RECIPE,
           FOUNDATION/"manifest.json",bench.WORK/"plan.json",ROOT/FEATURES,ROOT/TEAMS,ROOT/SEGMENTS,
           ROOT/"data/derived/variants/matchup/features/features_report.json",ROOT/"data/derived/athletes.parquet",
           ROOT/context.CLOCK,ROOT/context.CLOCK_REPORT,ROOT/"models/matchup_2025-12-31.json"]
    paths += [ROOT/f"scripts/{name}.py" for name in ("engine","nodes","matchups","foul_out","late_clock","rotations")]
    paths += [ROOT/p for p in read(bench.WORK/"plan.json")["sources"]]
    paths += [ROOT/"data/models"/context.MODEL/"config.json"]
    cfg=read(paths[-1]);paths += [ROOT/"data/models"/context.MODEL/m["file"] for m in cfg["nodes"].values()]
    paths += [ROOT/f"data/raw/hoopr/play_by_play_{y}.parquet" for y in range(2023,2027)]
    return {str(p.relative_to(ROOT)):sha256_file(p) for p in sorted(set(paths))}


def conversion_fit(players):
    base.assert_training(players)
    w=np.exp2(-(pd.Timestamp(base.CUTOFF)-pd.to_datetime(players.date_et)).dt.days.to_numpy()/180)
    counts=np.column_stack([players.field_goals_made-players.three_point_field_goals_made,
        players.field_goals_attempted-players.three_point_field_goals_attempted,players.three_point_field_goals_made,
        players.three_point_field_goals_attempted,players.free_throws_made,players.free_throws_attempted]).astype(float)
    if (counts<0).any() or (counts[:,::2]>counts[:,1::2]).any():raise ContractError("invalid conversion training truth")
    weighted=counts*w[:,None]
    totals=weighted.sum(0);league=totals[::2]/totals[1::2]
    f=pd.DataFrame(weighted,columns=list("abcdef")).assign(player=players.player.to_numpy()).groupby("player").sum()
    return {"players":{pid:r.tolist() for pid,r in f.iterrows()},"league":league.tolist(),"latest_input":players.date_et.max(),"pseudo_attempts":200}


def opportunity_draws(fit,gid,ids,attempts,origin):
    if fit["latest_input"]>=origin:raise ContractError("future opportunity conversion input")
    attempts=np.asarray(attempts,float)
    if attempts.shape!=(len(ids),3) or not np.isfinite(attempts).all() or (attempts<0).any() or (attempts!=np.floor(attempts)).any():raise ContractError("unsupported realised attempts")
    rng=np.random.default_rng(base.seed("opportunity",gid))
    made=np.zeros((1000,len(ids),3),np.int64)
    for i in sorted(range(len(ids)),key=lambda i:ids[i]):
        counts=fit["players"].get(ids[i],[0.]*6)
        for j in range(3):
            mean=fit["league"][j];a=counts[2*j]+200*mean;b=counts[2*j+1]-counts[2*j]+200*(1-mean)
            p=rng.beta(a,b,1000)
            made[:,i,j]=rng.binomial(int(attempts[i,j]),p)
    return {"pts":2*made[:,:,0]+3*made[:,:,1]+made[:,:,2],"fg3m":made[:,:,1]},made


def prepare():
    if WORK.exists():raise FileExistsError(WORK)
    bench.pinned()
    fingerprint=sources();foundation=read(FOUNDATION/"manifest.json")
    players,_,account=base.load_training()
    fit=conversion_fit(players)
    if fingerprint!=sources():raise ContractError("diagnostic sources changed before freeze")
    WORK.mkdir(parents=True,exist_ok=False)
    create_json(WORK/"conversion.json",fit)
    reused=[]
    previous=ROOT/"data/derived/experiments/c01_diagnostics_v1"
    archive=Path('/Users/moholom/Basketball_archive_ops/20261125_c01_diagnostic_group_guard_v1')
    if previous.exists():
        old=read(previous/"plan.json")
        if old["recipe_sha256"]!=sha256_file(RECIPE) or old["conversion_sha256"]!=sha256_file(WORK/"conversion.json"):raise ContractError("replay reuse recipe/input differs")
        # The correction changes only observed candidate group decoding. Prove
        # that the generation, observer, source and oracle functions are intact.
        for file,names in [("c01_contexts.py",["SourceBoundary","load_engine","make_game","ZoneObserver","stored_schedules"]),
                           ("c01_diagnostics.py",["conversion_fit","opportunity_draws","oracle_game","init_worker","replay_job"])]:
            def definitions(path):
                source=path.read_text();return {n.name:ast.get_source_segment(source,n) for n in ast.parse(source).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
            before=definitions(archive/"analysis"/file);after=definitions(ROOT/"analysis"/file)
            if any(before[name]!=after[name] for name in names):raise ContractError("replay reuse generation code differs")
        (WORK/"games").mkdir()
        for rpath in sorted((previous/"games").glob('*/receipt.json')):
            r=read(rpath)
            if any(sha256_file(rpath.parent/name)!=h for name,h in r["hashes"].items()):raise ContractError("previous replay cache changed")
            (WORK/"games"/r["game_id"]).symlink_to(rpath.parent.resolve(),target_is_directory=True)
            reused.append({"game_id":r["game_id"],"receipt":str(rpath.relative_to(ROOT)),"sha256":sha256_file(rpath)})
    plan={"kind":"C01 fixed diagnostic execution","created_at":datetime.now(timezone.utc).isoformat(),"sources":fingerprint,
          "conversion_sha256":sha256_file(WORK/"conversion.json"),"game_ids":foundation["game_ids"],"wiring_ids":foundation["game_ids"][:20],
          "references":foundation["references"],"recipe_sha256":sha256_file(RECIPE),"training":account,"worlds":1000,
          "reused_replays":reused,"supersedes":"v1 observed-event decoder incorrectly required contiguous candidate rows; no generation/recipe changes",
          "protected_or_reserved_outcomes_opened":False,"production_changed":False}
    create_json(WORK/"plan.json",plan)
    print("Frozen diagnostics, allowed outcomes, 1000-world schedule replay, oracle recipes and source graph",flush=True)


def pinned():
    p=read(WORK/"plan.json")
    if p["sources"]!=sources() or p["conversion_sha256"]!=sha256_file(WORK/"conversion.json"):raise ContractError("diagnostic source signature differs")
    return p


def oracle_game(gid):
    ref=STATE["refs"][gid];b=STATE["box"][gid].copy()
    b["player"]=b.athlete_id.astype("int64").astype(str);b=b.set_index("player")
    on=STATE["on"][gid].set_index("player").sec
    with np.load(bench.WORK/"games"/gid/"samples.npz",allow_pickle=False) as z:
        ids=z["player_ids"].tolist();side=z["side"].copy()
    if any(pid not in on.index or pid not in b.index for pid in ids):raise ContractError("unsupported oracle player")
    actual_minutes=np.array([on[pid]/60 for pid in ids]);fixed=np.broadcast_to(actual_minutes,(1000,len(ids))).copy()
    minute,missing=base.draw_players(STATE["player_fit"],gid,ids,fixed,ref["date_et"])
    attempts=np.array([[b.loc[pid,"field_goals_attempted"]-b.loc[pid,"three_point_field_goals_attempted"],b.loc[pid,"three_point_field_goals_attempted"],b.loc[pid,"free_throws_attempted"]] for pid in ids])
    opportunity,made=opportunity_draws(STATE["conversion"],gid,ids,attempts,ref["date_et"])
    rows=[];common={"game_id":gid,"date_et":ref["date_et"]}
    for model,values in (("realised_minutes",minute),("realised_minutes_and_attempts",opportunity)):
        for i,pid in enumerate(ids):
            for stat in (["pts","reb","ast","fg3m"] if model=="realised_minutes" else ["pts","fg3m"]):
                y=b.loc[pid,{"pts":"points","reb":"rebounds","ast":"assists","fg3m":"three_point_field_goals_made"}[stat]]
                rows.append({**common,"model":model,"entity":"player","stat":stat,"player":pid,"side":("home","away")[side[i]],**metrics.scalar_record(values[stat][:,i],y)})
        teams=np.column_stack([values["pts"][:,side==i].sum(1) for i in (0,1)])
        for i,label in enumerate(("home","away")):
            rows.append({**common,"model":model,"entity":"team","stat":"points","player":"","side":label,
                         **metrics.scalar_record(teams[:,i],ref["official_points"][ref[label]])})
    if (made>attempts[None,:,:]).any():raise ContractError("opportunity makes exceed attempts")
    return rows


def init_worker():
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    plan=read(WORK/"plan.json");refs={r["game_id"]:r for r in plan["references"]}
    e,access=context.load_engine(plan["game_ids"])
    STATE.update(engine=e,refs=refs,access=access,conversion=read(WORK/"conversion.json"),player_fit=read(bench.WORK/"player_fit.json"))
    for key in ("box","on"):
        STATE[key]={gid:f for gid,f in pd.read_parquet(bench.WORK/f"{key}.parquet").groupby("game_id")}
    STATE["pre"]=read_panel(ROOT/FEATURES,plan["game_ids"])
    STATE["teams"]=read_panel(ROOT/TEAMS,plan["game_ids"])


def replay_job(gid):
    started=time.monotonic();ref=STATE["refs"][gid]
    path=WORK/"games"/gid;path.mkdir(parents=True,exist_ok=False)
    g=context.make_game(ref,STATE["pre"],STATE["teams"])
    if sha256_file(ROOT/ref["capture"])!=ref["capture_sha256"]:raise ContractError("stored forecast changed")
    tables,combo,discretisation=context.stored_schedules(ROOT/ref["capture"])
    g.lineup_tables=lambda available,rng,fit_offsets=None:(tables,combo)
    e=STATE["engine"];observer=context.ZoneObserver();e.world_observer=observer
    e.simulate(g,1000,base.seed("schedule-replay",gid))
    st=e.last
    arrays={"points":st.pts.sum(2),"possessions":st.poss.copy(),"zone_attempts":observer.attempts,"zone_makes":observer.makes}
    for stat,key in (("fga","fga"),("fta","fta"),("tov","tov"),("oreb","oreb"),("dreb","dreb"),("pf","pf")):
        arrays[stat]=np.column_stack([st.box[key][:,g.side==side].sum((1,2)) for side in (0,1)])
    with (path/"replay.npz").open("xb") as stream:np.savez_compressed(stream,**arrays)
    oracles=pd.DataFrame(oracle_game(gid));oracles.to_parquet(path/"oracles.parquet",index=False)
    receipt={"game_id":gid,"seconds":time.monotonic()-started,"schedule_discretisation_max_player_minutes":discretisation,
             "generated_scoring_zone_minute_and_legal_state_checks":True,"new_simulation_scope":"Separate event replay on stored simulated schedules; not original incumbent worlds",
             "hashes":{n:sha256_file(path/n) for n in ("replay.npz","oracles.parquet")}}
    create_json(path/"receipt.json",receipt)
    return receipt


def event_analysis(ids):
    chain,datasets,access=context.load_chain(ids);e,model_access=context.load_engine(ids)
    pre=read_panel(ROOT/FEATURES,ids);teams=read_panel(ROOT/TEAMS,ids)
    refs={r["game_id"]:r for r in read(WORK/"plan.json")["references"]}
    all_parity=[];phase=[];sensitivities=[]
    for i,gid in enumerate(ids):
        g=context.make_game(refs[gid],pre,teams)
        s,cols,actor_valid,diff,timing=context.recorded_runtime(e,g,chain)
        all_parity.extend(diff);phase.append({"game_id":gid,**timing})
        sensitivities.extend(lineup_sensitivity(e,g,s,cols,actor_valid,pre,teams))
        if (i+1)%20==0:print(f"Recorded-history parity and swaps {i+1}/{len(ids)}",flush=True)
    rows=[];s=chain.seg.set_index("seg_id")
    actor_valid=chain.seg.actor.notna() & pd.DataFrame({i:chain.seg.actor.eq(chain.seg[f"off_{i}"]) for i in range(1,6)}).any(axis=1)
    valid_by_seg=pd.Series(actor_valid.to_numpy(),index=chain.seg.seg_id)
    for name,d in datasets.items():
        p,brier,uniform,pick=context.predict_node(e,name,d)
        segids=(d["group"] if d["kind"]=="candidate" else d["seg_id"])[pick]
        g=np.asarray(d["game"])[pick]
        strict=valid_by_seg.reindex(segids).to_numpy(bool) if name not in ("event","duration","rebound","rebounder") else np.ones(len(p),bool)
        clocks=s.start_clock.reindex(segids).to_numpy();period=s.period.reindex(segids).to_numpy();zone=s.zone.reindex(segids).fillna("unsupported").to_numpy()
        with np.errstate(divide="ignore"):loss=-np.log(p)
        frame=pd.DataFrame({"game_id":g,"loss":loss,"brier":brier,"uniform":uniform,"supported":strict,"period":np.where(period>4,"OT","regulation"),
                            "clock":np.where(clocks<=4,"<=4",np.where(clocks<=24,"4-24",">24")),"zone":zone})
        frame["duration_crps"]=np.nan;frame["duration_mae"]=np.nan;frame["runtime_phase_loss"]=np.nan
        if name=="duration":
            probs=e.m.boosters[name].predict(d["X"][e.m.nodes[name]["columns"]].to_numpy(np.float32),num_threads=1)
            proper,absolute=context.duration_scores(probs,e.m.bin_secs,s.shot_time.reindex(segids).to_numpy(float))
            frame["duration_crps"],frame["duration_mae"]=proper,absolute
        if "actor_sec_so_far" in e.m.nodes[name]["columns"] and "shot_time" in d["X"] and d["kind"]!="candidate":
            altered={**d,"X":d["X"].copy()}
            altered["X"]["actor_sec_so_far"]+=altered["X"].shot_time
            shifted,_,_,_=context.predict_node(e,name,altered)
            with np.errstate(divide="ignore"):frame["runtime_phase_loss"]=-np.log(shifted)
        for group_field in ("all","period","clock","zone"):
            f=frame.assign(context="all") if group_field=="all" else frame.rename(columns={group_field:"context"})
            for (gid,label),part in f.groupby(["game_id","context"]):
                good=part[part.supported]
                finite=good[np.isfinite(good.loss)]
                rows.append({"game_id":gid,"node":name,"context_field":group_field,"context":str(label),"source_rows":len(part),"rows":len(good),
                    "unsupported":int((~part.supported).sum()),"infinite_losses":int((~np.isfinite(good.loss)).sum()),
                    "finite_loss_sum":float(finite.loss.sum()),"brier_sum":float(good.brier.sum()),"uniform_loss_sum":float(good.uniform.sum()),
                    "duration_crps_sum":float(good.duration_crps.sum()),"duration_mae_sum":float(good.duration_mae.sum()),
                    "runtime_phase_loss_sum":float(good.runtime_phase_loss[np.isfinite(good.runtime_phase_loss)].sum()),
                    "runtime_phase_rows":int(np.isfinite(good.runtime_phase_loss).sum())})
        print(f"Observed-context node {name}: {int(strict.sum())}/{len(strict)} supported events",flush=True)
    return chain,pd.DataFrame(rows),pd.DataFrame(all_parity),pd.DataFrame(phase),pd.DataFrame(sensitivities),access+model_access


def lineup_sensitivity(e,g,s,cols,valid,pre,teams):
    """Prior-only substitutions; offence, actor, history and integration fixed."""
    shots=valid&s.end_type.eq("shot").to_numpy()&s.zone.isin(context.nodes.ZONES).to_numpy()
    chosen=np.flatnonzero(shots)
    if not len(chosen):return []
    # A bounded fixed prefix of recorded shots per side; no outcome-based choice.
    chosen=np.concatenate([np.flatnonzero(shots&s.off_home.eq(home).to_numpy())[:10] for home in (True,False)])
    if not len(chosen):return []
    out=[]
    for home in (True,False):
        idx=chosen[s.iloc[chosen].off_home.to_numpy()==home]
        if not len(idx):continue
        actor=np.array([g.ids.index(pid) for pid in s.iloc[idx].actor]);offside=0 if home else 1
        off5=np.array([[g.ids.index(r[f"off_{j}"]) for j in range(1,6)] for r in s.iloc[idx].to_dict("records")])
        slots=np.argmax(off5==actor[:,None],axis=1)
        defenders=np.flatnonzero(g.side!=offside)
        strength=np.nanmean(np.column_stack([g.P[f"d_fg_{z}"][defenders] for z in ("rim","paint","mid","three")]),axis=1)
        if len(defenders)<5 or not np.isfinite(strength).all():continue
        recorded=np.array([[g.ids.index(r[f"def_{j}"]) for j in range(1,6)] for r in s.iloc[idx].to_dict("records")])
        orders={"strong":np.tile(defenders[np.argsort(strength,kind="stable")[:5]],(len(idx),1)),"weak":np.tile(defenders[np.argsort(-strength,kind="stable")[:5]],(len(idx),1)),"recorded":recorded}
        games={key:g for key in orders};donor_team=None;donor_date=None
        own_team=g.game["home_id" if home else "away_id"];opponent=g.game["away_id" if home else "home_id"]
        candidates=pre[pre.date_et.lt(g.day)&~pre.team.isin([own_team,opponent])]
        for team_id,part in candidates.groupby("team",sort=True):
            latest=part[part.date_et.eq(part.date_et.max())].sort_values("player").drop_duplicates("player")
            style=teams[teams.team.eq(team_id)&teams.date_et.le(latest.date_et.iloc[0])].sort_values("date_et")
            if len(latest)<5 or style.empty:continue
            donor=latest.iloc[:5];gg=copy.copy(g);gg.P={k:v.copy() for k,v in g.P.items()}
            targets=defenders[:5]
            with context.SourceBoundary([str(g.game["game_id"])],"panel").installed():
                body=pd.read_parquet(ROOT/"data/derived/athletes.parquet",columns=["player","height_in","weight_lb"])
            body=body.assign(player=body.player.astype(str)).drop_duplicates("player").set_index("player").reindex(donor.player)
            for col in gg.P:
                if col in donor:gg.P[col][targets]=donor[col].to_numpy(np.float32)
                elif col in ("height_in","weight_lb"):gg.P[col][targets]=body[col].to_numpy(np.float32)
            grp=donor.pos.map(context.nodes.group)
            gg.P["grp_code"][targets]=grp.map({"G":0,"F":1,"C":2}).to_numpy();gg.P["is_big"][targets]=grp.eq("C").to_numpy()
            gg.style={k:dict(v) for k,v in g.style.items()};gg.style[1-offside]={col:float(style.iloc[-1][col]) for col in style if col.startswith(("off_","def_"))}
            orders["opponent_profile"]=np.tile(targets,(len(idx),1));games["opponent_profile"]=gg
            donor_team=str(team_id);donor_date=str(donor.date_et.iloc[0]);break
        cases={}
        for label,five in orders.items():
            gg=games[label];ld=five;mu=e._mu(gg,ld,actor,np.arange(len(idx)),off5,slots)
            # Full context lineup summaries are recomputed with the same state.
            common={k:np.asarray(v)[idx].copy() for k,v in cols.items()}
            for key,(side,src,how) in context.nodes.OPTIONAL_LINEUP.items():
                if side=="def" and key in common:
                    common[key]={"mean":np.nanmean,"min":np.nanmin,"max":np.nanmax,"sum":np.nansum}[how](gg.P[src][five],axis=1).astype(np.float32)
            for key,src,how in [("def_blk_sum","blk_rate",np.nansum),("def_blk_max","blk_rate",np.nanmax),("def_stl_sum","stl_rate",np.nansum),
                                ("def_dreb_sum","dreb_pct",np.nansum),("def_pf_sum","pf_rate",np.nansum),("def_bigs","is_big",np.nansum),("def_min_mean","min_avg",np.nanmean)]:
                common[key]=how(gg.P[src][five],axis=1).astype(np.float32)
            for key in ("pace","three","rim","tov","foul","oreb"):
                common[f"team_d_{key}"]=np.full(len(idx),gg.style[1-offside][f"def_{key}"],np.float32)
            common.update(mu)
            what=e.m.predict("what",common,len(idx))
            expected=np.zeros(len(idx))
            for zi,z in enumerate(context.nodes.ZONES):
                zk="three" if zi>=3 else z
                extra={"zone":np.full(len(idx),zi,np.float32)}
                for prefix in ("mu","mu1","mu2"):
                    if f"{prefix}_fg_{zk}" in mu:extra[f"{prefix}_fg_shot"]=mu[f"{prefix}_fg_{zk}"]
                pl=e.m.predict("location",{**common,**extra},len(idx))*context.nodes.LOCATION_MASK[zi]
                pl=pl/pl.sum(1,keepdims=True)
                conversion=np.zeros(len(idx))
                for band in np.flatnonzero(context.nodes.LOCATION_MASK[zi]):
                    pr=e.m.predict("shot_result",{**common,**extra,"distance":np.full(len(idx),e.m.band_d[band]),"lateral":np.full(len(idx),e.m.band_l[band])},len(idx))
                    conversion+=pl[:,band]*(pr[:,1]+pr[:,2])
                expected+=what[:,zi]*(3 if zi>=3 else 2)*conversion
            cases[label]=expected
        out.append({"game_id":str(g.game["game_id"]),"side":"home" if home else "away","shots":len(idx),"scope":"within-opponent lineup; fixed observed actor/offence/history; expected FG points per action",
                    "strong_expected_fg_points":float(cases["strong"].mean()),"weak_expected_fg_points":float(cases["weak"].mean()),
                    "strong_minus_weak":float((cases["strong"]-cases["weak"]).mean()),"opponent_profile_supported":donor_team is not None,
                    "donor_team":donor_team,"donor_date":donor_date,
                    "opponent_profile_minus_recorded":float((cases["opponent_profile"]-cases["recorded"]).mean()) if donor_team is not None else None})
    return out


def run(phase,jobs):
    plan=pinned();output=WORK/f"{phase}.json"
    if output.exists():raise FileExistsError(output)
    if phase=="development" and not (WORK/"wiring.json").exists():raise ContractError("diagnostic wiring first20 required")
    ids=plan["wiring_ids"] if phase=="wiring" else plan["game_ids"]
    started=time.monotonic();pending=[];done=[]
    for gid in ids:
        p=WORK/"games"/gid
        if (p/"receipt.json").exists():
            r=read(p/"receipt.json")
            if any(sha256_file(p/n)!=h for n,h in r["hashes"].items()):raise ContractError("diagnostic cache changed")
            done.append(r)
        elif p.exists():raise ContractError(f"partial diagnostic game requires inspection: {gid}")
        else:pending.append(gid)
    # Ten workers x one inner thread; parent starts contexts after pool shutdown.
    with ProcessPoolExecutor(max_workers=jobs,initializer=init_worker) as pool:
        for future in as_completed([pool.submit(replay_job,gid) for gid in pending]):
            done.append(future.result())
            if len(done)%5==0:print(f"Zone replay/oracles {len(done)}/{len(ids)}; {time.monotonic()-started:.1f}s",flush=True)
    chain,events,parity,timing,swaps,access=event_analysis(ids)
    for name,frame in (("events",events),("parity",parity),("timing",timing),("swaps",swaps)):
        frame.to_parquet(WORK/f"{phase}_{name}.parquet",index=False)
    report={"kind":"C01 connected diagnostic execution; not production or promotion","phase":phase,"games":len(ids),"game_ids":ids,
            "worlds":1000,"new_generated_worlds":len(pending)*1000,"jobs":jobs,"inner_threads":1,"seconds":time.monotonic()-started,
            "source_signature":sha256_file(WORK/"plan.json"),"source_access":access,"replay_receipts":{r["game_id"]:sha256_file(WORK/"games"/r["game_id"]/"receipt.json") for r in done},
            "artifacts":{n:sha256_file(WORK/f"{phase}_{n}.parquet") for n in ("events","parity","timing","swaps")},
            "production_changed":False,"reserved_or_protected_outcomes_opened":False}
    create_json(output,report)
    print({"phase":phase,"games":len(ids),"seconds":report["seconds"],"parity_mismatches":int(parity.mismatches.sum()),"actor_timing_phase_changes":int(timing.phase_changed_rows.sum())},flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage",choices=("prepare","wiring","development"));parser.add_argument("--jobs",type=int,default=10,choices=range(1,11))
    a=parser.parse_args()
    if any(os.environ.get(k)!="1" for k in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","VECLIB_MAXIMUM_THREADS")):raise ContractError("four inner thread caps must equal1")
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    prepare() if a.stage=="prepare" else run(a.stage,a.jobs)


if __name__=="__main__":main()
