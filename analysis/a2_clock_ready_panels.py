#!/usr/bin/env python3
"""Input-only readiness amendment; unchanged clock comparison on 100 supported games per fold."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from basketball_common import read_json, write_json, sha256_file
from analysis import a2_clock_engine as clock
from scripts import backtest, rotations
import pandas as pd

EXP = ROOT / 'analysis/experiments'
PLAN = EXP / '20261123_a2_clock_ready_panels_v1.json'
BASE = EXP / '20261122_a1_pre_candidate_manifest.json'
PROTOCOL = ROOT / 'docs/protocols/a2_clock_readiness_amendment_20261123.md'


def position(value):
    return isinstance(value, str) and bool(value.strip())


def inspect_fold(fold):
    info = clock.metadata(fold)
    cfg = ROOT / info['config']
    prepath = ROOT / read_json(cfg)['default']['features']
    pre = pd.read_parquet(prepath, columns=['game_id', 'date_et', 'team', 'player', 'pos'])
    season = int(backtest.FOLDS[fold][2][:4])
    stpath = ROOT / f'data/derived/history/{season}/stints.parquet'
    stints = pd.read_parquet(stpath)
    ids = [r['game_id'] for r in read_json(BASE)['confirmation'][fold]['games']]
    order = sorted(ids, key=lambda gid: hashlib.sha256(f'a2-clock-engine-{fold}|{gid}'.encode()).hexdigest())
    original = read_json(clock.MANIFEST)['earlier'][fold]
    if set(order[:100]) != set(original):
        raise ValueError('original hash order does not reproduce frozen panel')
    records = []
    for gid in order:
        rows = pre[pre['game_id'].eq(gid)]
        missing = rows[~rows['pos'].map(position)]
        reasons = []
        if rows['team'].nunique() != 2 or rows.groupby('team').size().min() < 5:
            reasons.append('fewer than two five-player input rosters')
        if len(missing):
            reasons.append('missing dated player position')
        unknown_templates = []
        for team, players in rows.groupby('team'):
            for template in rotations.templates_for(stints, team, str(players['date_et'].iloc[0])):
                if any(not position(slot['pos']) for slot in template['slots']):
                    unknown_templates.append(template['game_id'])
        if unknown_templates:
            reasons.append('missing prior rotation-template position')
        records.append({'game_id': gid, 'supported': not reasons, 'reasons': reasons,
            'missing_player_ids': missing['player'].tolist(), 'unknown_template_games': sorted(set(unknown_templates))})
    selected = [r['game_id'] for r in records if r['supported']][:100]
    if len(selected) != 100:
        raise ValueError(f'{fold}: fewer than100 supported games; no panel expansion allowed')
    return fold, {'game_ids': selected, 'original_ids': original,
        'excluded_original_ids': sorted(set(original) - set(selected)),
        'replacement_ids': sorted(set(selected) - set(original)), 'readiness': records,
        'input_sha256': {str(p.relative_to(ROOT)): sha256_file(p) for p in (cfg, prepath, stpath)}}


def fingerprints():
    return {**clock.fingerprints(), **{str(p.relative_to(ROOT)): sha256_file(p)
        for p in (Path(__file__), PLAN, BASE, PROTOCOL)}}


def freeze():
    if PLAN.exists():
        raise FileExistsError('readiness panel already frozen')
    with ProcessPoolExecutor(max_workers=3) as pool:
        panels = dict(pool.map(inspect_fold, ('F1', 'F2', 'F3')))
    write_json(PLAN, {'frozen_at': datetime.now(timezone.utc).isoformat(),
        'kind': 'input-only replacement before any earlier-fold quality score; F4 development is known',
        'selection': 'first100 supported in unchanged SHA256(a2-clock-engine-{fold}|game_id) order within original200',
        'earlier': panels, 'source_sha256': {str(p.relative_to(ROOT)): sha256_file(p)
            for p in (Path(__file__), BASE, PROTOCOL, clock.MANIFEST)},
        'limits': 'Conditional on usable dated positions; excluded inputs are unsupported, never evidence of clock harm. No new roster, position fill, fit, seed, threshold or final-season use.'}, pretty=True)
    for fold, data in panels.items():
        print(f"{fold}:100 selected; {len(data['excluded_original_ids'])} original unsupported inputs replaced", flush=True)


def declaration(path):
    result = read_json(path)
    if Path(path) == PLAN:
        return {**result, 'game_ids': result['earlier'][clock.FOLD]['game_ids'],
            'runner_metadata': clock.metadata(clock.FOLD)}
    return result


def game(task):
    gid, directory = task
    old = ROOT / f'data/derived/experiments/a2_clock_earlier_{clock.FOLD.lower()}_20261123_v1'
    meta = old / f'{gid}.json'
    if not meta.exists():
        return clock.game(task)
    if read_json(old / 'plan.json')['fingerprints'] != clock.fingerprints():
        raise ValueError('retained completed pair is from a different recipe')
    row = read_json(meta)
    for label, entry in row['outputs'].items():
        source = ROOT / entry['capture']
        if sha256_file(source) != entry['sha256']:
            raise ValueError('retained pair capture changed')
        target = Path(directory) / f'{gid}-{label}.npz'
        os.link(source, target)
        entry['capture'] = str(target.relative_to(ROOT))
    row['reused_pair'] = {'meta': str(meta.relative_to(ROOT)), 'sha256': sha256_file(meta)}
    target = Path(directory) / f'{gid}.json'
    write_json(target, row, pretty=False)
    cache = Path(directory).with_name(Path(directory).name + '_independent_audits')
    cache.mkdir(exist_ok=True)
    clock.auditor.audit_pair((str(target), str(cache / f'{gid}.json')))
    return row


if __name__ == '__main__':
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('action', choices=('freeze', 'run'))
    parser.add_argument('--fold', choices=('F1', 'F2', 'F3'))
    args, remaining = parser.parse_known_args()
    if args.action == 'freeze':
        freeze()
    else:
        if not args.fold:
            raise ValueError('earlier fold required')
        clock.FOLD, clock.PHASE = args.fold, 'earlier'
        os.environ['MUSNBA_CLOCK_FOLD'], os.environ['MUSNBA_CLOCK_PHASE'] = args.fold, 'earlier'
        frozen = read_json(PLAN)
        for name, digest in frozen['source_sha256'].items():
            if sha256_file(ROOT / name) != digest:
                raise ValueError('readiness source changed')
        for name, digest in frozen['earlier'][args.fold]['input_sha256'].items():
            if sha256_file(ROOT / name) != digest:
                raise ValueError('readiness inputs changed')
        if read_json(clock.MANIFEST)['source_sha256'] != clock.sources():
            raise ValueError('original frozen clock recipe changed')
        name = remaining[remaining.index('--name') + 1]
        sys.argv = [sys.argv[0], *remaining]
        clock.paired.PLAN, clock.paired.read_json = PLAN, declaration
        clock.paired.fingerprints, clock.paired.paired_game = fingerprints, game
        clock.paired.init_worker = clock.init_worker
        clock.paired.main()
        if (EXP / f'{name}.json').exists():
            clock.finish_audit(name)
