"""Offline per-game workers; persist complete legal worlds and their source inputs."""
from fractions import Fraction
from collections import deque
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
from dataclasses import asdict
from types import SimpleNamespace
import base64
import hashlib
import json
import os
import pickle
import time
from pathlib import Path
from queue import Queue
from threading import Event, Thread

import numpy as np

from basketball_common import packed, read_json, sha256_file, utc_now, write_json
from scripts import engine, lineup_forecast, player_worlds, projection

_ENGINE = None


def fingerprints(runtime=None):
    runtime = engine.ENGINE if runtime is None else runtime
    paths = [Path(__file__)]
    root = Path(__file__).resolve().parents[1]
    paths += [root / 'basketball_common.py']
    paths += [root / f'scripts/{name}.py' for name in ('engine', 'projection', 'minutes', 'rotations', 'nodes', 'matchups',
              'foul_out', 'lineup_forecast', 'a1_lineup_branches', 'player_worlds', 'forecast_output', 'world_mass', 'rotation_fit', 'late_clock', 'nightly', 'world_detail', 'shot_zones', 'visible_worlds', 'court_assets', 'competitions', 'competition_rules', 'season_stats', 'master_fixtures')]
    paths.append(root / 'models/competitions_2026.json')
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
    if _ENGINE.runtime.get('world_details') == 'visible-worlds-v1':
        raise ValueError('visible worlds require the canonical chunk queue')
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


def _store(g, folder, raw, summary, weights, source_id, pieces, provenance, runtime, selected, *, complete=True):
    from scripts.rotation_maps import summarise
    if 'rotation_map' not in summary:
        rotation=summarise(raw,weights)
        if rotation is not None:summary['rotation_map']=rotation
    if 'rotation_map' in summary:summary['rotation_map']['source_id']=source_id
    encoded = player_worlds.pack_capture(raw)
    players = {'ids': raw['player_ids'], 'side': raw['side'],
               'lines': np.frombuffer(base64.b64decode(encoded['lines']), np.uint8).reshape(len(raw['minutes']), g.n, -1),
               'minutes_schema': np.array(1, np.uint8), 'minutes': raw['minutes']}
    if 'zone_fga' in raw or 'zone_fgm' in raw:
        from scripts import shot_zones
        shot_zones.validate(raw)
        players.update(zone_schema=np.array(1, np.uint8), zone_fga=raw['zone_fga'], zone_fgm=raw['zone_fgm'])
    if weights is not None:
        players['weights'] = weights
    np.savez_compressed(folder / 'players.npz', **players)
    np.savez_compressed(folder / 'points.npz', points=raw['team_points'])
    write_json(folder / 'game.json', summary)
    write_json(folder / 'provenance.json', {'source_id': source_id, 'inputs': provenance, 'pieces': pieces,
                                           'engine': runtime, 'selected': bool(selected)})
    names = ['game.json', 'players.npz', 'points.npz', 'provenance.json', 'inputs.pkl']
    if selected:
        names.append('worlds.json')
    if runtime.get('world_details') == 'visible-worlds-v1':
        from scripts import court_assets
        court_assets.store_zones(folder, source_id, raw, weights)
        names.append('zones.json')
        if complete:
            raise ValueError('visible-world game cannot complete before its original-chunk replay jobs')
    if complete:
        write_json(folder / 'completion.json', {'schema': 1, 'completed_at': utc_now(),
                   'files': {name: sha256_file(folder / name) for name in names}})
    return str(folder)


def verified_completion(folder):
    """Only an aggregate receipt makes a game eligible for early publication."""
    folder = Path(folder)
    receipt = folder / 'completion.json'
    if not receipt.exists():
        return False
    saved = read_json(receipt)
    required = {'game.json', 'players.npz', 'points.npz', 'provenance.json', 'inputs.pkl'}
    provenance = read_json(folder / 'provenance.json')
    if provenance['selected']:
        required.add('worlds.json')
    if provenance.get('engine', {}).get('world_details') == 'visible-worlds-v1':
        required.update(('zones.json', 'replay.json', 'replay-plan.json', 'replay-receipt.json'))
    if saved.get('schema') != 1 or set(saved.get('files', {})) != required:
        raise ValueError('invalid complete-game receipt')
    if any(not (folder / name).is_file() or sha256_file(folder / name) != digest
           for name, digest in saved['files'].items()):
        raise ValueError('changed complete-game output')
    return True


def verified_chunk(plan, start, stop):
    path = Path(plan['chunks']) / f'{start:05d}-{stop:05d}.npz'
    if not path.with_suffix('.json').exists():
        return False
    entry = read_json(path.with_suffix('.json'))
    seed = projection.seed_for('world-chunk-v1', int(plan['seed']), start, stop)
    if (entry['start'], entry['stop'], entry['seed']) != (start, stop, str(seed)) or not path.is_file() or entry['sha256'] != sha256_file(path):
        raise ValueError('changed saved world chunk')
    with np.load(path, allow_pickle=False) as z:
        if len(z['minutes']) != stop - start:
            raise ValueError('saved world chunk has incorrect dimensions')
    return True


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
    detailed = _ENGINE.runtime.get('world_details') == 'visible-worlds-v1'
    result = _store(g, folder, raw, summary, weights, source_id, season_pieces, plan['provenance'], _ENGINE.runtime, plan['selected'], complete=not detailed)
    if not detailed:
        return result
    from scripts import visible_worlds
    selection = visible_worlds.select(folder)
    replay_plan = folder / 'replay-plan.json'
    if replay_plan.exists():
        if read_json(replay_plan) != json.loads(packed(selection)):
            raise ValueError('changed selection: refusing replay resume')
    else:
        write_json(replay_plan, selection, pretty=False)
    chunks = sorted({(e['branch_id'], e['chunk_start'], e['chunk_stop']) for e in selection['examples']})
    jobs = [{'kind': 'replay', 'folder': str(folder), 'branch': branch, 'start': start, 'stop': stop}
            for branch, start, stop in chunks]
    return {'folder': str(folder), 'replay_jobs': jobs}


def _replay_path(job):
    name = hashlib.sha256(job['branch'].encode()).hexdigest()[:12]
    return Path(job['folder']) / 'replay-chunks' / f"{name}-{job['start']:05d}-{job['stop']:05d}.json"


def _replay(job):
    from scripts import visible_worlds
    folder = Path(job['folder'])
    selection = read_json(folder / 'replay-plan.json')
    return visible_worlds.replay_chunk(_ENGINE, folder, selection, job['branch'], job['start'], job['stop'], _replay_path(job))


def _replay_finish(job):
    from scripts import visible_worlds
    folder = Path(job['folder'])
    selection = read_json(folder / 'replay-plan.json')
    chunks = sorted({(e['branch_id'], e['chunk_start'], e['chunk_stop']) for e in selection['examples']})
    paths = [_replay_path({'folder': str(folder), 'branch': branch, 'start': start, 'stop': stop})
             for branch, start, stop in chunks]
    output, receipt = folder / 'replay.json', folder / 'replay-receipt.json'
    if output.exists():
        saved = read_json(receipt) if receipt.exists() else None
        if not saved or saved['plan_sha256'] != sha256_file(folder / 'replay-plan.json') or saved['sha256'] != sha256_file(output):
            raise ValueError('orphan or changed final replay; inspect before resume')
    else:
        result = visible_worlds.finish_replays(selection, paths, output, _ENGINE.runtime['models'], _ENGINE.runtime['id'])
        write_json(receipt, {'plan_sha256': sha256_file(folder / 'replay-plan.json'), **result}, pretty=False)
    names = ['game.json', 'players.npz', 'points.npz', 'provenance.json', 'inputs.pkl',
             'zones.json', 'replay.json', 'replay-plan.json', 'replay-receipt.json']
    if read_json(folder / 'provenance.json')['selected']:
        names.append('worlds.json')
    write_json(folder / 'completion.json', {'schema': 1, 'completed_at': utc_now(),
               'files': {name: sha256_file(folder / name) for name in names}}, pretty=False)
    if not verified_completion(folder):
        raise ValueError('replay-complete game did not qualify for publication')
    return str(folder)


def run(tasks, runtime, median, *, workers=10, chunk_worlds=1000, resume=False):
    """Priority queue: complete world chunks, then branches, then games; never a fixed core assignment."""
    from scripts import a1_lineup_branches
    tasks = [(g, selected, worlds, str(Path(directory).expanduser().resolve()), provenance)
             for g, selected, worlds, directory, provenance in tasks]
    if len({task[3] for task in tasks}) != len(tasks) or len({task[0].game['game_id'] for task in tasks}) != len(tasks):
        raise ValueError('duplicate game or directory in world queue')
    if runtime.get('rotation_fit') != 'independent-v1':
        raise ValueError('chunk generation requires a qualified independent rotation recipe')
    if not 1 <= workers <= 10 or not 1 <= chunk_worlds <= 10000:
        raise ValueError('1–10 workers and 1–10k worlds/chunk required')
    if any(os.environ.get(key) != '1' for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS')):
        raise ValueError('world workers require OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1')
    pending, branch_left, game_left = deque(), {}, {}
    finished = []
    started, completed, total = time.monotonic(), 0, 0
    # Check every existing input before scheduling any work. Conservative byte identity
    # includes fitted medians and game state, alongside explicit source fingerprints.
    for g, selected, worlds, directory, provenance in tasks:
        folder = Path(directory)
        if folder.exists():
            if not resume:
                raise FileExistsError(folder)
            saved = read_json(folder / 'work-plan.json')
            expected = pickle.dumps({'game': g, 'median': median, 'runtime': runtime}, protocol=5)
            if ((folder / 'inputs.pkl').read_bytes() != expected or saved['worlds'] != worlds
                    or saved['selected'] != json.loads(packed([asdict(p) for p in selected]))
                    or any(saved['provenance'].get(k) != v for k, v in provenance.items())
                    or saved['provenance']['replay_input_sha256'] != sha256_file(folder / 'inputs.pkl')
                    or saved['provenance']['execution']['chunk_worlds'] != chunk_worlds):
                raise ValueError('changed inputs: refusing world resume')
    for g, selected, worlds, directory, provenance in tasks:
        if not isinstance(worlds, int) or worlds < 1:
            raise ValueError('positive complete-world count required')
        folder = Path(directory)
        exists = folder.exists()
        folder.mkdir(parents=True, exist_ok=resume)
        if not exists:
            with (folder / 'inputs.pkl').open('xb') as stream:
                pickle.dump({'game':g, 'median':median, 'runtime':runtime}, stream, protocol=5)
        provenance = {**provenance, 'replay_input_sha256':sha256_file(folder/'inputs.pkl'),
                      'execution':{'schema':1,'namespace':'world-chunk-v1','chunk_worlds':chunk_worlds}}
        variants = a1_lineup_branches.enumerate_branches(g, [(p.team_id,p.player_id) for p in selected]) if selected else (None,)
        batches = []
        for i, variant in enumerate(variants):
            branch = variant.branch_id if variant else 'unconditional'
            chunks = folder / 'chunks' / str(i)
            chunks.mkdir(parents=True, exist_ok=resume)
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
            missing = [job for job in jobs if not verified_chunk(batch, job['start'], job['stop'])]
            pending.extend(missing)
            total += worlds
            completed += sum(job['stop'] - job['start'] for job in jobs if job not in missing)
            branch_left[key] = len(missing)
            if not missing:
                pending.appendleft({'kind':'merge','key':key,'plan':batch})
            batches.append(batch)
        game_left[str(folder)] = len(batches)
        plan = {'selected':[asdict(p) for p in selected],'worlds':worlds,
                'provenance':provenance,'batches':batches}
        if exists:
            if read_json(folder/'work-plan.json') != json.loads(packed(plan)):
                raise ValueError('changed execution plan: refusing world resume')
        else:
            write_json(folder/'work-plan.json', plan, pretty=False)
        if verified_completion(folder):
            pending = deque(job for job in pending if job['plan']['folder'] != str(folder))
            finished.append(str(folder))
    functions = {'chunk':_chunk, 'merge':_merge, 'game':_finish_game, 'replay':_replay, 'replay_finish':_replay_finish}
    replay_left = {}
    if not pending:
        yield from finished
        return
    print(f'worlds {completed}/{total} verified on resume', flush=True)
    # Scheduling is light I/O. Keep it moving while the caller uses its reserved
    # compute slot to publish a completed game. At most one result per task,
    # plus an error and terminator, can enter this bounded notification queue.
    events, stopping = Queue(maxsize=len(tasks) + 2), Event()

    def cancel(pool, futures):
        processes = list((getattr(pool, '_processes', None) or {}).values())
        for future in futures:
            future.cancel()
        pool.shutdown(wait=False, cancel_futures=True)
        for process in processes:
            if process.is_alive():
                process.terminate()
        for process in processes:
            process.join(timeout=2)

    def manage():
        nonlocal completed
        pool, futures = None, {}
        try:
            pool = ProcessPoolExecutor(max_workers=workers, initializer=initialise, initargs=(runtime,))
            while (pending or futures) and not stopping.is_set():
                while pending and len(futures) < workers and not stopping.is_set():
                    job = pending.popleft()
                    futures[pool.submit(functions[job['kind']], job)] = job
                ready, _ = wait(futures, timeout=.25, return_when=FIRST_COMPLETED)
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
                    elif job['kind'] == 'game' and isinstance(result, dict) and 'replay_jobs' in result:
                        replay_left[result['folder']] = len(result['replay_jobs'])
                        pending.extendleft(reversed(result['replay_jobs']))
                        if not result['replay_jobs']:
                            pending.appendleft({'kind': 'replay_finish', 'folder': result['folder']})
                    elif job['kind'] == 'replay':
                        replay_left[job['folder']] -= 1
                        if replay_left[job['folder']] == 0:
                            pending.appendleft({'kind': 'replay_finish', 'folder': job['folder']})
                    else:
                        events.put(('game', result))
            if stopping.is_set():
                cancel(pool, futures)
            else:
                pool.shutdown(wait=True)
        except BaseException as error:
            if pool is not None:
                cancel(pool, futures)
            events.put(('error', error))
        finally:
            events.put(('done', None))

    manager = Thread(target=manage, name='world-queue', daemon=True)
    manager.start()
    try:
        yield from finished
        while True:
            kind, value = events.get()
            if kind == 'done':
                break
            if kind == 'error':
                raise value
            yield value
    finally:
        stopping.set()
        manager.join()
