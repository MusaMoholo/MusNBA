#!/usr/bin/env python3
"""Audit production minute-world decoding against an isolated research capture."""
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from analysis.a1_branch_browser_fixture import pack_capture  # noqa: E402
from basketball_common import read_json, sha256_file, write_json  # noqa: E402
from scripts import projection, views  # noqa: E402

NODE_PROBE = r"""
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
globalThis.location = {href: 'http://localhost/'};
const {worldData, mask, minuteMarginalData} = await import('./scripts/webapp/outcomes.mjs');
const raw = JSON.parse(readFileSync(process.argv[1]));
const phone = minuteMarginalData(JSON.parse(readFileSync(process.argv[2])));
const data = worldData(raw), periods = ['q1', 'q2', 'q3', 'q4', 'h1', 'h2', 'fg'];
const rows = [];
for (const [i, id] of raw.players.entries()) for (const period of periods) {
  const values = data.minuteValues(id, period), bytes = Buffer.alloc(values.length * 8);
  const phoneBytes = Buffer.alloc(values.length * 8);
  phone.minuteValues(id, period).forEach((value, w) => phoneBytes.writeDoubleLE(value, w * 8));
  const wins = data.values('t:' + (raw.side[i] === 0 ? 'home' : 'away'), 'win');
  const thresholds = [0, 10, 20, 30, 30.25, 40, 48].map(line => {
    let less = 0, equal = 0, more = 0, winMore = 0;
    for (let w = 0; w < values.length; w++) {
      bytes.writeDoubleLE(values[w], w * 8);
      less += values[w] < line; equal += values[w] === line; more += values[w] > line;
      winMore += wins[w] && values[w] > line;
    }
    return [less, equal, more, winMore];
  });
  const plays = period === 'fg' ? mask(data, [{subj: 'p:' + id, v: 'plays'}]).reduce((a, b) => a + b, 0) : null;
  rows.push({player: id, period, hash: createHash('sha256').update(bytes).digest('hex'),
    phoneHash: createHash('sha256').update(phoneBytes).digest('hex'), thresholds, plays});
}
console.log(JSON.stringify(rows));
"""


def audit(manifest: Path, branch_index: int, output: Path) -> None:
    if output.exists():
        raise FileExistsError('refusing to overwrite an experiment')
    start = time.monotonic()
    report_hash = sha256_file(manifest)
    branch = read_json(manifest)['branches'][branch_index]
    capture = ROOT / branch['capture']
    if sha256_file(capture) != branch['capture_sha256']:
        raise ValueError('capture hash differs from manifest')
    with np.load(capture, allow_pickle=False) as data, tempfile.TemporaryDirectory(prefix='musnba-minute-audit-') as tmp:
        packed = pack_capture(data)
        worlds, players, stats = packed['worlds'], len(packed['players']), len(packed['stats'])
        mins, teams = data['minutes'], data['team_points']
        lines = np.frombuffer(base64.b64decode(packed['lines']), dtype=np.uint8).reshape(worlds, players, stats)
        root = Path(tmp)
        np.savez_compressed(root / 'engine_players.npz', g__ids=np.array(packed['players']),
                            g__side=np.array(packed['side']), g__lines=lines,
                            g__minutes_schema=np.array(1, dtype=np.uint8), g__minutes=mins)
        np.savez_compressed(root / 'engine_worlds.npz', g=teams)
        raw = views.world_lines(root, 'g', worlds)
        if raw is None:
            raise ValueError('production view omitted minute worlds')
        fixture = root / 'worlds.json'
        write_json(fixture, raw)
        marginal = views.minute_marginals(root, 'g')
        if marginal is None:
            raise ValueError('phone minute marginals are missing')
        phone_fixture = root / 'marginals.json'
        write_json(phone_fixture, marginal)
        phone_bytes = phone_fixture.read_bytes()
        phone_gzip_bytes = len(gzip.compress(phone_bytes, compresslevel=6, mtime=0))
        proc = subprocess.run(['node', '--input-type=module', '-e', NODE_PROBE, str(fixture), str(phone_fixture)],
                              cwd=ROOT, check=True, text=True, capture_output=True)
        rows = json.loads(proc.stdout)
        expected = {(pid, period) for pid in packed['players'] for period in projection.PERIODS}
        if len(rows) != len(expected) or {(r['player'], r['period']) for r in rows} != expected:
            raise ValueError('missing or duplicate player-period rows')
        for row in rows:
            i = packed['players'].index(row['player'])
            values = np.ascontiguousarray(mins[:, i, projection.SLICES[row['period']]].sum(axis=1), dtype='<f8')
            if hashlib.sha256(values.tobytes()).hexdigest() != row['hash']:
                raise ValueError(f"{row['player']} {row['period']}: decoded values differ")
            if hashlib.sha256(np.sort(values).tobytes()).hexdigest() != row['phoneHash']:
                raise ValueError(f"{row['player']} {row['period']}: phone marginal values differ")
            side = packed['side'][i]
            win = teams[:, side, :].sum(axis=1) > teams[:, 1 - side, :].sum(axis=1)
            for line, actual in zip((0, 10, 20, 30, 30.25, 40, 48), row['thresholds'], strict=True):
                expected_counts = [int(np.count_nonzero(values < line)), int(np.count_nonzero(values == line)),
                                   int(np.count_nonzero(values > line)), int(np.count_nonzero(win & (values > line)))]
                if actual != expected_counts:
                    raise ValueError(f"{row['player']} {row['period']}: threshold {line} differs")
            if row['period'] == 'fg' and row['plays'] != np.count_nonzero(values > 0):
                raise ValueError(f"{row['player']}: participation differs")
    if sha256_file(capture) != branch['capture_sha256'] or sha256_file(manifest) != report_hash:
        raise ValueError('source changed during audit')
    write_json(output, {
        'kind': 'isolated production minute decoding audit; not a forecast or predictive test',
        'manifest': str(manifest), 'manifest_sha256': report_hash, 'branch_index': branch_index,
        'capture': str(capture.relative_to(ROOT)), 'capture_sha256': branch['capture_sha256'],
        'audit_sha256': sha256_file(Path(__file__)), 'decoder_sha256': sha256_file(ROOT / 'scripts/webapp/outcomes.mjs'),
        'worlds': worlds, 'players': players, 'distributions': len(rows), 'thresholds_per_distribution': 7,
        'conditional_win_thresholds': len(rows) * 7, 'values_bitwise_checked': worlds * len(rows),
        'phone_marginal_values_bitwise_checked': worlds * len(rows),
        'phone_minute_record_json_bytes': len(phone_bytes), 'phone_minute_record_gzip_bytes': phone_gzip_bytes,
        'size_limitation': 'Minute-only record, not a full bundle or a physical-phone performance measurement.',
        'seconds': round(time.monotonic() - start, 3),
    }, pretty=True)
    print(f'Audited {len(rows)} distributions and {worlds * len(rows):,} exact values in {time.monotonic() - start:.2f}s')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--branch', type=int, default=0)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    audit(args.manifest, args.branch, args.output)


if __name__ == '__main__':
    main()
