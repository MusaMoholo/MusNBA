#!/usr/bin/env python3
"""Audit persisted research branches and their recorded per-branch runtimes."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from analysis.a1_branch_persist_audit import audit  # noqa: E402
from basketball_common import read_json, sha256_file, write_json  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, action='append', required=True)
    parser.add_argument('--log', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('refusing to overwrite an experiment')
    if len(args.manifest) != len(args.log) or len(set(args.manifest)) != len(args.manifest):
        raise ValueError('each distinct manifest must have exactly one corresponding log')
    results = []
    for manifest, log in zip(args.manifest, args.log, strict=True):
        manifest_hash, log_hash = sha256_file(manifest), sha256_file(log)
        report = read_json(manifest)
        accounting = audit(report)
        if report['kind'] != 'research conditional branches; not a forecast or promotion':
            raise ValueError('expected isolated research branches')
        lines = re.findall(r'^branch (\d+)/(\d+): (\d+) worlds, ([\d.]+)s$', log.read_text(), re.MULTILINE)
        if len(lines) != len(report['branches']):
            raise ValueError('log and manifest branch counts differ')
        times = []
        for index, (number, total, worlds, seconds) in enumerate(lines, 1):
            elapsed = float(seconds)
            if (int(number) != index or int(total) != len(lines)
                    or int(worlds) != report['worlds_per_branch'] or elapsed <= 0):
                raise ValueError('log order, world count or elapsed time differs from manifest')
            times.append(elapsed)
        if sha256_file(manifest) != manifest_hash or sha256_file(log) != log_hash:
            raise ValueError('manifest or log changed during the audit')
        results.append({
            'game': report['game'], 'origin': report['origin'],
            'manifest': str(manifest), 'manifest_sha256': manifest_hash,
            'log': str(log), 'log_sha256': log_hash,
            'accounting': accounting, 'branch_seconds': times,
            'branch_seconds_sum': round(sum(times), 1),
        })
    if len({item['game'] for item in results}) != len(results):
        raise ValueError('duplicate games')
    write_json(args.output, {
        'kind': 'isolated observed branch runtime and saved-box accounting; not a forecast',
        'audit_sha256': sha256_file(Path(__file__)),
        'accounting_sha256': sha256_file(ROOT / 'analysis/a1_branch_persist_audit.py'),
        'games': results,
        'limitations': [
            'Per-branch timings exclude startup and do not measure a complete slate or nightly.',
            'Concurrency and thread allocation are not established by the individual log lines.',
            'Some captures began after tip; none is a verified published pre-tip forecast.',
            'Weights are uncalibrated assumptions; no predictive performance or retry rate is measured.',
        ],
    }, pretty=True)
    print(f"Audited {len(results)} games and {sum(item['accounting']['worlds'] for item in results):,} worlds")


if __name__ == '__main__':
    main()
