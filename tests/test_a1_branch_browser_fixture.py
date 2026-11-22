import base64
import unittest

import numpy as np

from analysis.a1_branch_browser_fixture import pack_capture, packed_bytes
from scripts.views import WORLD_STATS


class BranchBrowserFixtureTests(unittest.TestCase):
    def capture(self):
        data = {
            'player_ids': np.array([str(i) for i in range(1, 12)]), 'side': np.array([0] * 5 + [1] * 6),
            'available': np.ones((2, 11), dtype=bool),
            'minutes': np.zeros((2, 11, 5)),
            'team_points': np.zeros((2, 2, 5), dtype=int),
            'final_period': np.array([5, 4]),
            'trace_world': np.array([0, 1]), 'trace_period': np.array([1, 1]),
            'trace_clock': np.array([720.0, 720.0]), 'trace_phase': np.array([0, 0]),
            'trace_lineups': np.array([[[0, 1, 2, 3, 4], [5, 6, 7, 8, 9]]] * 2),
        }
        data['available'][1, 10] = False
        for stat in ('pts', 'oreb', 'dreb', 'ast', 'fg3m', 'stl', 'blk', 'tov',
                     'fgm', 'fga', 'fg3a', 'fta', 'ftm'):
            data[f'box_{stat}'] = np.zeros((2, 11, 5), dtype=int)
        data['team_points'][0, 0, 0] = data['box_pts'][0, 0, 0] = 3
        data['minutes'][0, 0, 0] = 12.0
        data['minutes'][0, 5, 0] = 0.1
        return data

    def test_roundtrip_keeps_availability_distinct_from_minutes(self):
        packed = pack_capture(self.capture())
        lines = np.frombuffer(base64.b64decode(packed['lines']), dtype=np.uint8).reshape(2, 11, -1)
        available = np.frombuffer(base64.b64decode(packed['availability']), dtype=np.uint8).reshape(2, 11)
        played = np.frombuffer(base64.b64decode(packed['played']), dtype=np.uint8).reshape(2, 11)
        minutes = np.frombuffer(base64.b64decode(packed['minutes_f64_le']), dtype='<f8').reshape(2, 11)
        periods = np.frombuffer(base64.b64decode(packed['team_periods']), dtype=np.uint8).reshape(2, 2, 5)
        player_periods = np.frombuffer(base64.b64decode(packed['period_lines']), dtype=np.uint8).reshape(2, 11, 5, -1)
        period_minutes = np.frombuffer(base64.b64decode(packed['period_minutes_f64_le']), dtype='<f8').reshape(2, 11, 5)
        self.assertEqual(packed['stats'], list(WORLD_STATS))
        self.assertEqual(lines[0, 0, WORLD_STATS.index('pts')], 3)
        self.assertEqual(periods[0, 0, 0], 3)
        self.assertEqual(packed['period_stats'], list(WORLD_STATS[1:]))
        self.assertEqual(player_periods[0, 0, 0, packed['period_stats'].index('pts')], 3)
        self.assertEqual(period_minutes[0, 5, 0], 0.1)
        self.assertEqual(list(base64.b64decode(packed['final_period'])), [5, 4])
        self.assertEqual(list(base64.b64decode(packed['opening_lineups']))[:10], list(range(10)))
        self.assertEqual(available[0, 5], 1)
        self.assertEqual(lines[0, 5, WORLD_STATS.index('min')], 0)
        self.assertEqual(played[0, 5], 1)
        self.assertEqual(minutes[0, 5], 0.1)
        self.assertEqual(available[1, 10], 0)
        self.assertEqual(played[1, 10], 0)

    def test_corrupt_or_unrepresentable_worlds_fail_instead_of_clipping(self):
        for bad in (-1, 256, float('nan'), 1.5):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                packed_bytes(np.array([bad]))
        data = self.capture()
        data['box_pts'][1, 10, 0] = 1
        with self.assertRaisesRegex(ValueError, 'unavailable'):
            pack_capture(data)
        data = self.capture()
        data['team_points'][0, 0, 0] += 1
        with self.assertRaisesRegex(ValueError, 'scores do not reconcile'):
            pack_capture(data)
        data = self.capture()
        data['final_period'][0] = 3
        with self.assertRaisesRegex(ValueError, 'dimensions'):
            pack_capture(data)
        data = self.capture()
        data['final_period'][0] = 4
        data['box_pts'][0, 0, 4] = data['team_points'][0, 0, 4] = 1
        with self.assertRaisesRegex(ValueError, 'overtime scores'):
            pack_capture(data)
        data = self.capture()
        data['trace_lineups'][0, 0, 1] = 0
        with self.assertRaisesRegex(ValueError, 'five distinct'):
            pack_capture(data)
        data = self.capture()
        data['trace_clock'][0] = 719
        with self.assertRaisesRegex(ValueError, 'opening trace'):
            pack_capture(data)
        data = self.capture()
        data['trace_world'][1] = 0
        with self.assertRaisesRegex(ValueError, 'every world'):
            pack_capture(data)
        data = self.capture()
        data['trace_lineups'][1, 1, 4] = 10
        with self.assertRaisesRegex(ValueError, 'available teammates'):
            pack_capture(data)
        data = self.capture()
        data['team_points'][0, 0, 0] -= 1
        data['team_points'][0, 0, 1] += 1
        with self.assertRaisesRegex(ValueError, 'scores do not reconcile'):
            pack_capture(data)


if __name__ == '__main__':
    unittest.main()
