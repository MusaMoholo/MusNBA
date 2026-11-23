#!/usr/bin/env python3
"""Single protected D56 confirmation; reuse qualified r1 controls and the existing final runner."""
import os
from datetime import datetime, timezone
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from basketball_common import read_json, sha256_file, write_json
from analysis import rule3_final as final
from scripts import engine, rotation_fit

MANIFEST = ROOT/'analysis/experiments/20261123_independent_rotation_final_manifest_v1.json'
BASE_MANIFEST = ROOT/'analysis/experiments/20261123_rule3_final_manifest_v1.json'
BASE_RUN = ROOT/'analysis/experiments/rule3_final_20261123_v1.json'
ORIGINAL_FINGERPRINTS = final.fingerprints


def fingerprints():
    paths = [Path(__file__), BASE_MANIFEST, BASE_RUN, ROOT/'scripts/rotation_fit.py',
             ROOT/'scripts/forecast_output.py', ROOT/'scripts/world_mass.py',
             ROOT/'docs/protocols/world_independence_20261123.md',
             ROOT/'docs/protocols/world_independence_amendment_20261123.md',
             ROOT/'docs/protocols/world_independence_stream_review_20261123.md']
    return {**ORIGINAL_FINGERPRINTS(), **{str(p.relative_to(ROOT)):sha256_file(p) for p in paths}}


def one(task):
    gid, directory = task
    prior = ROOT/'data/derived/experiments/rule3_final_20261123_v1'/f'{gid}.json'
    declared = next(row for row in read_json(BASE_RUN)['captures'] if row['game']==gid)
    if sha256_file(prior) != declared['meta_sha256']:
        raise ValueError('changed qualified final control metadata')
    control = read_json(prior)['outputs']['candidate']
    source = ROOT/control['capture']
    if sha256_file(source) != control['sha256']:
        raise ValueError('changed qualified final control')
    destination = Path(directory)/f'{gid}-control.npz'
    os.link(source, destination)  # retained captures are immutable; no unchanged simulation is repeated
    pre = final.backtest._W['inputs'][0]
    day = str(pre.loc[pre['game_id'].eq(gid),'date_et'].iloc[0])
    final.backtest._W['engine'].m.median = final.backtest._W['medians'][day]
    fitter = lambda curves, targets: rotation_fit.independent(curves,targets,engine.ROTATION)
    with patch.object(engine.Game,'_fit_offsets',staticmethod(fitter)):
        result = final.paired.paired_game(task,labels=('candidate',),corrected=(True,True),persist=False)
    result['outputs']['control'] = {**control,'capture':str(destination.relative_to(ROOT))}
    result.update(control_corrected=True, recipe='independent D29 offset fit; contextual clock off',
                  reused_control={'meta':str(prior.relative_to(ROOT)),'sha256':sha256_file(prior)})
    write_json(Path(directory)/f'{gid}.json',result,pretty=False)
    return result


def freeze():
    if MANIFEST.exists():raise FileExistsError('protected manifest is already frozen')
    evidence = []
    for name, stream in [('independent_rotation_f4_20261123_v1',False),('independent_rotation_stream_20261123_v1',True)]:
        path = ROOT/f'analysis/experiments/{name}_compare_gate.json'
        gate = read_json(path)
        allowed = ('established','unsupported','unresolved') if stream else ('established',)
        if (gate['core']['checks'] != 44 or any(r['status'] not in allowed for r in gate['core']['details'])
                or any(r['status']=='material_harm' for r in gate['coverage']['details'])):
            raise ValueError('development compatibility not established')
        audit = ROOT/f'analysis/experiments/{name}_audit.json'
        checked = read_json(audit)
        if (not checked['status'].startswith('pass') or checked['pairs'] != (30 if stream else 200)
                or checked['worlds_per_branch_game'] != 1000):
            raise ValueError('missing complete independent audit')
        evidence += [path,audit]
    stress = ROOT/'analysis/experiments/independent_rotation_stress_20261123_v1_audit.json'
    checked = read_json(stress)
    if checked['pairs'] != 3 or checked['worlds_per_branch_game'] != 10000 or not checked['status'].startswith('pass'):
        raise ValueError('three complete 10k stresses must pass independent audit')
    evidence.append(stress)
    determinism = ROOT/'analysis/experiments/20261123_world_chunk_workers_compare_v1.json'
    if not read_json(determinism)['all_chunks_and_merged_arrays_identical']:
        raise ValueError('worker-layout determinism not established')
    evidence.append(determinism)
    queue = ROOT/'analysis/experiments/20261123_world_queue_workers_compare_v1.json'
    if not read_json(queue)['all_game_branch_arrays_identical']:
        raise ValueError('complete live queue worker determinism not established')
    evidence.append(queue)
    preparation = ROOT/'analysis/experiments/20261123_world_independence_source_audit_v1.json'
    if read_json(preparation)['checks']['passed'] != 3:
        raise ValueError('independent preparation checks are incomplete')
    evidence.append(preparation)
    base = read_json(BASE_MANIFEST)
    # Retained r1 controls share all data/model inputs. Source adapters were separately checked for raw parity.
    changed = [p for p,h in base['fingerprints'].items() if p.startswith(('data/','models/')) and sha256_file(ROOT/p)!=h]
    if changed:raise ValueError(f'qualified final input recipe changed: {changed}')
    write_json(MANIFEST,{**base,'candidate':'engine-v1.3-r2','kind':'single protected independent-world mechanical confirmation',
                         'frozen_at':datetime.now(timezone.utc).isoformat(),
                         'seed_diagnostic_unresolved':[
                             row for row in read_json(ROOT/'analysis/experiments/independent_rotation_stream_20261123_v1_compare_gate.json')['core']['details']
                             if row['status']=='unresolved'],
                         'fingerprints':fingerprints(),'prerequisites':{str(p.relative_to(ROOT)):sha256_file(p) for p in evidence}},pretty=True)
    print(f"frozen {len(base['game_ids'])} protected IDs; no candidate protected score read",flush=True)


if __name__ == '__main__':
    final.MANIFEST, final.PROTOCOL = MANIFEST, ROOT/'docs/protocols/world_independence_amendment_20261123.md'
    final.fingerprints, final.one, final.freeze = fingerprints, one, freeze
    if not any(arg=='--name' or arg.startswith('--name=') for arg in sys.argv[1:]):
        sys.argv += ['--name','independent_rotation_final_20261123_v1']
    final.main()
