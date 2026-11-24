#!/usr/bin/env python3
"""Owner-run nightly followed by laptop and phone bundle exports, only on success.

Default destinations: iCloud Drive/MusNBA/MusNBA-laptop.musnba.gz and MusNBA.musnba.gz.
Other arguments pass to nightly.py.
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
sys.path.insert(0, str(ROOT))
from scripts.export_musnba import view_inventory  # noqa: E402

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


def laptop_output(phone_output: Path) -> Path:
    return phone_output.with_name(phone_output.name[:-len('.musnba.gz')] + '-laptop.musnba.gz')


def export_pair(output: Path) -> int:
    output = Path(output)
    laptop = laptop_output(output)
    before = view_inventory()
    retry = shlex.join([sys.executable, str(ROOT / 'scripts/nightly_musnba.py'), '--export-only', '--output', str(output)])
    for profile, destination in (('laptop', laptop), ('phone', output)):
        status = subprocess.run([sys.executable, str(ROOT / 'scripts/export_musnba.py'), '--output', str(destination),
                                 '--profile', profile], cwd=ROOT).returncode
        if status:
            print(f'{profile.capitalize()} export failed; the pair may differ. Retry both:\n' + retry, file=sys.stderr)
            return status
        if view_inventory() != before:
            print('Views changed while exporting; retry both:\n' + retry, file=sys.stderr)
            return 1
    return 0


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
    laptop = laptop_output(output)
    try:
        check_output_access(output)
        check_output_access(laptop)
    except OSError as error:
        print(f'Export destination is inaccessible: {error}\nNo data job was started. For iCloud, allow this terminal '
              'access in System Settings → Privacy & Security and make the file available locally in Finder.', file=sys.stderr)
        return 1
    if not args.export_only:
        env = {**os.environ, 'MUSNBA_EARLY_OUTPUT': str(output)}
        status = subprocess.run([sys.executable, str(ROOT / 'scripts/nightly.py'), *nightly_args], cwd=ROOT, env=env).returncode
        if status:
            print('Nightly did not succeed; a verified early export may be available. Check its generation and season freshness.', file=sys.stderr)
            return status
    return export_pair(output)


if __name__ == '__main__':
    raise SystemExit(main())
