import tempfile
import unittest
from pathlib import Path

import numpy as np

from analysis.a1_parallel_capture_audit import extract_world
from analysis.a1_parallel_capture_scale import merge_captures
from analysis.a1_parallel_world_probe import capture_digest


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


if __name__ == '__main__':
    unittest.main()
