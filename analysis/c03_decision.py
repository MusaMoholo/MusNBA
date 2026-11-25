"""Independent bounded-negative decision from saved rows; no fitting or new worlds."""
from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from analysis import c03_data as data,c03_reproduce as reproduce
from analysis.c01_core import ContractError
from analysis.c01_workbench import read,create_json
from basketball_common import sha256_file


def run():
    reproduce.source();p=read(data.WORK/'data.json');ids=p['game_ids'][:20];summary=read(data.WORK/'mvp.json');out=data.WORK/'negative_audit.json'
    if out.exists():raise FileExistsError(out)
    scores=pd.concat([pd.read_parquet(data.WORK/'rollout'/g/'scores.parquet') for g in ids],ignore_index=True)
    keys=['game_id','entity','stat','player','side'];ref=scores[scores.model.eq('control')].set_index(keys).sort_index();independent={}
    if ref.index.duplicated().any():raise ContractError('duplicate independent reference key')
    for f in 'ABC':
        cand=scores[scores.model.eq(f)].set_index(keys).sort_index()
        if not cand.index.equals(ref.index) or not np.array_equal(cand.truth,ref.truth):raise ContractError('independent candidate support differs')
        record={}
        for ent,stat in [('player','pts'),('team','points')]:
            r=ref.xs((ent,stat),level=('entity','stat'));q=cand.xs((ent,stat),level=('entity','stat'));delta=q.crps.to_numpy()-r.crps.to_numpy();change=float(sum(delta)/len(delta));base=float(sum(r.crps)/len(r));relative=change/base
            saved=summary['changes'][f][f'{ent}/{stat}']
            if abs(change-saved['change'])>1e-12:raise ContractError('independent mean differs')
            # Independent game aggregation and bootstrap arithmetic for the frozen intervals.
            game_ids=r.index.get_level_values('game_id').to_numpy();games=sorted(set(game_ids));numer=np.array([sum(delta[game_ids==g]) for g in games]);denom=np.array([sum(game_ids==g) for g in games])
            w=np.random.default_rng(20261125).multinomial(len(games),[1/len(games)]*len(games),size=10000)
            bootstrap=np.sum(w*numer,axis=1)/np.sum(w*denom,axis=1);ci=np.quantile(bootstrap,[.05/6,1-.05/6])
            if np.max(np.abs(ci-saved['familywise_game']))>1e-12:raise ContractError('independent selection-aware game interval differs')
            half1=float(q.crps_half1.mean()-r.crps_half1.mean());half2=float(q.crps_half2.mean()-r.crps_half2.mean())
            record[f'{ent}/{stat}']={'rows':len(r),'games':len(games),'control_crps':base,'candidate_crps':base+change,'change':change,'relative_change':relative,'half1_change':half1,'half2_change':half2,'independent_familywise_game':ci.tolist()}
        record['primary_promise_passed']=record['player/pts']['relative_change']<=-.005
        record['both_halves_improve']=max(record['player/pts']['half1_change'],record['player/pts']['half2_change'])<0
        record['team_points_practical_harm_passed']=record['team/points']['change']<=.1
        if record['primary_promise_passed'] or record['both_halves_improve'] or record['team_points_practical_harm_passed']:raise ContractError('negative audit assumptions differ; independently audit full shortlist')
        if summary['eligible'][f]['eligible']:raise ContractError('false positive eligibility')
        independent[f]=record
    if summary['shortlist']:raise ContractError('false positive shortlist')
    report={'kind':'C03 independent saved-row and familywise-interval bounded negative audit','games':20,'player_games':427,'world_accounting':read(data.WORK/'accounting.json'),'feature_parity':read(data.WORK/'feature_parity.json'),'independent_arithmetic':independent,'all_three_fail_primary_halves_and_team_harm':True,'shortlist':[],'expanded_games':0,'complete_working_mvp_library':True,'recipe_count':3,'release':'retain engine-v1.3-r3; research negative search; no product gain demonstrated','source_sha256':sha256_file(Path(__file__)),'mvp_receipt_sha256':sha256_file(data.WORK/'mvp.json'),'production_changed':False}
    create_json(out,report);create_json(ROOT/'analysis/experiments/20261125_c03_negative_audit_v1.json',report);print(report,flush=True);return report

if __name__=='__main__':run()
