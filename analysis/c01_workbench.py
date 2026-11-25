#!/usr/bin/env python3
"""Versioned C01 orchestration: freeze/verify the truth and comparison boundary.

The freeze stage inventories sources and support; it never fits or scores a model.
Outcome readers are predicate-bound to the known 200-game development panel.
Completed namespaces are immutable. Private source fixtures stay under data/.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
import pyarrow as pa

from analysis.c01_core import ContractError, participation, validate_box, validate_events
from basketball_common import sha256_file

CONTRACT = ROOT / "analysis/c01_contract_v1.json"
WORK = ROOT / "data/derived/experiments/c01_accuracy_workbench_v2"
SEGMENTS = "data/derived/history/2026/segments.parquet"
BOX = "data/raw/hoopr/player_box_2026.parquet"
PLAYS = "data/raw/hoopr/play_by_play_2026.parquet"
ON = "data/derived/history/2026/on_court.parquet"
FEATURES = "data/derived/variants/matchup/features/pregame.parquet"
TEAMS = "data/derived/variants/matchup/features/team_pregame.parquet"
MODEL = "data/models/folds/v1.2d_F4_all/config.json"
BOX_MAP = {"pts": "points", "fgm": "field_goals_made", "fga": "field_goals_attempted",
           "fg3m": "three_point_field_goals_made", "fg3a": "three_point_field_goals_attempted",
           "ftm": "free_throws_made", "fta": "free_throws_attempted", "reb": "rebounds",
           "oreb": "offensive_rebounds", "dreb": "defensive_rebounds"}


def read(path):
    return json.loads(Path(path).read_text())


def create_json(path, value):
    """Exclusive creation also protects evidence from accidental second runs."""
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def historical_panel(contract):
    panel = read(ROOT / contract["panel"]["receipt"])
    ids = panel[contract["panel"]["ids_key"]]
    if len(ids) != 200 or len(set(ids)) != 200 or any(not isinstance(g, str) or not g.isdigit() for g in ids):
        raise ContractError("frozen development panel differs")
    refs = [r for r in panel["receipts"] if r["arm"] == "reference"]
    if len(refs) != 200 or {r["game"] for r in refs} != set(ids):
        raise ContractError("reference population differs")
    return ids, {r["game"]: r for r in refs}


def read_panel(path, ids, columns=None, numeric=False):
    """No generic all-season outcome loader is permitted in this workbench."""
    values = list(map(int, ids)) if numeric else list(ids)
    frame = pd.read_parquet(path, columns=columns, filters=[("game_id", "in", values)])
    frame["game_id"] = frame.game_id.astype("int64").astype(str)
    if not set(frame.game_id).issubset(ids):
        raise ContractError("reader returned an outcome outside frozen development panel")
    return frame


def inventory():
    """Static coverage inventory. No execution or test removal is implied.

    Function/class names are retained so broad family tags cannot hide a missing
    protection. Independence labels describe evidence, not confidence in tests.
    """
    groups = [
        ("truth/causality", ("data_integrity", "court_observed", "retained_lineups", "court_profiles",
                             "dated_", "availability_labels", "availability_report", "prior_roster", "nightly_origin")),
        ("probability/accounting", ("mass", "weight", "mixture", "expected", "compare", "grade", "shooting_accounting",
                                      "branch_persist", "precise_minutes", "minute_cdfs", "slate_lead")),
        ("legal world/state", ("clock", "foul", "rotation", "substitution", "lineup", "rule3", "buzzer", "world_detail")),
        ("research/statistical", ("residual", "shooting", "form_prototype", "signal", "defence", "b2_paths", "penalty")),
        ("delivery/provenance", ("nightly", "live_resume", "queue", "retry", "capture", "output", "bundle", "forecast")),
        ("availability/minutes", ("availability", "minute", "roster", "projection")),
    ]
    modules = []
    for path in sorted((ROOT / "tests").glob("test_*")):
        if path.name.startswith("test_c01_") or path.suffix not in (".py", ".mjs"):
            continue
        source = path.read_text()
        names, imports = [], []
        if path.suffix == ".py":
            tree = ast.parse(source)
            names = [n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test_")]
            imports = sorted({n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module})
        tags = [label for label, needles in groups if any(v in path.stem for v in needles)]
        if path.suffix == ".mjs":
            tags.append("browser/presentation")
        modules.append({"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path),
                        "failure_modes": tags or ["presentation/derived views"], "test_functions": names,
                        "imports": imports, "decision": "retain",
                        "independence": "Synthetic/mocked assertions exercise imported implementation; source independence requires separate fixture review.",
                        "cost": "Node fixture/browser dependency; inspect runner" if path.suffix == ".mjs" else
                                "Python module; input footprint depends on fixtures/imports, runtime not measured here",
                        "replacement": "None retired. New C01 source/time/scorer boundaries complement this protection."})
    smoke = ROOT / "scripts/smoke.py"
    checks = []
    for call in ast.walk(ast.parse(smoke.read_text())):
        if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name) or call.func.id != "check" or not call.args:
            continue
        label = ast.get_source_segment(smoke.read_text(), call.args[0])
        lower = label.lower()
        accuracy = any(v in lower for v in ("baseline", "calibration", "worst"))
        replay = any(v in lower for v in ("re-simulate", "reproduce"))
        checks.append({"line": call.lineno, "label_expression": label,
                       "failure_mode": "historical node receipt assertion" if accuracy else
                                       "deterministic generation" if replay else "stored source/world/delivery accounting",
                       "independence": "Existing recorded result, not a new accuracy evaluation" if accuracy else
                                       "Same generator replay" if replay else "Cross-table identity, shared upstream sources possible",
                       "cost": "Model/generation CPU" if replay else "Retained data I/O/aggregation",
                       "decision": "retain; legacy regression only",
                       "c01_scope": "Excluded from new statistical evidence; baseline smoke required by AGENTS"})
    return {"method": "Static inventory, family classification is conservative and not a claim of independent coverage. Runtime/branch cases make 118 dynamic smoke checks; static call-site count differs.",
            "modules": modules, "smoke": {"path": "scripts/smoke.py", "sha256": sha256_file(smoke), "checks": checks},
            "removed": [], "replace_before_remove": True,
            "gaps": ["Independent common proper-score oracle", "Strict source/clock/ID fixtures including technical scoring and OT",
                     "Uniform cutoff injection across all auxiliaries", "Immutable pre-tip ledger with publication/retrieval proof",
                     "Training/runtime feature parity and connected error diagnosis"],
            "commands": {"fast_c01": ".venv/bin/python -m unittest discover -s tests -p 'test_c01_*.py'",
                         "source_c01": ".venv/bin/python analysis/c01_workbench.py verify",
                         "legacy_integration": ".venv/bin/python scripts/smoke.py",
                         "legacy_browser_release": "node analysis/browser_check.mjs --base http://127.0.0.1:8767",
                         "statistical": "Not implemented at checkpoint 1; never implied by fast/source passes"}}


def finite(value):
    return value is not None and bool(np.isfinite(value))


def checked_reference(descriptor):
    path = ROOT / descriptor["receipt"]
    if sha256_file(path) != descriptor["sha256"]:
        raise ContractError("retained receipt hash changed")
    row = read(path)
    if row["game"] != descriptor["game"] or row["arm"] != "reference":
        raise ContractError("retained reference key differs")
    entry = row["entry"]
    capture = ROOT / entry["capture"]
    if sha256_file(capture) != entry["sha256"]:
        raise ContractError("retained capture hash changed")
    with np.load(capture, allow_pickle=False) as z:
        players = z["player_ids"].tolist()
        sides = z["side"].tolist()
        if str(z["game_id"]) != descriptor["game"] or len(players) != len(set(players)):
            raise ContractError("retained capture IDs differ")
        if len(sides) != len(players) or set(sides) != {0, 1}:
            raise ContractError("retained capture sides differ")
        worlds = len(z["final_period"])
        if worlds != 1000:
            raise ContractError("1000 common worlds required")
        fields = sorted(z.files)
    # No forecast means, losses or ranks are recomputed at freeze.
    r = entry["result"]
    return {"game_id": descriptor["game"], "date_et": r["date_et"], "home": r["home"], "away": r["away"],
            "official_points": {r["home"]: r["real_home"], r["away"]: r["real_away"]},
            "actual_ot": int(r["real_ot"]), "worlds": worlds, "capture": entry["capture"],
            "capture_sha256": entry["sha256"], "receipt": descriptor["receipt"], "receipt_sha256": descriptor["sha256"],
            "captured_player_ids": players, "captured_sides": sides, "capture_fields": fields}


def game_support(ref, seg, box, on, pre, team, plays):
    gid = ref["game_id"]
    parts = [f[f.game_id.eq(gid)].copy() for f in (seg, box, on, pre, team, plays)]
    s, b, o, p, t, raw = parts
    issues = []
    if any(f.empty for f in parts):
        issues.append("missing source table")
    official = ref["official_points"]
    players = []
    for r in b.to_dict("records"):
        if not finite(r["athlete_id"]) or not finite(r["team_id"]):
            issues.append("missing box ID")
            continue
        row = {"game_id": gid, "player": str(int(r["athlete_id"])), "team": str(int(r["team_id"])),
               "minutes": r["minutes"] if finite(r["minutes"]) else None,
               "dnp": bool(r["did_not_play"]) if pd.notna(r["did_not_play"]) else None}
        row.update({key: r[col] for key, col in BOX_MAP.items()})
        players.append(row)
    try:
        validate_box(players, official)
        box_valid = True
    except (ContractError, TypeError, ValueError) as exc:
        issues.append(str(exc))
        box_valid = False
    states = Counter()
    for row in players:
        try:
            states[participation(row["dnp"], row["minutes"], [row[k] for k in BOX_MAP])] += 1
        except ContractError:
            states["conflict"] += 1
    event_rows = []
    for i, r in enumerate(s.to_dict("records")):
        row = {k: r[k] for k in ("game_id", "period", "poss", "offense", "defense", "start_clock", "action_clock", "end_clock", "points")}
        row.update({"event_index": i, "lineup_off": [r[f"off_{j}"] for j in range(1, 6)],
                    "lineup_def": [r[f"def_{j}"] for j in range(1, 6)], "actor": r["actor"] if pd.notna(r["actor"]) else None})
        event_rows.append(row)
    technical = raw[raw.type_text.str.contains("free throw", case=False, na=False) & raw.type_text.str.contains("technical", case=False, na=False)]
    technical_points = {tid: int(technical.loc[technical.team_id.eq(int(tid)), "score_value"].sum()) for tid in official}
    residual = {tid: int(official[tid] - s.loc[s.offense.eq(tid), "points"].sum()) for tid in official}
    try:
        validate_events(event_rows, list(official), int(s.period.max()), official, technical_points)
        event_valid = True
    except (ContractError, TypeError, ValueError) as exc:
        issues.append(str(exc))
        event_valid = False
    ids = set(ref["captured_player_ids"])
    observed = {r["player"] for r in players}
    primary_minutes = set(o.loc[o.sec.notna(), "player"].astype(str))
    try:
        tips = pd.to_datetime(b.game_date_time, utc=True).dropna().unique()
        tip = pd.Timestamp(tips[0]).isoformat() if len(tips) == 1 else None
    except (ValueError, TypeError):
        tip = None
    minutes_by_team = {str(k): float(v / 60) for k, v in o.groupby("team").sec.sum().items()}
    expected_minutes = 240 + 25 * (int(s.period.max()) - 4) if len(s) else None
    minute_errors = {tid: value - expected_minutes for tid, value in minutes_by_team.items()} if expected_minutes else {}
    if any(abs(v) > .05 for v in minute_errors.values()):
        issues.append("reconstructed on-court team minutes differ")
    pbp_points = {tid: int(raw.loc[raw.team_id.eq(int(tid)), "score_value"].sum()) for tid in official}
    if pbp_points != official:
        issues.append("raw PBP scoring differs from official box")
    shots = s[s.end_type.eq("shot")]
    invalid_lineups = sum(len(set(r["lineup_off"])) != 5 or len(set(r["lineup_def"])) != 5 or
                          bool(set(r["lineup_off"]) & set(r["lineup_def"])) for r in event_rows)
    actor_outside = s.actor.notna() & ~pd.DataFrame({j: s.actor.eq(s[f"off_{j}"]) for j in range(1, 6)}).any(axis=1)
    clocks = s[["start_clock", "action_clock", "end_clock"]]
    bad_clocks = (~np.isfinite(clocks).all(axis=1) | s.start_clock.lt(s.action_clock) |
                  s.action_clock.lt(s.end_clock) | s.end_clock.lt(0) |
                  s.start_clock.gt(np.where(s.period.le(4), 720, 300)))
    # Each supported and unsupported input remains explicit for this game's denominator.
    return {"game_id": gid, "date_et": ref["date_et"], "population": "actual_participant", "tip_utc": tip,
            "counts": {"segments": len(s), "shots": len(shots), "box_players": len(players), "captured_players": len(ids),
                       "prior_player_rows": len(p), "prior_team_rows": len(t), "raw_plays": len(raw)},
            "participation": dict(states), "support": {"box_identities": box_valid, "strict_segment_fixture": event_valid,
                "raw_pbp_scoring": pbp_points == official, "on_court_team_minutes_exact_to_0_05": bool(minute_errors) and all(abs(v) <= .05 for v in minute_errors.values()),
                "all_segments_game_ok": bool(len(s)) and bool(s.game_ok.all()),
                "missing_duration": int(s.duration.isna().sum()), "unknown_event_type": int(s.end_type.eq("unknown").sum()),
                "invalid_clock_rows": int(bad_clocks.sum()),
                "actor_outside_offensive_five": int(actor_outside.sum()),
                "actor_outside_by_end_type": {str(k): int(v) for k, v in s.loc[actor_outside].end_type.value_counts().items()},
                "dnp_blank_count_rows": sum(r["dnp"] is True and any(not finite(r[k]) for k in BOX_MAP) for r in players),
                "prior_numeric_missing_by_field": {col: int(p[col].isna().sum()) for col in p.select_dtypes(include="number").columns if p[col].isna().any()},
                "invalid_lineups": invalid_lineups, "missing_shot_coordinates": int(shots[["x", "y"]].isna().any(axis=1).sum()),
                "unsupported_shot_zone": int((~shots.zone.isin(["rim", "paint", "mid", "corner3", "above3"])).sum()),
                "captured_players_missing_box": sorted(ids - observed), "box_players_outside_capture": sorted(observed - ids),
                "captured_players_missing_on_court": sorted(ids - primary_minutes),
                "captured_players_missing_prior": sorted(ids - set(p.player)),
                "prior_dates_match_origin": bool(len(p)) and bool(p.date_et.eq(ref["date_et"]).all()),
                "prior_cutoff_provenance": "Causal prior-feature lineage asserted by retained study; not independently recertified by existence of matching rows.",
                "report_publication_before_tip": False, "report_retrieval_before_tip": False,
                "original_pre_tip": False, "causal_operational_hindcast": False,
                "verified_defender_tracking": False, "explicit_shot_clock": False,
                "simulated_zone_counts": any(k.startswith("zone_") for k in ref["capture_fields"])},
            "source_accounting": {"official_points": official, "raw_pbp_points": pbp_points,
                                  "official_minus_segment_points": residual, "raw_technical_ft_points": technical_points,
                                  "team_minute_errors": minute_errors},
            "exclusions": {"operational_skill": "No original pre-tip report/capture publication and retrieval proof in retained actual-participant study.",
                           "conditional_game": None if box_valid else "Unsupported box identity; fail metric closed pending reconciliation",
                           "event_strict": None if event_valid else "See source_issues; do not silently repair observed state"},
            "source_issues": sorted(set(issues))}


def freeze():
    started = time.monotonic()
    day = datetime.now(ZoneInfo("America/New_York")).strftime("%Y%m%d")
    output = ROOT / f"analysis/experiments/{day}_c01_contract_v2.json"
    if output.exists():
        raise FileExistsError(f"immutable receipt already exists: {output}")
    if WORK.exists():
        raise FileExistsError(f"immutable namespace already exists: {WORK}; use verify")
    contract = read(CONTRACT)
    ids, descriptors = historical_panel(contract)
    inv = inventory()
    paths = [CONTRACT, Path(__file__), ROOT / "analysis/c01_core.py", ROOT / "tests/test_c01_contract.py",
             ROOT / contract["panel"]["receipt"], ROOT / "analysis/experiments/b1_development_v2_reference.json",
             ROOT / "analysis/experiments/20261124_b1_source_audit_v2.json",
             ROOT / "analysis/experiments/20261124_b1_runtime_v2.json",
             *[ROOT / x for x in (SEGMENTS, BOX, PLAYS, ON, FEATURES, TEAMS, MODEL)],
             ROOT / "data/raw/hoopr/manifest.json", ROOT / "models/v1.2d.json", ROOT / "models/v1.3.json"]
    paths += [ROOT / x["path"] for x in inv["modules"]] + [ROOT / "scripts/smoke.py"]
    model = read(ROOT / MODEL)
    paths += [(ROOT / MODEL).parent / n["file"] for n in model["nodes"].values()]
    if model["train_through"] != "2025-12-31":
        raise ContractError("retained model training cutoff differs")
    paths = sorted(set(paths))
    sources = {str(p.relative_to(ROOT)): sha256_file(p) for p in paths}
    # I/O threads only; no fitting, simulation or nested BLAS pools.
    with ThreadPoolExecutor(max_workers=4) as pool:
        refs = list(pool.map(checked_reference, [descriptors[g] for g in ids]))
    print(f"Verified {len(refs)}/200 retained receipt/capture hashes; {time.monotonic()-started:.1f}s", flush=True)
    seg = read_panel(ROOT / SEGMENTS, ids)
    box = read_panel(ROOT / BOX, ids, numeric=True)
    on = read_panel(ROOT / ON, ids)
    pre = read_panel(ROOT / FEATURES, ids)
    teams = read_panel(ROOT / TEAMS, ids)
    plays = read_panel(ROOT / PLAYS, ids, numeric=True,
                       columns=["game_id", "type_text", "score_value", "team_id", "period_number", "id"])
    support = []
    for i, ref in enumerate(refs):
        support.append(game_support(ref, seg, box, on, pre, teams, plays))
        if (i + 1) % 20 == 0:
            print(f"Source support {i+1}/200; no new model scores; {time.monotonic()-started:.1f}s", flush=True)
    if sources != {str(p.relative_to(ROOT)): sha256_file(p) for p in paths}:
        raise ContractError("source changed during freeze")
    WORK.mkdir(parents=True, exist_ok=False)
    fixtures = [ids[0]]
    for key in ("actual_ot",):
        hit = next((r["game_id"] for r in refs if r[key]), None)
        if hit and hit not in fixtures:
            fixtures.append(hit)
    hit = next((r["game_id"] for r in support if sum(r["source_accounting"]["raw_technical_ft_points"].values())), None)
    if hit and hit not in fixtures:
        fixtures.append(hit)
    files = {}
    for label, frame in (("segments", seg), ("box", box), ("on_court", on), ("plays", plays)):
        path = WORK / f"fixture_{label}.parquet"
        frame[frame.game_id.isin(fixtures)].to_parquet(path, index=False)
        files[str(path.relative_to(ROOT))] = sha256_file(path)
    manifest = {"kind": "C01 checkpoint 1; truth/support and prospective comparison contract",
                "created_at": datetime.now(timezone.utc).isoformat(), "contract_sha256": sha256_file(CONTRACT),
                "game_ids": ids, "game_ids_sha256": digest(ids), "wiring_ids": ids[:20],
                "sources": sources, "references": refs, "games": support, "fixture_game_ids": fixtures,
                "fixture_hashes": files, "test_inventory": inv,
                "exposure": {"development": "Previously explored B1/C2/C3 panel; no fresh evidence",
                             "F1_F3": "Previously exposed historical folds; metadata inventory only, not fresh confirmation",
                             "reserved_confirmation_outcomes_opened": False, "protected_outcomes_opened": False,
                             "new_baseline_or_incumbent_scores": False, "training_launched": False}}
    create_json(WORK / "manifest.json", manifest)
    summary = {"kind": manifest["kind"], "created_at": manifest["created_at"],
               "contract": str(CONTRACT.relative_to(ROOT)), "contract_sha256": manifest["contract_sha256"],
               "manifest": str((WORK / "manifest.json").relative_to(ROOT)), "manifest_sha256": sha256_file(WORK / "manifest.json"),
               "games": len(ids), "game_ids_sha256": manifest["game_ids_sha256"], "wiring_games": 20,
               "retained_worlds_per_game": 1000, "retained_references_verified": len(refs),
               "conditional_box_supported_games": sum(r["support"]["box_identities"] for r in support),
               "strict_event_supported_games": sum(r["support"]["strict_segment_fixture"] for r in support),
               "operational_supported_games": 0,
               "source_issue_counts": dict(Counter(k for r in support for k in r["source_issues"])),
               "actor_outside_offensive_five_events": sum(r["support"]["actor_outside_offensive_five"] for r in support),
               "source_segments": sum(r["counts"]["segments"] for r in support),
               "dnp_blank_count_rows": sum(r["support"]["dnp_blank_count_rows"] for r in support),
               "unsupported_capture_fields": ["per-zone simulated attempts/makes", "explicit 24/14-second shot clock", "verified defender positions"],
               "test_modules_inventoried": len(inv["modules"]), "static_smoke_call_sites": len(inv["smoke"]["checks"]),
               "tests_retired": 0, "fixture_games": len(fixtures), "exposure": manifest["exposure"],
               "production_changed": False, "compute": {"io_threads": 4, "arrow_threads": 1, "fitting_or_simulation": False},
               "supersedes": {"receipt": "analysis/experiments/20261125_c01_contract_v1.json",
                              "reason": "First adapter counted explicit DNP blank statistics as unknown game truth. Correct DNP interpretation and add row-level actor/clock/missingness support. No model scores or recipe changes.",
                              "preserved_sources": "/Users/moholom/Basketball_archive_ops/20261125_c01_initial_adapter_v1/manifest.json"},
               "seconds": time.monotonic() - started}
    create_json(output, summary)
    create_json(WORK / "checkpoint1.json", {"receipt": str(output.relative_to(ROOT)), "sha256": sha256_file(output)})
    print(json.dumps(summary, indent=2), flush=True)


def verify():
    """Independent re-read of the pinned support inputs; no model scoring."""
    m = read(WORK / "manifest.json")
    if m["contract_sha256"] != sha256_file(CONTRACT) or digest(m["game_ids"]) != m["game_ids_sha256"]:
        raise ContractError("contract/panel changed")
    for path, expected in {**m["sources"], **m["fixture_hashes"]}.items():
        if sha256_file(ROOT / path) != expected:
            raise ContractError(f"pinned source changed: {path}")
    for ref in m["references"]:
        for path_key, hash_key in (("receipt", "receipt_sha256"), ("capture", "capture_sha256")):
            if sha256_file(ROOT / ref[path_key]) != ref[hash_key]:
                raise ContractError(f"retained {path_key} changed")
    cp = read(WORK / "checkpoint1.json")
    receipt = ROOT / cp["receipt"]
    if sha256_file(receipt) != cp["sha256"] or read(receipt)["manifest_sha256"] != sha256_file(WORK / "manifest.json"):
        raise ContractError("checkpoint/manifest receipt changed")
    verify_fixture_truth(m)
    print(f"Verified immutable contract, {len(m['game_ids'])} support records, all retained references and private fixtures; no model scores.")


def verify_fixture_truth(manifest):
    """Direct source arithmetic independent of the normalised-box/event helpers."""
    frames = {k: pd.read_parquet(WORK / f"fixture_{k}.parquet") for k in ("box", "segments", "on_court", "plays")}
    refs = {r["game_id"]: r for r in manifest["references"]}
    for gid in manifest["fixture_game_ids"]:
        b, s, on, raw = [frames[k][frames[k].game_id.eq(gid)] for k in ("box", "segments", "on_court", "plays")]
        played = b[b.did_not_play.eq(False)]
        if played[list(BOX_MAP.values())].isna().any().any():
            raise ContractError("private fixture has unsupported played box counts")
        official = refs[gid]["official_points"]
        # Each side is checked against the independently retained official total.
        for tid, points in official.items():
            side = played[played.team_id.eq(int(tid))]
            pts = float(side.points.sum())
            made = float((2 * side.field_goals_made + side.three_point_field_goals_made + side.free_throws_made).sum())
            if pts != points or made != points:
                raise ContractError("private fixture official scoring identity")
            pbp_points = raw.loc[raw.team_id.eq(int(tid)), "score_value"].sum()
            if pbp_points != points:
                raise ContractError("private fixture raw PBP score")
            technical = raw.type_text.str.contains("free throw.*technical", case=False, na=False) & raw.team_id.eq(int(tid))
            missing = points - s.loc[s.offense.eq(tid), "points"].sum()
            if missing != raw.loc[technical, "score_value"].sum():
                raise ContractError("private fixture non-segment technical points")
        final = int(s.period.max())
        for period, rows in s.groupby("period"):
            seconds = (rows.start_clock - rows.end_clock).sum()
            if abs(seconds - (720 if period <= 4 else 300)) > .05:
                raise ContractError("private fixture period clock sum")
        for tid, seconds in on.groupby("team").sec.sum().items():
            if tid not in official or abs(seconds / 60 - (240 + 25 * (final - 4))) > .05:
                raise ContractError("private fixture on-court minutes")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("freeze", "verify"))
    args = parser.parse_args()
    for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
        if os.environ.get(key) != "1":
            raise ContractError(f"set {key}=1 before importing/running the workbench")
    pa.set_cpu_count(1)
    pa.set_io_thread_count(1)
    freeze() if args.stage == "freeze" else verify()


if __name__ == "__main__":
    main()
