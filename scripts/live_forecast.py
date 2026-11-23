"""Offline per-game workers; persist complete legal worlds and their source inputs."""
from fractions import Fraction
from collections import deque
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
from dataclasses import asdict
from types import SimpleNamespace
import base64
import hashlib
import os
import pickle
import time
from pathlib import Path

import numpy as np

from basketball_common import packed, read_json, sha256_file, write_json
from scripts import engine, lineup_forecast, player_worlds, projection

_ENGINE = None


def fingerprints(runtime=None):
    runtime = engine.ENGINE if runtime is None else runtime
    paths = [Path(__file__)]
    root = Path(__file__).resolve().parents[1]
    paths += [root / 'basketball_common.py']
    paths += [root / f'scripts/{name}.py' for name in ('engine', 'projection', 'minutes', 'rotations', 'nodes', 'matchups',
              'foul_out', 'lineup_forecast', 'a1_lineup_branches', 'player_worlds', 'forecast_output', 'world_mass', 'rotation_fit', 'late_clock', 'nightly')]
    paths += list((engine.MODELS / runtime['models']).glob('*'))
    if runtime.get('clock_recipe') is not None:
        recipe = root / runtime['clock_recipe']
        if not recipe.is_file():
            raise FileNotFoundError(recipe)
        paths.append(recipe)
    return {str(path.relative_to(root)): sha256_file(path) for path in sorted(set(paths)) if path.is_file()}


def initialise(runtime):
    global _ENGINE
    _ENGINE = engine.Engine(runtime['models'], runtime=runtime)


def project(task):
    g, selected, W, directory, provenance = task
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=False)
    eng = _ENGINE
    # Private local replay input. Never included in app exports or Pages.
    with (folder / 'inputs.pkl').open('xb') as stream:
        pickle.dump({'game': g, 'median': eng.m.median, 'runtime': eng.runtime}, stream, protocol=5)
    provenance = {**provenance, 'replay_input_sha256': sha256_file(folder / 'inputs.pkl')}
    if selected:
        result = lineup_forecast.project(eng, g, selected, W, folder / 'branches', provenance)
        raw, summary, weights = result['raw'], result['summary'], result['weights']
        source_id = result['source_id']
        write_json(folder / 'worlds.json', result['payload'])
        summary['lineups'] = {key: result['payload'][key] for key in ('schema', 'source_id', 'selected_players', 'weight_assumptions')}
        summary['lineups']['worlds_per_branch'] = W
        pieces = [{'count': W, 'weight': [str(r['weight']['numerator']), str(r['weight']['denominator'])]}
                  for r in result['payload']['branches']]
    else:
        seed = projection.seed_for(eng.runtime['id'], g.day, g.game['game_id'])
        result = lineup_forecast.simulate(eng, g, W, seed)
        raw, summary, weights = result['raw'], result['summary'], None
        path = folder / 'capture.npz'
        np.savez_compressed(path, **raw)
        source_id = hashlib.sha256(packed({'capture': sha256_file(path), 'inputs': provenance}).encode()).hexdigest()
        pieces = [{'count': W, 'weight': ['1', '1']}]
    return _store(g, folder, raw, summary, weights, source_id, pieces, provenance, eng.runtime, selected)


def _store(g, folder, raw, summary, weights, source_id, pieces, provenance, runtime, selected):
    encoded = player_worlds.pack_capture(raw)
    players = {'ids': raw['player_ids'], 'side': raw['side'],
               'lines': np.frombuffer(base64.b64decode(encoded['lines']), np.uint8).reshape(len(raw['minutes']), g.n, -1),
               'minutes_schema': np.array(1, np.uint8), 'minutes': raw['minutes']}
    if weights is not None:
        players['weights'] = weights
    np.savez_compressed(folder / 'players.npz', **players)
    np.savez_compressed(folder / 'points.npz', points=raw['team_points'])
    write_json(folder / 'game.json', summary)
    write_json(folder / 'provenance.json', {'source_id': source_id, 'inputs': provenance, 'pieces': pieces,
                                           'engine': runtime, 'selected': bool(selected)})
    return str(folder)


def pieces(folder, points):
    from basketball_common import read_json
    records = read_json(Path(folder) / 'provenance.json')['pieces']
    start, result = 0, []
    for record in records:
        end = start + record['count']
        result.append((points[start:end], Fraction(*map(int, record['weight']))))
        start = end
    if start != len(points):
        raise ValueError('season pieces differ from saved game worlds')
    return result


def _working_game(plan):
    from scripts import a1_lineup_branches
    with Path(plan['inputs']).open('rb') as stream:
        saved = pickle.load(stream)
    _ENGINE.m.median = saved['median']
    g = saved['game']
    if plan.get('assignments'):
        g = a1_lineup_branches.prepare_branch(g, [tuple(a) for a in plan['assignments']])
    return g


def _chunk(job):
    plan = job['plan']
    g = _working_game(plan)
    seed = projection.seed_for('world-chunk-v1', int(plan['seed']), job['start'], job['stop'])
    record = lineup_forecast.simulate(_ENGINE, g, job['stop'] - job['start'], seed)
    path = Path(plan['chunks']) / f"{job['start']:05d}-{job['stop']:05d}.npz"
    np.savez_compressed(path, **record['raw'])
    metadata = {'start':job['start'], 'stop':job['stop'], 'seed':str(seed), 'sha256':sha256_file(path),
                'counts':record['counts'], 'targets':record['targets'].tolist()}
    write_json(path.with_suffix('.json'), metadata, pretty=False)
    return metadata


def _merge(job):
    plan = job['plan']
    records, metadata = [], []
    for start in range(0, plan['worlds'], plan['chunk_worlds']):
        stop = min(plan['worlds'], start + plan['chunk_worlds'])
        path = Path(plan['chunks']) / f'{start:05d}-{stop:05d}.npz'
        entry = read_json(path.with_suffix('.json'))
        seed = projection.seed_for('world-chunk-v1', int(plan['seed']), start, stop)
        if (entry['start'], entry['stop'], entry['sha256'], entry['seed']) != (start, stop, sha256_file(path), str(seed)):
            raise ValueError('missing, duplicated or changed world chunk')
        with np.load(path, allow_pickle=False) as z:
            if len(z['minutes']) != stop - start:
                raise ValueError('world chunk has the wrong number of complete worlds')
            records.append({'raw':{key:z[key] for key in z.files}})
        metadata.append(entry)
    raw = lineup_forecast.merge(records)
    if len(raw['minutes']) != plan['worlds']:
        raise ValueError('merged batch does not contain exactly the declared complete worlds')
    target = Path(plan['capture'])
    np.savez_compressed(target, **raw)
    counts = {key:sum(item['counts'].get(key,0) for item in metadata) for key in metadata[0]['counts']}
    if any(item['targets'] != metadata[0]['targets'] for item in metadata):
        raise ValueError('a chunk changed its branch minute inputs')
    entry = {**plan, 'capture_sha256':sha256_file(target), 'counts':counts, 'targets':metadata[0]['targets'],
             'execution':{'schema':1, 'namespace':'world-chunk-v1', 'chunk_worlds':plan['chunk_worlds'], 'chunks':metadata}}
    write_json(target.with_suffix('.json'), entry, pretty=False)
    return entry


def _finish_game(job):
    folder = Path(job['folder'])
    plan = read_json(folder / 'work-plan.json')
    with (folder / 'inputs.pkl').open('rb') as stream:
        g = pickle.load(stream)['game']
    records = []
    for batch in plan['batches']:
        item = read_json(Path(batch['capture']).with_suffix('.json'))
        with np.load(item['capture'], allow_pickle=False) as z:
            raw = {key:z[key] for key in z.files}
        records.append({**item, 'raw':raw, 'targets':np.asarray(item['targets']),
                        'assignments':tuple(tuple(a) for a in item['assignments']),
                        'weight':Fraction(*map(int,item['weight']))})
    if plan['selected']:
        result = lineup_forecast.assemble(g, plan['selected'], records, _ENGINE.runtime, plan['provenance'])
        raw, summary, weights = result['raw'], result['summary'], result['weights']
        source_id = result['source_id']
        write_json(folder / 'worlds.json', result['payload'])
        summary['lineups'] = {key:result['payload'][key] for key in ('schema','source_id','selected_players','weight_assumptions')}
        summary['lineups']['worlds_per_branch'] = plan['worlds']
    else:
        raw, weights = records[0]['raw'], None
        state = SimpleNamespace(minutes=raw['minutes'], pts=raw['team_points'], period=raw['final_period'],
                                poss=raw['possessions'], box={k:raw['box_'+k] for k in engine.STATS})
        summary = _ENGINE._package(g, state, plan['worlds'])
        source_id = hashlib.sha256(packed({'capture':records[0]['capture_sha256'], 'inputs':plan['provenance']}).encode()).hexdigest()
    season_pieces = [{'count':plan['worlds'], 'weight':item['weight']} for item in plan['batches']]
    return _store(g, folder, raw, summary, weights, source_id, season_pieces, plan['provenance'], _ENGINE.runtime, plan['selected'])


def run(tasks, runtime, median, *, workers=10, chunk_worlds=1000):
    """Priority queue: complete world chunks, then branches, then games; never a fixed core assignment."""
    from scripts import a1_lineup_branches
    if runtime.get('rotation_fit') != 'independent-v1':
        raise ValueError('chunk generation requires a qualified independent rotation recipe')
    if not 1 <= workers <= 10 or not 1 <= chunk_worlds <= 10000:
        raise ValueError('1–10 workers and 1–10k worlds/chunk required')
    if any(os.environ.get(key) != '1' for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS')):
        raise ValueError('world workers require OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1')
    pending, branch_left, game_left = deque(), {}, {}
    started, completed, total = time.monotonic(), 0, 0
    for g, selected, worlds, directory, provenance in tasks:
        if not isinstance(worlds, int) or worlds < 1:
            raise ValueError('positive complete-world count required')
        folder = Path(directory)
        folder.mkdir(parents=True, exist_ok=False)
        with (folder / 'inputs.pkl').open('xb') as stream:
            pickle.dump({'game':g, 'median':median, 'runtime':runtime}, stream, protocol=5)
        provenance = {**provenance, 'replay_input_sha256':sha256_file(folder/'inputs.pkl'),
                      'execution':{'schema':1,'namespace':'world-chunk-v1','chunk_worlds':chunk_worlds}}
        variants = a1_lineup_branches.enumerate_branches(g, [(p.team_id,p.player_id) for p in selected]) if selected else (None,)
        batches = []
        for i, variant in enumerate(variants):
            branch = variant.branch_id if variant else 'unconditional'
            chunks = folder / 'chunks' / str(i)
            chunks.mkdir(parents=True)
            capture = folder / 'branches' / f'branch-{i:03d}.npz' if selected else folder/'capture.npz'
            capture.parent.mkdir(exist_ok=True)
            seed = (projection.seed_for('lineup-v1',runtime['id'],g.input_before,g.day,g.game['game_id'],branch)
                    if selected else projection.seed_for(runtime['id'],g.day,g.game['game_id']))
            batch = {'game':g.game['game_id'],'branch_id':branch,'assignments':variant.assignments if variant else (),
                     'weight':[str(variant.weight.numerator),str(variant.weight.denominator)] if variant else ['1','1'],
                     'inputs':str(folder/'inputs.pkl'),'folder':str(folder),'worlds':worlds,'chunk_worlds':chunk_worlds,
                     'seed':str(seed),'chunks':str(chunks),'capture':str(capture)}
            key = (str(folder),i)
            jobs = [{'kind':'chunk','key':key,'plan':batch,'start':start,'stop':min(worlds,start+chunk_worlds)}
                    for start in range(0,worlds,chunk_worlds)]
            pending.extend(jobs)
            total += worlds
            branch_left[key] = len(jobs)
            batches.append(batch)
        game_left[str(folder)] = len(batches)
        write_json(folder/'work-plan.json', {'selected':[asdict(p) for p in selected],'worlds':worlds,
                   'provenance':provenance,'batches':batches}, pretty=False)
    functions = {'chunk':_chunk, 'merge':_merge, 'game':_finish_game}
    with ProcessPoolExecutor(max_workers=workers, initializer=initialise, initargs=(runtime,)) as pool:
        futures = {}
        while pending or futures:
            while pending and len(futures) < workers:
                job = pending.popleft()
                futures[pool.submit(functions[job['kind']],job)] = job
            ready, _ = wait(futures,return_when=FIRST_COMPLETED)
            for future in ready:
                job = futures.pop(future)
                result = future.result()
                if job['kind'] == 'chunk':
                    previous = completed * 10 // total
                    completed += job['stop'] - job['start']
                    if completed * 10 // total > previous:
                        print(f'worlds {completed}/{total} complete in {time.monotonic()-started:.1f}s', flush=True)
                    branch_left[job['key']] -= 1
                    if branch_left[job['key']] == 0:
                        pending.appendleft({'kind':'merge','key':job['key'],'plan':job['plan']})
                elif job['kind'] == 'merge':
                    folder = job['plan']['folder']
                    game_left[folder] -= 1
                    if game_left[folder] == 0:
                        pending.appendleft({'kind':'game','folder':folder})
                else:
                    yield result
