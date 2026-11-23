#!/usr/bin/env python3
"""Build data/master_fixtures.csv: every regular-season game, resulted or not.

Rows come from the latest collected team schedules; final scores and period counts prefer the
retained final summary. Undrawn games (e.g. the two NBA Cup-determined games per team) do not
exist until the provider schedules them — no placeholder opponents or dates are invented.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import MASTER_CSV, RAW, SEASON_LABEL, atomic_bytes, read_json, slate_date  # noqa: E402
from scripts.fetch_espn import latest_run  # noqa: E402

COLUMNS = ['game_id', 'season', 'date_et', 'tip_utc', 'time_valid', 'status', 'status_detail',
           'away_id', 'away_abbr', 'home_id', 'home_abbr', 'away_pts', 'home_pts', 'periods',
           'neutral', 'venue', 'city', 'tv', 'notes', 'source']

STATUS = {'STATUS_SCHEDULED': 'scheduled', 'STATUS_FINAL': 'final', 'STATUS_IN_PROGRESS': 'live',
          'STATUS_HALFTIME': 'live', 'STATUS_END_PERIOD': 'live', 'STATUS_POSTPONED': 'postponed',
          'STATUS_CANCELED': 'canceled', 'STATUS_SUSPENDED': 'suspended', 'STATUS_DELAYED': 'delayed'}


def score_value(score):
    if isinstance(score, dict):
        score = score.get('value', score.get('displayValue'))
    if score in (None, ''):
        return ''
    return str(int(float(score)))


def broadcasts(competition):
    names = []
    for b in competition.get('broadcasts') or []:
        for name in b.get('names') or []:
            names.append(name)
        media = (b.get('media') or {}).get('shortName')
        if media:
            names.append(media)
    return '|'.join(dict.fromkeys(names))


def row_from_event(event: dict) -> dict:
    c = event['competitions'][0]
    side = {t['homeAway']: t for t in c['competitors']}
    status = (c.get('status') or event.get('status') or {}).get('type') or {}
    venue = c.get('venue') or {}
    notes = '|'.join(n.get('headline', '') for n in c.get('notes') or [] if n.get('headline'))
    return {
        'game_id': event['id'], 'season': SEASON_LABEL, 'date_et': slate_date(event['date']),
        'tip_utc': event['date'], 'time_valid': int(c.get('timeValid') is True),
        'status': STATUS.get(status.get('name'), (status.get('name') or 'unknown').replace('STATUS_', '').lower()),
        'status_detail': status.get('shortDetail') or status.get('detail') or '',
        'away_id': side['away']['team']['id'], 'away_abbr': side['away']['team']['abbreviation'],
        'home_id': side['home']['team']['id'], 'home_abbr': side['home']['team']['abbreviation'],
        'away_pts': score_value(side['away'].get('score')), 'home_pts': score_value(side['home'].get('score')),
        'periods': '', 'neutral': int(bool(c.get('neutralSite'))), 'venue': venue.get('fullName', ''),
        'city': ', '.join(x for x in ((venue.get('address') or {}).get('city'), (venue.get('address') or {}).get('state')) if x),
        'tv': broadcasts(c), 'notes': notes, 'source': 'schedule',
    }


def apply_summary(row: dict, summary: dict) -> dict:
    c = summary['header']['competitions'][0]
    side = {t['homeAway']: t for t in c['competitors']}
    row = dict(row)
    row['away_pts'] = score_value(side['away'].get('score'))
    row['home_pts'] = score_value(side['home'].get('score'))
    row['periods'] = str(max(len(side['home'].get('linescores') or []), len(side['away'].get('linescores') or [])) or '')
    row['status'] = 'final'
    row['status_detail'] = ((c.get('status') or {}).get('type') or {}).get('shortDetail', row['status_detail'])
    row['source'] = 'summary'
    return row


def build(run: Path | None = None) -> list[dict]:
    run = run or latest_run()
    events = {}
    for path in sorted((run / 'schedule').glob('*.json.gz')):
        for event in read_json(path).get('events', []):
            events[event['id']] = event
    if not events:
        raise SystemExit(f'No schedule events in {run}')
    rows = []
    final_dir = RAW / 'final'
    for eid, event in events.items():
        row = row_from_event(event)
        summary_path = final_dir / f'{eid}.json.gz'
        if summary_path.exists():
            row = apply_summary(row, read_json(summary_path))
        rows.append(row)
    rows.sort(key=lambda r: (r['tip_utc'], r['game_id']))
    return rows


def write(rows: list[dict], path: Path = MASTER_CSV) -> None:
    from io import StringIO
    out = StringIO()
    writer = csv.DictWriter(out, COLUMNS, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    atomic_bytes(path, out.getvalue().encode('utf-8'))


def load(path: Path = MASTER_CSV) -> list[dict]:
    with open(path, newline='', encoding='utf-8') as stream:
        return list(csv.DictReader(stream))


def main():
    rows = build()
    write(rows)
    finals = sum(r['status'] == 'final' for r in rows)
    print(f'master fixtures: {len(rows)} games · {finals} final · {len(rows) - finals} not final -> {MASTER_CSV}')


if __name__ == '__main__':
    main()
