#!/usr/bin/env python3
"""Collect NBA Stats API responses into data/raw/nbastats (ENGINE_PLAN D32). Nothing is deleted.

stats.nba.com is unofficial and answers only requests that look like a browser on nba.com: without the Chrome fetch
headers (`Sec-Fetch-*`, `sec-ch-ua`) it accepts the TLS connection and never sends a byte (measured 20 Nov 2026,
FINDINGS §1). The owner authorised this source (D32); requests are spaced (≈1 per second with jitter), retried with
backoff, and the run stops after repeated failures rather than pressing on.

Raw retention: data/raw/nbastats/<endpoint>/<season>/<key>.json.gz, one manifest.json per folder (url, bytes, sha256,
fetched UTC). Per-game files of finished games are written once (resumable: present files are skipped); season logs of
the current season carry the collection date in their key (each night's copy is kept).

  .venv/bin/python scripts/fetch_nbastats.py --probe                         one request, report status
  .venv/bin/python scripts/fetch_nbastats.py --logs [--seasons 2022-23 …]     season game logs (players, teams)
  .venv/bin/python scripts/fetch_nbastats.py --matchups                       boxscorematchupsv3 for every logged game
  .venv/bin/python scripts/fetch_nbastats.py --ptdefend                       tracking defence per game date (closest defender)
  .venv/bin/python scripts/fetch_nbastats.py --pbp                            playbyplayv3 for every logged game
  .venv/bin/python scripts/fetch_nbastats.py --hustle                         hustle stats per game date (one request per date)
  .venv/bin/python scripts/fetch_nbastats.py --recent                         nightly: current season logs + missing per-game files
"""
from __future__ import annotations

import argparse
import gzip
import json
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import DATA, atomic_bytes, sha256_bytes, today_et, write_json  # noqa: E402

NBA_RAW = DATA / 'raw' / 'nbastats'
BASE = 'https://stats.nba.com/stats/'
SEASONS = ['2022-23', '2023-24', '2024-25', '2025-26', '2026-27']
CURRENT = '2026-27'
SEASON_TYPES = ['Regular Season', 'Playoffs', 'PlayIn', 'IST']
TYPE_KEY = {'Regular Season': 'regular', 'Playoffs': 'playoffs', 'PlayIn': 'playin', 'IST': 'cup'}
PTDEFEND_CATEGORIES = ['Overall', 'Less Than 6Ft', '3 Pointers']
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*', 'Accept-Language': 'en-US,en;q=0.9', 'Accept-Encoding': 'gzip',
    'Origin': 'https://www.nba.com', 'Referer': 'https://www.nba.com/', 'Connection': 'keep-alive',
    'Sec-Fetch-Site': 'same-site', 'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Dest': 'empty',
    'sec-ch-ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"', 'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
}


class Blocked(RuntimeError):
    """Raised after repeated failures: the source is not answering; stop and report (no hammering)."""


class Client:
    def __init__(self, delay: float = 1.0, jitter: float = 0.5, retries: int = 3, timeout: float = 30, max_fail: int = 5):
        self.delay, self.jitter, self.retries, self.timeout, self.max_fail = delay, jitter, retries, timeout, max_fail
        self.last, self.count, self.failed_in_row, self.seconds = 0.0, 0, 0, 0.0

    def get(self, url: str) -> bytes:
        for attempt in range(self.retries + 1):
            wait = self.delay + random.uniform(0, self.jitter) - (time.monotonic() - self.last)
            if wait > 0:
                time.sleep(wait)
            self.last = time.monotonic()
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=self.timeout) as r:
                    body = r.read()
                    if r.headers.get('Content-Encoding') == 'gzip':
                        body = gzip.decompress(body)
                self.count += 1
                self.failed_in_row = 0
                self.seconds += time.monotonic() - self.last
                return body
            except urllib.error.HTTPError as error:
                if error.code not in (429, 500, 502, 503, 504) or attempt == self.retries:
                    self._fail()
                    raise
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                if attempt == self.retries:
                    self._fail()
                    raise
            time.sleep(5 * 3 ** attempt)  # 5, 15, 45 s
        raise RuntimeError('unreachable')

    def _fail(self):
        self.failed_in_row += 1
        if self.failed_in_row >= self.max_fail:
            raise Blocked(f'{self.failed_in_row} requests in a row failed — stopping (stats.nba.com not answering)')


def url_for(endpoint: str, **params) -> str:
    return BASE + endpoint + '?' + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)


class Store:
    """One folder per endpoint and season with a manifest; files are gzip of the response bytes as received."""

    def __init__(self, endpoint: str, season: str):
        self.dir = NBA_RAW / endpoint / season
        self.manifest_path = self.dir / 'manifest.json'
        self.manifest = json.loads(self.manifest_path.read_text()) if self.manifest_path.exists() else {}
        self.dirty = 0
        if self.dir.exists():  # files written after the last flush of an interrupted run: record them (sha256 of the body)
            for f in self.dir.glob('*.json.gz'):
                key = f.name[:-len('.json.gz')]
                if key not in self.manifest:
                    body = gzip.decompress(f.read_bytes())
                    self.manifest[key] = {'url': None, 'bytes': len(body), 'sha256': sha256_bytes(body), 'fetched_utc': None,
                                          'note': 'recorded on resume (interrupted run)'}
                    self.dirty += 1
            self.flush()

    def path(self, key: str) -> Path:
        return self.dir / f'{key}.json.gz'

    def has(self, key: str) -> bool:
        return self.path(key).exists()

    def put(self, key: str, url: str, body: bytes) -> None:
        atomic_bytes(self.path(key), gzip.compress(body, 6))
        self.manifest[key] = {'url': url, 'bytes': len(body), 'sha256': sha256_bytes(body),
                              'fetched_utc': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}
        self.dirty += 1
        if self.dirty >= 25:
            self.flush()

    def flush(self) -> None:
        if self.dirty:
            write_json(self.manifest_path, self.manifest, pretty=True)
            self.dirty = 0


def read(endpoint: str, season: str, key: str):
    path = NBA_RAW / endpoint / season / f'{key}.json.gz'
    return json.loads(gzip.decompress(path.read_bytes())) if path.exists() else None


# ---------------------------------------------------------------- season logs

LOG_SPECS = {  # name → (endpoint, params); one request per season and season type
    'players_base': ('playergamelogs', {'MeasureType': 'Base'}),
    'players_adv': ('playergamelogs', {'MeasureType': 'Advanced'}),
    'teams_adv': ('teamgamelogs', {'MeasureType': 'Advanced'}),
}


def log_url(endpoint: str, season: str, season_type: str, extra: dict) -> str:
    p = {'DateFrom': '', 'DateTo': '', 'GameSegment': '', 'LastNGames': 0, 'LeagueID': '00', 'Location': '',
         'Month': 0, 'OppTeamID': 0, 'Outcome': '', 'PORound': 0, 'PaceAdjust': 'N', 'PerMode': 'Totals', 'Period': 0,
         'PlusMinus': 'N', 'Rank': 'N', 'Season': season, 'SeasonSegment': '', 'SeasonType': season_type,
         'ShotClockRange': '', 'VsConference': '', 'VsDivision': ''}
    p.update(extra)
    return url_for(endpoint, **p)


def log_key(name: str, season_type: str, season: str) -> str:
    key = f'{TYPE_KEY[season_type]}_{name}'
    return f'{key}_{today_et()}' if season == CURRENT else key


def fetch_logs(client: Client, seasons: list[str], force_current: bool = True) -> dict:
    out = {'requests': 0, 'skipped': 0, 'empty': []}
    for season in seasons:
        store = Store('gamelogs', season)
        try:
            for st in SEASON_TYPES:
                if season == CURRENT and st != 'Regular Season':
                    continue
                for name, (endpoint, extra) in LOG_SPECS.items():
                    key = log_key(name, st, season)
                    if store.has(key):
                        out['skipped'] += 1
                        continue
                    url = log_url(endpoint, season, st, extra)
                    body = client.get(url)
                    store.put(key, url, body)
                    out['requests'] += 1
                    rows = json.loads(body)['resultSets'][0]['rowSet']
                    if not rows:
                        out['empty'].append(f'{season} {st} {name}')
        finally:
            store.flush()
    return out


def latest_log(season: str, season_type: str, name: str):
    """The newest retained copy of a season log (the current season keeps one per night)."""
    folder = NBA_RAW / 'gamelogs' / season
    base = f'{TYPE_KEY[season_type]}_{name}'
    cands = sorted(folder.glob(f'{base}*.json.gz'))
    cands = [c for c in cands if c.name == f'{base}.json.gz' or c.name[len(base) + 1:len(base) + 11].count('-') == 2]
    if not cands:
        return None
    js = json.loads(gzip.decompress(cands[-1].read_bytes()))
    rs = js['resultSets'][0]
    return rs['headers'], rs['rowSet']


def logged_games(seasons: list[str]) -> list[tuple[str, str, str, str]]:
    """(season, season type, NBA game id, game date) for every game in the retained team logs."""
    games = {}
    for season in seasons:
        for st in SEASON_TYPES:
            got = latest_log(season, st, 'teams_adv')
            if not got:
                continue
            h, rows = got
            gi, di = h.index('GAME_ID'), h.index('GAME_DATE')
            for r in rows:
                games[r[gi]] = (season, st, r[gi], str(r[di])[:10])
    return sorted(games.values(), key=lambda g: (g[3], g[2]))


# ---------------------------------------------------------------- per-game and per-date endpoints

def fetch_games(client: Client, endpoint: str, seasons: list[str], max_requests: int | None = None,
                newest_first: bool = True) -> dict:
    games = logged_games(seasons)
    if newest_first:  # the backtest's season first, then older seasons, then the live one
        order = {s: i for i, s in enumerate(['2025-26', '2024-25', '2023-24', '2022-23', CURRENT])}
        games = sorted(games, key=lambda g: (order.get(g[0], 9), g[3], g[2]))
    out = {'requests': 0, 'skipped': 0, 'empty': 0, 'games': len(games)}
    stores: dict[str, Store] = {}
    today = today_et()
    t0 = time.monotonic()
    try:
        for season, st, gid, day in games:
            if day >= today:  # only finished slates (the logs list only played games; belt and braces)
                continue
            if season not in stores:
                stores[season] = Store(endpoint, season)
            store = stores[season]
            if store.has(gid):
                out['skipped'] += 1
                continue
            url = url_for(endpoint, GameID=gid) if endpoint == 'boxscorematchupsv3' else \
                url_for(endpoint, GameID=gid, StartPeriod=0, EndPeriod=0)
            body = client.get(url)
            store.put(gid, url, body)
            out['requests'] += 1
            if len(body) < 2000:
                out['empty'] += 1
            if out['requests'] % 100 == 0:
                rate = out['requests'] / max(time.monotonic() - t0, 1)
                left = len(games) - out['requests'] - out['skipped']
                print(f'  {endpoint}: {out["requests"]} fetched, {out["skipped"]} cached, {left} left '
                      f'(~{left / max(rate, 1e-6) / 60:.0f} min)', flush=True)
            if max_requests and out['requests'] >= max_requests:
                break
    finally:
        for s in stores.values():
            s.flush()
    return out


def fetch_ptdefend(client: Client, seasons: list[str], categories: list[str], max_requests: int | None = None) -> dict:
    """Closest-defender shooting allowed (D_FGM, D_FGA v the shooters' normal FG%) per defender and game date —
    one date = at most one game per team, so each row is a defender-game (cutoff-safe by construction)."""
    games = logged_games(seasons)
    dates = sorted({(g[0], g[1], g[3]) for g in games})
    out = {'requests': 0, 'skipped': 0, 'dates': len(dates)}
    stores: dict[str, Store] = {}
    today = today_et()
    try:
        for cat in categories:
            ck = cat.lower().replace(' ', '')
            for season, st, day in dates:
                if day >= today:
                    continue
                if season not in stores:
                    stores[season] = Store('leaguedashptdefend', season)
                store = stores[season]
                key = f'{ck}_{day}'
                if store.has(key):
                    out['skipped'] += 1
                    continue
                us = datetime.strptime(day, '%Y-%m-%d').strftime('%m/%d/%Y')
                url = url_for('leaguedashptdefend', College='', Conference='', Country='', DateFrom=us, DateTo=us,
                              DefenseCategory=cat, Division='', DraftPick='', DraftYear='', GameSegment='', Height='',
                              LastNGames=0, LeagueID='00', Location='', Month=0, OpponentTeamID=0, Outcome='', PORound=0,
                              PerMode='Totals', Period=0, PlayerExperience='', PlayerPosition='', Season=season,
                              SeasonSegment='', SeasonType=st, StarterBench='', TeamID=0, VsConference='', VsDivision='',
                              Weight='')
                body = client.get(url)
                store.put(key, url, body)
                out['requests'] += 1
                if out['requests'] % 100 == 0:
                    print(f'  ptdefend: {out["requests"]} fetched, {out["skipped"]} cached', flush=True)
                if max_requests and out['requests'] >= max_requests:
                    return out
    finally:
        for s in stores.values():
            s.flush()
    return out


def fetch_hustle(client: Client, seasons: list[str], max_requests: int | None = None) -> dict:
    """Hustle stats (contested shots, deflections, charges, loose balls, box-outs, screen assists) per player and game
    date — one request per date instead of one per game (owner: hustle only if cheap)."""
    games = logged_games(seasons)
    dates = sorted({(g[0], g[1], g[3]) for g in games})
    out = {'requests': 0, 'skipped': 0, 'dates': len(dates)}
    stores: dict[str, Store] = {}
    today = today_et()
    try:
        for season, st, day in dates:
            if day >= today:
                continue
            if season not in stores:
                stores[season] = Store('leaguehustlestatsplayer', season)
            store = stores[season]
            if store.has(day):
                out['skipped'] += 1
                continue
            us = datetime.strptime(day, '%Y-%m-%d').strftime('%m/%d/%Y')
            url = url_for('leaguehustlestatsplayer', College='', Conference='', Country='', DateFrom=us, DateTo=us, Division='',
                          DraftPick='', DraftYear='', Height='', LeagueID='00', Location='', Month=0, OpponentTeamID=0,
                          Outcome='', PORound=0, PerMode='Totals', PlayerExperience='', PlayerPosition='', Season=season,
                          SeasonSegment='', SeasonType=st, TeamID=0, VsConference='', VsDivision='', Weight='')
            body = client.get(url)
            store.put(day, url, body)
            out['requests'] += 1
            if max_requests and out['requests'] >= max_requests:
                break
    finally:
        for s_ in stores.values():
            s_.flush()
    return out


def probe(client: Client) -> dict:
    url = url_for('boxscorematchupsv3', GameID='0022500001')
    t = time.monotonic()
    body = client.get(url)
    js = json.loads(body)
    return {'ok': True, 'bytes': len(body), 'seconds': round(time.monotonic() - t, 2),
            'home': js['boxScoreMatchups']['homeTeam']['teamTricode'], 'away': js['boxScoreMatchups']['awayTeam']['teamTricode']}


def recent(client: Client) -> dict:
    """Nightly: today's copy of the current season's logs, then the per-game files of any final not yet retained."""
    out = {'logs': fetch_logs(client, [CURRENT])}
    out['matchups'] = fetch_games(client, 'boxscorematchupsv3', [CURRENT])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--probe', action='store_true')
    ap.add_argument('--logs', action='store_true')
    ap.add_argument('--matchups', action='store_true')
    ap.add_argument('--ptdefend', action='store_true')
    ap.add_argument('--categories', nargs='+', default=PTDEFEND_CATEGORIES)
    ap.add_argument('--pbp', action='store_true')
    ap.add_argument('--hustle', action='store_true', help='hustle stats per game date (cheap: one request per date)')
    ap.add_argument('--recent', action='store_true')
    ap.add_argument('--seasons', nargs='+', default=SEASONS)
    ap.add_argument('--max', type=int, default=None, help='stop after this many requests per endpoint')
    ap.add_argument('--delay', type=float, default=1.0)
    args = ap.parse_args()
    client = Client(delay=args.delay)
    report = {}
    try:
        if args.probe:
            report['probe'] = probe(client)
        if args.logs:
            report['logs'] = fetch_logs(client, args.seasons)
            print('logs', report['logs'], flush=True)
        if args.matchups:
            report['matchups'] = fetch_games(client, 'boxscorematchupsv3', args.seasons, args.max)
            print('matchups', report['matchups'], flush=True)
        if args.ptdefend:
            report['ptdefend'] = fetch_ptdefend(client, args.seasons, args.categories, args.max)
            print('ptdefend', report['ptdefend'], flush=True)
        if args.pbp:
            report['pbp'] = fetch_games(client, 'playbyplayv3', args.seasons, args.max)
            print('pbp', report['pbp'], flush=True)
        if args.hustle:
            report['hustle'] = fetch_hustle(client, args.seasons, args.max)
            print('hustle', report['hustle'], flush=True)
        if args.recent:
            report['recent'] = recent(client)
    except Blocked as e:
        report['blocked'] = str(e)
        print('BLOCKED:', e, flush=True)
        report['requests'] = client.count
        print(json.dumps(report, indent=1))
        sys.exit(2)
    report['requests'] = client.count
    report['mean_response_s'] = round(client.seconds / max(client.count, 1), 3)
    print(json.dumps(report, indent=1))


if __name__ == '__main__':
    main()
