#!/usr/bin/env python3
"""Retain small ESPN headshots for offline display, using URLs in already collected rosters."""
from __future__ import annotations

import argparse
import gzip
import hashlib
from pathlib import Path
import re
import sys
import time
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from basketball_common import DATA, RAW, atomic_bytes, read_json, sha256_file, utc_now, write_json
from scripts.fetch_espn import Client, latest_run

ICONS = DATA / 'player-icons'
MANIFEST = ICONS / 'manifest.json'


def collect(limit=None):
    sources = sorted((latest_run() / 'roster').glob('*.json.gz'))
    if not sources:
        raise ValueError('no retained rosters')
    people = {}
    for path in sources:
        with gzip.open(path, 'rt') as stream:
            roster = __import__('json').load(stream)
        for athlete in roster.get('athletes', []):
            pid = str(athlete['id'])
            url = (athlete.get('headshot') or {}).get('href')
            if not pid.isascii() or not pid.isdigit():
                raise ValueError('invalid ESPN athlete identity')
            people[pid] = {'name': athlete.get('displayName'), 'url': url}
    ids = sorted(people, key=int)
    if limit is not None:
        ids = ids[:limit]
    previous = read_json(MANIFEST) if MANIFEST.exists() else {'players': {}}
    entries = previous['players'].copy()
    client, errors = Client(delay=.5, retries=1, timeout=15), []
    started = time.monotonic()
    ICONS.mkdir(parents=True, exist_ok=True)
    retained = RAW / 'player-icons'
    retained.mkdir(parents=True, exist_ok=True)
    added = reused = 0
    for i, pid in enumerate(ids, 1):
        person = people[pid]
        try:
            url = person['url']
            parsed = urlparse(url or '')
            if parsed.scheme != 'https' or parsed.netloc != 'a.espncdn.com' or not re.fullmatch(r'/i/headshots/nba/players/full/' + pid + r'\.png', parsed.path):
                raise ValueError('no supported retained ESPN headshot URL')
            target = ICONS / f'{pid}.png'
            old = entries.get(pid)
            if old and old['source_url'] == url and target.exists():
                if sha256_file(target) != old['sha256']:
                    raise ValueError('existing icon differs from its manifest')
                reused += 1
            else:
                fetch_url = f'https://a.espncdn.com/combiner/i?img={parsed.path}&w=96&h=96&scale=crop'
                data = client.get(fetch_url)
                if data[:8] != b'\x89PNG\r\n\x1a\n' or len(data) < 24:
                    raise ValueError('headshot response is not PNG')
                width, height = int.from_bytes(data[16:20], 'big'), int.from_bytes(data[20:24], 'big')
                if not (0 < width <= 192 and 0 < height <= 192):
                    raise ValueError('headshot response is not a small icon')
                digest = hashlib.sha256(data).hexdigest()
                raw = retained / f'{digest}.png'
                if not raw.exists():
                    atomic_bytes(raw, data)
                if target.exists() and sha256_file(target) != digest:
                    from basketball_common import archive_paths
                    archive_paths([target])
                atomic_bytes(target, data)
                entries[pid] = {'name': person['name'], 'source_url': url, 'fetch_url': fetch_url,
                                'sha256': digest, 'raw': str(raw.relative_to(ROOT)), 'retrieved_at': utc_now(),
                                'width': width, 'height': height}
                added += 1
        except Exception as error:
            errors.append({'player': pid, 'reason': str(error)})
        if i == len(ids) or i % max(1, len(ids) // 10) == 0:
            write_json(MANIFEST, {'provider': 'ESPN retained roster headshot URLs', 'players': entries,
                                 'missing': errors, 'roster_sources': {str(p.relative_to(ROOT)): sha256_file(p) for p in sources}}, pretty=True)
            print(f'icons {i}/{len(ids)} in {time.monotonic() - started:.1f}s; added {added}, reused {reused}, missing {len(errors)}', flush=True)
    return {'population': len(ids), 'added': added, 'reused': reused, 'missing': len(errors), 'requests': client.count,
            'elapsed_seconds': time.monotonic() - started, 'manifest_sha256': sha256_file(MANIFEST),
            'retained_icons': len(entries), 'bytes': sum(p.stat().st_size for p in ICONS.glob('*.png'))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--limit', type=int)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or (args.limit is not None and args.limit < 1):
        raise ValueError('fresh output and positive limit required')
    report = collect(args.limit)
    write_json(args.output, {'kind': 'offline player icon collection; no model inputs changed', **report,
                            'source_sha256': sha256_file(Path(__file__))}, pretty=True)


if __name__ == '__main__':
    main()
