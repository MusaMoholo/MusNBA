"""Verified retained player photos shared by views, serving and exports."""
from basketball_common import DATA, read_json, sha256_file

ICONS = DATA / 'player-icons'


def catalogue():
    path = ICONS / 'manifest.json'
    if not path.exists():
        return {'ids': [], 'provider': 'ESPN'}
    manifest = read_json(path)
    ids = []
    for pid, entry in manifest['players'].items():
        if not pid.isascii() or not pid.isdigit() or sha256_file(ICONS / f'{pid}.png') != entry['sha256']:
            raise ValueError('retained player photo differs from its manifest')
        ids.append(pid)
    return {'ids': sorted(ids, key=int), 'provider': 'ESPN', 'manifest_sha256': sha256_file(path)}
