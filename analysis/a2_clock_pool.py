#!/usr/bin/env python3
"""Pool the three frozen dated clock panels by game, preserving each fold's prior roles."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from basketball_common import read_json, write_json, sha256_file
from analysis import a2_clock_scores
from scripts import backtest
import pandas as pd

EXP = ROOT / 'analysis/experiments'
DATA = ROOT / 'data/derived/experiments'
RUNTIME = EXP / '20261123_a2_clock_engine_runtime_manifest_v1.json'
PLAN = EXP / '20261123_a2_clock_pooled_adapter_manifest_v2.json'
SELECTION = EXP / '20261123_a2_clock_ready_panels_v1.json'
RUN = 'a2_clock_earlier_pooled_supported_20261123_v1'
FOLDS = ('F1', 'F2', 'F3')


def sources():
    runtime = read_json(RUNTIME)
    paths = [Path(__file__), RUNTIME, SELECTION, ROOT / 'analysis/a2_clock_scores.py',
             ROOT / 'scripts/a1_compare.py', ROOT / 'analysis/rule3_scores.py',
             ROOT / 'scripts/release_gate.py']
    for info in (runtime['runner_metadata'][fold] for fold in FOLDS):
        config = ROOT / info['config']
        paths += [config, ROOT / read_json(config)['default']['features']]
    return {str(p.relative_to(ROOT)): sha256_file(p) for p in paths}


def freeze():
    if PLAN.exists():
        raise FileExistsError('pooled adapter already frozen')
    write_json(PLAN, {'frozen_at': datetime.now(timezone.utc).isoformat(),
        'source_sha256': sources(), 'folds': list(FOLDS),
        'method': 'Concatenate original game/player rows, attach each game to its own dated pregame roles, then unchanged complete-game bootstrap; never average confidence intervals.',
        'acceptance': 'All supported proper bounds in every fold, no material coverage harm; all27 proper bounds in pooled300. No recipe, margin, panel or primary changes.'}, pretty=True)
    print('Frozen earlier-fold pooled adapter before fold scores.', flush=True)


def score():
    if read_json(PLAN)['source_sha256'] != sources():
        raise ValueError('pooled scoring source/prior identity changed')
    runtime = read_json(RUNTIME)
    union, parents, profiles, fingerprints = set(), {}, [], {}
    for fold in FOLDS:
        name = f'a2_clock_earlier_{fold.lower()}_supported_20261123_v1'
        report = read_json(EXP / f'{name}.json')
        audit = read_json(EXP / f'{name}_audit.json')
        gate = read_json(EXP / f'{name}_compare_gate.json')
        ids = set(report['game_ids'])
        if (ids != set(read_json(SELECTION)['earlier'][fold]['game_ids']) or len(ids) != 100 or ids & union
                or report['worlds'] != 1000 or report['stream'] is not None
                or audit['pairs'] != 100 or not audit['status'].startswith('pass')
                or not gate.get('supported_fold_compatibility')):
            raise ValueError(f'{fold}: complete, distinct, independently audited compatible panel required')
        union.update(ids)
        parents[fold] = name
        info = runtime['runner_metadata'][fold]
        pre = pd.read_parquet(ROOT / read_json(ROOT / info['config'])['default']['features'])
        profiles.append(pre[pre['game_id'].isin(ids)].copy())
        for suffix in ('', '_audit', '_compare', '_compare_gate', '_control', '_candidate'):
            p = EXP / f'{name}{suffix}.json'
            fingerprints[str(p.relative_to(ROOT))] = sha256_file(p)
        for label in ('control', 'candidate'):
            for suffix in ('', '_players'):
                p = DATA / f'{name}_{label}{suffix}.parquet'
                fingerprints[str(p.relative_to(ROOT))] = sha256_file(p)
    paths = [EXP / f'{RUN}{suffix}.json' for suffix in ('', '_control', '_candidate', '_compare', '_compare_gate')]
    paths += [DATA / f'{RUN}_{label}{suffix}.parquet' for label in ('control', 'candidate') for suffix in ('', '_players')]
    config = DATA / f'{RUN}_dated_configs.json'
    if any(p.exists() for p in [*paths, config]):
        raise FileExistsError('fresh aggregate namespace required')
    write_json(config, {'kind': 'evaluation-only union; not a fitted model',
        'fold_configs': runtime['runner_metadata']}, pretty=True)
    pre = pd.concat(profiles, ignore_index=True)
    if pre.duplicated(['game_id', 'player']).any():
        raise ValueError('duplicated dated pregame profiles')
    for label in ('control', 'candidate'):
        for suffix in ('', '_players'):
            frames = [pd.read_parquet(DATA / f'{name}_{label}{suffix}.parquet') for name in parents.values()]
            pd.concat(frames, ignore_index=True).to_parquet(DATA / f'{RUN}_{label}{suffix}.parquet', index=False)
        write_json(EXP / f'{RUN}_{label}.json', {'run': f'{RUN}_{label}', 'fold': 'F1-F3',
            'worlds': 1000, 'games': 300, 'game_ids': sorted(union),
            'config': str(config.relative_to(ROOT)), 'models': 'three original dated fold recipes',
            'parents': parents, 'simulation_stream': None}, pretty=True)
    write_json(EXP / f'{RUN}.json', {'run': RUN, 'game_ids': sorted(union),
        'parents': parents, 'input_sha256': fingerprints, 'adapter_plan_sha256': sha256_file(PLAN),
        'method': read_json(PLAN)['method'], 'release': 'evaluation only; no publication'}, pretty=True)
    original = backtest.load_inputs
    def dated_union(spec, fold, *args, **kwargs):
        if fold == 'F1-F3':
            if spec != read_json(config):
                raise ValueError('unrecognised pooled recipe')
            return (pre,)
        return original(spec, fold, *args, **kwargs)
    sys.argv = [sys.argv[0], RUN, '--output', str(EXP / f'{RUN}_compare.json')]
    with patch.object(backtest, 'load_inputs', side_effect=dated_union):
        a2_clock_scores.main()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('freeze', 'score'))
    args = parser.parse_args()
    freeze() if args.action == 'freeze' else score()
