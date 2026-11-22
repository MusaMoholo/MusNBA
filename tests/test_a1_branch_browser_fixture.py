import base64
import unittest

import numpy as np

from analysis.a1_branch_browser_fixture import pack_capture, packed_bytes
from scripts.views import WORLD_STATS


class BranchBrowserFixtureTests(unittest.TestCase):
    def capture(self):
        data = {
            'player_ids': np.array(['1', '2']), 'side': np.array([0, 1]),
            'available': np.array([[True, True], [True, False]]),
            'minutes': np.zeros((2, 2, 5)),
            'team_points': np.zeros((2, 2, 5), dtype=int),
            'final_period': np.array([5, 4]),
        }
        for stat in ('pts', 'oreb', 'dreb', 'ast', 'fg3m', 'stl', 'blk', 'tov',
                     'fgm', 'fga', 'fg3a', 'fta', 'ftm'):
            data[f'box_{stat}'] = np.zeros((2, 2, 5), dtype=int)
        data['team_points'][0, 0, 0] = data['box_pts'][0, 0, 0] = 3
        data['minutes'][0, 0, 0] = 12.0
        data['minutes'][0, 1, 0] = 0.1
        return data

    def test_roundtrip_keeps_availability_distinct_from_minutes(self):
        packed = pack_capture(self.capture())
        lines = np.frombuffer(base64.b64decode(packed['lines']), dtype=np.uint8).reshape(2, 2, -1)
        available = np.frombuffer(base64.b64decode(packed['availability']), dtype=np.uint8).reshape(2, 2)
        played = np.frombuffer(base64.b64decode(packed['played']), dtype=np.uint8).reshape(2, 2)
        minutes = np.frombuffer(base64.b64decode(packed['minutes_f64_le']), dtype='<f8').reshape(2, 2)
        periods = np.frombuffer(base64.b64decode(packed['team_periods']), dtype=np.uint8).reshape(2, 2, 5)
        player_periods = np.frombuffer(base64.b64decode(packed['period_lines']), dtype=np.uint8).reshape(2, 2, 5, -1)
        period_minutes = np.frombuffer(base64.b64decode(packed['period_minutes_f64_le']), dtype='<f8').reshape(2, 2, 5)
        self.assertEqual(packed['stats'], list(WORLD_STATS))
        self.assertEqual(lines[0, 0, WORLD_STATS.index('pts')], 3)
        self.assertEqual(periods[0, 0, 0], 3)
        self.assertEqual(packed['period_stats'], list(WORLD_STATS[1:]))
        self.assertEqual(player_periods[0, 0, 0, packed['period_stats'].index('pts')], 3)
        self.assertEqual(period_minutes[0, 1, 0], 0.1)
        self.assertEqual(list(base64.b64decode(packed['final_period'])), [5, 4])
        self.assertEqual(available[0, 1], 1)
        self.assertEqual(lines[0, 1, WORLD_STATS.index('min')], 0)
        self.assertEqual(played[0, 1], 1)
        self.assertEqual(minutes[0, 1], 0.1)
        self.assertEqual(available[1, 1], 0)
        self.assertEqual(played[1, 1], 0)

    def test_corrupt_or_unrepresentable_worlds_fail_instead_of_clipping(self):
        for bad in (-1, 256, float('nan'), 1.5):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                packed_bytes(np.array([bad]))
        data = self.capture()
        data['box_pts'][1, 1, 0] = 1
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
        data['team_points'][0, 0, 0] -= 1
        data['team_points'][0, 0, 1] += 1
        with self.assertRaisesRegex(ValueError, 'scores do not reconcile'):
            pack_capture(data)


if __name__ == '__main__':
    unittest.main()
