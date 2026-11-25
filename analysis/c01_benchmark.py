#!/usr/bin/env python3
"""C01 fixed-panel benchmark: prepare, wiring, development, verify. No live hooks."""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
import pyarrow as pa

from basketball_common import sha256_file
from analysis import c01_baselines as base, c01_metrics as metrics
from analysis.c01_core import ContractError
from analysis.c01_workbench import WORK as FOUNDATION, CONTRACT, read, create_json, read_panel, BOX, ON, FEATURES, TEAMS

WORK = ROOT / "data/derived/experiments/c01_benchmark_v1"
STATE = {}


def sources():
    paths = base.training_sources() + [Path(__file__), ROOT/"analysis/c01_baselines.py", ROOT/"analysis/c01_metrics.py",
        ROOT/"analysis/c01_core.py", ROOT/"analysis/c01_workbench.py", ROOT/"tests/test_c01_benchmark.py",
        CONTRACT, FOUNDATION/"manifest.json", *[ROOT/p for p in (BOX, ON, FEATURES, TEAMS)]]
    return {str(p.relative_to(ROOT)): sha256_file(p) for p in sorted(set(paths))}


def arrays_digest(arrays):
    h = hashlib.sha256()
    for key in sorted(arrays):
        a = np.ascontiguousarray(arrays[key])
        h.update(key.encode()); h.update(str(a.dtype).encode()); h.update(str(a.shape).encode()); h.update(a.tobytes())
    return h.hexdigest()


def prepare():
    if WORK.exists():
        raise FileExistsError("immutable benchmark namespace exists; use wiring/development/verify")
    foundation = read(FOUNDATION/"manifest.json")
    fingerprint = sources()
    started = time.monotonic()
    players, games, accounting = base.load_training()
    player = base.player_fit(players)
    features, state = base.team_features(games)
    team = base.team_fit(features, state)
    ids = foundation["game_ids"]
    box = read_panel(ROOT/BOX, ids, numeric=True)
    on = read_panel(ROOT/ON, ids)
    priors = read_panel(ROOT/FEATURES, ids, columns=["game_id","player","team","date_et","usage","start_share","min_avg"])
    teams = read_panel(ROOT/TEAMS, ids)
    if fingerprint != sources():
        raise ContractError("benchmark source changed during preparation")
    WORK.mkdir(parents=True, exist_ok=False)
    create_json(WORK/"player_fit.json", player)
    create_json(WORK/"team_fit.json", team)
    tables = {"training_features.parquet": features, "box.parquet": box, "on.parquet": on, "priors.parquet": priors, "teams.parquet": teams}
    for name, frame in tables.items():
        frame.to_parquet(WORK/name, index=False)
    artifacts = {name: sha256_file(WORK/name) for name in ["player_fit.json","team_fit.json",*tables]}
    plan = {"kind":"C01 frozen common benchmark, development only", "created_at":datetime.now(timezone.utc).isoformat(),
        "sources":fingerprint,"artifacts":artifacts,"game_ids":ids,"wiring_ids":ids[:20],"contract_sha256":sha256_file(CONTRACT),
        "training":accounting,"team_feature_rows":len(features),"residual_games":len(team["residuals"]),
        "references":foundation["references"], "worlds":1000,"seconds":time.monotonic()-started,
        "population":"actual_participant", "baseline_age_limitation":read(CONTRACT)["baselines"]["selection"],
        "protected_or_reserved_outcomes_opened":False,"production_changed":False}
    create_json(WORK/"plan.json", plan)
    print({k: plan[k] for k in ("training","team_feature_rows","residual_games","seconds")},flush=True)


def pinned():
    plan = read(WORK/"plan.json")
    if plan["sources"] != sources():
        raise ContractError("benchmark code/source signature differs")
    for name, expected in plan["artifacts"].items():
        if sha256_file(WORK/name) != expected:
            raise ContractError(f"benchmark prepared artifact changed: {name}")
    return plan


def init():
    pa.set_cpu_count(1); pa.set_io_thread_count(1)
    plan = read(WORK/"plan.json")
    STATE.update(plan=plan, refs={r["game_id"]:r for r in plan["references"]}, player_fit=read(WORK/"player_fit.json"), team_fit=read(WORK/"team_fit.json"))
    for k in ("box","on","priors","teams"):
        STATE[k] = {gid:part for gid,part in pd.read_parquet(WORK/f"{k}.parquet").groupby("game_id")}


def compute(gid):
    ref = STATE["refs"][gid]
    if sha256_file(ROOT/ref["capture"]) != ref["capture_sha256"]:
        raise ContractError("retained worlds changed")
    with np.load(ROOT/ref["capture"], allow_pickle=False) as z:
        ids, side = z["player_ids"].tolist(), z["side"].copy()
        incumbent = {stat:z[key].sum(2) for stat,key in [("min","minutes"),("pts","player_points"),("ast","player_ast"),("fg3m","player_fg3m")]}
        incumbent["reb"] = (z["player_oreb"]+z["player_dreb"]).sum(2)
        team_points = z["team_points"].sum(2)
        for s in (0,1):
            if not np.array_equal(incumbent["pts"][:,side==s].sum(1),team_points[:,s]):
                raise ContractError("incumbent player/team identity")
            expected = 240+25*(z["final_period"]-4)
            if np.max(np.abs(incumbent["min"][:,side==s].sum(1)-expected))>1e-8:
                raise ContractError("incumbent team minute identity")
    rate, unknown = base.draw_players(STATE["player_fit"],gid,ids,incumbent["min"],ref["date_et"])
    rate_teams = np.column_stack([rate["pts"][:,side==s].sum(1) for s in (0,1)])
    t = STATE["teams"][gid]
    rest = {r.team:float(r.rest_days) for r in t.itertuples()}
    team, prior = base.draw_teams(STATE["team_fit"],gid,ref["home"],ref["away"],ref["date_et"],rest)
    arrays = {"player_ids":np.array(ids),"side":side,"incumbent_team":team_points,"player_rate_team":rate_teams,"team_strength_team":team}
    for model, stats in (("incumbent",incumbent),("player_rate",rate)):
        for stat in ("min","pts","reb","ast","fg3m"):
            arrays[f"{model}_{stat}"] = stats[stat]
    box = STATE["box"][gid].copy()
    box["player"] = box.athlete_id.astype("int64").astype(str)
    box = box.set_index("player",verify_integrity=True)
    on = STATE["on"][gid].set_index("player",verify_integrity=True).sec
    priors = STATE["priors"][gid].set_index("player",verify_integrity=True)
    rows, joints = [], []
    actual = np.array([ref["official_points"][ref[s]] for s in ("home","away")],float)
    common = {"game_id":gid,"date_et":ref["date_et"],"month":ref["date_et"][:7],"population":"actual_participant"}
    for model in ("incumbent","player_rate","team_strength"):
        values = arrays[f"{model}_team"]
        for entity, stat, player, label, x, y in [("team","points","","home",values[:,0],actual[0]),
                ("team","points","","away",values[:,1],actual[1]),("game","total","","both",values.sum(1),actual.sum()),
                ("game","margin","","both",values[:,0]-values[:,1],actual[0]-actual[1])]:
            rg = "both" if label=="both" else "1" if rest[ref[label]]==1 else "2+"
            rows.append({**common,"model":model,"entity":entity,"stat":stat,"player":player,"side":label,"role":"all","minute_band":"all","rest_group":rg,**metrics.scalar_record(x,y)})
        joints.append({**common,"model":model,**metrics.joint_record(values,actual)})
        if model=="team_strength":
            continue
        for i,pid in enumerate(ids):
            p = priors.loc[pid] if pid in priors.index else None
            role = "unknown" if p is None or not np.isfinite([p.usage,p.start_share]).all() else "star" if p.usage>=.25 else "starter" if p.start_share>=.5 else "bench"
            band = "unknown" if p is None or not np.isfinite(p.min_avg) else "<12" if p.min_avg<12 else "12-24" if p.min_avg<24 else "24+"
            label = ("home","away")[side[i]]
            b = box.loc[pid] if pid in box.index else None
            ys = {"min":float(on[pid])/60 if pid in on.index else None,
                  **{stat:float(b[col]) if b is not None and pd.notna(b[col]) else None for stat,col in [("pts","points"),("reb","rebounds"),("ast","assists"),("fg3m","three_point_field_goals_made")]}}
            for stat,y in ys.items():
                rows.append({**common,"model":model,"entity":"player","stat":stat,"player":pid,"side":label,"role":role,"minute_band":band,
                    "rest_group":"1" if rest[ref[label]]==1 else "2+",**metrics.scalar_record(arrays[f"{model}_{stat}"][:,i],y)})
    return arrays, rows, joints, {"missing_player_histories":unknown,"team_prior":prior}


def job(gid):
    folder = WORK/"games"/gid
    folder.mkdir(parents=True,exist_ok=False)
    started = time.monotonic()
    arrays, rows, joints, support = compute(gid)
    with (folder/"samples.npz").open("xb") as stream:
        np.savez_compressed(stream,**arrays)
    pd.DataFrame(rows).to_parquet(folder/"scores.parquet",index=False)
    pd.DataFrame(joints).to_parquet(folder/"joint.parquet",index=False)
    receipt = {"game_id":gid,"digest":arrays_digest(arrays),"support":support,"seconds":time.monotonic()-started,
               "hashes":{name:sha256_file(folder/name) for name in ("samples.npz","scores.parquet","joint.parquet")}}
    create_json(folder/"receipt.json",receipt)
    return receipt


def verified_game(gid):
    folder = WORK/"games"/gid
    r = read(folder/"receipt.json")
    if r["game_id"]!=gid or any(sha256_file(folder/name)!=expected for name,expected in r["hashes"].items()):
        raise ContractError("cached benchmark game changed")
    return r


def run(phase,jobs):
    plan = pinned()
    output = WORK/f"{phase}.json"
    if output.exists():
        raise FileExistsError(output)
    if phase=="development" and not (WORK/"wiring.json").exists():
        raise ContractError("complete first20 wiring before development")
    ids = plan["wiring_ids"] if phase=="wiring" else plan["game_ids"]
    pending,done = [],[]
    for gid in ids:
        folder=WORK/"games"/gid
        if (folder/"receipt.json").exists():done.append(verified_game(gid))
        elif folder.exists():raise ContractError(f"partial game requires inspection, never overwrite: {gid}")
        else:pending.append(gid)
    started=time.monotonic()
    with ProcessPoolExecutor(max_workers=jobs,initializer=init) as pool:
        for future in as_completed([pool.submit(job,gid) for gid in pending]):
            done.append(future.result())
            if len(done)%10==0 or len(done)==len(ids):
                print(f"{phase}: {len(done)}/{len(ids)} cached games; {time.monotonic()-started:.1f}s",flush=True)
    # Pool is shut down before parent bootstrap work (one BLAS thread).
    scores=pd.concat([pd.read_parquet(WORK/"games"/gid/"scores.parquet") for gid in ids],ignore_index=True)
    joints=pd.concat([pd.read_parquet(WORK/"games"/gid/"joint.parquet") for gid in ids],ignore_index=True)
    print(f"{phase}: scoring complete; computing paired game/calendar-block uncertainty",flush=True)
    summary=metrics.summarise(scores,joints)
    report={"kind":"C01 common development benchmark, not promotion","phase":phase,"game_ids":ids,"summary":summary,
        "games":len(ids),"worlds":1000,"player_rows_per_model":int((scores.model.eq("incumbent")&scores.entity.eq("player")).sum()),
        "source_signature":sha256_file(WORK/"plan.json"),"receipts":{r["game_id"]:sha256_file(WORK/"games"/r["game_id"]/"receipt.json") for r in done},
        "population":"actual_participant","production_changed":False,"reserved_or_protected_outcomes_opened":False,
        "baseline_age_limitation":plan["baseline_age_limitation"],"jobs":jobs,"inner_threads":1,"seconds":time.monotonic()-started}
    create_json(output,report)
    scores.to_parquet(WORK/f"{phase}_scores.parquet",index=False)
    joints.to_parquet(WORK/f"{phase}_joint.parquet",index=False)
    print({"phase":phase,"games":len(ids),"seconds":report["seconds"],"models":{k:{s:v["pooled"]["crps"] for s,v in p.items() if s!="joint"} for k,p in summary["models"].items()}},flush=True)


def verify():
    plan=pinned();report=read(WORK/"development.json")
    checked=0
    for gid in plan["game_ids"]:
        r=verified_game(gid)
        if report["receipts"][gid]!=sha256_file(WORK/"games"/gid/"receipt.json"):
            raise ContractError("benchmark report receipt changed")
        with np.load(WORK/"games"/gid/"samples.npz",allow_pickle=False) as z:
            arrays={k:z[k] for k in z.files}
        if arrays_digest(arrays)!=r["digest"]:raise ContractError("cached array digest differs")
        frame=pd.read_parquet(WORK/"games"/gid/"scores.parquet")
        ids=arrays["player_ids"].tolist()
        for row in frame.itertuples():
            if not row.supported:continue
            if row.entity=="player":x=arrays[f"{row.model}_{row.stat}"][:,ids.index(row.player)]
            else:
                team=arrays[f"{row.model}_team"]
                x=team[:,0 if row.side=="home" else 1] if row.entity=="team" else team.sum(1) if row.stat=="total" else team[:,0]-team[:,1]
            if abs(metrics.crps(x,row.truth)-row.crps)>1e-10:raise ContractError("independent common CRPS disagrees")
            checked+=1
    init()
    gid=plan["wiring_ids"][0]
    expected=verified_game(gid)["digest"]
    if arrays_digest(compute(gid)[0])!=expected:raise ContractError("serial repeat differs")
    with ProcessPoolExecutor(max_workers=2,initializer=init) as pool:
        results=list(pool.map(compute,[gid,gid]))
    if any(arrays_digest(r[0])!=expected for r in results):raise ContractError("worker/order repeat differs")
    receipt={"kind":"C01 independent score and deterministic worker/resume check","games":200,"score_rows_checked":checked,
        "serial_and_two_workers_identical":True,"cached_resume_hashes_verified":True,"source_signature":sha256_file(WORK/"plan.json")}
    create_json(WORK/"verification.json",receipt)
    print(receipt,flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage",choices=("prepare","wiring","development","verify"))
    parser.add_argument("--jobs",type=int,default=10,choices=range(1,11))
    args=parser.parse_args()
    if any(os.environ.get(k)!="1" for k in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","VECLIB_MAXIMUM_THREADS")):
        raise ContractError("all four inner thread caps must be 1")
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    if args.stage=="prepare":prepare()
    elif args.stage=="verify":verify()
    else:run(args.stage,args.jobs)


if __name__=="__main__":main()
