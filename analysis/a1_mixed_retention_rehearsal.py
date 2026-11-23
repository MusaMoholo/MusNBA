#!/usr/bin/env python3
"""Rehearse retained and regenerated games in a temporary snapshot with an artificial clock."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import time
from datetime import date
from pathlib import Path
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, MASTER_CSV, RAW, SNAPSHOTS, forecast_meta, parse_utc, read_json, sha256_file, verified_pre_tip, write_json  # noqa: E402
from analysis import a1_mixed_availability_audit  # noqa: E402
from scripts import box_scores, engine, master_fixtures, nightly, pbp, projection, views  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--day', required=True)
    parser.add_argument('--synthetic-completed', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    parse_utc(args.synthetic_completed)
    if args.output.exists():
        raise FileExistsError(f'{args.output}: refusing to overwrite the rehearsal report')
    day, clock = args.day, args.synthetic_completed
    if date.fromisoformat(day).isoformat() != day:
        raise ValueError('day must be an ISO slate date')
    source = SNAPSHOTS / day
    source_files = [source / name for name in ('meta.json', 'games.json', 'games_placeholder.json', 'stats.json',
                                                'engine_worlds.npz', 'engine_players.npz')]
    source_files += [MASTER_CSV, *(DERIVED / name for name in ('teams.json', 'players.json', 'team_games.csv',
                                                                 'player_games.csv', 'player_periods.csv')),
                     *(engine.features_dir() / name for name in ('latest.parquet', 'team_latest.parquet')),
                     *(DERIVED / 'rotations' / name for name in ('stints.parquet', 'on_court.parquet')),
                     DERIVED.parent / 'models' / engine.ENGINE['models'] / 'config.json',
                     ROOT / 'basketball_common.py', ROOT / 'scripts' / 'nightly.py', ROOT / 'scripts' / 'engine.py',
                     ROOT / 'scripts' / 'views.py', ROOT / 'analysis' / 'a1_mixed_availability_audit.py',
                     Path(__file__).resolve()]
    model_dir = DERIVED.parent / 'models' / engine.ENGINE['models']
    source_files.extend(model_dir / node['file'] for node in read_json(model_dir / 'config.json')['nodes'].values())
    before = {str(path.relative_to(ROOT)): sha256_file(path) for path in source_files}
    master = master_fixtures.load()
    slate = [game for game in master if game['date_et'] == day]
    teams = read_json(DERIVED / 'teams.json')
    registry = read_json(DERIVED / 'players.json')['players']
    team_rows, player_rows = box_scores.load_csv('team_games.csv'), box_scores.load_csv('player_games.csv')
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='musnba-mixed-rehearsal-') as tmp:
        root = Path(tmp)
        target = root / 'snapshots' / day
        target.parent.mkdir()
        shutil.copytree(source, target)
        retained = nightly.load_retained(target, slate, clock)
        if not retained or len(retained) == len(slate):
            raise ValueError('rehearsal requires both retained and freshly regenerated games')
        print(f'RESEARCH ONLY: artificial clock; retained {len(retained)} games; '
              f'simulating {len(slate) - len(retained)} fresh games', flush=True)
        with patch.object(nightly, 'utc_now', return_value=clock):
            part = nightly.project_slate(day, teams, master, team_rows, player_rows, registry, True, 10000,
                                         pbp.load(), engine_worlds=10000, origin=day, retained=retained)
        season = projection.simulate_season(part['T'], part['lg'], master, day, teams, part['worlds'], 10000)
        with patch.object(nightly, 'SNAPSHOTS', target.parent), patch.object(nightly, 'utc_now', return_value=clock):
            meta = nightly.write_snapshot(part, season, root / 'archive')
        replay = projection.simulate_season(part['T'], part['lg'], master, day, teams, part['worlds'], 10000,
                                            season['pathway'])
        if json.dumps(replay, sort_keys=True) != json.dumps(season, sort_keys=True):
            raise ValueError('season replay differs')
        for gid, saved in retained.items():
            if meta['game_provenance'][gid] != saved['meta']:
                raise ValueError(f'{gid}: original provenance differs')
        fresh = set(part['games']) - set(retained)
        for gid in fresh:
            scores = part['worlds'][gid].sum(axis=2)
            players = part['player_worlds'][gid]
            for side in (0, 1):
                points = players['lines'][:, players['side'] == side, 1].astype(np.int64).sum(axis=1)
                if not np.array_equal(points, scores[:, side]):
                    raise ValueError(f'{gid}: player and team scores differ')
            if meta['game_provenance'][gid]['completed_at'] != clock:
                raise ValueError(f'{gid}: artificial game completion differs')
        origin_audit, audit_paths = a1_mixed_availability_audit.audit(target, RAW / 'runs')
        audit_hashes = {path: sha256_file(path) for path in audit_paths}
        with patch.object(views, 'SNAPSHOTS', target.parent), patch.object(views, 'today_et', return_value=day):
            views.build(root / 'views')
        for gid in part['games']:
            source_meta = forecast_meta(meta, gid)
            view = read_json(root / 'views' / 'api' / 'game' / f'{gid}.json')
            presented = view['projection']
            if (presented['completed_at'] != source_meta['completed_at']
                    or presented['model'] != source_meta['model']
                    or presented['pre_tip'] is not verified_pre_tip(source_meta, gid)
                    or presented['sim']['periods']['fg'] != part['games'][gid]['periods']['fg']):
                raise ValueError(f'{gid}: rendered game view differs from saved source')
        if any(sha256_file(path) != digest for path, digest in audit_hashes.items()):
            raise ValueError('origin audit inputs changed during rehearsal')
        origin_audit['input_sha256'] = {
            ('snapshot/' + str(path.relative_to(target)) if path.is_relative_to(target)
             else str(path.relative_to(ROOT))): digest for path, digest in audit_hashes.items()
        }
    if before != {str(path.relative_to(ROOT)): sha256_file(path) for path in source_files}:
        raise ValueError('live source snapshot changed during rehearsal')
    report = {'type': 'isolated_mixed_retention_rehearsal', 'published': False, 'day': day,
              'synthetic_clock': clock, 'retained_games': len(retained), 'regenerated_games': len(fresh),
              'worlds_per_game': 10000, 'season_worlds': 10000, 'season_games': len(season['games']),
              'season_replay_bit_for_bit': True, 'retained_provenance_identical': True,
              'player_team_points_identical': True, 'raw_origin_audit': origin_audit,
              'rendered_game_views_verified': len(part['games']), 'source_sha256': before,
              'elapsed_seconds': round(time.monotonic() - started, 2),
              'limitations': ['Artificial clock: no pre-tip publication was demonstrated.',
                              'No collection, live publication, bundle export or real-device import occurred.',
                              'Accounting and reproducibility only, not predictive validation.']}
    write_json(args.output, report, pretty=True)
    print(f"PASS mixed rehearsal: {len(retained)} retained + {len(fresh)} regenerated games, "
          f"{len(season['games'])} season games; {report['elapsed_seconds']}s", flush=True)


if __name__ == '__main__':
    main()
