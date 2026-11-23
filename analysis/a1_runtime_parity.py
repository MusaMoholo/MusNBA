#!/usr/bin/env python3
"""Compare the integrated runtime and formatter with three retained qualified captures."""
import argparse
import os
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from basketball_common import read_json, sha256_file, write_json
from analysis import rule3_confirmation as paired
from analysis.a1_parallel_world_probe import capture_digest
from scripts import backtest, engine, forecast_output, projection


def one(task):
    gid, independent = task
    if independent:
        original_engine = engine.Engine
        def integrated(version):
            runtime = {**engine.ENGINE,'id':'engine-v1.3-r2','version':'v1.3-r2',
                       'models':version,'foul_policy':'nba-rule3-v1','rotation_fit':'independent-v1'}
            return original_engine(version,runtime=runtime)
        with patch.object(engine,'Engine',side_effect=integrated):
            paired.init_worker(1000,None)
    else:
        paired.init_worker(1000, None)
    eng = backtest._W['engine']
    observer = paired.Observer(True)
    eng.rotation_policy = observer
    original, package = eng.simulate, projection.package
    checked = []
    def compare(*args, **kwargs):
        legacy = package(*args, **kwargs)
        assert legacy == forecast_output.game(*args, **kwargs), 'real game formatter changed'
        checked.append(True)
        return legacy
    def simulate(g, worlds, seed):
        result = original(g, worlds, seed)
        raw = observer.capture(g, eng.last)
        pre = backtest._W['inputs'][0]
        profile = pre.loc[pre['game_id'].eq(gid)].set_index('player').reindex(g.ids)
        raw['prior_usage'] = profile['usage'].to_numpy(float)
        raw['prior_start_share'] = profile['start_share'].to_numpy(float)
        run = 'independent_rotation_pilot_20261123_v1' if independent else 'rule3_pilot_20261123_v1'
        path = ROOT/f'data/derived/experiments/{run}/{gid}.json'
        manifest = read_json(ROOT/f'analysis/experiments/{run}.json')
        entry = next(row for row in manifest['captures'] if row['game']==gid)
        assert sha256_file(path)==entry['meta_sha256'], 'retained reference metadata changed'
        saved = read_json(path)
        assert capture_digest(raw) == saved['outputs']['candidate']['world_sha256'], 'runtime worlds changed'
        return result
    with patch.object(eng, 'simulate', side_effect=simulate), patch.object(projection, 'package', side_effect=compare):
        backtest.run_game(gid)
    return {'game': gid,'node_models':eng.runtime.get('models'),'raw_world_parity': True,
            'formatter_delegation_consistent': bool(checked)}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--independent',action='store_true')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise FileExistsError('fresh parity report required')
    if any(os.environ.get(k)!='1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS')):
        raise ValueError('single-thread workers required')
    ids = read_json(paired.PLAN)['pilot_games']
    with ProcessPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(one, [(gid,args.independent) for gid in ids]))
    write_json(args.output, {'games': results,'independent_fit':args.independent,
        'source_sha256':{p:sha256_file(ROOT/p) for p in ('analysis/a1_runtime_parity.py','scripts/engine.py',
                                                      'scripts/rotation_fit.py','scripts/forecast_output.py')},
        'limitation':'Formatter check covers delegation consistency; retained raw worlds are the independent reference.'}, pretty=True)
    print('runtime / real formatter parity:', len(results), flush=True)
