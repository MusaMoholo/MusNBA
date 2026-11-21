#!/usr/bin/env python3
"""Export the MusNBA data bundle and/or build the data-free static PWA shell.

  .venv/bin/python scripts/export_musnba.py --shell _site --base-path /MusNBA/
  .venv/bin/python scripts/export_musnba.py --output ~/Desktop/MusNBA.musnba.gz

No collection, fitting or simulation. The bundle is the exact set of retained views
(data/views/api) plus team logos, frozen first, verified, then published atomically.
The shell never contains data.
"""
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import ARCHIVE_ROOT, LOGOS, VIEWS, WEB, archive_paths, packed  # noqa: E402

MODULES = ['app', 'ui', 'today', 'game', 'league', 'players', 'lab', 'outcomes', 'scenario', 'pwa', 'pwa-storage', 'static-api']
ICONS = ['icon.svg', 'icon-192.png', 'icon-512.png', 'apple-touch-icon.png']
BOOT = "<script type=\"module\" id=\"boot\">import {boot} from './assets/app.mjs'; boot();</script>"
STATIC_BOOT = ("<script type=\"module\" id=\"boot\">import {boot} from './assets/app.mjs'; "
               "import {start} from './assets/pwa.mjs'; await start(boot);</script>")


def publish(staging: Path, output: Path) -> None:
    os.replace(staging, output)
    flags = getattr(output.stat(), 'st_flags', 0)
    if hasattr(os, 'chflags') and flags & stat.UF_HIDDEN:  # iCloud can keep a dot-file's hidden flag
        os.chflags(output, flags & ~stat.UF_HIDDEN)


def build_shell(destination: Path, base_path: str = '/', archive_root=None) -> str:
    destination = Path(destination)
    base_path = '/' + base_path.strip('/') + '/' if base_path.strip('/') else '/'
    if not re.fullmatch(r'/(?:[A-Za-z0-9_-]+/)*', base_path):
        raise SystemExit('Base path must contain only simple URL directory names.')
    present = sorted(p.stem for p in WEB.glob('*.mjs'))
    if present != sorted(MODULES):
        raise SystemExit(f'Module list out of date: on disk {present}, expected {sorted(MODULES)} (update sw.js and MODULES).')
    sw_text = (WEB / 'sw.js').read_text()
    if not all(f"'{m}'" in sw_text for m in MODULES):
        raise SystemExit('sw.js MODULES does not list every module.')
    if destination.exists() and any(destination.iterdir()):
        saved = archive_paths([destination], archive_root or ARCHIVE_ROOT)
        print(f'previous shell archived: {saved}')
        shutil.rmtree(destination)
    (destination / 'assets').mkdir(parents=True, exist_ok=True)
    html = (WEB / 'index.html').read_text()
    if html.count(BOOT) != 1:
        raise SystemExit('index.html boot script not found exactly once.')
    (destination / 'index.html').write_text(html.replace(BOOT, STATIC_BOOT))
    for name in MODULES:
        shutil.copy2(WEB / f'{name}.mjs', destination / 'assets' / f'{name}.mjs')
    for name in ICONS + ['sw.js']:
        shutil.copy2(WEB / name, destination / name)
    manifest = json.loads((WEB / 'manifest.webmanifest').read_text())
    for key in ('id', 'start_url', 'scope'):
        manifest[key] = base_path
    for icon in manifest['icons']:
        icon['src'] = base_path + icon['src'].lstrip('/')
    (destination / 'manifest.webmanifest').write_text(json.dumps(manifest, indent=2) + '\n')
    (destination / '.nojekyll').touch()
    version = hashlib.sha256(b''.join(p.read_bytes() for p in sorted(destination.rglob('*')) if p.is_file())).hexdigest()[:20]
    sw = destination / 'sw.js'
    sw.write_text(sw.read_text().replace('__SHELL_VERSION__', version))
    (destination / '_headers').write_text(f'{base_path}sw.js\n  Cache-Control: no-cache\n{base_path}manifest.webmanifest\n'
                                          f'  Cache-Control: no-cache\n/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: no-referrer\n')
    for path in destination.rglob('*'):
        if path.is_file():
            assert path.suffix not in {'.gz', '.csv', '.py', '.json'} or path.name == 'manifest.webmanifest', path
    print(f'static shell: {destination} · base {base_path} · version {version}')
    return version


def record(key: str, body: str, content_type: str = 'application/json', binary: bool = False, status: int = 200) -> dict:
    out = {'key': key, 'status': status, 'type': content_type, 'binary': binary,
           'sha256': hashlib.sha256(body.encode()).hexdigest()}
    if not binary and len(body) > 1024:
        compressed = gzip.compress(body.encode(), compresslevel=6, mtime=0)
        out.update({'body_gzip': base64.b64encode(compressed).decode(), 'packed_sha256': hashlib.sha256(compressed).hexdigest()})
    else:
        out['body'] = body
    return out


def verify(path: Path, header: dict, expected: int) -> None:
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        assert json.loads(next(stream)) == header
        count, ended = 0, False
        for line in stream:
            item = json.loads(line)
            assert not ended
            if item.get('end'):
                assert item['records'] == count == expected
                ended = True
                continue
            if 'body_gzip' in item:
                raw = base64.b64decode(item['body_gzip'], validate=True)
                assert hashlib.sha256(raw).hexdigest() == item['packed_sha256']
                body = gzip.decompress(raw)
            else:
                body = item['body'].encode()
            assert hashlib.sha256(body).hexdigest() == item['sha256'], item['key']
            count += 1
        assert ended


def phone_record(key: str, text: str) -> str | None:
    """D36 (owner, 20 Nov): the phone app is stripped back — the 10,000-world distributions for the expected lineup (players
    and teams) only. No per-world files, so no Scenarios, Given…, joint grids, duels or lineup branches; no duel of the
    night on the slate. Returns the record body to export, or None to leave it out. Localhost views keep everything."""
    parts = key.strip('/').split('/')
    if parts[:2] == ['api', 'game'] and len(parts) == 4 and parts[3] == 'worlds':
        return None
    if parts[:2] == ['api', 'game'] and len(parts) == 3:
        d = json.loads(text)
        d['worlds'] = False
        return json.dumps(d, separators=(',', ':'), ensure_ascii=False)
    if parts[:2] == ['api', 'slate']:
        d = json.loads(text)
        for g in d.get('games', []):
            if isinstance(g.get('proj'), dict):
                g['proj'].pop('duel', None)
        return json.dumps(d, separators=(',', ':'), ensure_ascii=False)
    return text


def export_bundle(output: Path, archive_root=None) -> dict:
    output = Path(output).expanduser().absolute()
    if not output.name.endswith('.musnba.gz'):
        raise SystemExit('Use a .musnba.gz filename.')
    if output.resolve().is_relative_to((ROOT / 'data').resolve()):
        raise SystemExit('Export outside data/.')
    api = VIEWS / 'api'
    if not (api / 'meta.json').exists():
        raise SystemExit('No views to export: run scripts/nightly.py first.')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='musnba-export-') as tmp:
        frozen = Path(tmp)
        inventory = lambda: {str(p): (p.stat().st_size, p.stat().st_mtime_ns) for root in (api, LOGOS) for p in root.rglob('*') if p.is_file()}
        before = inventory()
        shutil.copytree(api, frozen / 'api')
        shutil.copytree(LOGOS, frozen / 'logos')
        if inventory() != before:
            raise SystemExit('Views changed during export; retry after nightly finishes. The previous export is unchanged.')
        meta = json.loads((frozen / 'api' / 'meta.json').read_text())
        header = {'format': 'musnba', 'version': 1, 'created': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                  'latest': meta['latest'], 'snapshots': [s['date'] for s in meta['snapshots']]}
        descriptor, staging = tempfile.mkstemp(prefix='.musnba-', suffix='.partial', dir=output.parent)
        os.close(descriptor)
        count = 0
        try:
            with gzip.open(staging, 'wt', encoding='utf-8', compresslevel=6) as stream:
                stream.write(packed(header) + '\n')
                for path in sorted((frozen / 'api').rglob('*.json')):
                    key = '/api/' + path.relative_to(frozen / 'api').with_suffix('').as_posix()
                    body = phone_record(key, path.read_text(encoding='utf-8'))
                    if body is None:
                        continue
                    stream.write(packed(record(key, body)) + '\n')
                    count += 1
                for path in sorted((frozen / 'logos').glob('*.png')):
                    stream.write(packed(record('/logos/' + path.name, base64.b64encode(path.read_bytes()).decode(), 'image/png', True)) + '\n')
                    count += 1
                stream.write(packed({'end': True, 'records': count}) + '\n')
            verify(Path(staging), header, count)
            if output.exists():
                saved = archive_paths([output], archive_root or ARCHIVE_ROOT)
                print(f'previous bundle archived: {saved}')
            publish(Path(staging), output)
        finally:
            Path(staging).unlink(missing_ok=True)
    print(f'bundle: {output} · {count:,} records · {output.stat().st_size / 1e6:.1f} MB · latest {header["latest"]}')
    return header


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--shell', type=Path, help='Build the data-free PWA into this (new or empty) directory')
    parser.add_argument('--base-path', default='/', help='Hosting directory, e.g. /MusNBA/ for GitHub Pages')
    parser.add_argument('--output', type=Path, help='Write a .musnba.gz data bundle')
    parser.add_argument('--archive-root', type=Path)
    args = parser.parse_args()
    if not args.shell and not args.output:
        parser.error('Provide --shell and/or --output')
    if args.shell:
        build_shell(args.shell, args.base_path, args.archive_root)
    if args.output:
        export_bundle(args.output, args.archive_root)


if __name__ == '__main__':
    main()
