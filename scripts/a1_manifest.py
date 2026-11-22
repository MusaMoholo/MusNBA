#!/usr/bin/env python3
"""Freeze A1 game populations, seeds and input fingerprints before testing candidates.

  .venv/bin/python scripts/a1_manifest.py --output analysis/experiments/20261122_a1_manifest.json
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, write_json  # noqa: E402
from scripts import a1_compare, backtest, projection, train  # noqa: E402
from scripts.evaluate import EXPERIMENTS, FOLDS  # noqa: E402

ORIGINAL = '20261120T162930Z_v1.3_pool_per_world_F4'
REPRODUCTION = '20261122T015651Z_a1_s01_repro'
STRESS_PATH = Path('analysis/experiments/20261122_a1_10k_stress_games.json')
SELECTION_SEED = 20261122


def fingerprint(path: Path) -> dict:
    path = path if path.is_absolute() else ROOT / path
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'path': str(path.relative_to(ROOT)), 'bytes': path.stat().st_size, 'sha256': digest}


def require_fingerprints(current: list[dict], expected: list[dict], label: str) -> None:
    def keyed(items: list[dict]) -> dict:
        result = {item['path']: (item['bytes'], item['sha256']) for item in items}
        if len(result) != len(items):
            raise ValueError(f'{label}: duplicate fingerprint paths')
        return result
    before, after = keyed(expected), keyed(current)
    changed = sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))
    if changed:
        raise ValueError(f'{label}: fingerprints changed: {changed}')


def model_paths(folder: Path) -> list[Path]:
    config = folder / 'config.json'
    nodes = json.loads(config.read_text())['nodes']
    if set(nodes) != set(train.NODES):
        raise ValueError(f'{folder}: model configuration does not contain the expected nodes')
    names = [entry['file'] for entry in nodes.values()]
    if any(Path(name).name != name or not (folder / name).is_file() for name in names):
        raise FileNotFoundError(f'{folder}: a configured node model is missing or not a local file')
    return [config, *sorted(set(folder.glob('*.txt')) | {folder / name for name in names})]


def noise_floors(report: dict) -> dict:
    def metrics(row: dict) -> dict:
        return {'status': row['status'],
                **{key: max(abs(bound) for bound in value['ci_95']) if value['ci_95'] is not None else None
                   for key, value in row.items() if isinstance(value, dict) and 'ci_95' in value}}

    return {
        'definition': 'larger absolute endpoint of the paired 95% independent-seed interval',
        'players': {tier: {stat: metrics(result) for stat, result in stats.items()}
                    for tier, stats in report['players'].items()},
        'games': {stat: metrics(result) for stat, result in report['games'].items()},
        'win': metrics(report['win']),
    }


def input_paths() -> list[Path]:
    sources = ('backtest', 'engine', 'nodes', 'projection', 'rotations', 'minutes', 'aggregate', 'train',
               'evaluate', 'matchups', 'realmatch', 'pbp', 'plays', 'pathway', 'season_backtest')
    paths = [ROOT / 'basketball_common.py', *(ROOT / 'scripts' / f'{name}.py' for name in sources)]
    paths += [ROOT / 'models/v1.2d.json', ROOT / 'models/v1.3.json', ROOT / 'models/matchup_2025-12-31.json',
              DERIVED / 'teams.json', DERIVED / 'athletes.parquet',
              DERIVED / 'experiments/20261119T235148Z_m6a_v1.1_teams.parquet',
              DERIVED / 'variants/matchup/features/pregame.parquet',
              DERIVED / 'variants/matchup/features/team_pregame.parquet',
              DERIVED / 'features/pregame.parquet', DERIVED / 'features/team_pregame.parquet']
    folder = ROOT / 'data/models/folds/v1.2d_F4_all'
    paths += model_paths(folder)
    for season in range(2023, 2027):
        history = DERIVED / 'history' / str(season)
        paths += [history / name for name in ('segments.parquet', 'stints.parquet', 'on_court.parquet', 'player_periods.csv.gz')]
        paths += [ROOT / f'data/raw/hoopr/player_box_{season}.parquet',
                  ROOT / f'data/raw/hoopr/play_by_play_{season}.parquet']
    return paths


def stress_selection(frame: pd.DataFrame, pre: pd.DataFrame) -> dict[str, list[str]]:
    counts = pre.groupby(['game_id', 'team']).size()
    frame = frame.copy()
    frame['shortest_roster'] = [min(int(counts.loc[(r.game_id, r.home)]), int(counts.loc[(r.game_id, r.away)]))
                                for r in frame.itertuples()]
    frame['absolute_margin'] = (frame['real_home'] - frame['real_away']).abs()
    chosen: set[str] = set()
    strata = {}
    definitions = [('overtime', frame[frame['real_ot'] == 1], 'game_id', True),
                   ('short_roster', frame, 'shortest_roster', True),
                   ('close', frame, 'absolute_margin', True),
                   ('blowout', frame, 'absolute_margin', False)]
    for label, rows, key, ascending in definitions:
        rows = rows[~rows['game_id'].isin(chosen)]
        by = ['game_id'] if key == 'game_id' else [key, 'game_id']
        order = [ascending] if key == 'game_id' else [ascending, True]
        selected = rows.sort_values(by, ascending=order).head(5)['game_id'].tolist()
        if len(selected) != 5:
            raise ValueError(f'not enough games for stress stratum {label}')
        strata[label] = selected
        chosen.update(selected)
    declared = json.loads((ROOT / STRESS_PATH).read_text())
    if sorted(chosen) != declared:
        raise ValueError('fixed 10k stress IDs no longer agree with their preregistered selection')
    return strata


def seeded_games(ids: list[str], dates: pd.Series, seed_key: str) -> list[dict]:
    return [{'game_id': gid, 'date_et': str(dates.loc[gid]),
             'simulation_seed_stream_0': str(backtest.simulation_seed('', str(dates.loc[gid]), gid, 0, seed_key)),
             'simulation_seed_stream_1': str(backtest.simulation_seed('', str(dates.loc[gid]), gid, 1, seed_key))}
            for gid in ids]


def validate_run(run: str, stream: int | None, screen: list[dict]) -> None:
    record = json.loads((EXPERIMENTS / f'{run}.json').read_text())
    expected = {'config': 'models/v1.2d.json', 'fold': 'F4', 'models': 'folds/v1.2d_F4_all',
                'games': 200, 'worlds': 1000, 'rotation': 'targets', 'known_starters': False, 'pool': 0,
                'game_selection_seed': 20261119, 'game_ids_file': None, 'simulation_stream': stream, 'seed_key': None}
    for key, value in expected.items():
        if key not in record or record[key] != value:
            raise ValueError(f'{run}: {key} is {record.get(key)!r}, expected {value!r}')
    frame = pd.read_parquet(DERIVED / 'experiments' / f'{run}.parquet', columns=['game_id', 'simulation_seed'])
    if frame['game_id'].duplicated().any():
        raise ValueError(f'{run}: duplicate game IDs')
    expected_seeds = {r['game_id']: r['simulation_seed_original' if stream is None else 'simulation_seed_stream_1']
                      for r in screen}
    actual_seeds = dict(zip(frame['game_id'], frame['simulation_seed']))
    if actual_seeds != expected_seeds or sorted(record['game_ids']) != sorted(expected_seeds):
        raise ValueError(f'{run}: game IDs or simulation seeds do not match the pinned control')


def build(control_run: str | None = None, seed_run: str | None = None) -> dict:
    spec_path = ROOT / 'models/v1.2d.json'
    spec = json.loads(spec_path.read_text())
    cfg = json.loads((ROOT / 'data/models/folds/v1.2d_F4_all/config.json').read_text())
    original_games = pd.read_parquet(DERIVED / 'experiments' / f'{ORIGINAL}.parquet')
    original_players = pd.read_parquet(DERIVED / 'experiments' / f'{ORIGINAL}_players.parquet')
    selections = {}
    stress = {}
    tier_counts = {}
    for fold in FOLDS:
        pre, _, seg, *_ = backtest.load_inputs(spec, fold)
        eligible = backtest.eligible_games(seg)
        pairs = seg[['game_id', 'date_et']].drop_duplicates()
        if pairs.duplicated('game_id').any():
            raise ValueError(f'{fold}: game has more than one date')
        dates = pairs.set_index('game_id')['date_et']
        seed_key = f'a1-confirmation-{fold}'
        if fold == 'F4':
            expected = backtest.select_games(eligible, 200, 20261119)
            if sorted(original_games['game_id'].tolist()) != expected.tolist():
                raise ValueError('retained control no longer matches the fixed 200-game selection')
            ids = eligible.tolist()
            stress = stress_selection(original_games, pre)
            selected = set(sum(stress.values(), []))
            chosen_players = original_players[original_players['game_id'].isin(selected)]
            roles = a1_compare.roles(chosen_players[['game_id', 'player']], pre,
                                     original_games[original_games['game_id'].isin(selected)])
            tier_counts = {tier: int((roles['tier'] == tier).sum()) for tier in a1_compare.ROLE_TIERS}
        else:
            sample_seed = projection.seed_for('a1-confirmation', SELECTION_SEED, fold)
            ids = backtest.select_games(eligible, 200, sample_seed).tolist()
        selections[fold] = {
            'training_end': FOLDS[fold][0], 'validation_start': FOLDS[fold][1], 'validation_end': FOLDS[fold][2],
            'eligible_games': len(eligible), 'selected_games': len(ids),
            'selection_seed': str(projection.seed_for('a1-confirmation', SELECTION_SEED, fold)) if fold != 'F4' else None,
            'simulation_seed_key': seed_key, 'games': seeded_games(ids, dates, seed_key)}
    screen = []
    for row in original_games.sort_values('game_id').itertuples():
        gid, day = str(row.game_id), str(row.date_et)
        screen.append({'game_id': gid, 'date_et': day,
                       'simulation_seed_original': str(backtest.simulation_seed(cfg['version'], day, gid)),
                       'simulation_seed_stream_1': str(backtest.simulation_seed(cfg['version'], day, gid, 1))})
    for run, stream in ((control_run, None), (seed_run, 1)):
        if run:
            validate_run(run, stream, screen)
    artifacts = [EXPERIMENTS / f'{ORIGINAL}.json', DERIVED / 'experiments' / f'{ORIGINAL}.parquet',
                 DERIVED / 'experiments' / f'{ORIGINAL}_players.parquet',
                 EXPERIMENTS / f'{REPRODUCTION}.json', DERIVED / 'experiments' / f'{REPRODUCTION}.parquet',
                 DERIVED / 'experiments' / f'{REPRODUCTION}_players.parquet',
                 ROOT / STRESS_PATH, EXPERIMENTS / '20261122_a1_reproduction_games.json',
                 EXPERIMENTS / '20261122_a1_quarter_audit.json', EXPERIMENTS / '20261122_a1_repro_accounting.json',
                 EXPERIMENTS / '20261122_a1_report_coverage.json',
                 EXPERIMENTS / '20261122_a1_prior_box_coverage.json',
                 DERIVED / 'experiments/20261122_a1_prior_box_membership.parquet',
                 EXPERIMENTS / '20261122_a1_pre_candidate_manifest.json',
                 EXPERIMENTS / '20261122_a1_production_baseline.json']
    for run in (control_run, seed_run):
        if run:
            artifacts += [EXPERIMENTS / f'{run}.json', DERIVED / 'experiments' / f'{run}.parquet',
                          DERIVED / 'experiments' / f'{run}_players.parquet']
    if control_run and seed_run:
        artifacts += [EXPERIMENTS / '20261122_a1_control_accounting.json',
                      EXPERIMENTS / '20261122_a1_seed_accounting.json',
                      EXPERIMENTS / '20261122_a1_seed_noise.json']
    production = ROOT / 'data/models/v1.3'
    upstream = [ROOT / 'requirements.txt',
                *(ROOT / 'scripts' / f'{name}.py' for name in
                  ('features', 'history', 'possessions', 'nbastats', 'athletes', 'fetch_nbastats', 'fetch_espn')),
                ROOT / 'data/raw/hoopr/manifest.json',
                DERIVED / 'features/features_report.json',
                DERIVED / 'variants/matchup/features/features_report.json']
    inputs = [fingerprint(p) for p in input_paths()]
    production_models = [fingerprint(p) for p in model_paths(production)]
    upstream_build = [fingerprint(p) for p in upstream]
    seed_noise = None
    if control_run and seed_run:
        preregistered = json.loads((EXPERIMENTS / '20261122_a1_pre_candidate_manifest.json').read_text())
        baseline = json.loads((EXPERIMENTS / '20261122_a1_production_baseline.json').read_text())
        comparison = json.loads((EXPERIMENTS / '20261122_a1_seed_noise.json').read_text())
        if comparison['runs'] != {'control': control_run, 'candidate': seed_run}:
            raise ValueError('independent-seed comparison does not match the selected runs')
        seed_noise = noise_floors(comparison)
        require_fingerprints(inputs, preregistered['input_fingerprints'], 'control inputs')
        require_fingerprints(production_models, baseline['production_model_fingerprints'], 'production models')
        require_fingerprints(upstream_build, baseline['upstream_build_fingerprints'], 'upstream build inputs')
        require_fingerprints([fingerprint(ROOT / 'exports/MusNBA.musnba.gz')],
                             [baseline['local_bundle_fingerprint']], 'local served bundle')
    return {
        'experiment': 'a1_baseline_and_confirmation_manifest', 'selection_date': '2026-11-22',
        'source_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'runtime': {'python': platform.python_version(),
                    'packages': {p: importlib.metadata.version(p) for p in ('numpy', 'pandas', 'pyarrow', 'lightgbm')}},
        'control': {'original_run': ORIGINAL, 'regenerated_run': control_run, 'independent_seed_run': seed_run,
                    'config': 'models/v1.2d.json', 'fitted_models': 'folds/v1.2d_F4_all',
                    'fitted_through': cfg['train_through'], 'worlds': 1000, 'rotation': 'targets', 'pool': 0,
                    'availability': 'actual participants', 'starters': 'projected', 'games': screen},
        'confirmation': selections,
        'stress_10000_worlds': {'selection': str(STRESS_PATH), 'strata': stress, 'player_tiers': tier_counts,
                                'purpose': 'outcome-stratified stress diagnostic, not representative or a tuning panel'},
        'seed_noise_floor': seed_noise,
        'protocol': {'game_cluster_bootstrap_replicates': a1_compare.BOOTSTRAP_REPLICATES,
                     'game_cluster_bootstrap_seed': a1_compare.BOOTSTRAP_SEED,
                     'shared_seeds': 'same starting seed, not proof random draws remain aligned across different mechanisms',
                     'cutoff_limitations': 'F1-F3 require dated assignment fits and rebuilt matchup features; '
                                           'first-retained-season fallback priors need correction before promotion'},
        'commands': {
            'control': '.venv/bin/python -u scripts/backtest.py --config models/v1.2d.json '
                       '--models folds/v1.2d_F4_all --fold F4 --games 200 --seed 20261119 --worlds 1000 '
                       '--jobs 4 --rotation targets --pool 0 --name a1_s01_control',
            'independent_seed': '.venv/bin/python -u scripts/backtest.py --config models/v1.2d.json '
                                '--models folds/v1.2d_F4_all --fold F4 --games 200 --seed 20261119 --worlds 1000 '
                                '--jobs 4 --rotation targets --pool 0 --simulation-stream 1 --name a1_s01_seed2',
            'compare': '.venv/bin/python scripts/a1_compare.py <control-run> <independent-seed-run> --output <new-report>',
            'confirmation': 'Run the manifest IDs with --game-ids, --seed-key a1-confirmation-<fold> and '
                            '--simulation-stream 0; repeat with stream 1. Fit dated fold inputs first.'},
        'input_fingerprints': inputs,
        'production_model_fingerprints': production_models,
        'upstream_build_fingerprints': upstream_build,
        'protocol_code_fingerprints': [fingerprint(ROOT / 'scripts/a1_compare.py'),
                                       fingerprint(ROOT / 'scripts/a1_manifest.py'),
                                       fingerprint(ROOT / 'scripts/a1_quarter_audit.py'),
                                       fingerprint(ROOT / 'scripts/a1_output_audit.py'),
                                       fingerprint(ROOT / 'scripts/a1_availability_cohort.py')],
        'artifact_fingerprints': [fingerprint(p) for p in artifacts],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--output', type=Path, required=True, help='new manifest path; existing manifests are never overwritten')
    ap.add_argument('--control-run', help='regenerated full-control run ID, when complete')
    ap.add_argument('--seed-run', help='independent-seed run ID, when complete')
    args = ap.parse_args()
    if args.output.exists():
        raise FileExistsError(f'refusing to overwrite {args.output}')
    manifest = build(args.control_run, args.seed_run)
    write_json(args.output, manifest, pretty=True)
    print(f"saved {args.output}: {len(manifest['control']['games'])} screen games; "
          f"confirmation games {[x['selected_games'] for x in manifest['confirmation'].values()]}")


if __name__ == '__main__':
    main()
