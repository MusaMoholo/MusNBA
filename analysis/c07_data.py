"""C07 immutable split/source inventory; reuse audited C05 causal inputs."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from analysis import c05_data as old,c05_models as models,c05_rollout as runtime
from analysis.c01_workbench import read,create_json
from analysis.c01_core import ContractError
from basketball_common import sha256_file
WORK=ROOT/'data/derived/experiments/c07_coherent_experts_v1';CONTRACT=ROOT/'analysis/c07_contract_v1.json'

def sources():
    return {'member_sources':runtime.signature(),'contract':sha256_file(CONTRACT),'core':sha256_file(ROOT/'analysis/c07_core.py'),'data':sha256_file(Path(__file__))}

def prepare():
    p=old.verify();refs=sorted(p['references'],key=lambda r:(r['date_et'],r['game_id']));train=[r['game_id'] for r in refs if r['date_et']<='2026-01-21'];ev=[r['game_id'] for r in refs if r['date_et']>='2026-01-22']
    if len(train)!=41 or len(ev)!=159 or set(train)&set(ev):raise ContractError('C07 split differs')
    WORK.mkdir(parents=True,exist_ok=False);r={'sources':sources(),'references':refs,'train_ids':train,'eval_ids':ev,'train_through':'2026-01-21','member_fit_through':'2025-12-31','training_games':41,'evaluation_games':159,'production_changed':False};create_json(WORK/'data.json',r);create_json(ROOT/'analysis/experiments/20261126_c07_data_v1.json',{k:v for k,v in r.items() if k not in ('references','train_ids','eval_ids')});return r

def verify():
    p=read(WORK/'data.json')
    if p['sources']!=sources():raise ContractError('C07 fixed source/split changed')
    return p
