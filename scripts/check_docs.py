#!/usr/bin/env python3
"""Check lean live docs, local links/fences and immutable historical snapshots (stdlib only)."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import tarfile
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
# Review gates, not targets to fill. Record a reason before changing a budget.
WORD_BUDGETS = {
    'AGENTS.md': 1300,
    'HANDOFF_NEXT.md': 1800,
    'PLAN.md': 1300,
    'MODEL.md': 2400,
    'README.md': 1400,
}
TOTAL_WORD_BUDGET = 9000  # Includes policy references, not only root docs.
REFERENCE_WORD_BUDGET = 1400
POLICIES = {'docs/protocols/promotion_v1_20261122.md',
            'docs/protocols/promotion_v2_20261123.md',
            'docs/protocols/promotion_v3_20261123.md'}
LIVE_FILE_BUDGET = 8  # Five current homes plus three immutable acceptance contracts.
LINK = re.compile(r'!?\[[^\]\n]*\]\((<[^>]+>|[^\s)]+)(?:\s+"[^"]*")?\)')


def prose_and_anchors(source: str) -> tuple[str, set[str], bool]:
    """Ignore fenced examples when finding links/headings; follow GitHub heading slugs."""
    prose = []
    anchors = set()
    duplicates: dict[str, int] = {}
    fence = ''
    for line in source.splitlines():
        marker = re.match(r'^\s{0,3}(`{3,}|~{3,})', line)
        if marker:
            current = marker[1]
            if not fence:
                fence = current
            elif current[0] == fence[0] and len(current) >= len(fence):
                fence = ''
            continue
        if fence:
            continue
        prose.append(line)
        heading = re.match(r'^#{1,6}\s+(.+?)\s*#*$', line)
        if heading:
            slug = re.sub(r'[^\w\- ]', '', heading[1].lower()).replace(' ', '-')
            number = duplicates.get(slug, 0)
            duplicates[slug] = number + 1
            anchors.add(f'{slug}-{number}' if number else slug)
        anchors.update(re.findall(r'<a\s+(?:id|name)=["\']([^"\']+)', line))
    return '\n'.join(prose), anchors, bool(fence)


def main() -> int:
    errors = []
    total = 0
    files = []
    for directory, folders, names in os.walk(ROOT):
        folders[:] = [name for name in folders if not name.startswith('.')
                      and name not in ('data', 'node_modules', 'exports')]
        files.extend(Path(directory) / name for name in names if name.endswith('.md'))
    files.sort()
    names = {str(p.relative_to(ROOT)) for p in files}
    expected_names = set(WORD_BUDGETS) | POLICIES
    if names != expected_names:
        errors.append(f'live document inventory: missing={sorted(expected_names-names)}, '
                      f'unplanned={sorted(names-expected_names)}; consolidate before adding a file')
    if len(files) > LIVE_FILE_BUDGET:
        errors.append(f'{len(files)} live documents exceed file budget {LIVE_FILE_BUDGET}')
    parsed = {}
    for path in files:
        if not path.is_file():
            errors.append(f'missing document: {path.relative_to(ROOT)}')
            continue
        source = path.read_text()
        parsed[path] = prose_and_anchors(source)
        if parsed[path][2]:
            errors.append(f'{path.relative_to(ROOT)}: unclosed code fence')
        words = len(source.split())
        total += words
        if path.parent == ROOT:
            budget = WORD_BUDGETS.get(path.name, REFERENCE_WORD_BUDGET)
            print(f'{path.name:20} {words:5,} / {budget:,} words')
        else:
            budget = REFERENCE_WORD_BUDGET
        if words > budget:
            errors.append(f'{path.relative_to(ROOT)}: {words} words exceed budget {budget}')
    if total > TOTAL_WORD_BUDGET:
        errors.append(f'live docs: {total} words exceed total budget {TOTAL_WORD_BUDGET}')

    links = 0
    for path, (prose, _, _) in list(parsed.items()):
        for match in LINK.finditer(prose):
            target = urlsplit(match[1].strip('<>'))
            if target.scheme or target.netloc:
                continue
            linked = (path.parent / unquote(target.path)).resolve() if target.path else path
            links += 1
            if not linked.exists():
                errors.append(f'{path.relative_to(ROOT)}: missing link {match[1]}')
                continue
            if target.fragment and linked.suffix == '.md':
                if linked not in parsed:
                    parsed[linked] = prose_and_anchors(linked.read_text())
                if unquote(target.fragment) not in parsed[linked][1]:
                    errors.append(f'{path.relative_to(ROOT)}: missing heading {match[1]}')

    archived = 0
    manifest = ROOT / 'docs/archive/20261123_document_history.manifest.json'
    try:
        report = json.loads(manifest.read_text())
        archive = manifest.parent / report['archive']
        if hashlib.sha256(archive.read_bytes()).hexdigest() != report['sha256']:
            errors.append('documentation archive checksum changed')
        for name in POLICIES:
            path = ROOT / name
            if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() != report['files'][name]['sha256']:
                errors.append(f'versioned policy changed in place: {name}; freeze a new version instead')
        with tarfile.open(archive) as tar:
            if len(tar.getmembers()) != len(report['files']) or set(tar.getnames()) != set(report['files']):
                errors.append('documentation archive inventory changed')
            for name, expected in report['files'].items():
                member = tar.getmember(name)
                if not member.isfile():
                    errors.append(f'archive member is not a regular file: {name}')
                    continue
                data = tar.extractfile(member).read()
                actual = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data),
                          'words': len(data.decode().split()), 'lines': len(data.splitlines())}
                if actual != expected:
                    errors.append(f'archived original changed: {name}')
                archived += 1
            # The earlier eight-document snapshot keeps its original independent manifest too.
            nested = 'docs/archive/2026-11-23-before-lean/'
            original = json.loads(tar.extractfile(nested + 'manifest.json').read())
            if len(original['files']) != 8:
                errors.append('original eight-document snapshot incomplete')
            for name, expected in original['files'].items():
                data = tar.extractfile(nested + name).read()
                if hashlib.sha256(data).hexdigest() != expected['sha256']:
                    errors.append(f'original snapshot checksum mismatch: {name}')
    except (OSError, ValueError, KeyError, tarfile.TarError) as error:
        errors.append(f'documentation archive invalid: {error}')

    print(f'Live total: {len(files)}/{LIVE_FILE_BUDGET} files; {total:,}/{TOTAL_WORD_BUDGET:,} words; '
          f'{links} local links; {archived} archived originals; {len(errors)} errors')
    for error in errors:
        print(f'FAIL {error}')
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
