#!/usr/bin/env python3
"""Three real 10k-world clock stress pairs, scheduled as thirty fixed paired 1k chunks."""
import argparse
from concurrent.futures import ProcessPoolExecutor, FIRST_COMPLETED, wait
from datetime import datetime, timezone
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from basketball_common import read_json, write_json, sha256_file
from analysis import a2_clock_engine as clock
from scripts import backtest

PLAN = ROOT / 'analysis/experiments/20261123_a2_clock_stress_manifest_v1.json'
EXP = ROOT / 'analysis/experiments'
RUN = 'a2_clock_stress_20261123_v1'


def fingerprints():
    return {**clock.fingerprints(), str(Path(__file__).relative_to(ROOT)): sha256_file(Path(__file__))}


def freeze():
    if PLAN.exists():
        raise FileExistsError('stress recipe already frozen')
    if read_json(clock.MANIFEST)['source_sha256'] != clock.sources():
        raise ValueError('original frozen clock recipe changed')
    evidence = {}
    names = [('a2_clock_development_20261123_v1', 'full'),
             *((f'a2_clock_earlier_{f}_supported_20261123_v1', 'fold') for f in ('f1', 'f2', 'f3')),
             ('a2_clock_earlier_pooled_supported_20261123_v1', 'full'),
             ('a2_clock_confirmation_20261123_v1', 'full'), ('a2_clock_stream_20261123_v1', 'stream')]
    for name, kind in names:
        path = EXP / f'{name}_compare_gate.json'
        gate = read_json(path)
        expected = 30 if kind == 'stream' else 100 if kind == 'fold' else 300 if 'pooled' in name else 200
        if (gate['population']['games'] != expected or gate['core']['checks'] != 27
                or any(x['status'] == 'material_harm' for x in gate['core']['details'] + gate['coverage']['details'])
                or not gate['primary']['improvement_established'] or not gate['primary']['also_beats_clean_bridge']
                or kind == 'full' and not gate['statistical_compatibility']
                or kind == 'fold' and not gate['supported_fold_compatibility']):
            raise ValueError(f'{name}: prerequisite not qualified')
        evidence[str(path.relative_to(ROOT))] = sha256_file(path)
        if 'pooled' not in name:
            audit = EXP / f'{name}_audit.json'
            checked = read_json(audit)
            if (not checked['status'].startswith('pass') or checked['worlds_per_branch_game'] != 1000
                    or checked['pairs'] != expected):
                raise ValueError(f'{name}: independent accounting required')
            evidence[str(audit.relative_to(ROOT))] = sha256_file(audit)
    declared = read_json(clock.MANIFEST)
    if len(declared['stress']) != 3 or len(set(declared['stress'])) != 3:
        raise ValueError('the original three distinct stress games are required')
    write_json(PLAN, {'frozen_at': datetime.now(timezone.utc).isoformat(), 'game_ids': declared['stress'],
        'real_games': 3, 'chunks_per_game': 10, 'worlds_per_chunk_arm': 1000,
        'seed_key': 'a2-clock-stress-chunk-v1|{zero_based_chunk_index}',
        'method': 'Original three stress games; ten independent fixed 1k chunks per game/arm. Audit every chunk; disjoint declared world ranges cover10k per arm. Never count chunks as independent real games.',
        'fingerprints': fingerprints(), 'prerequisite_sha256': evidence}, pretty=True)
    print('Frozen three-game/10k stress recipe; no stress outcome generated.', flush=True)


def init_worker():
    clock.FOLD, clock.PHASE = 'F4', 'stress_chunks'
    clock.init_worker(1000, None)


def pair_paths(root, chunk, gid):
    folder = root / f'chunk_{chunk:02d}'
    return folder, folder / f'{gid}.json', folder.with_name(folder.name + '_independent_audits') / f'{gid}.json'


def saved_pair(meta, cache):
    row = read_json(meta)
    if set(row['outputs']) != {'control', 'candidate'}:
        raise ValueError('incomplete stress pair')
    captures = {}
    for label, entry in row['outputs'].items():
        path = ROOT / entry['capture']
        if path != meta.parent / f'{row["game"]}-{label}.npz' or sha256_file(path) != entry['sha256']:
            raise ValueError('stress capture changed')
        captures[entry['capture']] = entry['sha256']
    if cache.exists():
        audit = read_json(cache)
        if audit['meta_sha256'] != sha256_file(meta) or audit['captures'] != captures:
            raise ValueError('stress audit identity changed')
        return audit
    return None


def work(task):
    root, chunk, gid = task
    folder, meta, cache = pair_paths(Path(root), chunk, gid)
    if not meta.exists():
        old = backtest._W['seed_key']
        backtest._W['seed_key'] = f'a2-clock-stress-chunk-v1|{chunk}'
        try:
            clock.game((gid, str(folder)))
        finally:
            backtest._W['seed_key'] = old
    elif not cache.exists():
        cache.parent.mkdir(exist_ok=True)
        clock.auditor.audit_pair((str(meta), str(cache)))
    return chunk, gid, saved_pair(meta, cache)


def run(resume, stop_after, jobs):
    declared = read_json(PLAN)
    if declared['fingerprints'] != fingerprints():
        raise ValueError('stress source/inputs changed')
    if any(sha256_file(ROOT / p) != digest for p, digest in declared['prerequisite_sha256'].items()):
        raise ValueError('stress prerequisites changed')
    root = ROOT / 'data/derived/experiments' / RUN
    output = EXP / f'{RUN}_audit.json'
    if output.exists() or root.exists() and not resume:
        raise FileExistsError('fresh stress namespace required; completed run is immutable')
    if not root.exists():
        root.mkdir()
        write_json(root / 'plan.json', declared, pretty=True)
    elif read_json(root / 'plan.json') != declared:
        raise ValueError('resume identity differs')
    tasks, done, allowed_root = [], {}, {root / 'plan.json'}
    for chunk in range(10):
        for gid in declared['game_ids']:
            folder, meta, cache = pair_paths(root, chunk, gid)
            folder.mkdir(exist_ok=True)
            allowed_root.update((folder, cache.parent))
            if meta.exists() and (audit := saved_pair(meta, cache)) is not None:
                done[chunk, gid] = audit
            else:
                tasks.append((str(root), chunk, gid))
        allowed = {folder / f'{gid}{suffix}' for gid in declared['game_ids']
                   if (folder / f'{gid}.json').exists() for suffix in ('.json', '-control.npz', '-candidate.npz')}
        if set(folder.iterdir()) - allowed:
            raise ValueError('orphan/partial stress files need inspection; never overwrite')
    if set(root.iterdir()) - allowed_root:
        raise ValueError('unexpected stress directories')
    resumed = len(done)
    print(f'{resumed}/30 verified paired chunks already complete; {len(tasks)} pending.', flush=True)
    if stop_after is not None:
        tasks = tasks[:stop_after]
    began = time.monotonic()
    with ProcessPoolExecutor(max_workers=jobs, initializer=init_worker) as pool:
        queue, pending = iter(tasks), {}
        def submit_one():
            task = next(queue, None)
            if task is not None:
                pending[pool.submit(work, task)] = task
        for _ in range(min(jobs, len(tasks))):
            submit_one()
        while pending:
            completed, _ = wait(pending, return_when=FIRST_COMPLETED)
            for future in completed:
                task = pending.pop(future)
                try:
                    chunk, gid, audit = future.result()
                except BaseException as error:
                    print(f'Stress task {task[1:]} failed: {error!r}; stop submitting, preserve completed files.', flush=True)
                    for active in pending:
                        active.cancel()
                    raise
                done[chunk, gid] = audit
                if len(done) % 3 == 0:
                    print(f'{len(done)}/30 audited paired chunks; 3 real games; {time.monotonic()-began:.1f}s', flush=True)
                submit_one()
    if fingerprints() != declared['fingerprints']:
        raise ValueError('stress source changed during execution')
    if len(done) != 30:
        print(f'Clean stop: {len(done)}/30 audited paired chunks; resume identical sources/name.', flush=True)
        return
    rows = []
    for gid in declared['game_ids']:
        records = [r for (chunk, game), value in done.items() if game == gid for r in value['audits']]
        if any(sum(r['worlds'] for r in records if r['label'] == side) != 10000 for side in ('control', 'candidate')):
            raise ValueError('incomplete10k stress arm')
        rows.append({'game': gid, 'worlds_per_arm': 10000,
            'lineup_fives_checked': sum(r['lineup_fives_checked'] for r in records),
            'max_replayed_player_minute_error': max(r['max_replayed_player_minute_error'] for r in records)})
    write_json(output, {'run': RUN, 'status': 'pass; independent chunk accounting, not an accuracy test',
        'real_games': 3, 'worlds_per_arm_game': 10000, 'paired_chunks': 30, 'games': rows,
        'resumed_completed_chunks': resumed, 'newly_executed_chunks': len(tasks),
        'configured_workers': jobs, 'inner_compute_threads': 1,
        'manifest_sha256': sha256_file(PLAN), 'elapsed_this_invocation': time.monotonic()-began,
        'captures': [{'game': gid, 'chunk': chunk, 'world_range': [chunk*1000, (chunk+1)*1000],
            'meta_sha256': sha256_file(pair_paths(root, chunk, gid)[1]), 'audit': value}
            for (chunk, gid), value in sorted(done.items())]}, pretty=True)
    print('All three10k stress pairs independently reconcile.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('freeze', 'run'))
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--stop-after', type=int)
    parser.add_argument('--jobs', type=int, default=10)
    args = parser.parse_args()
    if args.stop_after is not None and args.stop_after < 1:
        raise ValueError('positive clean-stop count required')
    if not 1 <= args.jobs <= 10:
        raise ValueError('1–10 total single-thread workers required')
    if any(os.environ.get(k) != '1' for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS')):
        raise ValueError('all inner compute threads must be limited to1')
    freeze() if args.action == 'freeze' else run(args.resume, args.stop_after, args.jobs)
