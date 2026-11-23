#!/usr/bin/env python3
"""Check lean live docs, local links/fences and immutable historical snapshots (stdlib only)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
# Review gates, not targets to fill. Record a reason before changing a budget.
WORD_BUDGETS = {
    'AGENTS.md': 1600,
    'HANDOFF_NEXT.md': 1800,
    'PLAN.md': 1800,
    'ENGINE_PLAN.md': 2400,
    'TRAINING_PLAN.md': 2600,
    'FINDINGS.md': 2200,
    'DASHBOARD_PLAN.md': 1500,
    'README.md': 1300,
}
TOTAL_WORD_BUDGET = 15000
REFERENCE_WORD_BUDGET = 2500
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
    files = [ROOT / name for name in WORD_BUDGETS]
    files.extend(sorted((ROOT / 'docs').rglob('*.md')))
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
        if path.parent == ROOT:
            total += words
            budget = WORD_BUDGETS[path.name]
            print(f'{path.name:20} {words:5,} / {budget:,} words')
        elif 'archive' not in path.relative_to(ROOT).parts:
            budget = REFERENCE_WORD_BUDGET
        else:
            continue  # Frozen source history is not startup reading and has no live-doc budget.
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
    manifests = sorted((ROOT / 'docs' / 'archive').glob('*/manifest.json'))
    if not manifests:
        errors.append('missing documentation archive manifest')
    for manifest in manifests:
        report = json.loads(manifest.read_text())
        if set(report['files']) != set(WORD_BUDGETS):
            errors.append(f'{manifest.relative_to(ROOT)}: expected all eight original docs')
        for name, expected in report['files'].items():
            path = manifest.parent / name
            if not path.is_file():
                errors.append(f'missing archived original: {path.relative_to(ROOT)}')
                continue
            data = path.read_bytes()
            actual = {
                'sha256': hashlib.sha256(data).hexdigest(),
                'bytes': len(data),
                'words': len(data.decode().split()),
                'lines': len(data.splitlines()),
            }
            if actual != expected:
                errors.append(f'archived original changed: {path.relative_to(ROOT)}')
            archived += 1

    print(f'Live total: {total:,}/{TOTAL_WORD_BUDGET:,} words; '
          f'{links} local links; {archived} archived originals; {len(errors)} errors')
    for error in errors:
        print(f'FAIL {error}')
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
