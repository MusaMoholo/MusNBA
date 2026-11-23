"""Shared paths, identities, time and storage helpers for MusNBA.

Slate dates are US Eastern game dates (the NBA's own definition of a day). Displayed tip-offs
use UK time with ET alongside; the frontend owns display formatting.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import shutil
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
RAW = DATA / 'raw' / 'espn'
DERIVED = DATA / 'derived'
SNAPSHOTS = DATA / 'snapshots'
VIEWS = DATA / 'views'
LOGOS = DATA / 'logos'
MASTER_CSV = DATA / 'master_fixtures.csv'
WEB = ROOT / 'scripts' / 'webapp'
ARCHIVE_ROOT = Path.home() / 'Basketball_archive_ops'

ET = ZoneInfo('America/New_York')
UK = ZoneInfo('Europe/London')

APP_NAME = 'MusNBA'
SEASON = 2027            # ESPN's season year for 2026-27
SEASON_LABEL = '2026-27'
SEASON_TYPE = 2          # regular season

# Conference/division membership by ESPN abbreviation. Checked against the collected team list.
DIVISIONS = {
    'Atlantic': ['BOS', 'BKN', 'NY', 'PHI', 'TOR'],
    'Central': ['CHI', 'CLE', 'DET', 'IND', 'MIL'],
    'Southeast': ['ATL', 'CHA', 'MIA', 'ORL', 'WSH'],
    'Northwest': ['DEN', 'MIN', 'OKC', 'POR', 'UTAH'],
    'Pacific': ['GS', 'LAC', 'LAL', 'PHX', 'SAC'],
    'Southwest': ['DAL', 'HOU', 'MEM', 'NO', 'SA'],
}
EAST_DIVISIONS = {'Atlantic', 'Central', 'Southeast'}
# ESPN franchise ids. All-Star and exhibition sides (31, 32, 111386, 132374, 132375 in 2022-26) have others and
# are excluded from training data (FINDINGS §3h).
NBA_TEAM_IDS = frozenset(str(i) for i in range(1, 31))
DIVISION_OF = {abbr: div for div, teams in DIVISIONS.items() for abbr in teams}
CONFERENCE_OF = {abbr: ('East' if div in EAST_DIVISIONS else 'West') for abbr, div in DIVISION_OF.items()}
LINEUP_TIMING_POLICY = 'completed_before_tip-v1'


def parse_utc(value: str) -> datetime:
    """ESPN instants look like 2026-11-20T01:00Z or 2026-11-20T01:00:00Z."""
    text = value.strip().replace('Z', '+00:00')
    if len(text) == len('2026-11-20T01:00+00:00'):
        text = text[:16] + ':00' + text[16:]
    return datetime.fromisoformat(text).astimezone(timezone.utc)


def slate_date(utc_iso: str) -> str:
    return parse_utc(utc_iso).astimezone(ET).date().isoformat()


def today_et() -> str:
    return datetime.now(ET).date().isoformat()


def day_shift(day: str, days: int) -> str:
    return (date.fromisoformat(day) + timedelta(days=days)).isoformat()


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def forecast_meta(meta: dict, game_id: str) -> dict:
    """Return a game's original metadata when a snapshot carries per-game provenance."""
    schema = meta.get('game_provenance_schema')
    if schema is None:
        if 'game_provenance' in meta:
            raise ValueError(f'{game_id}: game provenance has no schema')
        return meta
    if type(schema) is not int or schema != 1:
        raise ValueError(f'unknown game provenance schema: {schema!r}')
    records = meta.get('game_provenance')
    if not isinstance(records, dict) or not isinstance(records.get(game_id), dict):
        raise ValueError(f'{game_id}: missing game provenance')
    record = records[game_id]
    if 'game_provenance_schema' in record or 'game_provenance' in record:
        raise ValueError(f'{game_id}: nested game provenance is invalid')
    return record


def verified_pre_tip(meta: dict, game_id: str) -> bool | None:
    meta = forecast_meta(meta, game_id)
    flags = meta.get('pre_tip')
    if not meta.get('completed_at') or not isinstance(flags, dict):
        return None
    try:
        completed = datetime.fromisoformat(meta['completed_at'].replace('Z', '+00:00'))
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError('invalid snapshot completion timestamp') from exc
    if completed.utcoffset() is None:
        raise ValueError('snapshot completion timestamp needs a timezone')
    value = flags.get(game_id)
    return value if isinstance(value, bool) else None


def packed(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def read_json(path: Path):
    path = Path(path)
    if path.suffix == '.gz':
        with gzip.open(path, 'rt', encoding='utf-8') as stream:
            return json.load(stream)
    return json.loads(path.read_text(encoding='utf-8'))


def atomic_bytes(path: Path, data: bytes) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, staging = tempfile.mkstemp(prefix='.' + path.name + '.', suffix='.partial', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(data)
        os.replace(staging, path)
    finally:
        Path(staging).unlink(missing_ok=True)


def write_json(path: Path, value, pretty: bool = False) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=1 if pretty else None,
                      separators=None if pretty else (',', ':'), allow_nan=False)
    data = text.encode('utf-8')
    if Path(path).suffix == '.gz':
        data = gzip.compress(data, compresslevel=6, mtime=0)
    atomic_bytes(path, data)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def archive_paths(paths, root: Path | None = None) -> Path:
    """Copy files/directories outside the repo and verify bytes before the caller replaces them."""
    root = Path(root or ARCHIVE_ROOT)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    target = root / f'archive_{stamp}_{os.getpid()}'
    for path in paths:
        path = Path(path)
        if not path.exists():
            continue
        try:
            rel = path.resolve().relative_to(ROOT)
        except ValueError:
            rel = Path(path.name)
        destination = target / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        if path.is_dir():
            shutil.copytree(path, destination)
            for item in path.rglob('*'):
                if item.is_file():
                    assert item.read_bytes() == (destination / item.relative_to(path)).read_bytes()
        else:
            shutil.copy2(path, destination)
            assert path.read_bytes() == destination.read_bytes()
    return target
