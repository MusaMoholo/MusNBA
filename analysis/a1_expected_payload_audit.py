#!/usr/bin/env python3
"""Independently check the isolated Expected-only payload against audited inputs."""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import sha256_file, write_json  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('probe', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an existing audit')
    probe = json.loads(args.probe.read_text())
    paths = {key: Path(probe[key]) for key in ('fixture', 'fixture_audit', 'summary_probe', 'summary_audit', 'payload')}
    for key, path in paths.items():
        if sha256_file(path) != probe[f'{key}_sha256']:
            raise ValueError(f'{key} hash differs')
    fixture = json.loads(paths['fixture'].read_text())
    summary_probe = json.loads(paths['summary_probe'].read_text())
    summary_path = Path(summary_probe['summary'])
    if sha256_file(summary_path) != summary_probe['summary_sha256']:
        raise ValueError('summary hash differs')
    summary = json.loads(summary_path.read_text())
    payload_bytes = paths['payload'].read_bytes()
    payload = json.loads(payload_bytes)
    expected_keys = {'kind', 'fixture_sha256', 'source_sha256', 'game', 'origin', 'engine', 'model',
                     'snapshot_inputs', 'selected_players', 'weight_assumptions', 'player_metadata', 'roster',
                     'limitations', 'expected'}
    if set(payload) != expected_keys or payload['expected'] != summary['result']:
        raise ValueError('payload shape or Expected summaries differ')
    for key in ('game', 'origin', 'engine', 'model', 'source_sha256', 'snapshot_inputs', 'selected_players',
                'weight_assumptions', 'player_metadata'):
        if payload[key] != fixture[key]:
            raise ValueError(f'payload {key} differs from fixture')
    world_meta = fixture['branches'][0]['worlds']
    if (payload['roster'] != {'players': world_meta['players'], 'side': world_meta['side']}
            or payload['fixture_sha256'] != probe['fixture_sha256'] or payload['expected']['choices']):
        raise ValueError('payload roster, source or selection differs')
    if len(payload_bytes) != probe['payload_bytes']:
        raise ValueError('payload size differs')
    forbidden = {'branches', 'lines', 'team_periods', 'availability', 'played', 'minutes_f64_le',
                 'period_lines', 'period_minutes_f64_le', 'opening_lineups', 'final_period'}

    def contains_raw(value: object) -> bool:
        if isinstance(value, dict):
            return any((key in forbidden and isinstance(item, str)) or contains_raw(item) for key, item in value.items())
        if isinstance(value, list):
            return any(contains_raw(item) for item in value)
        return False

    if contains_raw(payload):
        raise ValueError('payload contains encoded raw branch-world data')
    write_json(args.output, {'kind': 'independent Expected-only payload accounting; not a phone test',
                             'probe': str(args.probe), 'probe_sha256': sha256_file(args.probe),
                             'audit_sha256': sha256_file(Path(__file__)), 'payload_sha256': sha256_file(paths['payload']),
                             'game': payload['game'], 'origin': payload['origin'], 'players': len(payload['player_metadata']),
                             'selected_worlds': payload['expected']['selected_worlds'],
                             'bytes': len(payload_bytes), 'gzip6_bytes_python': len(gzip.compress(payload_bytes, compresslevel=6, mtime=0))}, pretty=True)
    print(f"{len(payload['player_metadata'])} player identities and all Expected summaries reconciled; no raw worlds")


if __name__ == '__main__':
    main()
