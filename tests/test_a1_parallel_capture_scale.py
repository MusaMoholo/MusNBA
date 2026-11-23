import tempfile
import unittest
from pathlib import Path

import numpy as np

from analysis.a1_parallel_capture_audit import extract_world
from analysis.a1_parallel_capture_scale import merge_captures, resume_records
from analysis.a1_parallel_world_probe import capture_digest
from basketball_common import write_json


def fixture(dtype):
    return {
        'game_id': np.asarray('1'),
        'player_ids': np.asarray(['1', '2']),
        'side': np.array([0, 1]),
        'minutes': np.zeros((1, 2, 5)),
        'trace_world': np.zeros(2, dtype=dtype),
        'trace_lineups': np.array([[[0]], [[1]]], dtype=dtype),
    }


class ParallelCaptureTests(unittest.TestCase):
    def test_round_trip_preserves_per_world_dtypes(self):
        captures = [fixture(np.int32), fixture(np.int64)]
        captures[1]['trace_lineups'][0, 0, 0] = 257
        merged = merge_captures(captures)
        overrides = [{key: value.dtype.str for key, value in capture.items()
                      if value.dtype != merged[key].dtype} for capture in captures]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'batch.npz'
            np.savez_compressed(path, allow_pickle=False, **merged)
            with np.load(path, allow_pickle=False) as data:
                for world, capture in enumerate(captures):
                    self.assertEqual(capture_digest(extract_world(data, world, overrides[world])),
                                     capture_digest(capture))
                with self.assertRaisesRegex(ValueError, 'lossy dtype restoration'):
                    extract_world(data, 1, {'trace_lineups': '|u1'})

    def test_rejects_mismatched_game_or_world_index(self):
        first, second = fixture(np.int32), fixture(np.int32)
        second['game_id'] = np.asarray('2')
        with self.assertRaisesRegex(ValueError, 'identities differ'):
            merge_captures([first, second])
        second = fixture(np.int32)
        second['trace_world'][0] = 1
        with self.assertRaisesRegex(ValueError, 'single-world traces'):
            merge_captures([first, second])

    def test_resume_requires_matching_configuration_and_complete_contiguous_pairs(self):
        config = {'batches': 3, 'fingerprints': {'engine': 'abc'}}
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            write_json(directory / 'run.json', config)
            record = {'path': str(directory / 'batch_000.npz')}
            write_json(directory / 'batch_000.json', record)
            with self.assertRaisesRegex(ValueError, 'incomplete saved pair'):
                resume_records(directory, config)
            (directory / 'batch_000.npz').touch()
            self.assertEqual(resume_records(directory, config), [record])
            with self.assertRaisesRegex(ValueError, 'configuration or fingerprints changed'):
                resume_records(directory, {'batches': 3, 'fingerprints': {'engine': 'different'}})
            (directory / 'batch_002.npz').touch()
            with self.assertRaisesRegex(ValueError, 'non-contiguous'):
                resume_records(directory, config)
            self.assertTrue((directory / 'batch_002.npz').exists())

    def test_resume_rejects_capture_path_outside_run_directory(self):
        config = {'batches': 1}
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            write_json(directory / 'run.json', config)
            write_json(directory / 'batch_000.json', {'path': '/elsewhere/batch_000.npz'})
            (directory / 'batch_000.npz').touch()
            with self.assertRaisesRegex(ValueError, 'capture path differs'):
                resume_records(directory, config)


if __name__ == '__main__':
    unittest.main()
