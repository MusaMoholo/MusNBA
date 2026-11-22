#!/usr/bin/env python3
"""Rebuild real historical slices after injecting same-day and future results."""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, sha256_file, write_json  # noqa: E402
from scripts import features  # noqa: E402


def audit() -> dict:
    source = DERIVED / 'history' / '2023'
    segment_path, on_path = source / 'segments.parquet', source / 'on_court.parquet'
    seg, on = pd.read_parquet(segment_path), pd.read_parquet(on_path)
    games = seg[['game_id', 'date_et']].drop_duplicates().sort_values(['date_et', 'game_id'])
    first_dates = sorted(games['date_et'].unique())[:2]
    chosen = games[games['date_et'].isin(first_dates)].groupby('date_et', sort=True).head(2)
    if len(chosen) != 4:
        raise ValueError('the real-game injection needs two games on each of the first two dates')
    target_date = first_dates[1]
    target_pair = chosen.loc[chosen['date_et'].eq(target_date), 'game_id'].tolist()
    target_game, injected_game = target_pair
    injected_teams = seg.loc[seg['game_id'].eq(injected_game), 'offense'].dropna().unique()
    future = seg[(seg['date_et'] > target_date) & seg['offense'].isin(injected_teams)]
    future = future[['game_id', 'date_et']].drop_duplicates().sort_values(['date_et', 'game_id']).head(1)
    if future.empty:
        raise ValueError('the injected teams have no later retained game')
    chosen = pd.concat([chosen, future], ignore_index=True)
    game_ids = chosen['game_id'].tolist()
    seg, on = seg[seg['game_id'].isin(game_ids)].copy(), on[on['game_id'].isin(game_ids)].copy()
    later = (seg['date_et'] > target_date) | ((seg['date_et'] == target_date) & (seg['game_id'] != target_game))
    changed_shots = later & seg['end_type'].eq('shot') & seg['made'].notna()
    changed_players = (on['date_et'] > target_date) | ((on['date_et'] == target_date) & (on['game_id'] != target_game))
    if not changed_shots.any() or not changed_players.any():
        raise ValueError('no eligible future or same-day rows to inject')
    with tempfile.TemporaryDirectory(prefix='musnba-a1-injection-') as tmp:
        root = Path(tmp)
        history = root / 'source' / 'history' / '2023'
        history.mkdir(parents=True)
        seg.to_parquet(history / 'segments.parquet', index=False)
        on.to_parquet(history / 'on_court.parquet', index=False)
        before_dir, shot_dir, after_dir = root / 'before', root / 'shots', root / 'after'

        def build_slice(out: Path) -> None:
            paths = [(history / 'segments.parquet', history / 'on_court.parquet')]
            with patch.object(features, 'sources', return_value=paths):
                features.build(out=out, segments=root / 'source', causal_first=True,
                               causal_positions=True, history_only=True)

        build_slice(before_dir)
        altered = seg.copy()
        altered.loc[changed_shots, 'made'] = ~altered.loc[changed_shots, 'made'].astype(bool)
        altered.loc[changed_shots, 'points'] = np.where(altered.loc[changed_shots, 'made'], 2, 0)
        altered.to_parquet(history / 'segments.parquet', index=False)
        build_slice(shot_dir)
        altered_on = on.copy()
        altered_on.loc[changed_players, 'sec'] += 300
        altered_on.loc[changed_players, 'pos'] = 'C'
        altered_on.to_parquet(history / 'on_court.parquet', index=False)
        build_slice(after_dir)
        comparisons, shot_differences, player_differences = {}, 0, 0
        for filename, keys in (('pregame.parquet', ['game_id', 'player']),
                               ('team_pregame.parquet', ['game_id', 'team'])):
            before, shots, after = (pd.read_parquet(folder / filename) for folder in (before_dir, shot_dir, after_dir))
            safe = (before['date_et'] < target_date) | before['game_id'].eq(target_game)
            a = before.loc[safe].sort_values(keys).reset_index(drop=True)
            b = after[after['game_id'].isin(a['game_id'])].sort_values(keys).reset_index(drop=True)
            c = shots[shots['game_id'].isin(a['game_id'])].sort_values(keys).reset_index(drop=True)
            pd.testing.assert_frame_equal(a, b, check_exact=True)
            pd.testing.assert_frame_equal(a, c, check_exact=True)
            comparisons[filename] = {'safe_rows': len(a), 'columns': len(a.columns),
                                     'identical_values': int(a.size)}
            x = before[before['date_et'] > target_date].sort_values(keys).reset_index(drop=True)
            y = after[after['date_et'] > target_date].sort_values(keys).reset_index(drop=True)
            z = shots[shots['date_et'] > target_date].sort_values(keys).reset_index(drop=True)
            numeric = x.select_dtypes(include=np.number).columns
            for col in numeric:
                shot_differences += int((~np.isclose(x[col], z[col], rtol=0, atol=0, equal_nan=True)).sum())
                player_differences += int((~np.isclose(z[col], y[col], rtol=0, atol=0, equal_nan=True)).sum())
        if not shot_differences or not player_differences:
            raise ValueError('each injected input must affect later-date profiles')
    return {'experiment': 'a1_future_injection_real_slice',
            'population': 'five retained 2022-23 games, including a later game for an injected team; no final-test data',
            'game_ids': game_ids, 'target_date': target_date, 'target_game': target_game,
            'mutated_shot_rows': int(changed_shots.sum()), 'mutated_player_rows': int(changed_players.sum()),
            'safe_comparisons': comparisons, 'later_shot_values_changed': shot_differences,
            'later_player_values_changed': player_differences,
            'scope': 'base player/team causal feature rebuild with explicit scratch sources; not publication times or fitted nodes',
            'source_sha256': {str(p.relative_to(ROOT)): sha256_file(p) for p in (segment_path, on_path)},
            'audit_sha256': sha256_file(Path(__file__))}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f'refusing to overwrite {args.output}')
    result = audit()
    write_json(args.output, result, pretty=True)
    print(f'saved {args.output}: {result["later_shot_values_changed"]} shot and '
          f'{result["later_player_values_changed"]} player later values changed', flush=True)


if __name__ == '__main__':
    main()
