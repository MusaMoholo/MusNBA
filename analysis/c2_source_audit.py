"""Input-only court-source audit. Never fits, scores forecasts or edits production data."""
import argparse
import gzip
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, read_json, sha256_file, write_json
from scripts import pbp, plays, possessions


def unique_clock_pairs(native, espn, tolerance=1):
    """Match only mutually unique player/period clock neighbours; no outcome/location costs."""
    edges = []
    for i, row in native.iterrows():
        if pd.isna(row['player']) or not row['player']:
            continue
        choices = espn[(espn.player == row['player']) & (espn.period == row['period'])
                       & ((espn.clock - row['clock']).abs() <= tolerance)]
        edges.extend((i, j) for j in choices.index)
    left, right = {}, {}
    for i, j in edges:
        left.setdefault(i, []).append(j)
        right.setdefault(j, []).append(i)
    pairs = [(i, j) for i, j in edges if len(left[i]) == len(right[j]) == 1]
    return pairs, {'ambiguous_native': sum(len(v) > 1 for v in left.values()),
                   'ambiguous_espn': sum(len(v) > 1 for v in right.values())}


def audit_game(game, output_root):
    gid, nba = str(game.espn_game), str(game.nba_game)
    source = ROOT / 'data/raw/nbastats/shotchartdetail' / game.season / f'{nba}.json.gz'
    raw = json.loads(gzip.decompress(source.read_bytes()))
    table = next(r for r in raw['resultSets'] if r['name'] == 'Shot_Chart_Detail')
    native = pd.DataFrame(table['rowSet'], columns=table['headers'])
    people = pd.read_parquet(DERIVED / 'nbastats/player_games_map.parquet', filters=[('nba_game', '==', nba)])
    native['player'] = native.PLAYER_ID.map(dict(zip(people.person.astype(int), people.player.astype(str))))
    native['period'] = native.PERIOD.astype(int)
    native['clock'] = (native.MINUTES_REMAINING * 60 + native.SECONDS_REMAINING).astype(float)
    season = int(game.espn_season)
    pp = ROOT / f'data/raw/hoopr/play_by_play_{season}.parquet'
    bb = ROOT / f'data/raw/hoopr/player_box_{season}.parquet'
    canonical = plays.from_hoopr(gid, pd.read_parquet(pp, filters=[('game_id', '==', int(gid))]).to_dict('records'),
                                 pd.read_parquet(bb, filters=[('game_id', '==', int(gid))]).to_dict('records'))
    espn = pd.DataFrame([{'player': p['participants'][0] if p['participants'] else None,
                         'period': p['period'], 'clock': pbp.clock_seconds(p['clock']), 'x': p['x'], 'y': p['y'],
                         'seq': p['seq'], 'value': p['points_attempted'], 'made': p['scoring']}
                        for p in canonical['plays'] if p['shooting'] and p['points_attempted'] in (2, 3)])
    pairs, ambiguous = unique_clock_pairs(native, espn)
    matched = pd.DataFrame([{**native.loc[i].to_dict(), **{f'espn_{k}': v for k, v in espn.loc[j].items()}}
                            for i, j in pairs])
    assert len({j for i, j in pairs}) == len(pairs) == len({i for i, j in pairs})
    made = matched.SHOT_MADE_FLAG.astype(bool).to_numpy() == matched.espn_made.to_numpy()
    value = np.where(matched.SHOT_TYPE == '3PT Field Goal', 3, 2) == matched.espn_value.to_numpy()
    known = matched[['espn_x', 'espn_y', 'LOC_X', 'LOC_Y']].notna().all(axis=1)
    dx = (25 + matched.loc[known, 'LOC_X'] / 10 - matched.loc[known, 'espn_x']).abs()
    dy = (matched.loc[known, 'LOC_Y'] / 10 - matched.loc[known, 'espn_y']).abs()
    legacy = [possessions.zone(row.espn_x, row.espn_y, row.espn_value) for row in matched.itertuples()]
    native_parent = matched.SHOT_ZONE_BASIC.map({'Restricted Area': 'rim', 'In The Paint (Non-RA)': 'paint',
                  'Mid-Range': 'mid', 'Left Corner 3': 'corner3', 'Right Corner 3': 'corner3',
                  'Above the Break 3': 'above3', 'Backcourt': 'above3'})
    confusion = pd.crosstab(pd.Series(legacy, name='legacy'), native_parent.rename('native_parent'))
    matched.to_parquet(output_root / f'{gid}.parquet', index=False)
    return {'espn_game': gid, 'nba_game': nba, 'date': game.date, 'nba_attempts': len(native), 'espn_attempts': len(espn),
            'exact_clock_pairs': int((matched.clock == matched.espn_clock).sum()),
            'within_one_second_unique_pairs': len(pairs), **ambiguous, 'unmapped_people': int(native.player.isna().sum()),
            'make_agreement': int(made.sum()), 'value_agreement': int(value.sum()),
            'coordinate_known_pairs': int(known.sum()), 'coordinate_mae_feet': {'x': float(dx.mean()), 'y': float(dy.mean())},
            'coordinate_max_error_feet': {'x': float(dx.max()), 'y': float(dy.max())},
            'coarse_zone_agreement': int((np.array(legacy) == native_parent.to_numpy()).sum()),
            'coarse_zone_confusion': confusion.to_dict(),
            'basic_counts': {str(k): int(v) for k, v in native.SHOT_ZONE_BASIC.value_counts().items()},
            'source': str(source.relative_to(ROOT)), 'source_sha256': sha256_file(source)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--arrays', required=True, type=Path)
    args = p.parse_args()
    if args.output.exists() or args.arrays.exists():
        raise FileExistsError('new immutable audit namespace required')
    args.arrays.mkdir(parents=True)
    games = pd.read_parquet(DERIVED / 'nbastats/games.parquet')
    games = games[games.nba_game.isin(['0022200001', '0022200002', '0022200003'])].sort_values('nba_game')
    assert len(games) == 3 and (games.date < '2023-01-01').all()
    results = [audit_game(game, args.arrays) for game in games.itertuples()]
    write_json(args.output, {'kind': 'C2 input/source audit; no candidate losses inspected', 'games': results,
        'inventory': read_json(DERIVED / 'experiments/c2_input_inventory_v1.json'),
        'native_coordinate_transform': {'x': '25 + LOC_X/10', 'y': 'LOC_Y/10'},
        'joining': 'Game/person crosswalk, then mutually unique player/period clocks within1s; no event-ID equality or outcome/location costs.',
        'native_schema_source': 'https://raw.githubusercontent.com/swar/nba_api/master/src/nba_api/stats/endpoints/shotchartdetail.py',
        'zone_reference': 'https://jr.nba.com/how-to-read-a-shot-chart/',
        'limits': ['No original publication/revision timestamps in shot-chart payload; fetched UTC is retained.',
                   'LeagueAverages numeric values are whole-season and excluded from all features/fits.',
                   'Observed native labels and derived ESPN coordinates are distinct sources; boundary differences are imprecision, not predictive harm.']}, pretty=True)
    print(json.dumps(results), flush=True)


if __name__ == '__main__':
    main()
