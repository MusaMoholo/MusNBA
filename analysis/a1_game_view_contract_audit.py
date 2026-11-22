#!/usr/bin/env python3
"""Independently compare research view data with already-audited selected summaries."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import sha256_file, write_json  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('probe', type=Path)
    parser.add_argument('summary_audit', type=Path)
    parser.add_argument('payload_audit', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an existing audit')
    probe = json.loads(args.probe.read_text())
    for path, digest in probe['source_sha256'].items():
        if sha256_file(Path(path)) != digest:
            raise ValueError(f'{path} hash differs')
    view_path = Path(probe['view'])
    if sha256_file(view_path) != probe['view_sha256']:
        raise ValueError('view hash differs')
    summary_audit = json.loads(args.summary_audit.read_text())
    payload_audit = json.loads(args.payload_audit.read_text())
    if (summary_audit['summary_sha256'] != sha256_file(Path(probe['summary']))
            or payload_audit['payload_sha256'] != sha256_file(Path(probe['payload']))):
        raise ValueError('inputs do not match independently audited files')
    summary = json.loads(Path(probe['summary']).read_text())['result']
    payload = json.loads(Path(probe['payload']).read_text())
    game = json.loads(Path(probe['game']).read_text())['game']
    view = json.loads(view_path.read_text())
    research, sim = view['research'], view['sim']
    if (set(view) != {'game', 'research', 'sim'} or view['game']['id'] != game['id']
            or research['fixture_sha256'] != payload['fixture_sha256']
            or research['choices'] != summary['choices']
            or research['selected_worlds'] != summary['selected_worlds']
            or research['selected_mass'] != summary['selected_mass']
            or research['total_mass'] != summary['total_mass']
            or research['selected_players'] != summary['selected_players']
            or research['weight_assumptions'] != summary['weight_assumptions']
            or sim['periods'] != summary['periods'] or sim['ot'] != summary['ot']):
        raise ValueError('view selection, team distributions or provenance differ')
    metadata = {p['id']: p for p in payload['player_metadata']}
    fields = ('id', 'played', 'opening_share', 'periods',
              'double_double', 'triple_double', 'quadruple_double', 'quintuple_double', 'five_by_five')
    players = distributions = 0
    for side in ('home', 'away'):
        if sim[side]['box'] != summary[side]['box']:
            raise ValueError(f'{side} box differs')
        for actual, expected in zip(sim[side]['players'], summary[side]['players'], strict=True):
            if (any(actual[k] != expected[k] for k in fields)
                    or actual['selected_availability'] != expected['availability']
                    or actual.get('if_plays') != expected.get('if_plays')
                    or actual['name'] != metadata[expected['id']]['name']
                    or any(actual[k] != metadata[expected['id']].get(k)
                           for k in ('pos', 'jersey', 'status', 'availability_basis'))
                    or 'availability' in actual or 'starter' in actual or 'minutes_basis' in actual):
                raise ValueError(f"{expected['id']}: selected player differs")
            distributions += sum(len(period['stats']) for period in actual['periods'].values())
            players += 1
    write_json(args.output, {
        'kind': 'independent selected view adaptation accounting; not a browser or forecast test',
        'probe': str(args.probe), 'probe_sha256': sha256_file(args.probe),
        'summary_audit': str(args.summary_audit), 'summary_audit_sha256': sha256_file(args.summary_audit),
        'payload_audit': str(args.payload_audit), 'payload_audit_sha256': sha256_file(args.payload_audit),
        'audit_sha256': sha256_file(Path(__file__)), 'players_checked': players,
        'player_distributions_checked': distributions, 'selected_worlds': research['selected_worlds'],
        'selected_mass': research['selected_mass'],
    }, pretty=True)
    print(f"{players} players and {distributions} player distributions reconciled")


if __name__ == '__main__':
    main()
