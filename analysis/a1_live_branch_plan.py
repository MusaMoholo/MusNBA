#!/usr/bin/env python3
"""Plan all current-slate branch counts and exact masses without simulating or changing inputs."""
import argparse
from dataclasses import asdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from basketball_common import DERIVED, SNAPSHOTS, read_json, sha256_file, write_json
from scripts import a1_lineup_branches, box_scores, engine, master_fixtures
from scripts.a1_branch_persist import source_paths
from scripts.season_stats import period_profiles, player_table, team_table


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--day', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    meta = read_json(SNAPSHOTS / args.day / 'meta.json')
    if meta['origin'] != args.day or meta['kind'] != 'prospective':
        raise ValueError('requires a current prospective snapshot origin')
    paths = source_paths(engine.ENGINE['models']) + [Path(__file__), SNAPSHOTS / args.day / 'meta.json']
    hashes = {str(p.relative_to(ROOT)): sha256_file(p) for p in paths}
    teams = read_json(DERIVED / 'teams.json')
    registry = read_json(DERIVED / 'players.json')['players']
    tr, pr, qr = [box_scores.load_csv(name + '.csv') for name in ('team_games', 'player_games', 'player_periods')]
    T, lg = team_table(tr, args.day, teams)
    P = player_table(pr, args.day)
    Q, priors = period_profiles(qr, pr, args.day, tr, blowout=15)
    rows = []
    for fixture in master_fixtures.load():
        if fixture['date_et'] != args.day:
            continue
        g = engine.inputs_for(fixture, args.day, T, lg, P, registry, Q, priors, origin=args.day)
        selected, ranking = a1_lineup_branches.live_selection(g, registry, engine._MINUTES[args.day], T, lg, P, Q, priors)
        branches = a1_lineup_branches.enumerate_branches(g, [(p.team_id, p.player_id) for p in selected]) if selected else ()
        rows.append({'game': fixture['game_id'], 'selected': [asdict(p) for p in selected],
                     'branches': [{'id': b.branch_id, 'weight': {'numerator': str(b.weight.numerator), 'denominator': str(b.weight.denominator)}} for b in branches],
                     'simulations_needed': max(1, len(branches)), 'ranking': ranking})
        print(f'planned {len(rows)} games; {sum(r["simulations_needed"] for r in rows)} game/branch batches', flush=True)
    if any(sha256_file(ROOT / p) != digest for p, digest in hashes.items()):
        raise ValueError('planning inputs changed')
    write_json(args.output, {'kind': 'current-slate branch planning only; no simulations or release', 'origin': args.day,
                            'input_sha256': hashes, 'source_sha256': sha256_file(Path(__file__)), 'games': rows,
                            'game_branch_batches': sum(r['simulations_needed'] for r in rows), 'worlds_per_batch': 10000}, pretty=True)


if __name__ == '__main__':
    main()
