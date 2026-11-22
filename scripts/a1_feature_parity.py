#!/usr/bin/env python3
"""Compare training and engine matchup inputs on identical pinned historical states.

  .venv/bin/python -m scripts.a1_feature_parity --output analysis/experiments/new-parity.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, sha256_file, write_json  # noqa: E402
from scripts import engine, matchups, nodes  # noqa: E402

MANIFEST = ROOT / 'analysis' / 'experiments' / '20261122_a1_manifest.json'
FEATURES = DERIVED / 'variants' / 'matchup' / 'features' / 'pregame.parquet'
BODY = DERIVED / 'athletes.parquet'
THETA = ROOT / 'models' / 'matchup_2025-12-31.json'


def audit(features: Path = FEATURES, theta_path: Path = THETA, fold: str | None = None) -> dict:
    features, theta_path = features.resolve(), theta_path.resolve()
    manifest = json.loads(MANIFEST.read_text())
    sample = manifest['confirmation'][fold]['games'] if fold else manifest['control']['games']
    game_ids = [str(g['game_id']) for g in sample[:3]]
    first_date = str(sample[0]['date_et'])
    year, month = int(first_date[:4]), int(first_date[5:7])
    segments = DERIVED / 'history' / str(year + (month >= 10)) / 'segments.parquet'
    seg = pd.read_parquet(segments)
    seg = seg[seg['game_id'].astype(str).isin(game_ids) & seg['game_ok']].copy().reset_index(drop=True)
    if set(seg['game_id'].astype(str)) != set(game_ids):
        raise ValueError('not all pinned sample games have reconciled segments')
    seg['seg_id'] = np.arange(len(seg))
    pre = pd.read_parquet(features)
    pre = pre[pre['game_id'].astype(str).isin(game_ids)].copy()
    pre['game_id'], pre['player'] = pre['game_id'].astype(str), pre['player'].astype(str)
    if pre.duplicated(['game_id', 'player']).any():
        raise ValueError('duplicate pre-game player profile')
    feature_report = features.parent / 'features_report.json'
    report = json.loads(feature_report.read_text()) if feature_report.exists() else {}
    prior_positions = bool(report.get('causal_positions'))
    if prior_positions:
        from scripts.features import known_group
        pre['grp'] = pre['pos'].map(known_group)
    else:
        pre['grp'] = pre['pos'].map(nodes.group)
    body = pd.read_parquet(BODY, columns=['player', 'height_in', 'weight_lb'])
    body['player'] = body['player'].astype(str)
    if body['player'].duplicated().any():
        raise ValueError('duplicate player body record')
    profile = nodes.PROFILE + [c for c in nodes.OPTIONAL_PROFILE if c in pre.columns]
    def_profile = profile + [c for c in nodes.DEF_SIDE if c in pre.columns]
    chain = object.__new__(nodes.Chain)
    chain.seg = seg
    chain._preserve_groups = prior_positions
    chain._relative_missing_policy = report.get('relative_missing_policy', 'legacy')
    chain.off = nodes.Chain._side(seg, pre, 'off', profile, preserve_missing_group=prior_positions)
    chain.dfn = nodes.Chain._side(seg, pre, 'def', def_profile, preserve_missing_group=prior_positions)
    chain._deterrence = False
    theta = json.loads(theta_path.read_text())
    if theta.get('kind') == 'dated_implicit_schedule':
        used = Path(report['matchup'])
        if not used.is_absolute():
            used = ROOT / used
        if used.resolve() != theta_path or report['input_sha256'][report['matchup']] != sha256_file(theta_path):
            raise ValueError('dated assignment differs from the profile-build schedule')
    chain._matchup(theta)
    relative = chain._relative_missing_policy == 'lineup_median'
    if relative:
        chain._relative()
        present = [c for c in nodes.OPTIONAL_PROFILE if c in pre.columns]
        def_present = [c for c in nodes.DEF_SIDE if c in pre.columns]
        chain.lineup = nodes.LINEUP + [c for c, (side, src, _) in nodes.OPTIONAL_LINEUP.items()
                                      if src in present or (side == 'def' and src in def_present)]
        chain._lineups()
    theta_engine = object.__new__(engine.Engine)
    theta_engine.m = SimpleNamespace(theta=None, relative_missing_policy=chain._relative_missing_policy,
                                     style=[c for c in nodes.OPTIONAL_PROFILE if c in pre.columns],
                                     optional_lineup=[c for c in chain.lineup if c in nodes.OPTIONAL_LINEUP] if relative else [])
    comparisons: dict[str, dict] = {}
    excluded = Counter()

    def compare(column, trained, served):
        trained, served = np.asarray(trained, dtype=np.float32), np.asarray(served, dtype=np.float32)
        same = np.isclose(trained, served, rtol=1e-6, atol=1e-6, equal_nan=True)
        finite = np.isfinite(trained) & np.isfinite(served)
        result = comparisons.setdefault(column, {'states': 0, 'mismatches': 0, 'both_missing': 0,
                                                   'max_absolute_difference': 0.0})
        result['states'] += len(same)
        result['mismatches'] += int((~same).sum())
        result['both_missing'] += int((np.isnan(trained) & np.isnan(served)).sum())
        if finite.any():
            result['max_absolute_difference'] = max(result['max_absolute_difference'],
                                                    float(np.max(np.abs(trained[finite] - served[finite]))))

    for game_id in game_ids:
        game_dates = seg.loc[seg['game_id'].astype(str).eq(game_id), 'date_et'].unique()
        if len(game_dates) != 1:
            raise ValueError(f'{game_id}: expected exactly one game date')
        theta_engine.m.theta = (matchups.dated_masks(theta, game_dates)[0][0]
                                if theta.get('kind') == 'dated_implicit_schedule' else theta)
        profiles = pre[pre['game_id'].eq(game_id)].set_index('player')
        profiles = profiles.join(body.set_index('player'), how='left', rsuffix='_body')
        candidates = chain.seg[chain.seg['game_id'].astype(str).eq(game_id) & chain.seg['actor'].notna()]
        offenses = chain.off[chain.off['seg_id'].isin(candidates['seg_id'])].groupby('seg_id')['player'].agg(list)
        defenders = chain.dfn[chain.dfn['seg_id'].isin(candidates['seg_id'])].groupby('seg_id')['player'].agg(list)
        usable, actor_ids, offender_ids, defender_ids = [], [], [], []
        for row in candidates.itertuples(index=False):
            ds = defenders.get(row.seg_id, [])
            offensive_players = offenses.get(row.seg_id, [])
            actor = str(row.actor)
            if actor not in offensive_players:
                excluded['actor_not_on_recorded_offensive_lineup'] += 1
                continue
            if len(offensive_players) != 5 or len(set(offensive_players)) != 5:
                excluded['invalid_offensive_lineup'] += 1
                continue
            if len(ds) != 5 or len(set(ds)) != 5:
                excluded['invalid_defender_lineup'] += 1
                continue
            if any(str(player) not in profiles.index for player in offensive_players + ds):
                excluded['missing_pregame_profile'] += 1
                continue
            usable.append(row.seg_id)
            actor_ids.append(actor)
            offender_ids.append([str(player) for player in offensive_players])
            defender_ids.append([str(player) for player in ds])
        if not usable:
            raise ValueError(f'{game_id}: no complete actor/defender states to compare')
        ids = sorted(set(actor_ids).union(*(set(d) for d in defender_ids + offender_ids)))
        p = profiles.reindex(ids)
        columns = list(dict.fromkeys(nodes.PROFILE + nodes.OPTIONAL_PROFILE + nodes.DEF_SIDE + matchups.MU_SOURCES))
        P = {c: p[c].to_numpy(dtype=np.float32) for c in columns if c in p}
        codes = p['grp'].map({'G': 0, 'F': 1, 'C': 2})
        P['grp_code'] = (codes if prior_positions else codes.fillna(1)).to_numpy(dtype=np.float32)
        P['is_big'] = np.where(p['grp'].notna(), (p['grp'] == 'C').astype(float), np.nan).astype(np.float32)
        for column in ('height_in', 'weight_lb'):
            source = f'{column}_body' if f'{column}_body' in p else column
            P[column] = p[source].to_numpy(dtype=np.float32)
        index = {player: i for i, player in enumerate(ids)}
        lineup = np.array([[index[player] for player in row] for row in defender_ids])
        off_lineup = np.array([[index[player] for player in row] for row in offender_ids])
        actors = np.array([index[player] for player in actor_ids])
        values = theta_engine._mu(SimpleNamespace(P=P), lineup, actors, np.arange(len(usable)))
        actual = chain.seg.set_index('seg_id').loc[usable]
        for column, served in values.items():
            compare(column, actual[column], served)
        if relative:
            n = len(usable)
            state = SimpleNamespace(period=actual['period'].to_numpy(), clock=actual['start_clock'].to_numpy(),
                                    off=np.zeros(n, dtype=int), score=np.zeros((n, 2)), tfouls=np.zeros((n, 2)),
                                    start=np.zeros(n), ingame={c: np.zeros((n, len(ids))) for c in nodes.IN_GAME})
            style = {f'{side}_{key}': 0. for side in ('off', 'def') for key in ('pace', 'three', 'rim', 'tov', 'foul', 'oreb')}
            game = SimpleNamespace(P=P, season=int(actual['season'].iloc[0]), rest={0: 0., 1: 0.},
                                   season_day=0., style={0: style, 1: style})
            context = theta_engine._context(game, state, np.arange(n), off_lineup, lineup)
            for name in chain.lineup:
                compare(name, actual[name], context[name])
            for side, players, selected, columns in (
                ('off', offender_ids, off_lineup, engine.OFF_REL), ('def', defender_ids, lineup, engine.DEF_REL)
            ):
                five = theta_engine._five(game, state, np.arange(n), selected, columns)
                table = (chain.off if side == 'off' else chain.dfn).set_index(['seg_id', 'player'])
                keys = pd.MultiIndex.from_arrays([np.repeat(usable, 5), np.asarray(players).reshape(-1)])
                for column in columns:
                    for suffix in ('share', 'rank'):
                        name = f'{column}_{suffix}'
                        compare(f'{side}_{name}', table.loc[keys, name], five[name].reshape(-1))
    files = [MANIFEST, features, segments, BODY, theta_path, ROOT / 'scripts' / 'nodes.py',
             ROOT / 'scripts' / 'engine.py', ROOT / 'scripts' / 'matchups.py', Path(__file__)]
    if theta.get('kind') == 'dated_implicit_schedule':
        files.append(feature_report)
    return {'experiment': 'a1_matchup_train_engine_parity', 'game_ids': game_ids,
            'population': f'first three pinned {fold or "F4 control"} games; matched real actor and five-defender segment states',
            'scope': ('matchup, lineup aggregates and candidate-relative columns; ' if relative else 'matchup columns only; ') +
                     'equality is not evidence that raw revisions or underlying data were available at every historical origin',
            'tolerance': {'absolute': 1e-6, 'relative': 1e-6}, 'excluded_states': dict(excluded),
            'columns': comparisons, 'input_sha256': {str(p.relative_to(ROOT)): sha256_file(p) for p in files}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output', type=Path, required=True, help='new report path; existing reports are never overwritten')
    parser.add_argument('--features', type=Path, default=FEATURES, help='pregame profiles to compare')
    parser.add_argument('--theta', type=Path, default=THETA, help='single assignment or dated fold schedule')
    parser.add_argument('--fold', choices=['F1', 'F2', 'F3', 'F4'], help='sample the pinned confirmation games for this fold')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f'refusing to overwrite {args.output}')
    report = audit(args.features, args.theta, args.fold)
    write_json(args.output, report, pretty=True)
    bad = [name for name, result in report['columns'].items() if result['mismatches']]
    print(f"saved {args.output}: {sum(r['states'] for r in report['columns'].values())} column-state comparisons")
    if bad:
        raise SystemExit(f'train/engine feature mismatches: {bad}; see {args.output}')


if __name__ == '__main__':
    main()
