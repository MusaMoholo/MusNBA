#!/usr/bin/env python3
"""Actual-clock CLI integration on explicitly SYNTHETIC ledger artifacts only."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime,timedelta,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from analysis.c01_core import ContractError
from analysis.c01_workbench import create_json

OUTPUT=ROOT/'data/derived/experiments/c01_ledger_integration_v1'


def now():return datetime.now(timezone.utc).isoformat()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(output=OUTPUT):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    ledger=output/'synthetic_ledger'
    request={'game_id':'100','model_id':'synthetic-model','runtime_id':'synthetic-runtime','provider':'ESPN',
             'population':'original_pre_tip','tip_utc':(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat(),
             'fixture':'Synthetic API/clock exercise; not NBA data, ESPN reporting or forecast evidence'}
    role_times={}
    for role in ('model','inputs','report'):
        role_times[role]=now();path=output/f'{role}.json'
        create_json(path,{'synthetic':True,'role':role,'created_at':role_times[role]})
        request[role]={'path':str(path.resolve()),'sha256':sha(path)}
    request['model']['fitted_at']=role_times['model']
    request['inputs'].update(as_of=role_times['inputs'],retrieved_at=role_times['inputs'])
    request['report'].update(published_at=role_times['report'],retrieved_at=now(),publication_evidence='Actual-clock synthetic publication fixture',retrieval_evidence='Actual-clock synthetic retrieval fixture')
    generated=now();forecast=output/'forecast.json'
    create_json(forecast,{'synthetic':True,'game_id':request['game_id'],'tip_utc':request['tip_utc'],'model_id':request['model_id'],'runtime_id':request['runtime_id'],
        'generated_at':generated,'inputs_sha256':request['inputs']['sha256'],'report_sha256':request['report']['sha256'],'forecast':{'toy_values':[0,1]}})
    request['forecast']={'path':str(forecast.resolve()),'sha256':sha(forecast),'generated_at':generated}
    request_path=output/'request.json';create_json(request_path,request)
    def command(args,name,success=True):
        result=subprocess.run([str(ROOT/'.venv/bin/python'),str(ROOT/'analysis/c01_run.py'),*args],cwd=ROOT,capture_output=True,text=True)
        (output/f'{name}.stdout').write_text(result.stdout);(output/f'{name}.stderr').write_text(result.stderr)
        if (result.returncode==0)!=success:raise ContractError(f'ledger integration command failed expectation: {name}')
        return result
    args=['ledger-capture','--request',str(request_path),'--ledger',str(ledger)]
    command(args,'first_capture')
    first=list(ledger.glob('*/entry.json'))[0];original=sha(first)
    command(args,'second_capture')
    result=command(['ledger-audit','--ledger',str(ledger)],'audit')
    audit=json.loads(result.stdout)
    if audit['entries']!=2 or sha(first)!=original:raise ContractError('ledger capture overwrote original')
    unknown=deepcopy(request);unknown['report']['published_at']=None;unknown_path=output/'unknown.json';create_json(unknown_path,unknown)
    rejected=command(['ledger-capture','--request',str(unknown_path),'--ledger',str(ledger)],'unknown_rejected',False)
    if 'unknown pre-tip timestamp' not in rejected.stderr:raise ContractError('unknown timing rejected for wrong reason')
    late=deepcopy(request);late['tip_utc']=(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat();late['captured_at']=role_times['model']
    late_path=output/'late.json';create_json(late_path,late)
    rejected=command(['ledger-capture','--request',str(late_path),'--ledger',str(ledger)],'late_rejected',False)
    if 'late pre-tip' not in rejected.stderr:raise ContractError('late timing rejected for wrong reason')
    final=command(['ledger-audit','--ledger',str(ledger)],'final_audit')
    if json.loads(final.stdout)['entries']!=2 or sha(first)!=original:raise ContractError('rejected captures changed ledger')
    real=command(['ledger-audit'],'real_ledger_audit')
    receipt={'kind':'Actual-clock CLI ledger integration using synthetic artifacts, not NBA forecast evidence',
        'synthetic_entries':2,'real_certified_entries':json.loads(real.stdout)['entries'],'original_forecast_unchanged':True,
        'unknown_publication_rejected':True,'late_capture_and_backdating_rejected':True,'rejected_attempts_created_no_entries':True,
        'capture_api_and_audit_cli_passed':True,'production_generation_hook_changed':False,'production_changed':False,
        'test_request_sha256':sha(request_path),'source_sha256':sha(Path(__file__))}
    create_json(output/'receipt.json',receipt);print(receipt,flush=True)
    return receipt


if __name__=='__main__':run()
