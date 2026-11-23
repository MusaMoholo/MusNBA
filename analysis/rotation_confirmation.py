#!/usr/bin/env python3
"""D56 offset-fit compatibility; reuse the audited paired runner and corrected controls."""
import argparse
import os
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from basketball_common import read_json, sha256_file, write_json
from analysis import rule3_confirmation as paired
from scripts import engine, rotation_fit

PANELS = ROOT / 'analysis/experiments/20261123_independent_rotation_panels_v2.json'
PHASE = os.environ.get('MUSNBA_ROTATION_PHASE', 'development')
ORIGINAL_GAME, ORIGINAL_FINGERPRINTS, ORIGINAL_READ = paired.paired_game, paired.fingerprints, paired.read_json
BASE = {'development':'rule3_confirmation_20261123_v1','pilot':'rule3_pilot_20261123_v1',
        'stream':'rule3_stream_20261123_v1','stress':'rule3_stress_20261123_v1'}


def game(task):
    gid, directory = task
    result = {'game':gid, 'outputs':{}, 'control_corrected':True, 'recipe':'independent D29 offset fit; contextual clock off'}
    if PHASE in BASE:
        source = ROOT / 'data/derived/experiments' / BASE[PHASE] / f'{gid}.json'
        control = read_json(source)['outputs']['candidate']
        if sha256_file(ROOT / control['capture']) != control['sha256']:
            raise ValueError('changed reused corrected control')
        result['outputs']['control'] = control
        result['reused_control'] = {'meta':str(source.relative_to(ROOT)), 'sha256':sha256_file(source)}
    legacy = engine.Game._fit_offsets
    for label in ('control', 'candidate'):
        if label in result['outputs']:
            continue
        fit = legacy if label == 'control' else lambda curves, targets: rotation_fit.independent(curves, targets, engine.ROTATION)
        with patch.object(engine.Game, '_fit_offsets', staticmethod(fit)):
            row = ORIGINAL_GAME(task, labels=(label,), corrected=(True,True), persist=False)
        result['outputs'].update(row['outputs'])
        result.update({key:row[key] for key in ('worker_pid','worker_peak_rss_bytes')})
    write_json(Path(directory) / f'{gid}.json',result,pretty=False)
    return result


def fingerprints():
    paths = [Path(__file__), PANELS, ROOT/'scripts/rotation_fit.py', ROOT/'scripts/forecast_output.py',
             ROOT/'scripts/world_mass.py', ROOT/'docs/protocols/world_independence_20261123.md', ROOT/'docs/protocols/world_independence_amendment_20261123.md']
    return {**ORIGINAL_FINGERPRINTS(), **{str(p.relative_to(ROOT)):sha256_file(p) for p in paths}}


def declaration(path):
    result = ORIGINAL_READ(path)
    if Path(path) == PANELS:
        return {**result,'game_ids':result['confirmation' if PHASE=='confirmation' else 'development'],
                'pilot_games':result['pilot'],'stress_10000_games':result['stress'],'independent_stream_games':result['stream']}
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--phase',choices=('development','confirmation','pilot','stream','stress'),default='development')
    args, remaining = parser.parse_known_args()
    PHASE = args.phase
    os.environ['MUSNBA_ROTATION_PHASE'] = PHASE
    mode = {'pilot':'--pilot','stream':'--stream-check','stress':'--stress'}.get(PHASE)
    sys.argv = [sys.argv[0],*remaining,*([mode] if mode else [])]
    paired.PLAN, paired.paired_game, paired.fingerprints, paired.read_json = PANELS, game, fingerprints, declaration
    paired.main()
