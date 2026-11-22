#!/usr/bin/env python3
"""Add isolated research inputs to a new phone or laptop bundle for offline testing."""
import argparse
import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import packed, sha256_file  # noqa: E402
from scripts.export_musnba import record, verify  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('view', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--fixture', type=Path)
    parser.add_argument('--payload', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an existing bundle')
    view_text = args.view.read_text()
    view = json.loads(view_text)
    research = view['research']
    if (research['label'] != 'Research only; not a validated forecast' or research['choices']
            or research['selected_mass'] != research['total_mass']
            or set(view) != {'game', 'research', 'sim'} or not view['game']['id'].isdigit()):
        raise ValueError('Expected-only research view required')
    key = '/api/research/a1/' + view['game']['id']
    if bool(args.fixture) != bool(args.payload):
        raise ValueError('Laptop research requires both fixture and payload')
    if args.fixture:
        payload_text = args.payload.read_text()
        payload = json.loads(payload_text)
        if (sha256_file(args.fixture) != payload['fixture_sha256']
                or payload['fixture_sha256'] != research['fixture_sha256']
                or payload['game'] != view['game']['id']):
            raise ValueError('Research fixture provenance differs')
        modules = {name: (ROOT / 'analysis' / path).read_text() for name, path in (
            ('source', 'a1_branch_world_source.mjs'), ('summary', 'a1_branch_game_summary.mjs'),
            ('contract', 'a1_game_view_contract.mjs'))}
        view_text = ('{"view":' + view_text + ',"payload":' + payload_text
                     + ',"modules":' + json.dumps(modules) + ',"fixture":' + args.fixture.read_text() + '}')
    with gzip.open(args.bundle, 'rt', encoding='utf-8') as src, gzip.open(args.output, 'xt', encoding='utf-8', compresslevel=6) as dst:
        header = json.loads(next(src))
        profile = 'laptop' if args.fixture else 'phone'
        if header.get('profile') != profile:
            raise ValueError(f'A {profile} bundle is required')
        dst.write(packed(header) + '\n')
        count = 0
        ended = False
        for line in src:
            item = json.loads(line)
            if ended:
                raise ValueError('Data after bundle end')
            if item.get('end'):
                if item['records'] != count:
                    raise ValueError('Original bundle count differs')
                ended = True
                continue
            if item['key'] == key or (profile == 'phone' and item['key'].startswith('/api/game/') and item['key'].endswith('/worlds')):
                raise ValueError('Bundle already contains research or per-world data')
            dst.write(line)
            count += 1
        if not ended:
            raise ValueError('Incomplete original bundle')
        dst.write(packed(record(key, view_text)) + '\n')
        count += 1
        dst.write(packed({'end': True, 'records': count}) + '\n')
    verify(args.output, header, count)
    print(f'Research-only {profile} bundle: {count} records, {args.output.stat().st_size} bytes')


if __name__ == '__main__':
    main()
