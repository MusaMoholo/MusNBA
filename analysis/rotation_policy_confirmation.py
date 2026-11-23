#!/usr/bin/env python3
"""Fresh F4 confirmation after the documented v3 methodology review; never reruns protected games."""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import sys

os.environ['MUSNBA_ROTATION_PHASE'] = 'confirmation'
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from basketball_common import read_json, sha256_file, write_json
from analysis import rotation_confirmation as recipe
from analysis import rule3_pipeline_audit as audit

recipe.paired.PLAN = recipe.PANELS
MANIFEST = ROOT/'analysis/experiments/20261123_rotation_policy_confirmation_manifest_v1.json'
PROTOCOL = ROOT/'docs/protocols/promotion_v3_20261123.md'
RUN = 'independent_rotation_policy_confirmation_20261123_v1'


def sources():
    paths = [Path(__file__), PROTOCOL, Path(audit.__file__), ROOT/'scripts/release_gate.py',
             ROOT/'analysis/rule3_scores.py', ROOT/'scripts/a1_minutes_gate.py',
             ROOT/'analysis/experiments/20261123_independent_rotation_gate_sanity_v1.json',
             ROOT/'analysis/experiments/independent_rotation_final_20261123_v1_compare_gate.json']
    return {**recipe.fingerprints(), **{str(p.relative_to(ROOT)):sha256_file(p) for p in paths}}


def freeze():
    if MANIFEST.exists():
        raise FileExistsError('confirmation is already frozen')
    panels = read_json(recipe.PANELS)
    ids = sorted(panels['confirmation'])
    if len(ids)!=200 or set(ids)&set(panels['development']) or set(ids)&set(panels['final']):
        raise ValueError('fresh independent F4 IDs required')
    old = ROOT/'data/derived/experiments'
    for run in ('independent_rotation_f4_20261123_v1','independent_rotation_stream_20261123_v1',
                'independent_rotation_stress_20261123_v1','independent_rotation_final_20261123_v1'):
        if any((old/run/f'{gid}.json').exists() for gid in ids):
            raise ValueError('confirmation overlaps known candidate outcomes')
    write_json(MANIFEST, {'frozen_at':datetime.now(timezone.utc).isoformat(),
               'kind':'fresh development-data confirmation following known protected v2 failure',
               'run':RUN, 'game_ids':ids, 'worlds':1000, 'policy':'promotion-v3-20261123',
               'recipe':'qualified r1 versus unchanged canonical row-local offset correction; clock off',
               'known_result':'r2 protected v2 42/44; preserved, never repeated or relabelled',
               'sources':sources()}, pretty=True)
    print('frozen 200 fresh F4 pairs and v3 policy; no new engine outcomes', flush=True)


def fingerprints():
    return {**sources(), str(MANIFEST.relative_to(ROOT)):sha256_file(MANIFEST)}


def game(task):
    result = recipe.game(task)
    gid, directory = task
    folder = Path(directory).with_name(Path(directory).name+'_independent_audits')
    folder.mkdir(exist_ok=True)
    # Independent accounting executes after simulation in this same single-thread worker.
    # Ten workers therefore use ten compute slots, including audits, without nested pools.
    audit.audit_pair((str(Path(directory)/f'{gid}.json'), str(folder/f'{gid}.json')))
    return result


def run(remaining):
    frozen = read_json(MANIFEST)
    if frozen['sources'] != sources():
        raise ValueError('frozen policy/recipe/input differs')
    recipe.PHASE = 'confirmation'
    paired = recipe.paired
    paired.PLAN, paired.paired_game = recipe.PANELS, game
    paired.fingerprints, paired.read_json = fingerprints, recipe.declaration
    sys.argv = [sys.argv[0], '--name', RUN, *remaining]
    paired.main()
    report = ROOT/f'analysis/experiments/{RUN}.json'
    if not report.exists():
        return  # clean partial stop; resume under identical fingerprints
    folder = ROOT/f'data/derived/experiments/{RUN}'
    cache = folder.with_name(folder.name+'_independent_audits')
    cache.mkdir(exist_ok=True)
    cache_plan = {'plan_sha256':sha256_file(folder/'plan.json'),
                  'auditor_sha256':sha256_file(Path(audit.audit.__file__)),
                  'pipeline_sha256':sha256_file(Path(audit.__file__))}
    plan = cache/'plan.json'
    if plan.exists() and read_json(plan)!=cache_plan:
        raise ValueError('independent audit cache source differs')
    if not plan.exists():
        write_json(plan, cache_plan, pretty=True)
    sys.argv = [sys.argv[0], RUN, '--resume', '--jobs','1','--output',
                str(ROOT/f'analysis/experiments/{RUN}_audit.json')]
    audit.main()  # verifies cached pair/capture hashes against the complete run manifest


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__, add_help=False)
    parser.add_argument('action', choices=('freeze','run'))
    args, remaining = parser.parse_known_args()
    if args.action=='freeze':
        freeze()
    else:
        run(remaining)
