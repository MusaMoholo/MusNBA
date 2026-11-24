#!/usr/bin/env python3
"""One paired pass for D51 Rule 3 confirmation, world dependence and late-state capture."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import os
from pathlib import Path
import resource
import sys
import time
from unittest.mock import patch

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from basketball_common import read_json, sha256_file, write_json  # noqa: E402
from scripts import backtest, foul_out  # noqa: E402
from analysis.a1_parallel_world_probe import capture_digest  # noqa: E402

PLAN = ROOT / 'analysis/experiments/20261123_rule3_confirmation_manifest_v1.json'
LEGACY = '20261122T022323Z_a1_s01_control'


def expected_coverage(samples, actual):
    values = np.asarray(samples, dtype=float)
    if values.ndim != 1 or not len(values) or not np.isfinite(values).all() or not np.isfinite(actual):
        raise ValueError('expected PIT coverage needs finite samples and a known outcome')
    lower, upper = float((values < actual).mean()), float((values <= actual).mean())
    return (max(0., min(.9, upper) - max(.1, lower)) / (upper - lower)
            if upper > lower else float(.1 <= lower <= .9))


class Observer:
    """Read-only capture around the optional rule policy; consumes no simulation draws."""
    def __init__(self, corrected, policy=None):
        self.policy = policy if policy is not None else foul_out.Rule3Policy(capture_events=True) if corrected else None
        self.counts = {}  # backtest's legacy policy-summary fields are not this observer's output.

    def begin(self, g, worlds, available, seed):
        self.available = available.copy()
        self.trace, self.late = [], []
        self.previous = np.zeros_like(available, dtype=float)
        if self.policy:
            self.policy.begin(g, worlds, available, seed)

    def record(self, g, st, active, lineups, phase):
        full = st.ingame['pf_so_far'][active]
        if not np.isfinite(full).all() or (full < 0).any() or (full > 65535).any() or (full != np.floor(full)).any():
            raise ValueError('invalid captured personal-foul count')
        self.trace.append({'world': active.astype(np.uint16), 'period': st.period[active].astype(np.uint16),
                           'clock': st.clock[active].copy(), 'lineups': lineups.astype(np.uint16),
                           'all_fouls': full.astype(np.uint16), 'off': st.off[active].astype(np.uint8),
                           'tfouls': st.tfouls[active].astype(np.uint16),
                           'phase': np.full(len(active), phase, dtype=np.uint8)})

    def before_segment(self, g, st, active, scheduled):
        lineups = self.policy.before_segment(g, st, active, scheduled) if self.policy else scheduled
        self.previous[active] = st.ingame['pf_so_far'][active]
        self.record(g, st, active, lineups, 0)
        self.late_world = active[(st.period[active] >= 4) & (st.clock[active] <= 120)]
        w = self.late_world
        off = st.off[w]
        self.late_before = {'world': w.copy(), 'period': st.period[w].copy(), 'clock': st.clock[w].copy(),
                            'off': off.copy(), 'margin': st.score[w, off] - st.score[w, 1 - off],
                            'pf_before': np.column_stack([st.ingame['pf_so_far'][w][:, g.side == s].sum(1) for s in (0, 1)]),
                            'fga_before': st.box['fga'][w].sum((1, 2)),
                            'fg3a_before': st.box['fg3a'][w].sum((1, 2))}
        return lineups

    def after_fouls(self, g, st, active, offense, defense):
        changed = self.policy.after_fouls(g, st, active, offense, defense) if self.policy else np.zeros(len(active), bool)
        off = st.off[active]
        post = changed | (st.ingame['pf_so_far'][active] != self.previous[active]).any(axis=1)
        if post.any():
            lineups = np.empty((len(active), 2, 5), dtype=int)
            lineups[np.arange(len(active)), off] = offense
            lineups[np.arange(len(active)), 1 - off] = defense
            self.record(g, st, active[post], lineups[post], 1)
        w = self.late_world
        if len(w):
            self.late.append({**self.late_before, 'clock_after': st.clock[w].copy(),
                              'pf_after': np.column_stack([st.ingame['pf_so_far'][w][:, g.side == s].sum(1) for s in (0, 1)]),
                              'fga_after': st.box['fga'][w].sum((1, 2)),
                              'fg3a_after': st.box['fg3a'][w].sum((1, 2))})
        return changed

    def finish(self, g, st):
        if self.policy:
            self.policy.finish(g, st)
        if not st.done.all():
            raise ValueError('observer captured an unfinished game')

    def capture(self, g, st):
        result = {'game_id': np.asarray(str(g.game['game_id'])), 'player_ids': np.asarray(g.ids),
                  'side': g.side.copy(), 'available': self.available.copy(), 'final_period': st.period.copy(),
                  'final_score': st.score.copy(), 'final_tfouls': st.tfouls.copy(), 'possessions': st.poss.copy(),
                  'minutes': st.minutes.copy(), 'team_points': st.pts.copy(),
                  'player_ft_pct': g.P['ft_pct'].copy()}
        for key in ('pts', 'pf', 'oreb', 'dreb', 'ast', 'fg3m', 'fta', 'ftm', 'fga', 'fg3a'):
            result['player_' + {'pts': 'points', 'pf': 'fouls'}.get(key, key)] = st.box[key].copy()
        for key in self.trace[0]:
            result['trace_' + key] = np.concatenate([r[key] for r in self.trace])
        result['trace_fouls'] = result['trace_all_fouls'][np.arange(len(result['trace_world']))[:, None, None], result['trace_lineups']]
        for key in self.late_before:
            result['late_' + key] = np.concatenate([r[key] for r in self.late]) if self.late else np.empty((0, 2) if key == 'pf_before' else (0,))
        for key in ('clock_after', 'pf_after', 'fga_after', 'fg3a_after'):
            result['late_' + key] = np.concatenate([r[key] for r in self.late]) if self.late else np.empty((0, 2) if key == 'pf_after' else (0,))
        events = self.policy.technical_events if self.policy else []
        for key in ('world', 'period', 'clock', 'fouler', 'shooter', 'made', 'probability', 'offensive'):
            dtype = float if key in ('clock', 'probability') else int
            result['technical_' + key] = np.asarray([r[key] for r in events], dtype=dtype)
        return result


def init_worker(worlds, stream):
    backtest._init('folds/v1.2d_F4_all', str(ROOT / 'models/v1.2d.json'), 'F4', worlds,
                   rotation='targets', pool=0, stream=stream)


def add_coverage(result, capture):
    points = capture['team_points']
    measures = {'home': points[:, 0].sum(1), 'away': points[:, 1].sum(1),
                'total': points.sum((1, 2)), 'margin': points[:, 0].sum(1) - points[:, 1].sum(1)}
    actual = {'home': result['real_home'], 'away': result['real_away'],
              'total': result['real_home'] + result['real_away'], 'margin': result['real_home'] - result['real_away']}
    for q in range(4):
        for kind, values in (('total', points[:, 0, q] + points[:, 1, q]),
                             ('margin', points[:, 0, q] - points[:, 1, q])):
            key = f'q{q + 1}_{kind}'
            measures[key], actual[key] = values, result[f'{key}_actual']
    for key, samples in measures.items():
        result[key + '_coverage_expected'] = expected_coverage(samples, actual[key])
    ids = capture['player_ids'].tolist()
    for row in result['players']:
        i = ids.index(row['player'])
        samples = {'min': capture['minutes'][:, i].sum(1), 'pts': capture['player_points'][:, i].sum(1),
                   'reb': (capture['player_oreb'][:, i] + capture['player_dreb'][:, i]).sum(1),
                   'ast': capture['player_ast'][:, i].sum(1), 'fg3m': capture['player_fg3m'][:, i].sum(1)}
        for stat, values in samples.items():
            observed = row.get(stat + '_actual')
            if observed is not None and np.isfinite(observed):
                row[stat + '_coverage_expected'] = expected_coverage(values, observed)


def paired_game(task, *, labels=('control', 'candidate'), corrected=(False, True), persist=True, policy_factory=None):
    gid, directory = task
    folder = Path(directory)
    eng = backtest._W['engine']
    original = eng.simulate
    result = {'game': gid, 'outputs': {}}
    for label in labels:
        observer = Observer(corrected[('control', 'candidate').index(label)],
                            policy_factory(label) if policy_factory else None)
        previous = eng.rotation_policy
        eng.rotation_policy = observer
        saved = {}
        def run(g, worlds, seed):
            output = original(g, worlds, seed)
            saved['capture'] = observer.capture(g, eng.last)
            pre = backtest._W['inputs'][0]
            profile = pre.loc[pre['game_id'].eq(gid)].set_index('player').reindex(g.ids)
            saved['capture']['prior_usage'] = profile['usage'].to_numpy(float)
            saved['capture']['prior_start_share'] = profile['start_share'].to_numpy(float)
            return output
        try:
            with patch.object(eng, 'simulate', side_effect=run):
                values = backtest.run_game(gid)
        finally:
            eng.rotation_policy = previous
        capture = saved['capture']
        add_coverage(values, capture)
        path = folder / f'{gid}-{label}.npz'
        if path.exists():
            raise FileExistsError(path)
        with path.with_suffix('.partial').open('xb') as stream:
            np.savez_compressed(stream, **capture)
        path.with_suffix('.partial').rename(path)
        result['outputs'][label] = {'capture': str(path.relative_to(ROOT)), 'sha256': sha256_file(path),
                                    'world_sha256': capture_digest(capture), 'result': values,
                                    'counts': dict(observer.policy.counts) if observer.policy else {}}
    result['worker_pid'] = os.getpid()
    result['worker_peak_rss_bytes'] = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * (1 if sys.platform == 'darwin' else 1024)
    if persist:
        write_json(folder / f'{gid}.json', result, pretty=False)
    return result


def fingerprints():
    model = ROOT / 'data/models/folds/v1.2d_F4_all'
    cfg = read_json(model / 'config.json')
    feat = ROOT / Path(cfg['features']).parent
    paths = [PLAN, Path(__file__), ROOT / 'scripts/foul_out.py', ROOT / 'analysis/rule3_capture_audit.py',
             ROOT / 'docs/protocols/rule3_implementation_20261123.md', ROOT / 'models/v1.2d.json',
             feat / 'pregame.parquet', feat / 'team_pregame.parquet', feat / 'features_report.json',
             ROOT / cfg['matchup'], ROOT / 'data/derived/athletes.parquet', ROOT / 'data/derived/teams.json']
    paths.extend(model.glob('*'))
    paths.extend(ROOT / f'scripts/{name}.py' for name in ('engine', 'backtest', 'minutes', 'projection', 'rotations', 'matchups', 'nodes', 'a1_compare', 'a1_substitution_world_audit'))
    paths.append(ROOT / 'basketball_common.py')
    for year in range(2023, 2027):
        paths.extend(ROOT / f'data/derived/history/{year}/{name}' for name in
                     ('segments.parquet', 'stints.parquet', 'on_court.parquet', 'player_periods.csv.gz'))
        paths.append(ROOT / f'data/raw/hoopr/player_box_{year}.parquet')
    required = paths[:]
    if any(not p.is_file() for p in required):
        raise FileNotFoundError([str(p) for p in required if not p.is_file()])
    return {str(p.relative_to(ROOT)): sha256_file(p) for p in sorted(set(paths))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--pilot', action='store_true')
    modes.add_argument('--stream-check', action='store_true')
    modes.add_argument('--stress', action='store_true')
    parser.add_argument('--jobs', type=int, default=8)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--stop-after', type=int)
    args = parser.parse_args()
    if not args.name.isidentifier() or not args.name.isascii() or not 1 <= args.jobs <= 10 or (args.stop_after is not None and args.stop_after < 1):
        raise ValueError('ASCII name and 1–10 single-thread workers required')
    if any(os.environ.get(name) != '1' for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS')):
        raise ValueError('set OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1')
    declared = read_json(PLAN)
    ids = declared['pilot_games'] if args.pilot else declared['stress_10000_games'] if args.stress else declared['independent_stream_games'] if args.stream_check else declared['game_ids']
    ids = sorted(ids)
    worlds, stream = (10000 if args.stress else 1000), (1 if args.stream_check else None)
    root = ROOT / 'data/derived/experiments' / args.name
    output = ROOT / f'analysis/experiments/{args.name}.json'
    signature = {'game_ids': ids, 'worlds': worlds, 'stream': stream, 'fingerprints': fingerprints()}
    if args.resume:
        if output.exists() or read_json(root / 'plan.json') != signature:
            raise ValueError('resume source/input identity differs or run already complete')
    else:
        if root.exists() or output.exists():
            raise FileExistsError('fresh namespace required')
        root.mkdir(parents=True)
        write_json(root / 'plan.json', signature, pretty=True)
    done = {}
    allowed = {root / 'plan.json'}
    for gid in ids:
        path = root / f'{gid}.json'
        if path.exists():
            row = read_json(path)
            if row['game'] != gid:
                raise ValueError('completed game identity differs')
            if set(row['outputs']) != {'control', 'candidate'}:
                raise ValueError('completed pair is missing a branch')
            done[gid] = row
            allowed.add(path)
            for label, entry in row['outputs'].items():
                p = ROOT / entry['capture']
                reused = row.get('reused_control') if label == 'control' else None
                if reused:
                    original = ROOT / reused['meta']
                    if (sha256_file(original) != reused['sha256']
                            or read_json(original)['outputs']['candidate'] != entry):
                        raise ValueError('reused control differs from its qualified source')
                elif p != root / f'{gid}-{label}.npz':
                    raise ValueError('completed capture belongs to a different run')
                if label not in ('control', 'candidate') or sha256_file(p) != entry['sha256']:
                    raise ValueError('completed capture differs')
                allowed.add(p)
    if set(root.iterdir()) - allowed:
        raise ValueError('orphan/partial files require inspection; refusing automatic resume')
    pending = [gid for gid in ids if gid not in done]
    selected = pending[:args.stop_after] if args.stop_after is not None else pending
    started = time.monotonic()
    if selected:
        with ProcessPoolExecutor(max_workers=min(args.jobs, len(selected)), initializer=init_worker, initargs=(worlds, stream)) as pool:
            for future in as_completed([pool.submit(paired_game, (gid, str(root))) for gid in selected]):
                row = future.result()
                done[row['game']] = row
                if args.pilot or len(done) % max(1, len(ids) // 10) == 0:
                    print(f'{len(done)}/{len(ids)} paired games in {time.monotonic() - started:.1f}s', flush=True)
    if signature['fingerprints'] != fingerprints():
        raise ValueError('source/model/input changed during paired run')
    if len(done) != len(ids):
        print(f'clean stop: {len(done)}/{len(ids)} persisted games; resume same name', flush=True)
        return
    for label in ('control', 'candidate'):
        name = args.name + '_' + label
        games = [dict(done[gid]['outputs'][label]['result']) for gid in ids]
        players = [r for game in games for r in game.pop('players')]
        pd.DataFrame(games).to_parquet(ROOT / f'data/derived/experiments/{name}.parquet', index=False)
        pd.DataFrame(players).to_parquet(ROOT / f'data/derived/experiments/{name}_players.parquet', index=False)
        write_json(ROOT / f'analysis/experiments/{name}.json', {'run': name,
                   **declared.get('runner_metadata', {'fold':'F4', 'config':'models/v1.2d.json', 'models':'folds/v1.2d_F4_all'}),
                   'games': len(ids), 'worlds': worlds, 'rotation': 'targets',
                   'pool': 0, 'known_starters': False, 'simulation_stream': stream, 'seed_key': None,
                   'game_ids': ids, 'kind': 'conditional paired rule confirmation; no pre-game injury calibration'}, pretty=True)
    write_json(output, {'kind': 'D51 paired rule confirmation and raw diagnostic capture', 'run': args.name,
               **signature, 'directory': str(root.relative_to(ROOT)), 'pilot': args.pilot, 'stress': args.stress,
               'workers': min(args.jobs, len(selected)) if selected else 0, 'elapsed_this_invocation': time.monotonic() - started,
               'resumed_completed_games': len(ids) - len(selected),
               'captures': [{'game': gid, 'meta': str((root / f'{gid}.json').relative_to(ROOT)),
                             'meta_sha256': sha256_file(root / f'{gid}.json')} for gid in ids],
               'release': 'not enabled; independent accounting/score/confirmation gates still apply'}, pretty=True)


if __name__ == '__main__':
    main()
