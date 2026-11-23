#!/usr/bin/env python3
"""Build an isolated browser-format fixture from audited research branch worlds."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from analysis import a1_branch_persist_audit  # noqa: E402
from basketball_common import sha256_file, write_json  # noqa: E402
from scripts import a1_expected  # noqa: E402


from scripts.player_worlds import packed_bytes, opening_lineups, pack_capture


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an existing browser fixture')
    report = json.loads(args.report.read_text())
    a1_branch_persist_audit.audit(report)
    snapshot_paths = [f"data/snapshots/{report['origin']}/{name}.json" for name in ('meta', 'games')]
    snapshot_inputs = {path: report['input_sha256'][path] for path in snapshot_paths}
    snapshot_game = json.loads((ROOT / snapshot_paths[1]).read_text())[report['game']]
    snapshot_players = {}
    for side, name in enumerate(('home', 'away')):
        for player in snapshot_game[name]['players']:
            if player['id'] in snapshot_players:
                raise ValueError('snapshot player identity is duplicated')
            snapshot_players[player['id']] = (side, player)
    branches = a1_expected.selected_branches(report, {})
    records = []
    roster = None
    for branch, weight in branches:
        with np.load(branch['capture'], allow_pickle=False) as data:
            packed = pack_capture(data)
        this_roster = (packed['players'], packed['side'])
        if roster is not None and roster != this_roster:
            raise ValueError('branch rosters differ')
        roster = this_roster
        records.append({'branch_id': branch['branch_id'], 'assignments': branch['assignments'],
                        'weight': a1_expected.fraction_json(weight), 'capture_sha256': branch['capture_sha256'],
                        'worlds': packed})
    ids, sides = roster
    if set(ids) != set(snapshot_players) or any(snapshot_players[player][0] != side for player, side in zip(ids, sides, strict=True)):
        raise ValueError('snapshot player identities or sides differ from captured worlds')
    identity_fields = ('id', 'name', 'pos', 'jersey', 'status', 'injury', 'availability_basis')
    player_metadata = [{key: snapshot_players[player][1].get(key) for key in identity_fields} for player in ids]
    write_json(args.output, {
        'kind': 'isolated research fixture; not a forecast or serving contract',
        'source': str(args.report), 'source_sha256': sha256_file(args.report),
        'algorithm_sha256': sha256_file(Path(__file__)), 'game': report['game'], 'origin': report['origin'],
        'engine': report['engine'], 'model': report['model'], 'snapshot_inputs': snapshot_inputs,
        'player_metadata': player_metadata,
        'selected_players': report['selected'], 'weight_assumptions': report['weight_assumptions'],
        'limitations': ['Availability probabilities are not calibrated.',
                        'Joint availability independence is unvalidated.',
                        'Not integrated into any served dashboard or bundle.'],
        'branches': records,
    }, pretty=False)
    print(f"{len(records)} branches, {sum(r['worlds']['worlds'] for r in records)} worlds; isolated fixture")


if __name__ == '__main__':
    main()
