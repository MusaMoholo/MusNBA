#!/usr/bin/env python3
"""Independently account exact marginal CDFs from retained branch minutes; no new forecasts."""
import argparse
import base64
import gzip
from pathlib import Path
import resource
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from basketball_common import packed, read_json, sha256_file, write_json
from scripts import a1_expected, lineup_minutes, projection
from scripts.world_mass import branch_masses


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--cdf-output', required=True, type=Path)
    parser.add_argument('--split', action='store_true')
    args = parser.parse_args()
    if args.output.exists() or args.cdf_output.exists():
        raise FileExistsError('fresh outputs required')
    source = read_json(args.report)
    branches = a1_expected.selected_branches(source, {})
    minutes, weights, ids = [], [], None
    for record, probability in branches:
        path = ROOT / record['capture']
        if sha256_file(path) != record['capture_sha256']:
            raise ValueError('changed retained branch')
        with np.load(path, allow_pickle=False) as z:
            current = z['player_ids'].tolist()
            if ids is not None and ids != current:
                raise ValueError('branch rosters differ')
            ids = current
            minutes.append(z['minutes'])
            weights.append(probability)
    masses = branch_masses([len(x) for x in minutes], weights)
    minutes = np.concatenate(minutes)
    started = time.monotonic()
    if args.split:
        result = lineup_minutes.encode_players(minutes, ids, masses, args.cdf_output, sha256_file(args.report))
        records = {pid: read_json(args.cdf_output / f'{pid}.json') for pid in ids}
    else:
        result = lineup_minutes.encode(minutes, ids, masses)
        records = {pid: result for pid in ids}
    elapsed = time.monotonic() - started
    checks = 0
    support_count = 0
    for i, pid in enumerate(ids):
        record = records[pid]
        def unpack(key):
            raw = np.frombuffer(base64.b64decode(record[key]), dtype=np.uint8)
            return (raw.reshape(8, -1).T.copy() if record.get('byte_shuffle') == 8 else raw).view('<f8').ravel()
        support, cdf, offsets = unpack('minutes_f64_le'), unpack('cumulative_f64_le'), record['offsets']
        if args.split:
            support_count += len(support)
        elif i == 0:
            support_count = len(support)
        for q, cols in enumerate(projection.SLICES.values()):
            values = minutes[:, i, cols].sum(1)
            index = q if args.split else i * 7 + q
            a, b = offsets[index:index + 2]
            x, c = support[a:b], cdf[a:b]
            for line in (0., .001, 5.5, 12., 29.999, 30., 30.001, 36., 48.):
                for side, condition in (('left', values < line), ('right', values <= line)):
                    k = np.searchsorted(x, line, side=side)
                    actual = int(c[k - 1]) if k else 0
                    if actual != int(masses[condition].sum()):
                        raise ValueError((pid, q, line, side, 'CDF threshold differs from original weighted worlds'))
                    checks += 1
    bodies = [packed(records[pid]).encode() for pid in ids] if args.split else [packed(result).encode()]
    if not args.split:
        write_json(args.cdf_output, result, pretty=False)
    write_json(args.output, {'kind': 'new marginal codec accounting/size only; retained unpromoted research worlds',
                            'source_report_sha256': sha256_file(args.report), 'source_sha256': sha256_file(Path(__file__)),
                            'encoder_sha256': sha256_file(Path(lineup_minutes.__file__)), 'worlds': len(minutes), 'players': len(ids),
                            'probability_mass': int(masses.sum()), 'unique_support_values': support_count, 'independent_threshold_checks': checks,
                            'encode_seconds': elapsed, 'json_bytes': sum(map(len,bodies)),
                            'gzip_bytes': sum(len(gzip.compress(body,mtime=0)) for body in bodies),
                            'largest_json_record': max(map(len,bodies)), 'records': len(bodies),
                            'process_peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == 'darwin' else 1024),
                            'cdf_output': str(args.cdf_output), 'cdf_sha256': {p.name: sha256_file(p) for p in sorted(args.cdf_output.glob('*.json'))} if args.split else sha256_file(args.cdf_output),
                            'status': 'pass; not engine qualification or device acceptance'}, pretty=True)
    print(checks, 'threshold identities;', sum(map(len,bodies)), 'JSON bytes;', sum(len(gzip.compress(body,mtime=0)) for body in bodies), 'gzip bytes;', max(map(len,bodies)), 'largest record', flush=True)


if __name__ == '__main__':
    main()
