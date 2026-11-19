#!/usr/bin/env python3
"""Owner-run nightly followed by the MusNBA bundle export, only on success.

Default destination: iCloud Drive/MusNBA/MusNBA.musnba.gz. Other arguments pass to nightly.py.
This wrapper installs no scheduler and never touches a running server.

  .venv/bin/python scripts/nightly_musnba.py
  .venv/bin/python scripts/nightly_musnba.py --export-only      retry the export, no collection/sims
"""
import argparse
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ICLOUD_DRIVE = Path.home() / 'Library/Mobile Documents/com~apple~CloudDocs'
DEFAULT_OUTPUT = ICLOUD_DRIVE / 'MusNBA/MusNBA.musnba.gz'


def check_output_access(output: Path) -> None:
    """Fail before collection if the previous export cannot be read or replaced."""
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        with output.open('rb') as previous:
            previous.read(1)
    with tempfile.TemporaryDirectory(prefix='.musnba-access-', dir=output.parent) as tmp:
        probe = Path(tmp) / 'probe'
        probe.write_bytes(b'MusNBA access check')
        os.replace(probe, Path(tmp) / 'renamed')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--export-only', action='store_true')
    args, nightly_args = parser.parse_known_args()
    if args.export_only and nightly_args:
        parser.error('--export-only cannot be combined with nightly options')
    output = args.output.expanduser().absolute()
    if not output.name.endswith('.musnba.gz'):
        parser.error('Choose a .musnba.gz destination.')
    if output == DEFAULT_OUTPUT and not ICLOUD_DRIVE.is_dir():
        parser.error('Enable iCloud Drive on this Mac, or pass --output.')
    try:
        check_output_access(output)
    except OSError as error:
        print(f'Export destination is inaccessible: {error}\nNo data job was started. For iCloud, allow this terminal '
              'access in System Settings → Privacy & Security and make the file available locally in Finder.', file=sys.stderr)
        return 1
    if not args.export_only:
        status = subprocess.run([sys.executable, str(ROOT / 'scripts/nightly.py'), *nightly_args], cwd=ROOT).returncode
        if status:
            print('Nightly did not succeed; the previous export is unchanged.', file=sys.stderr)
            return status
    status = subprocess.run([sys.executable, str(ROOT / 'scripts/export_musnba.py'), '--output', str(output)], cwd=ROOT).returncode
    if status:
        retry = shlex.join([sys.executable, str(ROOT / 'scripts/nightly_musnba.py'), '--export-only', '--output', str(output)])
        print('Export failed; snapshots remain on this Mac. Retry with:\n' + retry, file=sys.stderr)
    return status


if __name__ == '__main__':
    raise SystemExit(main())
