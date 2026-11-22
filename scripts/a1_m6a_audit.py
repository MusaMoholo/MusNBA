#!/usr/bin/env python3
"""Independently account for the matched A1 teacher-forced aggregation output."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, sha256_file, write_json  # noqa: E402
from scripts import a1_signal, aggregate, backtest  # noqa: E402
from scripts.evaluate import EXPERIMENTS  # noqa: E402


def audit(run: str, ids_path: Path) -> dict:
    report_path = EXPERIMENTS / f'{run}.json'
    report = json.loads(report_path.read_text())
    paths = {name: DERIVED / 'experiments' / f'{run}{suffix}.parquet'
             for name, suffix in (('players', ''), ('teams', '_teams'), ('components', '_components'), ('events', '_events'))}
    players, teams, components, events = (pd.read_parquet(paths[k]) for k in ('players', 'teams', 'components', 'events'))
    control_path = DERIVED / 'experiments' / f'{a1_signal.CONTROL}.parquet'
    control = a1_signal.fixed_games(pd.read_parquet(control_path), json.loads(a1_signal.MANIFEST.read_text()))
    ids = backtest.select_games(control['game_id'].to_numpy(), 0, 0, ids_path)
    if report['experiment'] != 'm6a_aggregation' or sorted(report['game_ids']) != ids.tolist():
        raise ValueError('replay report does not name exactly the selected games')
    for label, frame in (('players', players), ('teams', teams), ('components', components), ('events', events)):
        if set(frame['game_id']) != set(ids):
            raise ValueError(f'{label} does not cover exactly the selected games')
    if players.duplicated(['game_id', 'player']).any() or components.duplicated(['game_id', 'side']).any():
        raise ValueError('duplicate player or team-side output')
    if len(components) != 2 * len(ids) or set(components['side']) != {'home', 'away'}:
        raise ValueError('expected exactly one home and away side per game')
    if components.groupby('game_id')['side'].nunique().ne(2).any():
        raise ValueError('a game lacks a home or away side')
    if teams.duplicated(['game_id', 'measure']).any() or len(teams) != 4 * len(ids):
        raise ValueError('expected four team-score measures per game')
    if set(teams['measure']) != {'home_pts', 'away_pts', 'margin', 'total'}:
        raise ValueError('unexpected team-score measures')
    if events.duplicated(['game_id', 'event']).any():
        raise ValueError('duplicate per-game decision events')

    frozen = json.loads(a1_signal.MANIFEST.read_text())
    fingerprints = {r['path']: r['sha256'] for r in frozen['input_fingerprints']}
    folder = Path(report['models']).resolve()
    expected_models = {p: h for p, h in fingerprints.items() if (ROOT / p).parent == folder}
    actual_models = {str(Path(p).resolve().relative_to(ROOT)): h for p, h in report['model_sha256'].items()}
    if len(expected_models) != 17 or actual_models != expected_models:
        raise ValueError('saved replay models do not exactly match the S01 control model hashes')
    if any(sha256_file(ROOT / p) != h for p, h in actual_models.items()):
        raise ValueError('a persisted replay model changed since it was scored')
    pregame = Path(json.loads(Path(report['config']).read_text())['default']['features']).resolve()
    if report['pregame_sha256'] != fingerprints[str(pregame.relative_to(ROOT))] or sha256_file(pregame) != report['pregame_sha256']:
        raise ValueError('replay profiles differ from the frozen control')
    if any(sha256_file(Path(path)) != digest for path, digest in report['scoring_sha256'].items()):
        raise ValueError('replay scoring code differs from its recorded fingerprint')

    pre = pd.read_parquet(pregame, columns=['game_id', 'player', 'team'])
    tagged = players.merge(pre, on=['game_id', 'player'], how='left', validate='one_to_one')
    if tagged['team'].isna().any():
        raise ValueError(f"{int(tagged['team'].isna().sum())} replay players have no independently recorded team")
    columns = [f'{stat}_{kind}' for stat in aggregate.STATS for kind in ('actual', 'sim')]
    totals = tagged.groupby(['game_id', 'team'])[columns].sum()
    sides = components.set_index(['game_id', 'team'])
    if set(totals.index) != set(sides.index):
        raise ValueError('player and team-side keys do not match')
    delta = totals.to_numpy() - sides.loc[totals.index, columns].to_numpy()
    if not np.allclose(delta, 0, rtol=0, atol=1e-9):
        raise ValueError('player and team components do not reconcile')
    score_residuals = {}
    for kind in ('actual', 'sim'):
        residual = components[f'pts_{kind}'] - (2 * components[f'fgm_{kind}'] +
                                                  components[f'fg3m_{kind}'] + components[f'ftm_{kind}'])
        if not np.allclose(residual, 0, rtol=0, atol=1e-9):
            raise ValueError(f'{kind} points do not reconcile with field goals and free throws')
        score_residuals[kind] = float(residual.abs().max())
    for side in ('home', 'away'):
        a = components[components['side'] == side].set_index('game_id')
        b = teams[teams['measure'] == f'{side}_pts'].set_index('game_id')
        for column, measure in (('pts_actual', 'actual'), ('pts_sim', 'sim')):
            if not np.allclose(a[column].sort_index(), b[measure].sort_index(), rtol=0, atol=1e-9):
                raise ValueError(f'{side} team-score and component totals differ')

    expected_events = set(report['summary']['events'])
    if set(events['event']) != expected_events or len(events) != len(ids) * len(expected_events):
        raise ValueError('per-game event outputs do not cover the summary events')
    event_totals = events.groupby('event')[['expected', 'actual']].sum().to_dict()
    for name in expected_events:
        for key in ('expected', 'actual'):
            if abs(float(event_totals[key][name]) - report['summary']['events'][name][key]) > 0.051:
                raise ValueError(f'{name} {key} event totals do not reconcile')

    official = components.merge(control[['game_id', 'real_home', 'real_away']], on='game_id', validate='many_to_one')
    official_points = np.where(official['side'] == 'home', official['real_home'], official['real_away'])
    differences = official['pts_actual'].to_numpy(dtype=float) - official_points
    per_game = components.groupby('game_id')[['unmatched_actual_players_game', 'unmatched_actual_points_game']].first()
    return {
        'experiment': 'a1_s03_teacher_forced_accounting', 'run': run, 'games': len(ids),
        'team_sides': len(components), 'player_games': len(players), 'decision_event_rows': len(events),
        'model_artifacts_matching_s01': len(actual_models),
        'player_team_component_values_checked': len(totals) * len(columns),
        'max_player_team_difference': float(np.abs(delta).max()),
        'score_identity_max_difference': score_residuals,
        'unmatched_actual_players': int(per_game['unmatched_actual_players_game'].sum()),
        'unmatched_actual_points': float(per_game['unmatched_actual_points_game'].sum()),
        'actor_lineup_accounting': report['matchup_actor_accounting'],
        'teacher_actual_minus_official': {
            'team_sides_different': int(np.count_nonzero(differences)),
            'mean': float(np.mean(differences)), 'minimum': float(np.min(differences)), 'maximum': float(np.max(differences)),
        },
        'limitations': 'teacher-forced real-state replay is not a forecast; eligible-event actuals differ from official scores',
        'sha256': {str(p): sha256_file(p) for p in [report_path, ids_path, control_path, pregame, *paths.values(), Path(__file__)]},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run')
    parser.add_argument('--game-ids', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f'refusing to overwrite {args.output}')
    result = audit(args.run, args.game_ids)
    write_json(args.output, result, pretty=True)
    print(f"audited {result['games']} games / {result['team_sides']} sides / {result['player_games']} players")
    print(f"eligible-event actuals differ from official scores on {result['teacher_actual_minus_official']['team_sides_different']} sides")
    print(f'saved {args.output}')


if __name__ == '__main__':
    main()
