#!/usr/bin/env python3
"""Audit research game context against a snapshot-pinned master and pre-origin records."""
import argparse
import csv
import hashlib
import io
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import parse_utc, sha256_file, write_json  # noqa: E402


def audit_provenance(meta: dict, meta_digest: str, view: dict, payload: dict) -> None:
    research = view['research']
    if (research['game'] != view['game']['id'] or research['origin'] != meta['origin']
            or payload['game'] != research['game'] or payload['origin'] != research['origin']
            or payload['fixture_sha256'] != research['fixture_sha256']
            or payload['snapshot_inputs'].get(f"data/snapshots/{meta['origin']}/meta.json") != meta_digest):
        raise ValueError('view, payload and snapshot provenance differ')


def audit_context(meta: dict, rows: list[dict], game: dict) -> dict:
    origin = meta['origin']
    if date.fromisoformat(origin).isoformat() != origin or meta['kind'] != 'prospective':
        raise ValueError('prospective origin required')
    cutoff = meta['cutoff']
    if date.fromisoformat(cutoff).isoformat() != cutoff or cutoff >= origin or game['id'] not in meta['games']:
        raise ValueError('game or cutoff does not match the snapshot')
    if any(date.fromisoformat(r['date_et']).isoformat() != r['date_et'] for r in rows):
        raise ValueError('master dates must be ISO formatted')
    matches = [r for r in rows if r['game_id'] == game['id']]
    if len(matches) != 1:
        raise ValueError('game is missing or duplicated in master')
    row = matches[0]
    if (row['date_et'] < origin or row['status'] != 'scheduled' or row['time_valid'] != '1'
            or meta.get('pre_tip', {}).get(game['id']) is not True
            or parse_utc(meta['completed_at']) >= parse_utc(row['tip_utc'])):
        raise ValueError('scheduled pre-tip origin context required')
    expected = {
        'id': row['game_id'], 'date': row['date_et'], 'tip_utc': row['tip_utc'],
        'time_valid': True, 'status': row['status'], 'detail': row['status_detail'],
        'tv': [x for x in row['tv'].split('|') if x], 'venue': row['venue'], 'city': row['city'],
        'neutral': bool(int(row['neutral'])), 'notes': [x for x in row['notes'].split('|') if x],
        'periods': None,
    }
    if row['periods']:
        raise ValueError('scheduled game has periods')
    for side in ('home', 'away'):
        team = row[f'{side}_id']
        wins = losses = 0
        for result in rows:
            if result['date_et'] >= origin or result['status'] != 'final':
                continue
            if team not in (result['home_id'], result['away_id']):
                continue
            if not result['home_pts'] or not result['away_pts']:
                raise ValueError('pre-origin final is missing a score')
            home = int(result['home_pts'])
            away = int(result['away_pts'])
            if home == away:
                raise ValueError('pre-origin final has a tied score')
            won = (home > away) == (result['home_id'] == team)
            wins += won
            losses += not won
        expected[side] = {'id': team, 'abbr': row[f'{side}_abbr'], 'score': None, 'record': [wins, losses]}
    if game != expected:
        raise ValueError('view context differs from snapshot master or pre-origin records')
    return {'game': game['id'], 'origin': origin, 'home_record': expected['home']['record'],
            'away_record': expected['away']['record']}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('meta', type=Path)
    parser.add_argument('master', type=Path)
    parser.add_argument('views', type=Path, nargs='+')
    parser.add_argument('--payloads', type=Path, nargs='+', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an existing report')
    meta_bytes = args.meta.read_bytes()
    meta = json.loads(meta_bytes)
    master_bytes = args.master.read_bytes()
    digest = lambda data: hashlib.sha256(data).hexdigest()
    if digest(master_bytes) != meta['inputs']['master_sha256']:
        raise ValueError('master does not match the snapshot fingerprint')
    if len(args.payloads) != len(args.views):
        raise ValueError('each view requires its corresponding payload')
    rows = list(csv.DictReader(io.StringIO(master_bytes.decode('utf-8'), newline='')))
    views = [(path, path.read_bytes()) for path in args.views]
    payloads = [(path, path.read_bytes()) for path in args.payloads]
    results = []
    for (_, view_bytes), (_, payload_bytes) in zip(views, payloads, strict=True):
        view, payload = json.loads(view_bytes), json.loads(payload_bytes)
        audit_provenance(meta, digest(meta_bytes), view, payload)
        results.append(audit_context(meta, rows, view['game']))
    source = {str(args.meta): digest(meta_bytes), str(args.master): digest(master_bytes)}
    source.update({str(path): digest(data) for path, data in views})
    source.update({str(path): digest(data) for path, data in payloads})
    source[str(Path(__file__).relative_to(ROOT))] = sha256_file(Path(__file__))
    write_json(args.output, {'kind': 'research game-context cutoff audit; not a predictive or promotion test',
                             'source_sha256': source,
                             'results': results,
                             'limitations': ['Applies only to these views and this snapshot-pinned master.',
                                             'The research adapter does not enforce this audit at runtime.']}, pretty=True)
    print(f'{len(results)} snapshot-pinned game contexts and pre-origin records reconciled')


if __name__ == '__main__':
    main()
