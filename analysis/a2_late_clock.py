#!/usr/bin/env python3
"""Exact, prior-fitted late-clock screen. Never fits or scores the protected season."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, NBA_TEAM_IDS, read_json, sha256_file, write_json
from scripts.evaluate import FOLDS, TEST_FROM

PROTOCOL = ROOT / 'docs/protocols/a2_late_clock_20261123.md'
MANIFEST = ROOT / 'analysis/experiments/20261123_a2_late_clock_manifest_v1.json'
KNOWN = ('shot', 'turnover', 'fouled', 'foul', 'end_period', 'violation', 'jump_ball')


def cell(clock, margin):
    return np.searchsorted([4, 8, 16], clock, side='left') * 7 + np.searchsorted([-8, -3, 0, 1, 4, 9], margin, side='right')


def valid(frame):
    c, t = frame['start_clock'], frame['shot_time']
    ending = frame['end_type'].eq('end_period')
    return (frame['end_type'].isin(KNOWN) & np.isfinite(c) & c.gt(0) & c.le(24)
            & (ending | (np.isfinite(t) & t.ge(0) & t.le(c))))


@dataclass
class Pool:
    x: np.ndarray
    quiet: float

    def __post_init__(self):
        self.x = np.sort(np.asarray(self.x, dtype=float))
        if not len(self.x) or not np.isfinite(self.x).all() or (self.x < 0).any() or not 0 <= self.quiet <= 1:
            raise ValueError('invalid empirical pool')
        n = len(self.x)
        self.prefix = np.r_[0., np.cumsum(self.x)]
        self.weighted = np.r_[0., np.cumsum((2 * np.arange(1, n + 1) - n - 1) * self.x)]

    def score(self, outcome, limit):
        """CRPS of min(X, limit), analytically, without constructing sampled forecasts."""
        y, cap = np.broadcast_arrays(np.asarray(outcome, float), np.asarray(limit, float))
        if not np.isfinite(y).all() or not np.isfinite(cap).all() or ((y < 0) | (y > cap)).any():
            raise ValueError('invalid outcome/support')
        n = len(self.x)
        k = np.searchsorted(self.x, cap, side='right')
        r = np.searchsorted(self.x, y, side='left')
        absolute = y * r - self.prefix[r] + self.prefix[k] - self.prefix[r] + (n - k) * cap - y * (n - r)
        dispersion = (self.weighted[k] + cap * k * (n - k)) / n**2
        return absolute / n - dispersion


def fit(history, cutoff):
    if cutoff >= TEST_FROM:
        raise ValueError('this experiment cannot fit the protected season')
    train = history[history['game_ok'] & history['date_et'].le(cutoff) & history['start_clock'].le(24)].copy()
    if not len(train) or train['start_clock'].isna().any():
        raise ValueError('missing legacy training pool')
    bucket = np.floor(train['start_clock']).clip(0, 24).astype(int)
    quiet = train['end_type'].isin(('end_period', 'unknown')).to_numpy()
    # Match Models.late float32 tables and Engine.simulate's effective-time transformation exactly.
    raw = np.minimum(train['shot_time'].clip(lower=0).fillna(0).to_numpy(np.float32), train['start_clock'].to_numpy(np.float32))
    legacy_values = np.where(quiet, 24., raw)
    legacy = {int(k): Pool(legacy_values[bucket.eq(k)], quiet[bucket.eq(k)].mean()) for k in bucket.unique()}
    clean = train.loc[valid(train)].copy()
    clean['quiet'] = clean['end_type'].eq('end_period')
    clean['effective'] = np.where(clean['quiet'], clean['start_clock'], clean['shot_time'])
    clean['bucket'] = np.floor(clean['start_clock']).astype(int)
    bridge = {int(k): Pool(np.where(g['quiet'], 24., g['effective']), g['quiet'].mean()) for k, g in clean.groupby('bucket')}
    contextual = clean[clean['period'].ge(4) & np.isfinite(clean['score_off']) & np.isfinite(clean['score_def'])].copy()
    contextual['cell'] = cell(contextual['start_clock'], contextual['score_off'] - contextual['score_def'])
    pools, support = {}, {}
    for k, group in contextual.groupby('cell'):
        enough = len(group) >= 100 and group['game_id'].nunique() >= 30
        support[int(k)] = {'opportunities': len(group), 'games': int(group['game_id'].nunique()), 'supported': enough}
        if enough:
            pools[int(k)] = Pool(group['effective'] / group['start_clock'], group['quiet'].mean())
    info = {'cutoff': cutoff, 'latest_training_date': str(train['date_et'].max()), 'legacy_rows': len(train),
            'clean_rows': len(clean), 'excluded_unknown_or_invalid': len(train) - len(clean), 'cells': support}
    return {'legacy': legacy, 'bridge': bridge, 'contextual': pools, 'info': info}


def predict(table, frame):
    """Return per-opportunity time/Brier losses plus the exact fallback source."""
    if not valid(frame).all():
        raise ValueError('evaluation contains an unknown/invalid outcome')
    clock = frame['start_clock'].to_numpy(float)
    quiet = frame['end_type'].eq('end_period').to_numpy()
    outcome = np.where(quiet, clock, frame['shot_time'])
    bucket = np.floor(clock).astype(int)
    margin = (frame['score_off'] - frame['score_def']).to_numpy(float)
    cells = cell(clock, margin)
    eligible_context = frame['period'].ge(4).to_numpy() & np.isfinite(margin)
    result = frame[['game_id', 'date_et', 'period', 'start_clock']].copy().reset_index(drop=True)
    for mode in ('legacy', 'bridge', 'candidate'):
        losses = np.empty((len(frame), 2))
        sources = []
        for j in range(len(frame)):
            key = int(bucket[j])
            if key not in table['legacy']:
                raise ValueError(f'no legacy support for clock {clock[j]}')
            source, pool = 'legacy', table['legacy'][key]
            if mode != 'legacy' and (mode == 'bridge' or eligible_context[j]):
                if key in table['bridge']:
                    source, pool = 'bridge', table['bridge'][key]
                if mode == 'candidate' and int(cells[j]) in table['contextual']:
                    source, pool = 'contextual', table['contextual'][int(cells[j])]
            t = pool.score(outcome[j] / clock[j], 1.) if source == 'contextual' else pool.score(outcome[j], clock[j]) / clock[j]
            losses[j] = [t, (pool.quiet - quiet[j])**2]
            sources.append(source)
        for i, label in enumerate(('time', 'quiet')):
            result[f'{mode}_{label}'] = losses[:, i]
        result[f'{mode}_joint'] = losses.mean(1)
        result[f'{mode}_source'] = sources
    return result


def summarise(rows):
    names = [f'{mode}_{stat}' for mode in ('legacy', 'bridge', 'candidate') for stat in ('time', 'quiet', 'joint')]
    grouped = rows.groupby('game_id')[names].sum()
    count = rows.groupby('game_id').size().reindex(grouped.index).to_numpy()
    weights = np.random.default_rng(20261122).multinomial(len(grouped), np.full(len(grouped), 1 / len(grouped)), size=10000)
    means = grouped.sum() / count.sum()
    boot = weights @ grouped.to_numpy() / (weights @ count)[:, None]
    positions = {name: i for i, name in enumerate(names)}
    support = len(grouped) >= 50 and len(rows) >= 100
    report = {'games': len(grouped), 'opportunities': len(rows), 'supported': support,
              'scores': {name: float(value) for name, value in means.items()}, 'comparisons': {}}
    for control in ('legacy', 'bridge'):
        comparisons = {}
        for stat in ('time', 'quiet', 'joint'):
            a, b = f'{control}_{stat}', f'candidate_{stat}'
            comparisons[stat] = {'change': float(means[b] - means[a]),
                                 'ci_95': np.quantile(boot[:, positions[b]] - boot[:, positions[a]], [.025, .975]).tolist() if support else None}
        report['comparisons'][control] = comparisons
    report['primary_pass'] = support and all(report['comparisons'][c]['joint']['ci_95'][1] < 0 for c in ('legacy', 'bridge'))
    report['component_compatible'] = support and all(report['comparisons'][c][s]['ci_95'][1] < .005
                                                     for c in ('legacy', 'bridge') for s in ('time', 'quiet'))
    report['candidate_sources'] = rows['candidate_source'].value_counts().to_dict()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=('screen', 'confirmation'), required=True)
    parser.add_argument('--screen', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    code_hash = sha256_file(Path(__file__))
    if args.phase == 'confirmation':
        screen = read_json(args.screen) if args.screen else {}
        if screen.get('decision') != 'screen_pass' or screen.get('source_sha256') != code_hash or screen.get('protocol_sha256') != sha256_file(PROTOCOL):
            raise ValueError('confirmation requires a passed screen of this exact recipe')
    paths = sorted((DERIVED / 'history').glob('*/segments.parquet'))
    columns = ['game_id', 'date_et', 'game_ok', 'start_clock', 'shot_time', 'end_type', 'period',
               'score_off', 'score_def', 'season_type', 'offense', 'defense']
    history = pd.concat([pd.read_parquet(p, columns=columns, filters=[('start_clock', '<=', 24), ('date_et', '<', TEST_FROM)]) for p in paths], ignore_index=True)
    if history['date_et'].ge(TEST_FROM).any():
        raise ValueError('protected observations entered the experiment')
    folder = ROOT / 'data/derived/experiments' / args.output.stem
    folder.mkdir(exist_ok=False)
    outputs, reports, pools = [], {}, {}
    folds = ('F1', 'F2', 'F3') if args.phase == 'screen' else ('F4',)
    for fold in folds:
        cutoff, start, stop = FOLDS[fold]
        table = fit(history, cutoff)
        raw = history[history['game_ok'] & history['date_et'].between(start, stop) & history['period'].ge(4)
                      & history['season_type'].eq(2) & history['offense'].astype(str).isin(NBA_TEAM_IDS)
                      & history['defense'].astype(str).isin(NBA_TEAM_IDS)]
        if fold == 'F4':
            raw = raw[raw['game_id'].isin(read_json(MANIFEST)['game_ids'])]
        work = raw.loc[valid(raw)]
        scored = predict(table, work)
        scored['fold'] = fold
        scored.to_parquet(folder / f'{fold}.parquet', index=False)
        write_json(folder / f'{fold}_pools.json', {name: {str(k): {'x': p.x.tolist(), 'quiet': float(p.quiet)} for k, p in table[name].items()}
                                                   for name in ('legacy', 'bridge', 'contextual')}, pretty=False)
        reports[fold] = {**summarise(scored), 'excluded_unknown_or_invalid': len(raw) - len(work), 'training': table['info']}
        outputs.append(scored)
        pools[fold] = sha256_file(folder / f'{fold}_pools.json')
        print(f'{fold}: {len(work)} opportunities; contextual {reports[fold]["candidate_sources"].get("contextual", 0)}', flush=True)
    combined = summarise(pd.concat(outputs, ignore_index=True))
    passed = combined['primary_pass'] and combined['component_compatible'] and all(r['component_compatible'] for r in reports.values())
    report = {'phase': args.phase, 'source_sha256': code_hash, 'protocol_sha256': sha256_file(PROTOCOL),
              'manifest_sha256': sha256_file(MANIFEST), 'inputs': {str(p.relative_to(ROOT)): sha256_file(p) for p in paths},
              'fitted_pools_sha256': pools, 'folds': reports, 'pooled': combined,
              'final_test_untouched_from': TEST_FROM, 'decision': ('screen_pass' if args.phase == 'screen' else 'confirmation_pass') if passed else 'retain_legacy',
              'artifacts': str(folder.relative_to(ROOT))}
    write_json(args.output, report, pretty=True)
    print(report['decision'], flush=True)


if __name__ == '__main__':
    main()
