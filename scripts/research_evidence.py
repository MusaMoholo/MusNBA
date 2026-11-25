"""Build a small, source-bound research summary from immutable aggregate decisions only."""
from basketball_common import ROOT,read_json,sha256_file

def build():
    base=ROOT/'analysis/experiments'
    paths=[base/'20261124_b1_development_decision_v2.json',base/'20261124_b2_decision_v1.json']
    b1,b2=map(read_json,paths)
    return {'schema':'research-evidence-v1','team_score_objective_met':b1['team_score_objective_met'],
            'studies':[{'id':'B1','title':'End-of-period shots','qualified':b1['qualified'],'metric':'Team-points CRPS','unit':'points; lower is better',
                        'support':'200 historical development games; actual participants. Independent candidate panel not run after rejection.',
                        'scores':b1['team_metrics'],'limit':'This tests one long-shot recipe. It does not settle wider end-of-period modelling.'},
                       {'id':'B2','title':'Season starting strength and memory','qualified':b2['qualified'],'metric':'Final-wins CRPS','unit':'wins; lower is better',
                        'support':'16 starts across four completed seasons; 10,000 paths per arm/start. Three fixed candidates; no development nominee.',
                        'candidates':{k:{'label':{'carry8':'Carry-over start','opponent8':'Opponent-adjusted start','opponent40':'Longer memory'}[k],'gain':v['mean_gain'],'ci95':v['familywise_ci95'],'heldout_gain':v['independent2025_26_gain']} for k,v in b2['reports'].items()},
                        'control_crps':sum(r['crps'] for r in b2['metrics'] if r['arm']=='reference')/16,
                        'limit':'Conditional reconstructed regular schedules; four adjacent seasons are sparse evidence. No title, injury-path or historical live-lineup calibration.'}],
            'sources':[{'report':p.name,'sha256':sha256_file(p)} for p in paths],
            'interpretation':'No model change qualified. Current prediction models retained. Better visibility does not establish better prediction accuracy.'}
