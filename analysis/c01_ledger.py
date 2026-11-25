"""Immutable prospective forecast capture, deliberately separate from live serving.

No historical import/backdating. The capture clock is read inside the operation.
Publication/retrieval evidence is required, never inferred from a game date or
file mtime. This tool does not certify the factual content of supplied sources.
"""
from __future__ import annotations

from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re

from analysis.c01_core import ContractError,require_pre_tip,source_id

ROLES=("model","inputs","report","forecast")
PROVIDERS={"ESPN","sportsdataverse","NBA Stats"}
ROOT=Path(__file__).resolve().parents[1]


def utc_now():
    return datetime.now(timezone.utc)


def timestamp(value):
    if not isinstance(value,str):raise ContractError("unknown ledger provenance time")
    try:out=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError as exc:raise ContractError("invalid ledger provenance time") from exc
    if out.tzinfo is None:raise ContractError("ledger times need timezone")
    return out


def fingerprint(payload):
    return hashlib.sha256(payload).hexdigest()


def validate_request(request,captured):
    source_id(request.get("game_id"))
    if not request.get("model_id") or not request.get("runtime_id"):
        raise ContractError("unknown model/runtime identity")
    if request.get("population")!="original_pre_tip":raise ContractError("ledger requires prospective original population")
    if request.get("provider") not in PROVIDERS:raise ContractError("unapproved ledger source provider")
    for role in ROLES:
        value=request.get(role)
        if not isinstance(value,dict) or not value.get("path") or not re.fullmatch(r"[a-f0-9]{64}",value.get("sha256","")):
            raise ContractError(f"missing ledger {role} bytes/provenance")
    report=request["report"]
    if not report.get("publication_evidence") or not report.get("retrieval_evidence"):
        raise ContractError("unknown report publication/retrieval evidence")
    times={"captured":captured.isoformat(),"model_fitted":request["model"].get("fitted_at"),
           "input_as_of":request["inputs"].get("as_of"),"report_published":report.get("published_at"),"report_retrieved":report.get("retrieved_at")}
    require_pre_tip(request.get("tip_utc"),times)
    generated=timestamp(request["forecast"].get("generated_at"))
    retrieved=timestamp(request["inputs"].get("retrieved_at"))
    boundary=timestamp(request["tip_utc"])
    if not (max(timestamp(times[k]) for k in ("model_fitted","input_as_of","report_retrieved"))<=generated<=captured<boundary and retrieved<=generated):
        raise ContractError("forecast/input provenance order or late capture")
    return times


def capture(root,request,entry_id=None):
    """Copy four hash-bound source artifacts into one exclusive sealed entry.

    Required request fields are explicit API inputs; their evidence descriptors
    are retained with the bytes. Unknown/late timing rejects the entire capture.
    Source paths are never modified. An existing entry can never be overwritten.
    """
    root=Path(root).resolve()
    if root.is_relative_to(ROOT) and not root.is_relative_to(ROOT/"data"):
        raise ContractError("ledger artifacts must stay under ignored data or outside the repository")
    captured=utc_now();times=validate_request(request,captured)
    payload={}
    for role in ROLES:
        source=Path(request[role]["path"])
        body=source.read_bytes()
        if fingerprint(body)!=request[role]["sha256"]:raise ContractError(f"changed ledger {role} source")
        payload[role]=body
    # Bind the forecast's own identity/provenance, not just an external label.
    try:forecast=json.loads(payload["forecast"])
    except (ValueError,UnicodeError) as exc:raise ContractError("forecast requires JSON provenance envelope") from exc
    for key,expected in (("game_id",request["game_id"]),("tip_utc",request["tip_utc"]),("model_id",request["model_id"]),("runtime_id",request["runtime_id"]),
                         ("generated_at",request["forecast"]["generated_at"]),("inputs_sha256",request["inputs"]["sha256"]),("report_sha256",request["report"]["sha256"])):
        if forecast.get(key)!=expected:raise ContractError(f"forecast provenance envelope differs: {key}")
    # A slow copy cannot cross tip while retaining an earlier capture timestamp.
    checked=utc_now()
    validate_request(request,checked)
    if checked<captured:raise ContractError("capture clock moved backwards")
    for role in ROLES:
        if fingerprint(Path(request[role]["path"]).read_bytes())!=request[role]["sha256"]:
            raise ContractError(f"ledger {role} source changed during capture")
    if entry_id is None:entry_id=f"{captured.strftime('%Y%m%dT%H%M%S%fZ')}-{request['game_id']}-{request['forecast']['sha256'][:12]}"
    if not isinstance(entry_id,str) or not re.fullmatch(r"[A-Za-z0-9_.-]+",entry_id) or entry_id in (".",".."):
        raise ContractError("invalid ledger entry ID")
    root.mkdir(parents=True,exist_ok=True)
    folder=root/entry_id;folder.mkdir(exist_ok=False)
    for role,body in payload.items():
        path=folder/f"{role}.bin"
        with path.open("xb") as stream:stream.write(body)
        path.chmod(0o444)
    sealed=utc_now()
    validate_request(request,sealed)
    if sealed<captured:raise ContractError("capture clock moved backwards")
    entry={"schema":"c01-prospective-ledger-v1","entry_id":entry_id,"game_id":request["game_id"],"model_id":request["model_id"],
           "runtime_id":request["runtime_id"],"population":"original_pre_tip","tip_utc":request["tip_utc"],"captured_at":captured.isoformat(),
           "sealed_at":sealed.isoformat(),"provenance":request,"files":{role:{"file":f"{role}.bin","sha256":fingerprint(payload[role]),"bytes":len(payload[role])} for role in ROLES}}
    body=(json.dumps(entry,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
    with (folder/"entry.json").open("xb") as stream:stream.write(body)
    with (folder/"entry.sha256").open("x") as stream:stream.write(fingerprint(body)+"\n")
    (folder/"entry.json").chmod(0o444);(folder/"entry.sha256").chmod(0o444)
    return entry


def audit(root):
    """Read-only audit; partial or changed entries never masquerade as captures."""
    root=Path(root)
    entries=[]
    if not root.exists():return {"entries":0,"game_ids":[],"partial_entries":[],"scope":"No certified captures yet"}
    partial=[]
    for folder in sorted(root.iterdir()):
        if not folder.is_dir():raise ContractError("unexpected file at ledger root")
        if not (folder/"entry.json").exists() or not (folder/"entry.sha256").exists():
            partial.append(folder.name);continue
        body=(folder/"entry.json").read_bytes()
        if fingerprint(body)!=(folder/"entry.sha256").read_text().strip():raise ContractError("ledger manifest changed")
        entry=json.loads(body)
        if entry["entry_id"]!=folder.name:raise ContractError("ledger entry identity changed")
        if timestamp(entry["sealed_at"])<timestamp(entry["captured_at"]):raise ContractError("ledger capture clock order")
        validate_request(entry["provenance"],timestamp(entry["captured_at"]))
        validate_request(entry["provenance"],timestamp(entry["sealed_at"]))
        for role in ROLES:
            descriptor=entry["files"][role]
            if descriptor["file"]!=f"{role}.bin":raise ContractError("invalid ledger artifact name")
            data=(folder/descriptor["file"]).read_bytes()
            if fingerprint(data)!=descriptor["sha256"] or len(data)!=descriptor["bytes"]:raise ContractError("ledger artifact changed")
            if descriptor["sha256"]!=entry["provenance"][role]["sha256"]:raise ContractError("ledger artifact/provenance differs")
        entries.append(entry)
    return {"entries":len(entries),"game_ids":sorted({e["game_id"] for e in entries}),"partial_entries":partial,
            "scope":"Original pre-tip captures with retained supplied publication/retrieval evidence; no historical backfill"}
