#!/usr/bin/env python3
"""Freeze one B1 buzzer-possession mechanism before any candidate outcomes."""
from pathlib import Path
from datetime import datetime, timezone
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
import pyarrow as pa
from basketball_common import read_json, write_json, sha256_file

REPORT = ROOT / 'analysis/experiments/20261124_b1_frozen_recipe_v2.json'
WORK = ROOT / 'data/derived/experiments/d42_b1_buzzer_v2'
STARTS = ['made_fg', 'made_ft', 'dreb', 'steal', 'dead_turnover', 'jump_ball']


def fit(frame, cutoff):
    """Only prior known shot geometry/outcomes; feed heave text is never a target."""
    shots = frame[frame.date_et.le(cutoff) & frame.end_type.eq('shot') & frame.game_ok].copy()
    shots['distance'] = np.hypot(shots.x - 25, shots.y)
    context = shots.start_clock.le(4) & shots.action_clock.le(2) & shots.start_type.isin(STARTS)
    eligible = shots[context & shots.distance.notna() & shots.value.isin([2, 3])].copy()
    eligible['long'] = eligible.distance.ge(40) & eligible.value.eq(3)
    long = shots[shots.distance.ge(40) & shots.value.eq(3)]
    if len(eligible) < 1000 or len(long) < 1000:
        raise ValueError('insufficient prior numeric-coordinate support')
    cells = {}
    # A fixed two-way split: made-basket inbound versus other changes of possession.
    for key, inbound in [('inbound', True), ('change', False)]:
        part = eligible[eligible.start_type.isin(['made_fg', 'made_ft']).eq(inbound)]
        if len(part) < 100 or part.game_id.nunique() < 30:
            raise ValueError('unsupported prospective heave-routing cell')
        cells[key] = {'shots': len(part), 'games': part.game_id.nunique(), 'long': int(part.long.sum()),
                      'probability': float(part.long.mean())}
    return {'kind': 'b1-buzzer-shots-v1', 'train_through': cutoff, 'latest_training_date': str(shots.date_et.max()),
            'definition': 'Numeric distance>=40ft AND official shot value3; never text heave or made/missed for routing.',
            'routing': {'start_clock_max': 4, 'action_clock_max': 2, 'start_types': STARTS, 'cells': cells},
            'conversion': {'shots': len(long), 'games': long.game_id.nunique(), 'made': int(long.made.astype(bool).sum()),
                           'probability': float(long.made.astype(bool).mean())},
            'geometry': {'distance': long.distance.tolist(), 'lateral': (long.x - 25).abs().tolist()},
            'missing_context_coordinates': int((context & shots.distance.isna()).sum()),
            'distance_value_conflicts': int((shots.distance.ge(40) & ~shots.value.eq(3)).sum())}


def main():
    pa.set_cpu_count(1)
    if REPORT.exists() or WORK.exists():
        raise FileExistsError('immutable recipe/auxiliary namespace required')
    baseline = ROOT / 'analysis/experiments/20261124_b1_source_audit_v2.json'
    panels_path = ROOT / 'analysis/experiments/20261124_c2_ready_panels_v1.json'
    panels = read_json(panels_path)
    paths = [ROOT / f'data/derived/history/{year}/segments.parquet' for year in range(2023, 2027)]
    columns = ['game_id','date_et','game_ok','end_type','start_type','start_clock','action_clock',
               'period','duration','shot_time','x','y','value','made','heave']
    # Do not load any independent/protected rows: predicate is applied by parquet reader.
    prior = pd.concat([pd.read_parquet(p, columns=columns, filters=[('date_et','<=','2025-12-31')]) for p in paths])
    dev = pd.read_parquet(paths[-1], columns=columns, filters=[('game_id', 'in', panels['development_F4'])])
    aux = fit(prior, '2025-12-31')
    # Mechanism validation is chronologically held out within unprotected historical training data.
    valid_from = '2025-10-01'
    validation_aux = fit(prior, '2025-09-30')
    valid = prior[prior.date_et.ge(valid_from) & prior.end_type.eq('shot') & prior.game_ok].copy()
    valid['distance'] = np.hypot(valid.x - 25, valid.y)
    valid = valid[valid.start_clock.le(4) & valid.action_clock.le(2) & valid.start_type.isin(STARTS)
                  & valid.distance.notna() & valid.value.isin([2,3])].copy()
    valid['long'] = valid.distance.ge(40) & valid.value.eq(3)
    validation = {}
    for key, inbound in [('inbound', True), ('change', False)]:
        part = valid[valid.start_type.isin(['made_fg','made_ft']).eq(inbound)]
        probability = validation_aux['routing']['cells'][key]['probability']
        validation[key] = {'shots': len(part), 'games': part.game_id.nunique(), 'predicted_long_probability': probability,
                           'actual_long_probability': float(part.long.mean()),
                           'brier': float(((part.long.astype(float)-probability)**2).mean())}
    shots = dev[dev.end_type.eq('shot')].copy()
    distance = np.hypot(shots.x-25, shots.y)
    long = shots[distance.ge(40) & shots.value.eq(3)]
    WORK.mkdir(parents=True)
    auxiliary = WORK / 'F4.json'
    write_json(auxiliary, aux, pretty=False)
    sources = {str(p.relative_to(ROOT)): sha256_file(p) for p in
               paths + [baseline, panels_path, Path(__file__), ROOT/'scripts/engine.py', ROOT/'scripts/nodes.py']}
    report = {'kind': 'B1 single prospective mechanism/target freeze; no candidate engine outcomes',
        'frozen_at': datetime.now(timezone.utc).isoformat(), 'mechanism': 'Prior-fitted end-of-period long-shot choice and conversion',
        'setup_amendment': {'supersedes': '20261124_b1_frozen_recipe_v1.json',
            'reason': 'Exclude ambiguous source other: engine other is a retained violation, not a verified new possession. Repair before full development outcomes; same single mechanism/thresholds/policy, no new variant or outcome-based tuning.',
            'earlier_wiring': '20261124_b1_wiring_v1.json',
            'earlier_development_launched': False,
            'original_sources': ['data/derived/experiments/d42_b1_buzzer_v1/b1_prepare_v1.py',
                                 'data/derived/experiments/d42_b1_buzzer_v1/b1_engine_runner_v1.py']},
        'distinct_from_C2': 'Time/possession-state routing for numeric40+ft shots omitted or collapsed by accepted heave filtering; no new court partition, defender feature, C2 fit or nominee is reused.',
        'variants': ['buzzer-v1'], 'maximum_variants': 1, 'no_rescue_or_retune': True,
        'candidate': 'On an already selected shot, with a new possession starting<=4s and release<=2s, route to a40+ft3 with prior empirical probability by inbound/change start. Draw supported prior geometry and empirical long-shot make probability. Other possessions retain r3.',
        'selection_independence': 'Routing never sees current outcome; numeric distance and official value define prior training targets. Feed heave labels excluded because they are not a complete symmetric sample.',
        'control': 'Accepted r3 F4 nodes, D29 independent rotations, Rule3 and prior-fit F4 contextual clock; same inputs/seeds.',
        'source_diagnosis': {'development_games': 200, 'development_long_shots': len(long),
             'development_long_makes': int(long.made.astype(bool).sum()),
             'prior_long_shots': aux['conversion']['shots'], 'prior_long_make_probability': aux['conversion']['probability'],
             'ordinary_missed_heaves': 'Accepted Models.band_d and nodes shot datasets exclude feed-labelled heaves; >=31ft is the final existing band.',
             'foul_diagnostic': 'Empirical bonus timing is imprecise, but source combines ordinary and special penalties. No foul candidate selected; no causal accuracy claim from elevated FTA alone.',
             'observed_segments': len(dev), 'observed_mean_duration': float(dev.duration.mean()),
             'observed_duration_missing': int(dev.duration.isna().sum()),
             'shots_missing_coordinates': int(distance.isna().sum())},
        'mechanism_validation': {'fit_through': '2025-09-30', 'validation_from': valid_from, 'validation_through': '2025-12-31',
             'cells': validation, 'interpretation': 'Descriptive independent historical support; no choice among variants or future fits. Does not establish full-engine benefit.'},
        'auxiliary': str(auxiliary.relative_to(ROOT)), 'auxiliary_sha256': sha256_file(auxiliary),
        'policy': {'version': 'b1-team-score-v1-20261124', 'class': 'learned', 'primary': 'paired mean home/away team-points CRPS',
             'bootstrap': {'replicates':10000,'seed':20261122,'unit':'complete game; home/away together'},
             'benefit': 'Control-minus-candidate CRPS CI95 lower>0; point gain>=.05. MAE and RMSE must not increase.',
             'bias': 'If independent control signed mean bias CI95 excludes0, require>=25% absolute bias reduction. Otherwise candidate absolute signed mean bias<=1.0point/team.',
             'safeguards': 'All27 proper-score bounds and25 coverage vetoes from promotion-v3-20261123; player tiers graded first;17 bias diagnostics retained.',
             'development_qualification': 'Same benefit/MAE/RMSE/bias target and v3 safeguards. No independent screen unless qualified; no treating a failed setup as mechanism rejection.',
             'confirmation': 'One disjoint200-game independent screen, same unchanged recipe and policy.',
             'attribution': 'One added mechanism; removing it is r3. At wiring, no-heave contexts and disabled mode must reproduce old raw worlds.',
             'release': 'Only a survivor receives seed/10k/earlier-fold/stress and prospective new protected recipe once; never r3 protected rescore.'},
        'panels': {'development': panels['development_F4'], 'confirmation': panels['reserved_confirmation_F4']},
        'worlds': 1000, 'seed_key': 'v1.2d_F4', 'threads': '10 workers x1 OMP/BLAS; no concurrent heavy job',
        'limits': ['Sparse long-shot player support: use pooled prior conversion, no fabricated player skill/tracking.',
             'Coarse saved zone remains above3; exact numeric geometry must pass through dependent shot nodes.',
             'Routing conditional on selected shots; event/actor and live availability remain r3 assumptions.',
             'Source shot coordinates/revision times retain known limitations; missing geometry excluded and counted.',
             'A negative fixed attempt retains r3; it cannot establish that the broader team-score objective is met.'],
        'production_changed': False, 'protected_scoring': False, 'candidate_engine_outcomes_opened': False,
        'source_sha256': sources}
    write_json(REPORT, report, pretty=True)
    print('Frozen one buzzer candidate and team-score policy; prior auxiliary and historical support retained', flush=True)


if __name__ == '__main__':
    main()
