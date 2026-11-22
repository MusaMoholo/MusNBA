#!/usr/bin/env python3
"""Verify atomic export publication preserves bytes and clears Finder's hidden flag on macOS."""
from pathlib import Path
import hashlib
import os
import stat
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.export_musnba import publish

with tempfile.TemporaryDirectory(prefix='musnba-visibility-') as folder:
    root = Path(folder)
    staging, output = root / 'MusNBA-export-check.partial', root / 'MusNBA.musnba.gz'
    body = b'MusNBA visibility regression\n'
    staging.write_bytes(body)
    output.write_bytes(b'previous export')
    if hasattr(os, 'chflags'):
        os.chflags(staging, staging.stat().st_flags | stat.UF_HIDDEN)
        os.chflags(output, output.stat().st_flags | stat.UF_HIDDEN)
        assert staging.stat().st_flags & stat.UF_HIDDEN
    publish(staging, output)
    assert output.read_bytes() == body and not staging.exists()
    assert not getattr(output.stat(), 'st_flags', 0) & getattr(stat, 'UF_HIDDEN', 0)
    print('PASS atomic publish: bytes preserved, staging consumed, Finder hidden flag clear')
    print('SHA256', hashlib.sha256(output.read_bytes()).hexdigest())
