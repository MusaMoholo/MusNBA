#!/usr/bin/env python3
"""Independently account for an isolated fold's saved node datasets."""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from basketball_common import sha256_file, write_json  # noqa: E402
from scripts import evaluate, nodes, train  # noqa: E402


def matrix_shape(path: Path) -> tuple[int, ...]:
    with zipfile.ZipFile(path) as archive, archive.open('X.npy') as matrix:
        version = np.lib.format.read_magic(matrix)
        if version == (1, 0):
            shape, _, _ = np.lib.format.read_array_header_1_0(matrix)
        elif version == (2, 0):
            shape, _, _ = np.lib.format.read_array_header_2_0(matrix)
        else:
            raise ValueError(f'unsupported matrix header {version} in {path}')
    return shape


def audit(features: Path, fold: str) -> dict:
    cutoff, validation_from, validation_to = evaluate.FOLDS[fold]
    folder = nodes.cache_dir(features)
    if json.loads((folder / 'signature.json').read_text()) != nodes.signature(features):
        raise ValueError('node-cache signature no longer matches the source inputs')
    expected = set(train.NODES)
    actual = {p.stem for p in folder.glob('*.npz')}
    if actual != expected:
        raise ValueError(f'node cache coverage differs: missing={expected - actual}, extra={actual - expected}')
    output = {}
    for i, name in enumerate(train.NODES, start=1):
        path = folder / f'{name}.npz'
        shape = matrix_shape(path)
        with np.load(path, allow_pickle=False) as data:
            y, date, game = data['y'], data['date'].astype('datetime64[D]'), data['game']
            columns = data['columns']
            kind, classes = str(data['kind']), int(data['classes'])
            if len(shape) != 2 or shape != (len(y), len(columns)) or len(date) != len(y) or len(game) != len(y):
                raise ValueError(f'{name}: matrix, label, date or game dimensions disagree')
            if np.isnat(date).any() or np.any(date >= np.datetime64(evaluate.TEST_FROM)):
                raise ValueError(f'{name}: invalid or protected-season date')
            if not np.isfinite(y).all() or np.any(y != np.floor(y)):
                raise ValueError(f'{name}: non-finite or non-integral label')
            if ((kind == 'multiclass' and (classes < 2 or np.any((y < 0) | (y >= classes)))) or
                    (kind in ('binary', 'candidate') and np.any((y != 0) & (y != 1))) or
                    kind not in ('multiclass', 'binary', 'candidate')):
                raise ValueError(f'{name}: invalid labels for {kind}')
            entry = {'rows': len(y), 'columns': len(columns), 'date_min': str(date.min()),
                     'date_max': str(date.max()), 'games': len(np.unique(game)), 'kind': kind,
                     'train_rows': int(np.count_nonzero(date <= np.datetime64(cutoff))),
                     'validation_rows': int(np.count_nonzero((date >= np.datetime64(validation_from)) &
                                                              (date <= np.datetime64(validation_to)))),
                     'sha256': sha256_file(path)}
            if 'group' in data.files:
                group = data['group']
                if len(group) != len(y):
                    raise ValueError(f'{name}: group/label dimensions disagree')
                _, inverse, counts = np.unique(group, return_inverse=True, return_counts=True)
                chosen = np.bincount(inverse, weights=y)
                if not np.all(chosen == 1):
                    raise ValueError(f'{name}: candidate groups without exactly one chosen player')
                entry['groups'] = len(counts)
                entry['candidate_group_sizes'] = {str(n): int(np.count_nonzero(counts == n))
                                                   for n in np.unique(counts)}
                if 'profile_score' in data.files:
                    score = data['profile_score']
                    if len(score) != len(y) or not np.isfinite(score).all():
                        raise ValueError(f'{name}: missing or non-finite profile baseline')
                    group_total = np.bincount(inverse, weights=score)
                    entry['zero_profile_groups'] = int(np.count_nonzero(group_total <= 0))
                    if entry['zero_profile_groups']:
                        raise ValueError(f'{name}: candidate baseline has a nonpositive group total')
            output[name] = entry
        print(f'{i}/{len(train.NODES)} {name}: {entry["rows"]:,} rows', flush=True)
    return {'experiment': 'a1_scheduled_node_cache_accounting', 'fold': fold,
            'population': 'all retained historical node rows; training and validation counted separately',
            'limits': 'shape, date, labels, group accounting and hashes only; not a model-accuracy test',
            'features': str(features), 'cache': str(folder.relative_to(ROOT)), 'cutoff': cutoff,
            'validation_from': validation_from, 'validation_to': validation_to, 'nodes': output,
            'audit_sha256': sha256_file(Path(__file__))}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--features', type=Path, required=True)
    parser.add_argument('--fold', choices=evaluate.FOLDS, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f'refusing to overwrite {args.output}')
    report = audit(args.features, args.fold)
    write_json(args.output, report, pretty=True)
    print(f'saved {args.output}', flush=True)


if __name__ == '__main__':
    main()
