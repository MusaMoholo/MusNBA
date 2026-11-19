#!/usr/bin/env python3
"""Collect ESPN NBA responses into data/raw/espn. Nothing is deleted.

* runs/<UTC stamp>/      volatile responses as seen at collection time (teams, schedules,
                          rosters, injuries, scoreboard). Each run keeps its own copy.
* final/<game id>.json.gz summaries (box score + full play-by-play) of final games, written once.
* data/logos/             small team logos for offline display (light and dark variants).

ESPN's site API is public and unofficial. Requests are spaced, retried with backoff and use a
generic client name. Provider details stay behind this module so another source can replace it.
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import (LOGOS, RAW, SEASON, SEASON_TYPE, atomic_bytes, read_json,  # noqa: E402
                               today_et, write_json)

SITE = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba'
LOGO_URL = 'https://a.espncdn.com/i/teamlogos/nba/{variant}/{abbr}.png'
LOGO_SMALL = 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/{variant}/{abbr}.png&w=96&h=96'
USER_AGENT = 'MusNBA/0.1 (personal research client)'


class Client:
    def __init__(self, delay: float = 0.35, retries: int = 3, timeout: float = 30):
        self.delay, self.retries, self.timeout = delay, retries, timeout
        self.last = 0.0
        self.count = 0

    def get(self, url: str) -> bytes:
        for attempt in range(self.retries + 1):
            wait = self.delay - (time.monotonic() - self.last)
            if wait > 0:
                time.sleep(wait)
            self.last = time.monotonic()
            request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT,
                                                           'Accept-Encoding': 'gzip'})
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    body = response.read()
                    if response.headers.get('Content-Encoding') == 'gzip':
                        body = gzip.decompress(body)
                    self.count += 1
                    return body
            except urllib.error.HTTPError as error:
                if error.code not in (429, 500, 502, 503, 504) or attempt == self.retries:
                    raise
            except (urllib.error.URLError, TimeoutError):
                if attempt == self.retries:
                    raise
            time.sleep(1.5 * (attempt + 1))
        raise RuntimeError('unreachable')

    def json(self, url: str):
        return json.loads(self.get(url))


def save(path: Path, value) -> None:
    write_json(path, value)


def is_final(competition: dict) -> bool:
    status = (competition.get('status') or {}).get('type') or {}
    return bool(status.get('completed')) and status.get('name') == 'STATUS_FINAL'


def collect(day: str | None = None, finals: bool = True, logos: bool = True,
            max_finals: int | None = None, client: Client | None = None) -> dict:
    day = day or today_et()
    client = client or Client()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    run = RAW / 'runs' / stamp
    report = {'run': stamp, 'slate_date': day, 'started': stamp, 'failures': [], 'finals_added': 0}

    teams_doc = client.json(f'{SITE}/teams')
    save(run / 'teams.json.gz', teams_doc)
    teams = [t['team'] for t in teams_doc['sports'][0]['leagues'][0]['teams']]
    report['teams'] = len(teams)
    print(f'teams: {len(teams)}', flush=True)

    events = {}
    for i, team in enumerate(teams, 1):
        tid = team['id']
        try:
            schedule = client.json(f'{SITE}/teams/{tid}/schedule?season={SEASON}&seasontype={SEASON_TYPE}')
            save(run / 'schedule' / f'{tid}.json.gz', schedule)
            for event in schedule.get('events', []):
                events[event['id']] = event
        except Exception as error:  # keep collecting; report the gap
            report['failures'].append({'what': f'schedule {team["abbreviation"]}', 'error': repr(error)})
        try:
            save(run / 'roster' / f'{tid}.json.gz', client.json(f'{SITE}/teams/{tid}/roster'))
        except Exception as error:
            report['failures'].append({'what': f'roster {team["abbreviation"]}', 'error': repr(error)})
        print(f'schedule+roster {i}/{len(teams)} {team["abbreviation"]}', flush=True)
    report['scheduled_events'] = len(events)

    try:
        save(run / 'injuries.json.gz', client.json(f'{SITE}/injuries'))
    except Exception as error:
        report['failures'].append({'what': 'injuries', 'error': repr(error)})
    try:
        save(run / f'scoreboard_{day}.json.gz', client.json(f'{SITE}/scoreboard?dates={day.replace("-", "")}'))
    except Exception as error:
        report['failures'].append({'what': 'scoreboard', 'error': repr(error)})

    if finals:
        final_dir = RAW / 'final'
        wanted = sorted(eid for eid, e in events.items()
                        if is_final(e['competitions'][0]) and not (final_dir / f'{eid}.json.gz').exists())
        if max_finals is not None:
            wanted = wanted[:max_finals]
        print(f'final summaries to collect: {len(wanted)}', flush=True)
        for i, eid in enumerate(wanted, 1):
            try:
                summary = client.json(f'{SITE}/summary?event={eid}')
                competition = summary['header']['competitions'][0]
                players = summary.get('boxscore', {}).get('players', [])
                if not is_final(competition) or len(players) != 2:
                    report['failures'].append({'what': f'summary {eid}', 'error': 'not final or no box score yet'})
                    continue
                save(final_dir / f'{eid}.json.gz', summary)
                report['finals_added'] += 1
            except Exception as error:
                report['failures'].append({'what': f'summary {eid}', 'error': repr(error)})
            if i % 20 == 0 or i == len(wanted):
                print(f'summaries {i}/{len(wanted)}', flush=True)

    if logos:
        for team in teams:
            for variant, suffix in (('500', ''), ('500-dark', '-dark')):
                target = LOGOS / f'{team["id"]}{suffix}.png'
                if target.exists():
                    continue
                abbr = team['abbreviation'].lower()
                for template in (LOGO_SMALL, LOGO_URL):
                    try:
                        data = client.get(template.format(variant=variant, abbr=abbr))
                        if data[:8] == b'\x89PNG\r\n\x1a\n':
                            atomic_bytes(target, data)
                            break
                    except Exception as error:
                        report['failures'].append({'what': f'logo {abbr}{suffix}', 'error': repr(error)})

    report['requests'] = client.count
    report['finished'] = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    save(run / 'report.json', report)
    (RAW / 'runs' / 'LATEST').write_text(stamp + '\n')
    print(f'collected run {stamp}: {client.count} requests, {report["finals_added"]} new finals, '
          f'{len(report["failures"])} failures', flush=True)
    return report


def latest_run() -> Path:
    marker = RAW / 'runs' / 'LATEST'
    if not marker.exists():
        raise SystemExit('No ESPN collection yet. Run scripts/fetch_espn.py first.')
    return RAW / 'runs' / marker.read_text().strip()


def runs_through(day_utc_stamp: str | None = None) -> list[Path]:
    runs = sorted(p for p in (RAW / 'runs').iterdir() if p.is_dir()) if (RAW / 'runs').exists() else []
    if day_utc_stamp:
        runs = [p for p in runs if p.name <= day_utc_stamp]
    return runs


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--date', help='Slate date (ET) for the scoreboard; default today ET')
    parser.add_argument('--no-finals', action='store_true')
    parser.add_argument('--no-logos', action='store_true')
    parser.add_argument('--max-finals', type=int)
    parser.add_argument('--delay', type=float, default=0.35)
    args = parser.parse_args()
    report = collect(args.date, not args.no_finals, not args.no_logos, args.max_finals, Client(args.delay))
    for failure in report['failures'][:20]:
        print('  failure:', failure['what'], failure['error'][:160], file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
