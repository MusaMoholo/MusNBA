#!/usr/bin/env python3
"""Summarise pinned C01 diagnostics with game/block uncertainty. No fitting candidates."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import pyarrow as pa

from analysis import c01_benchmark as bench,c01_diagnostics as diag,c01_metrics as metrics,c01_contexts as context
from analysis.c01_core import ContractError
from analysis.c01_workbench import read,create_json,read_panel,SEGMENTS,FEATURES,TEAMS,WORK as FOUNDATION
from basketball_common import sha256_file


def create_table(path,frame):
    """Resume an identical table; refuse to replace a completed derived output."""
    path=Path(path)
    if path.exists():
        try:pd.testing.assert_frame_equal(pd.read_parquet(path),frame,check_exact=True)
        except AssertionError as exc:raise ContractError('completed diagnostic table differs; preserve and version it') from exc
        return
    with path.open('xb') as stream:frame.to_parquet(stream,index=False)


def weights(days):
    n=len(days)
    game=np.random.default_rng(20261125).multinomial(n,np.full(n,1/n),size=10000)
    blocks=pd.to_datetime(days).map(lambda t:t.date().toordinal()//7).to_numpy()
    _,codes=np.unique(blocks,return_inverse=True);nb=int(codes.max()+1)
    bw=np.random.default_rng(20261125).multinomial(nb,np.full(nb,1/nb),size=10000)
    return game,bw[:,codes]


def ratio_change(frame,numerator,denominator,other_numerator=None,other_denominator=None,scale=1):
    """Ratio of totals, with both sides/players inside one sampled NBA game."""
    fields=list(dict.fromkeys([numerator,denominator]+([other_numerator,other_denominator] if other_numerator else [])))
    grouped=frame.groupby("game_id",sort=True)[fields].sum()
    days=frame.groupby("game_id").date_et.first().reindex(grouped.index)
    first=grouped[numerator].to_numpy();denom=grouped[denominator].to_numpy()
    if denom.sum()<=0:return {"supported":False,"reason":"zero denominator"}
    estimate=first.sum()/denom.sum()
    if other_numerator:
        other=grouped[other_numerator].to_numpy();odenom=grouped[other_denominator].to_numpy()
        if odenom.sum()<=0:return {"supported":False,"reason":"zero other denominator"}
        estimate-=other.sum()/odenom.sum()
    result={"games":len(grouped),"denominator":float(denom.sum()),"mean":float(scale*estimate),"supported_for_ranking":len(grouped)>=100}
    for label,w in zip(("ci95_game","ci95_calendar_week"),weights(days)):
        valid=(w@denom)>0
        b=(w[valid]@first)/(w[valid]@denom)
        if other_numerator:
            valid_other=(w[valid]@odenom)>0
            b=b[valid_other]-(w[valid][valid_other]@other)/(w[valid][valid_other]@odenom)
        result[label]=np.quantile(scale*b,[.025,.975]).tolist()
    return result


def oracle_summary(ids):
    frames=pd.concat([pd.read_parquet(diag.WORK/"games"/gid/"oracles.parquet") for gid in ids],ignore_index=True)
    reference=pd.concat([pd.read_parquet(bench.WORK/"games"/gid/"scores.parquet") for gid in ids],ignore_index=True)
    result={}
    for model,part in frames.groupby("model"):
        result[model]={}
        for (entity,stat),f in part.groupby(["entity","stat"]):
            report={"crps":float(f.crps.mean()),"absolute_error":float(f.absolute_error.mean()),"bias":float(f.bias.mean()),"games":f.game_id.nunique(),"rows":len(f),"paired":{}}
            for control in ("player_rate","incumbent"):
                r=reference[reference.model.eq(control)&reference.entity.eq(entity)&reference.stat.eq(stat)]
                pair=metrics.paired_frame(r,f)
                report["paired"][control]={"pooled":metrics.bootstrap_change(pair),"equal_game":metrics.bootstrap_change(pair,False)}
            if entity=="player" and stat=="pts":
                keys=["game_id","player","side","entity","stat"]
                metadata=reference[reference.model.eq("player_rate")&reference.entity.eq(entity)&reference.stat.eq(stat)]
                joined=f.merge(metadata[keys+["role","minute_band","month","rest_group"]],on=keys,validate="one_to_one")
                report["contexts"]={}
                for field in ("role","minute_band","month","rest_group","side"):
                    report["contexts"][field]={}
                    for label,g in joined.groupby(field):
                        r=metadata[metadata[field].eq(label)]
                        pair=metrics.paired_frame(r,g)
                        ci=metrics.bootstrap_change(pair);ci["context_support"]=ci["games"]>=30 and len(g)>=200
                        report["contexts"][field][str(label)]=ci
            result[model][entity+"/"+stat]=report
    return result


def node_summary(events):
    result={}
    for (node,field,label),group in events.groupby(["node","context_field","context"]):
        f=group[group.rows.gt(0)].copy()
        if f.empty:continue
        if node=="location":
            # Independent support check: once the shot zone is given, only its
            # distance bands are possible. Uniform over all21 bands is invalid.
            counts=[];sums=[]
            for gid in f.game_id:
                count,value=LOCATION_REFERENCE[(gid,field,label)]
                counts.append(count);sums.append(value)
            if not np.array_equal(f.rows.to_numpy(),counts):raise ContractError("location reference support differs")
            f["uniform_loss_sum"]=sums
        f["date_et"]=f.game_id.map(DATES)
        total=int(f.rows.sum());infinite=int(f.infinite_losses.sum())
        report={"games":f.game_id.nunique(),"rows":total,"unsupported_rows":int(group.unsupported.sum()),"infinite_losses":infinite,
            "log_loss_nats_per_event":None if infinite else float(f.finite_loss_sum.sum()/total),
            "uniform_reference_loss":float(f.uniform_loss_sum.sum()/total),"brier":float(f.brier_sum.sum()/total),
            "support":f.game_id.nunique()>=30 and total>=200}
        if not infinite:
            f["loss_change_sum"]=f.finite_loss_sum-f.uniform_loss_sum
            report["loss_minus_uniform"]=ratio_change(f,"loss_change_sum","rows")
        if node=="duration":
            report["crps_seconds"]=ratio_change(f,"duration_crps_sum","rows")
            report["mae_seconds"]=ratio_change(f,"duration_mae_sum","rows")
        phased=f[f.runtime_phase_rows.gt(0)].copy()
        if len(phased) and not infinite and phased.runtime_phase_rows.equals(phased.rows):
            phased["runtime_minus_training_loss_sum"]=phased.runtime_phase_loss_sum-phased.finite_loss_sum
            report["runtime_elapsed_phase_minus_training_nats"]=ratio_change(phased,"runtime_minus_training_loss_sum","rows")
        result.setdefault(node,{}).setdefault(field,{})[label]=report
    return result


def location_reference(seg):
    """Independent zone-conditional uniform reference on the same source rows."""
    actor=seg.actor.notna()&pd.DataFrame({i:seg.actor.eq(seg[f"off_{i}"]) for i in range(1,6)}).any(axis=1)
    part=seg[actor&seg.end_type.eq("shot")&~seg.heave.fillna(False).astype(bool)&seg.zone.isin(context.nodes.ZONES)&seg[["x","y"]].notna().all(axis=1)].copy()
    counts={z:int(context.nodes.LOCATION_MASK[i].sum()) for i,z in enumerate(context.nodes.ZONES)}
    part["loss"]=part.zone.map(lambda z:np.log(counts[z]));part["timing"]=np.where(part.start_clock<=4,"<=4",np.where(part.start_clock<=24,"4-24",">24"))
    part["period_kind"]=np.where(part.period>4,"OT","regulation")
    result={}
    for field,column in (("all",None),("period","period_kind"),("clock","timing"),("zone","zone")):
        f=part.assign(context="all") if column is None else part.assign(context=part[column])
        for (gid,label),group in f.groupby(["game_id","context"]):result[(gid,field,str(label))]=(len(group),float(group.loss.sum()))
    return result


def regression(frame,actual,predicted):
    f=frame.dropna(subset=["off_rating","opp_def_rating","home_flag","rest",actual,predicted]).copy()
    x=np.column_stack([np.ones(len(f)),f[["off_rating","opp_def_rating","home_flag","rest"]].to_numpy(float)])
    if len(f)<100 or np.linalg.matrix_rank(x)<x.shape[1]:return {"supported":False,"team_games":len(f)}
    y=f[[actual,predicted]].to_numpy(float);coef=np.linalg.lstsq(x,y,rcond=None)[0]
    ids=sorted(f.game_id.unique());n=len(ids);lookup={gid:i for i,gid in enumerate(ids)}
    xx=np.zeros((n,x.shape[1],x.shape[1]));xy=np.zeros((n,x.shape[1],2))
    for i,gid in enumerate(f.game_id):
        k=lookup[gid];xx[k]+=np.outer(x[i],x[i]);xy[k]+=np.outer(x[i],y[i])
    days=f.groupby("game_id").date_et.first().reindex(ids)
    result={"supported":True,"games":n,"team_games":len(f),"observed_opponent_coefficient":float(coef[2,0]),"predicted_opponent_coefficient":float(coef[2,1]),
            "predicted_minus_observed":float(coef[2,1]-coef[2,0]),"association_not_causal":True}
    for label,w in zip(("game","calendar_week"),weights(days)):
        lhs=np.einsum("bi,ijk->bjk",w,xx);rhs=np.einsum("bi,ijk->bjk",w,xy)
        full=np.linalg.matrix_rank(lhs)==x.shape[1]
        b=np.linalg.solve(lhs[full],rhs[full])[:,2,:]
        result["ci95_"+label]={"observed":np.quantile(b[:,0],[.025,.975]).tolist(),"predicted":np.quantile(b[:,1],[.025,.975]).tolist(),
                               "difference":np.quantile(b[:,1]-b[:,0],[.025,.975]).tolist(),"full_rank_bootstraps":int(full.sum())}
    ci=result["ci95_game"]["observed"]
    result["ratio_predicted_over_observed"]=float(coef[2,1]/coef[2,0]) if ci[0]*ci[1]>0 else None
    return result


def component_and_zone_summary(ids):
    source=read(ROOT/"analysis/experiments/20261124_b1_source_audit_v2.json")
    table=next(path for path in source["arrays"] if path.endswith("teams.parquet"))
    if sha256_file(ROOT/table)!=source["arrays"][table]:raise ContractError("retained component audit changed")
    f=pd.read_parquet(ROOT/table)
    if set(f.game_id)!=set(ids):raise ContractError("component panel differs")
    f["date_et"]=f.game_id.map(DATES)
    for col in ("off_rating","opp_def_rating","home_flag","rest"):
        f[col]=0.
    for gid,idx in f.groupby("game_id").groups.items():
        prior=read(bench.WORK/"games"/gid/"receipt.json")["support"]["team_prior"]
        for i in idx:
            home=f.loc[i,"side"]=="home"
            f.loc[i,["off_rating","opp_def_rating","home_flag","rest"]]=[prior["home_off" if home else "away_off"],prior["away_def" if home else "home_def"],float(home),prior["home_rest" if home else "away_rest"]]
    if np.max(np.abs(f.pace_points+f.efficiency_points-(f.sim-f.actual)))>1e-9:raise ContractError("error budget identity")
    mse=float(((f.sim-f.actual)**2).mean());pace=float((f.pace_points**2).mean());eff=float((f.efficiency_points**2).mean());cross=float((2*f.pace_points*f.efficiency_points).mean())
    if abs(mse-pace-eff-cross)>1e-8:raise ContractError("MSE covariance accounting")
    f["actual_points100"]=100*f.actual/f.actual_poss
    f["pred_points100_source_poss"]=100*f.sim/f.actual_poss
    f["pred_points100_own_poss"]=100*f.sim/f.sim_poss
    boxes=pd.read_parquet(bench.WORK/"box.parquet")
    boxes["team"]=boxes.team_id.astype("int64").astype(str)
    actual_dreb=boxes.groupby(["game_id","team"]).defensive_rebounds.sum()
    for gid,idx in f.groupby("game_id").groups.items():
        with np.load(ROOT/REFS[gid]["capture"],allow_pickle=False) as capture:
            for i in idx:
                side=0 if f.loc[i,"side"]=="home" else 1
                f.loc[i,"actual_dreb"]=float(actual_dreb.loc[(gid,f.loc[i,"team"])])
                f.loc[i,"sim_dreb"]=float(capture["player_dreb"][:,capture["side"]==side].sum((1,2)).mean())
    result={"error_budget":{"units":"points squared; signed covariance retained; not causal shares","games":len(ids),"team_games":len(f),"total_mse":mse,"pace_squared":pace,"efficiency_squared":eff,"twice_cross_product":cross},
            "defence_points100_source_possessions":regression(f,"actual_points100","pred_points100_source_poss"),
            "defence_points100_own_possessions":regression(f,"actual_points100","pred_points100_own_poss"),"components":{}}
    for stat in ("fga","fg3a","fta","tov","oreb","dreb","pf"):
        f["a_"+stat]=100*f["actual_"+stat]/f.actual_poss;f["p_"+stat]=100*f["sim_"+stat]/f.sim_poss
        result["components"][stat]={"units":"events per100 possessions","actual":float(f["a_"+stat].mean()),"predicted":float(f["p_"+stat].mean()),
            "opponent_response":regression(f,"a_"+stat,"p_"+stat)}
    seg=read_panel(ROOT/SEGMENTS,ids);shots=seg[seg.end_type.eq("shot")&seg.zone.isin(context.nodes.ZONES)]
    zones=[];replay_scores=[]
    for gid in ids:
        ref=REFS[gid]
        with np.load(diag.WORK/"games"/gid/"replay.npz",allow_pickle=False) as z:
            for side,label in enumerate(("home","away")):
                actual=shots[shots.game_id.eq(gid)&shots.offense.eq(ref[label])]
                total=len(actual);pred_total=float(z["zone_attempts"][:,side].sum(1).mean())
                for zi,zone in enumerate(context.nodes.ZONES):
                    part=actual[actual.zone.eq(zone)]
                    zones.append({"game_id":gid,"date_et":DATES[gid],"side":label,"zone":zone,"actual_attempts":len(part),"actual_makes":int(part.made.eq(True).sum()),
                                  "actual_total":total,"pred_attempts":float(z["zone_attempts"][:,side,zi].mean()),"pred_makes":float(z["zone_makes"][:,side,zi].mean()),"pred_total":pred_total,
                                  **{f'{key}_{half}':float(z[field][sl,side,zi].mean()) for key,field in [('attempts','zone_attempts'),('makes','zone_makes')] for half,sl in [('half1',slice(0,500)),('half2',slice(500,1000))]},
                                  **{f'total_{half}':float(z['zone_attempts'][sl,side].sum(1).mean()) for half,sl in [('half1',slice(0,500)),('half2',slice(500,1000))]}})
                replay_scores.append({"game_id":gid,"date_et":DATES[gid],"entity":"team","stat":"points","player":"","side":label,**metrics.scalar_record(z["points"][:,side],ref["official_points"][ref[label]])})
    zf=pd.DataFrame(zones).merge(f[["game_id","side","off_rating","opp_def_rating","home_flag","rest"]],on=["game_id","side"],validate="many_to_one")
    result["zones"]={}
    for zone,group in zf.groupby("zone"):
        group=group.copy()
        group["actual_share100"]=100*group.actual_attempts/group.actual_total
        group["pred_share100"]=100*group.pred_attempts/group.pred_total
        group["actual_conversion100"]=100*group.actual_makes/group.actual_attempts.replace(0,np.nan)
        group["pred_conversion100"]=100*group.pred_makes/group.pred_attempts.replace(0,np.nan)
        result["zones"][zone]={"games":group.game_id.nunique(),"observed_attempts":int(group.actual_attempts.sum()),
            "observed_zero_attempt_team_games":int(group.actual_attempts.eq(0).sum()),"replay_zero_attempt_team_games":int(group.pred_attempts.eq(0).sum()),
            "attempt_share_change_percentage_points":ratio_change(group,"pred_attempts","pred_total","actual_attempts","actual_total",100),
            "conversion_change_percentage_points":ratio_change(group,"pred_makes","pred_attempts","actual_makes","actual_attempts",100),
            "opponent_response_attempt_share":regression(group,"actual_share100","pred_share100"),
            "opponent_response_conversion":regression(group,"actual_conversion100","pred_conversion100"),
            "simulation_half_sensitivity_percentage_points":{"attempt_share_mean_abs_difference":float((100*group.attempts_half2/group.total_half2-100*group.attempts_half1/group.total_half1).abs().mean()),
                 "conversion_mean_abs_difference":float((100*group.makes_half2/group.attempts_half2.replace(0,np.nan)-100*group.makes_half1/group.attempts_half1.replace(0,np.nan)).abs().mean())},
            "scope":"Source shots versus separate generated replay on stored simulated schedules; not unavailable original incumbent zone counts"}
    replay=pd.DataFrame(replay_scores)
    result["separate_replay_team_score"]={"crps":float(replay.crps.mean()),"scope":"Not the primary incumbent benchmark","simulation_half_difference":metrics.bootstrap_change(replay.assign(change=replay.crps_half2-replay.crps_half1))}
    create_table(diag.WORK/"zone_error_rows.parquet",zf)
    create_table(diag.WORK/"connected_team_rows.parquet",f)
    return result


def event_reliability(ids):
    chain,datasets,_=context.load_chain(ids);e,_=context.load_engine(ids)
    relative_missing={side:{col:int(table[col].isna().sum()) for col in columns} for side,table,columns in (
        ("offence",chain.off,context.engine.OFF_REL),("defence",chain.dfn,context.engine.DEF_REL))}
    actor_ok=chain.seg.actor.notna()&pd.DataFrame({i:chain.seg.actor.eq(chain.seg[f"off_{i}"]) for i in range(1,6)}).any(axis=1)
    valid=pd.Series(actor_ok.to_numpy(),index=chain.seg.seg_id)
    result={}
    for name,d in datasets.items():
        cols=e.m.nodes[name]["columns"]
        raw=e.m.boosters[name].predict(d["X"][cols].to_numpy(np.float32),raw_score=d["kind"]=="candidate",num_threads=1)
        if d["kind"]=="candidate":
            groups=d["group"];p=np.empty(len(raw))
            for gid,part in pd.Series(np.arange(len(raw))).groupby(groups):
                idx=part.to_numpy();p[idx]=context.engine.softmax((raw[idx]/e.m.nodes[name]["temperature"])[None,:])[0]
            truth=d["y"].astype(float);game=d["game"];segs=groups
        else:
            p=np.column_stack([1-raw,raw]) if d["kind"]=="binary" else raw
            if name=="location":p=p*context.nodes.LOCATION_MASK[d["X"].zone.astype(int).to_numpy()];p/=p.sum(1,keepdims=True)
            truth=np.eye(p.shape[1])[d["y"]].ravel();game=np.repeat(d["game"],p.shape[1]);segs=np.repeat(d["seg_id"],p.shape[1]);p=p.ravel()
        eligible=valid.reindex(segs).to_numpy(bool) if name not in ("event","duration","rebound","rebounder") else np.ones(len(p),bool)
        frame=pd.DataFrame({"game_id":np.asarray(game)[eligible],"p":np.asarray(p)[eligible],"truth":np.asarray(truth)[eligible]})
        frame["bin"]=np.minimum((frame.p*5).astype(int),4)
        result[name]={str(b):{"class_predictions":len(part),"games":part.game_id.nunique(),"mean_probability":float(part.p.mean()),"observed_frequency":float(part.truth.mean())} for b,part in frame.groupby("bin")}
    candidate_parity=candidate_feature_parity(e,chain,ids)
    return result,relative_missing,candidate_parity


def start_histories(segments,ids):
    """Independent event-by-event recorded history, without Chain helpers."""
    lookup={pid:i for i,pid in enumerate(ids)}
    current={key:np.zeros(len(ids),float) for key in context.nodes.IN_GAME}
    histories={key:np.empty((len(segments),len(ids)),np.float32) for key in current}
    for i,row in enumerate(segments.to_dict("records")):
        for key in current:histories[key][i]=current[key]
        for side in ("off","def"):
            for j in range(1,6):
                pid=row[f"{side}_{j}"]
                if pid in lookup:current["sec_so_far"][lookup[pid]]+=row["duration"]
        actor=row["actor"]
        if actor in lookup:
            k=lookup[actor];current["uses_so_far"][k]+=1
            current["fga_so_far"][k]+=row["end_type"]=="shot"
            current["made_so_far"][k]+=row["end_type"]=="shot" and row["made"]==True
            current["pts_so_far"][k]+=row["points"]
        for field,counter in (("fouler","pf_so_far"),("assister","ast_so_far")):
            if row[field] in lookup:current[counter][lookup[row[field]]]+=1
    return histories


def candidate_feature_parity(e,chain,ids):
    """Compare every offensive/defensive candidate against independent history."""
    from types import SimpleNamespace
    pre=read_panel(ROOT/FEATURES,ids);teams=read_panel(ROOT/TEAMS,ids)
    totals={};unsupported=0;rows_checked=0
    for gid in ids:
        g=context.make_game(REFS[gid],pre,teams);lookup={pid:i for i,pid in enumerate(g.ids)}
        s=chain.seg[chain.seg.game_id.eq(gid)].copy()
        history=start_histories(s,g.ids)
        known=s[[f'{side}_{j}' for side in ('off','def') for j in range(1,6)]].isin(g.ids).all(axis=1).to_numpy()
        unsupported+=int((~known).sum());s=s[known].copy();rows_checked+=len(s)
        st=SimpleNamespace(period=s.period.to_numpy(),ingame={key:values[known] for key,values in history.items()})
        for side,table,relative in (("off",chain.off,context.engine.OFF_REL),("def",chain.dfn,context.engine.DEF_REL)):
            roster=s[[f'{side}_{j}' for j in range(1,6)]].to_numpy()
            lineup=np.vectorize(lookup.__getitem__)(roster)
            runtime=e._five(g,st,np.arange(len(s)),lineup,relative)
            native=table[table.seg_id.isin(s.seg_id)].set_index(['seg_id','player'])
            index=pd.MultiIndex.from_arrays([np.repeat(s.seg_id.to_numpy(),5),roster.ravel()])
            expected=native.reindex(index)
            for col,values in runtime.items():
                if col not in expected:continue
                a=np.asarray(values).ravel();b=expected[col].to_numpy(float)
                same=np.isclose(a,b,atol=1e-5,rtol=1e-5,equal_nan=True);error=np.abs(a-b);finite=np.isfinite(error)
                key=f'{side}_candidate/{col}'
                r=totals.setdefault(key,{'rows':0,'mismatches':0,'max_abs_error':0.})
                r['rows']+=len(a);r['mismatches']+=int((~same).sum())
                r['max_abs_error']=max(r['max_abs_error'],float(error[finite].max()) if finite.any() else 0.)
    return {'features':totals,'recorded_segments':rows_checked,'unsupported_roster_rows':unsupported,
            'total_mismatches':sum(r['mismatches'] for r in totals.values()),
            'scope':'Candidate features at recorded segment start using an independent raw-event history accumulator; actor-time phase is separate'}


DATES={};REFS={};LOCATION_REFERENCE={}


def run():
    if any(os.environ.get(k)!='1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS')):raise ContractError('four inner thread caps must equal1')
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    plan=diag.pinned();execution=read(diag.WORK/"development.json");ids=plan["game_ids"]
    global DATES,REFS,LOCATION_REFERENCE
    REFS={r["game_id"]:r for r in plan["references"]};DATES={gid:r["date_et"] for gid,r in REFS.items()}
    LOCATION_REFERENCE=location_reference(read_panel(ROOT/SEGMENTS,ids))
    output=diag.WORK/"localisation.json"
    if output.exists():raise FileExistsError(output)
    events=pd.read_parquet(diag.WORK/"development_events.parquet")
    parity=pd.read_parquet(diag.WORK/"development_parity.parquet")
    timing=pd.read_parquet(diag.WORK/"development_timing.parquet")
    swaps=pd.read_parquet(diag.WORK/"development_swaps.parquet")
    print("Localising fixed200 oracle error and observed-context nodes",flush=True)
    oracles=oracle_summary(ids);nodes=node_summary(events)
    print("Localising exact score identities, defence response and shot zones",flush=True)
    components=component_and_zone_summary(ids)
    print("Checking probability calibration on the same supported observed contexts",flush=True)
    reliability,relative_missing,candidate_parity=event_reliability(ids)
    grouped=parity.groupby("feature").agg(rows=("rows","sum"),mismatches=("mismatches","sum"),max_abs_error=("max_abs_error","max"))
    parity_report={name:{k:int(v) if k!="max_abs_error" else float(v) for k,v in row.items()} for name,row in grouped.to_dict("index").items()}
    supported=swaps[swaps.opponent_profile_supported].copy();supported["date_et"]=supported.game_id.map(DATES)
    swaps["date_et"]=swaps.game_id.map(DATES)
    result={"kind":"C01 fixed200 connected localisation, not deployable gains or causal attribution","games":len(ids),
        "oracles":oracles,"observed_context_nodes":nodes,"event_reliability":reliability,"components":components,
        "feature_parity":{"identical_recorded_start_history":parity_report,"total_mismatches":int(parity.mismatches.sum()),
            "independent_candidate_history":candidate_parity,
            "scope":"Shared context, actor, candidate and assignment features; specialised trip/rebound candidate layouts are scored but not all runtime feature transitions certified",
            "actor_phase":{"eligible_rows":int(timing.eligible_actor_rows.sum()),"changed_rows":int(timing.phase_changed_rows.sum()),"mean_elapsed_seconds":float(timing.sum_elapsed_seconds.sum()/timing.eligible_actor_rows.sum()),
                           "explanation":"Actual runtime adds elapsed shot_time before actor selection; Chain start-history features exclude it. This is reported separately from identical-history parity."}},
        "sensitivity":{"within_opponent_lineup":metrics.bootstrap_change(swaps.assign(change=swaps.strong_minus_weak)),
            "opponent_profile":metrics.bootstrap_change(supported.assign(change=supported.opponent_profile_minus_recorded)) if len(supported) else {"supported":False},
            "units":"Expected field-goal points per action with fixed observed offence/actor/history; sensitivity, not accuracy or causal effect"},
        "worlds_per_game":1000,"execution_sha256":sha256_file(diag.WORK/"development.json"),"localiser_sha256":sha256_file(Path(__file__)),
        "diagnostic_reference_accounting":{"location":"Independent uniform reference conditions on known zone and its3-5 distance bands, not all21. Cached candidate probabilities/losses and fixed populations are unchanged; reference support reconciles exactly.",
             "duration":"Raw learned within-bin timing mixture on supported >24-second starts; engine period caps are applied during generation.",
             "actor_support":"Conservative actor-supported subset is also used for some defensive actor nodes; native dataset coverage may be wider. Unsupported counts remain explicit.",
             "relative_profile_missingness":relative_missing,"validation_median_cannot_affect_if_all_zero":not any(n for side in relative_missing.values() for n in side.values())},
        "source_recipe_sha256":sha256_file(diag.RECIPE),"production_changed":False,"protected_or_reserved_outcomes_opened":False}
    result['derived_tables']={name:sha256_file(diag.WORK/name) for name in ('zone_error_rows.parquet','connected_team_rows.parquet')}
    create_json(output,result)
    print({"games":len(ids),"shared_feature_mismatches":result["feature_parity"]["total_mismatches"],"oracles":{m:{k:v["crps"] for k,v in r.items()} for m,r in oracles.items()}},flush=True)


if __name__=="__main__":run()
