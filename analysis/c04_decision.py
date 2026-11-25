"""Independent component-gain/calibration-stop decision; no fits or new worlds."""
from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from analysis import c04_data as data,c04_reproduce as reproduce
from analysis.c01_workbench import read,create_json
from analysis.c01_core import ContractError
from basketball_common import sha256_file


def run():
    reproduce.source();p=read(data.WORK/'data.json');saved=read(data.WORK/'minute_screen.json');rows=pd.read_parquet(data.WORK/'minute_scores.parquet');independent=reproduce.decision(rows);native=rows[rows.model.eq('native')];reports={}
    if saved['shortlist']:raise ContractError('independent expected stop differs')
    for f in 'ABC':
        q=rows[rows.model.eq(f)];r=independent[f]
        if abs(r['crps_change']-saved['changes'][f]['overall']['change'])>1e-12 or r['coverage_rule_passed']:raise ContractError('independent minute stop differs')
        # Independent aggregation/bootstrap for the frozen simultaneous game bounds.
        keys=['game_id','player'];a=native.set_index(keys).sort_index();b=q.set_index(keys).sort_index();game=np.array(a.index.get_level_values(0));d=b.crps.to_numpy()-a.crps.to_numpy();ids=sorted(set(game));num=np.array([sum(d[game==g]) for g in ids]);den=np.array([sum(game==g) for g in ids]);w=np.random.default_rng(20261125).multinomial(len(ids),[1/len(ids)]*len(ids),10000);ci=np.quantile(np.sum(w*num,1)/np.sum(w*den,1),[.05/6,1-.05/6])
        if np.max(np.abs(ci-saved['changes'][f]['overall']['familywise_game']))>1e-12:raise ContractError('independent simultaneous interval differs')
        r['independent_familywise_game']=ci.tolist();r['source_quality_sensitivity']={}
        flagged=set(p['flagged_reconstructed_minute_ids'])
        for label,ids_here in [('reconciled',set(p['game_ids'])-flagged),('flagged',set(p['game_ids'])&flagged)]:
            cr=native[native.game_id.isin(ids_here)];cq=q[q.game_id.isin(ids_here)];r['source_quality_sensitivity'][label]={'games':len(ids_here),'player_games':len(cq),'native_crps':float(cr.crps.mean()),'candidate_crps':float(cq.crps.mean()),'native_coverage80':float(cr.covered80.mean()),'candidate_coverage80':float(cq.covered80.mean()),'interpretation':'diagnostic only; fixed all200 decision unchanged'}
        r['critical_coverage80']=float(q[q.critical].covered80.mean());reports[f]=r
    wiring_ids=p['game_ids'][:2];decoder={arm:{'mean_absolute_minutes':float(np.mean([read(data.WORK/'games'/g/'receipt.json')['decoder_fit_errors'][arm]['mean_absolute_minutes'] for g in wiring_ids])),'max_absolute_minutes':float(max(read(data.WORK/'games'/g/'receipt.json')['decoder_fit_errors'][arm]['max_absolute_minutes'] for g in wiring_ids))} for arm in ('bridge','A','B','C')}
    result={'kind':'C04 independent component-skill and calibration-stop audit','games':200,'player_games':4292,'independent_arithmetic':reports,'decision':'No candidate advances: meaningful dated minute skill recovered, frozen uncertainty-coverage rule fails for every family. No end-to-end improvement established.','shortlist':[],'expanded_game_accuracy_panel':False,'what_is_ruled_out':'Lack of usable signal in these dated minute/role features cannot explain all earlier model failures; all3 improve proper minute scores with full-slate game/week support.','what_remains_unresolved':'Why joint uncertainty is too narrow after legal projection; schedule decoder separately distorts some target tails. Neither model-class impossibility nor successful player-points/team translation established.','decoder_diagnostic':decoder,'history_audit':read(data.WORK/'history_audit.json'),'minute_audit':read(data.WORK/'minute_audit.json'),'world_audit':read(data.WORK/'world_audit.json'),'source_sha256':sha256_file(Path(__file__)),'production_changed':False}
    create_json(data.WORK/'decision_audit.json',result);create_json(ROOT/'analysis/experiments/20261125_c04_decision_v1.json',result);print(result,flush=True);return result

if __name__=='__main__':run()
