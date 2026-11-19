#!/usr/bin/env python3
"""Serve the MusNBA dashboard and its read-only API on the laptop.

  .venv/bin/python scripts/serve.py            http://127.0.0.1:8766
  .venv/bin/python scripts/serve.py --host 0.0.0.0   reachable from a phone on the same network

Read-only: files under data/views/api and data/logos plus the web app. Never fetches providers,
fits or simulates. Rebuild views with scripts/nightly.py; edits to web files appear on refresh.
"""
from __future__ import annotations

import argparse
import gzip
import json
import mimetypes
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import LOGOS, VIEWS, WEB  # noqa: E402

API_PATH = re.compile(r'^/api/([a-z0-9_-]+(?:/[A-Za-z0-9_.-]+)*)$')
LOGO_PATH = re.compile(r'^/logos/(\d+(?:-dark)?)\.png$')
WEB_FILES = {'/': 'index.html', '/index.html': 'index.html', '/manifest.webmanifest': 'manifest.webmanifest',
             '/sw.js': 'sw.js', '/icon.svg': 'icon.svg', '/icon-192.png': 'icon-192.png',
             '/icon-512.png': 'icon-512.png', '/apple-touch-icon.png': 'apple-touch-icon.png'}
TYPES = {'.mjs': 'text/javascript', '.js': 'text/javascript', '.html': 'text/html; charset=utf-8',
         '.json': 'application/json', '.webmanifest': 'application/manifest+json', '.svg': 'image/svg+xml',
         '.png': 'image/png'}


class Handler(BaseHTTPRequestHandler):
    server_version = 'MusNBA/0.1'

    def log_message(self, fmt, *args):
        if getattr(self.server, 'verbose', False):
            super().log_message(fmt, *args)

    def send(self, status: int, body: bytes, content_type: str, cache: str = 'no-cache'):
        if len(body) > 1024 and 'gzip' in (self.headers.get('Accept-Encoding') or '') and not content_type.startswith('image/'):
            body = gzip.compress(body, compresslevel=5)
            encoded = True
        else:
            encoded = False
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', cache)
        self.send_header('X-Content-Type-Options', 'nosniff')
        if encoded:
            self.send_header('Content-Encoding', 'gzip')
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def error_json(self, status: int, message: str):
        self.send(status, json.dumps({'error': message}).encode(), 'application/json')

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        path = self.path.split('?', 1)[0].split('#', 1)[0]
        if (m := API_PATH.match(path)):
            target = (VIEWS / 'api' / (m.group(1) + '.json')).resolve()
            if not target.is_relative_to((VIEWS / 'api').resolve()) or not target.is_file():
                return self.error_json(404, 'Not in the retained data. Run scripts/nightly.py to build it.')
            return self.send(200, target.read_bytes(), 'application/json')
        if (m := LOGO_PATH.match(path)):
            target = LOGOS / (m.group(1) + '.png')
            if not target.is_file():
                return self.error_json(404, 'Logo not collected')
            return self.send(200, target.read_bytes(), 'image/png', 'max-age=86400')
        name = WEB_FILES.get(path)
        if name is None and re.fullmatch(r'/assets/[a-z0-9-]+\.mjs', path):
            name = path.removeprefix('/assets/')
        if name and (WEB / name).is_file():
            target = WEB / name
            return self.send(200, target.read_bytes(), TYPES.get(target.suffix, mimetypes.guess_type(target.name)[0] or 'application/octet-stream'))
        return self.error_json(404, 'Not found')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8766)
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()
    if not (VIEWS / 'api' / 'meta.json').exists():
        print('No views yet: run .venv/bin/python scripts/nightly.py first (the app will show an error until then).',
              file=sys.stderr)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.verbose = args.verbose
    print(f'MusNBA on http://{args.host}:{args.port}  (Ctrl+C to stop)', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
