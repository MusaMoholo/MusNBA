"""Fresh gate fitting, exact weighted laws and four single-worker member replays."""
from pathlib import Path
import argparse,sys,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from analysis import c07_data as data,c07_model as model,c07_members as members,c07_evaluate as evaluate,c07_audit as audit
from analysis.c01_workbench import read,create_json
from analysis.c01_core import ContractError
from basketball_common import sha256_file


def run(output):
    p=data.verify();output=Path(output).resolve()
    if not output.is_relative_to(ROOT/'data'):raise ContractError('private expert fits must stay ignored')
    output.mkdir(parents=True,exist_ok=False);start=time.monotonic();meta=model.fit(output)
    if meta['models_sha256']!=read(data.WORK/'fit.json')['models_sha256']:raise ContractError('fresh expert models differ')
    fresh=model.Predictor(output);members.init();stage='final' if (data.WORK/'final_decision.json').exists() else 'short';ids=p['eval_ids'] if stage=='final' else p['eval_ids'][:20];values=0;player_probabilities=0
    for gid in ids:
        receipt=read(data.WORK/'forecasts'/gid/'receipt.json');families=[f for f in 'ABC' if f in receipt['families']];arrays=evaluate.forecasts(gid,families,fresh)
        if 'C' in families:
            current=fresh.player_prob(gid);original=members.STATE['gates'].player_prob(gid)
            if not np.array_equal(current,original):raise ContractError('fresh player gate probabilities differ')
            player_probabilities+=current.size
        for f,a in arrays.items():
            with np.load(data.WORK/'forecasts'/gid/f'{f}.npz',allow_pickle=False) as z:
                if set(z.files)!=set(a) or any(not np.array_equal(z[k],a[k]) for k in z.files):raise ContractError('fresh weighted expert law differs')
            values+=len(a['weight'])
    gid=p['eval_ids'][0];replays={}
    for arm in ('H','V','R','C'):
        arrays,new,info=members.generate(gid,arm,fresh_gate=fresh);old=members.load(gid,arm)
        if set(arrays)!=set(old) or any(not np.array_equal(arrays[k],old[k]) for k in old):raise ContractError('fresh single-worker expert member differs')
        with (output/f'{arm}_replay.npz').open('xb') as stream:np.savez_compressed(stream,**arrays)
        replays[arm]={'all_arrays_exact':True,'new_worlds':new,'info':info};print('C07 fresh member replay exact',arm,flush=True)
    original_worlds=sum(read(f)['new_worlds'] for f in (data.WORK/'members').glob('*/*/receipt.json'));total=original_worlds+sum(r['new_worlds'] for r in replays.values())
    if total>806000:raise ContractError('expert total world budget exceeded')
    result={'fresh_gate_model_file_exact':True,'training_gates':meta['training'],'returned_world_weights_and_arrays_exact':values,'player_gate_probabilities_exact':player_probabilities,'replays':replays,'original_new_worlds':original_worlds,'total_new_worlds_including_replay':total,'independent_decision':audit.decision(stage),'seconds':time.monotonic()-start,'retained_inputs':'Immutable training member forecasts and fixed C05 member models/native captures; gates freshly fit and new member worlds regenerated. No fresh-test claim.','production_changed':False};create_json(output/'reproduction.json',result);create_json(ROOT/'analysis/experiments/20261126_c07_reproduction_v1.json',result)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ROOT/'data/derived/experiments/c07_reproduction_v1');a=p.parse_args();run(a.output)
