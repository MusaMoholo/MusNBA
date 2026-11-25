"""Fresh repeat of C01 fits, baseline samples, oracle/event scores and conclusions.

Original incumbent worlds and zone-replay arrays are pinned INPUTS, not newly
generated worlds. Nothing is collected, published or changed in production.
"""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor,as_completed
import json
from pathlib import Path
import shutil
import time
from unittest.mock import patch

import numpy as np
import pandas as pd
import pyarrow as pa

from analysis import c01_baselines as base,c01_benchmark as bench,c01_diagnostics as diag,c01_localise as local,c01_metrics as metrics
from analysis.c01_core import ContractError
from analysis.c01_workbench import ROOT,read,create_json,read_panel,BOX,ON,FEATURES,TEAMS
from basketball_common import sha256_file


def compare_numeric(a,b,tolerance=1e-10):
    """Same shape, keys, missingness and text; bounded floating reduction noise."""
    if isinstance(a,dict) and isinstance(b,dict):
        if set(a)!=set(b):raise ContractError("reproduction summary keys differ")
        return max((compare_numeric(a[k],b[k],tolerance) for k in a),default=0.)
    if isinstance(a,list) and isinstance(b,list):
        if len(a)!=len(b):raise ContractError("reproduction summary support differs")
        return max((compare_numeric(x,y,tolerance) for x,y in zip(a,b)),default=0.)
    if isinstance(a,bool) or isinstance(b,bool):
        if type(a) is not type(b) or a!=b:raise ContractError("reproduction Boolean semantics differ")
        return 0.
    if isinstance(a,(int,float)) and isinstance(b,(int,float)):
        delta=abs(a-b)
        if delta>tolerance:raise ContractError(f"reproduction summary differs by {delta}")
        return float(delta)
    if a!=b:raise ContractError("reproduction summary value/missingness differs")
    return 0.


def init(player,team,conversion):
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    bench.init()
    ids=bench.STATE["plan"]["game_ids"]
    bench.STATE["player_fit"],bench.STATE["team_fit"]=player,team
    # Re-read truth/profile rows from the predicate-bound original sources,
    # independently of the prepared evaluation tables.
    for key,path,numeric,columns in [("box",BOX,True,None),("on",ON,False,None),("priors",FEATURES,False,["game_id","player","team","date_et","usage","start_share","min_avg"]),("teams",TEAMS,False,None)]:
        f=read_panel(ROOT/path,ids,numeric=numeric,columns=columns)
        bench.STATE[key]={gid:g for gid,g in f.groupby("game_id")}
    diag.STATE.update(refs=bench.STATE["refs"],box=bench.STATE["box"],on=bench.STATE["on"],player_fit=player,conversion=conversion)


def task(gid):
    arrays,rows,joints,_=bench.compute(gid)
    old=bench.verified_game(gid)
    if bench.arrays_digest(arrays)!=old["digest"]:raise ContractError("fresh baseline sample arrays differ")
    oracles=diag.oracle_game(gid)
    cached=pd.read_parquet(diag.WORK/"games"/gid/"oracles.parquet")
    fresh=pd.DataFrame(oracles)
    key=["model","entity","stat","player","side"]
    a,b=cached.set_index(key).sort_index(),fresh.set_index(key).sort_index()
    if not a.index.equals(b.index):raise ContractError("fresh oracle keys differ")
    numeric=["truth","mean","crps","bias","absolute_error","crps_half1","crps_half2"]
    maximum=float(np.max(np.abs(a[numeric].to_numpy()-b[numeric].to_numpy())))
    if maximum>1e-10:raise ContractError("fresh oracle scores differ")
    return gid,rows,joints,oracles,maximum


def check_sources():
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    from analysis.c01_workbench import verify
    verify();p=bench.pinned();q=diag.pinned()
    report=read(diag.WORK/"development.json")
    localisation=read(diag.WORK/"localisation.json")
    if localisation["localiser_sha256"]!=sha256_file(ROOT/"analysis/c01_localise.py"):raise ContractError("localisation source code changed")
    for name,expected in localisation['derived_tables'].items():
        if sha256_file(diag.WORK/name)!=expected:raise ContractError('localisation derived table changed')
    for gid in p["game_ids"]:
        bench.verified_game(gid)
        folder=diag.WORK/"games"/gid;r=read(folder/"receipt.json")
        if sha256_file(folder/"receipt.json")!=report["replay_receipts"][gid] or any(sha256_file(folder/name)!=h for name,h in r["hashes"].items()):raise ContractError("diagnostic receipt/artifact changed")
    for name,h in report["artifacts"].items():
        if sha256_file(diag.WORK/f"development_{name}.parquet")!=h:raise ContractError("recorded-context artifact changed")
    return {"games":200,"source_hashes_verified":True,"scope":"Pinned source/integration check; no fitting, generation or accuracy evaluation"}


def reproduce(output,jobs=10):
    output=Path(output).resolve()
    if output.is_relative_to(ROOT) and not output.is_relative_to(ROOT/"data"):
        raise ContractError("reproduction arrays must stay under ignored data or outside the repository")
    if output.exists():raise FileExistsError("reproduction output must be a new namespace")
    started=time.monotonic();check_sources()
    output.mkdir(parents=True,exist_ok=False)
    players,games,accounting=base.load_training()
    player=base.player_fit(players);features,state=base.team_features(games);team=base.team_fit(features,state);conversion=diag.conversion_fit(players)
    if player!=read(bench.WORK/"player_fit.json") or team!=read(bench.WORK/"team_fit.json") or conversion!=read(diag.WORK/"conversion.json"):
        raise ContractError("independent training fit differs")
    for name,value in (("player_fit.json",player),("team_fit.json",team),("conversion_fit.json",conversion)):
        create_json(output/name,value)
    ids=read(bench.WORK/"plan.json")["game_ids"]
    done={}
    with ProcessPoolExecutor(max_workers=jobs,initializer=init,initargs=(player,team,conversion)) as pool:
        for future in as_completed([pool.submit(task,gid) for gid in ids]):
            result=future.result();done[result[0]]=result
            if len(done)%20==0:print(f"Fresh fit/sample/oracle reproduction {len(done)}/200; {time.monotonic()-started:.1f}s",flush=True)
    scores=pd.DataFrame([row for gid in ids for row in done[gid][1]])
    joints=pd.DataFrame([row for gid in ids for row in done[gid][2]])
    summary=metrics.summarise(scores,joints)
    benchmark_error=compare_numeric(summary,read(bench.WORK/"development.json")["summary"])
    create_json(output/"benchmark_summary.json",summary)
    diagnostic_root=output/"diagnostics";diagnostic_root.mkdir()
    for name in ("plan.json","conversion.json","development.json"):
        shutil.copy2(diag.WORK/name,diagnostic_root/name)
    (diagnostic_root/"games").mkdir()
    for gid in ids:
        folder=diagnostic_root/"games"/gid;folder.mkdir()
        (folder/"replay.npz").symlink_to((diag.WORK/"games"/gid/"replay.npz").resolve())
        pd.DataFrame(done[gid][3]).to_parquet(folder/"oracles.parquet",index=False)
    print("Recomputing all recorded-context predictions, parity and fixed swaps",flush=True)
    chain,events,parity,timing,swaps,access=diag.event_analysis(ids)
    for name,frame in (("events",events),("parity",parity),("timing",timing),("swaps",swaps)):
        old=pd.read_parquet(diag.WORK/f"development_{name}.parquet")
        # Identical row order is part of the recorded-history contract.
        pd.testing.assert_frame_equal(frame,old,check_exact=False,atol=1e-10,rtol=0)
        frame.to_parquet(diagnostic_root/f"development_{name}.parquet",index=False)
    original=read(diag.WORK/"localisation.json")
    with patch.object(diag,"WORK",diagnostic_root):
        local.run()
    reproduced=read(diagnostic_root/"localisation.json")
    # Execution hashes identify the input run; semantic conclusions must agree.
    diagnostic_error=compare_numeric({k:v for k,v in original.items() if k not in ("execution_sha256","derived_tables")},
                                    {k:v for k,v in reproduced.items() if k not in ("execution_sha256","derived_tables")})
    for name in original['derived_tables']:
        pd.testing.assert_frame_equal(pd.read_parquet(diag.WORK/name),pd.read_parquet(diagnostic_root/name),check_exact=True)
    result={"kind":"C01 independent fresh-fit/sample/event/oracle reproduction","games":200,"worlds_per_game":1000,
        "fresh_player_team_and_conversion_fits_identical":True,"all_baseline_sample_arrays_identical":True,
        "max_oracle_score_difference":max(done[gid][4] for gid in ids),"max_benchmark_summary_difference":benchmark_error,
        "max_localisation_summary_difference":diagnostic_error,"all_recorded_context_tables_reproduced":True,
        "retained_incumbent_and_zone_worlds":"Reused, SHA256 verified; no claim of fresh engine generation",
        "training":accounting,"jobs":jobs,"inner_threads":1,"seconds":time.monotonic()-started,"production_changed":False,
        "sources":{"benchmark_plan":sha256_file(bench.WORK/"plan.json"),"diagnostic_plan":sha256_file(diag.WORK/"plan.json"),
                   "localisation":sha256_file(diag.WORK/"localisation.json"),"reproducer":sha256_file(Path(__file__))}}
    create_json(output/"receipt.json",result)
    print(result,flush=True)
    return result
