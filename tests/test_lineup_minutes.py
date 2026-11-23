import base64
import unittest

import numpy as np

from scripts.lineup_minutes import encode


class MinuteCdfTests(unittest.TestCase):
    def test_exact_weighted_full_game_thresholds_without_rounding(self):
        values = np.zeros((3, 1, 5), dtype=np.float64)
        values[:, 0, 0] = [.001, 10., 10.001]
        values[:, 0, 1:3] = 10.
        result = encode(values, ['1'], np.array([3, 4, 17]))
        self.assertEqual(result['worlds'], 3)
        self.assertEqual(result['probability_mass'], 24)
        raw = np.frombuffer(base64.b64decode(result['minutes_f64_le']), dtype='<f8')
        cumulative = np.frombuffer(base64.b64decode(result['cumulative_f64_le']), dtype='<f8')
        start, stop = result['offsets'][-2:]
        x, c = raw[start:stop], cumulative[start:stop]
        np.testing.assert_array_equal(x, values.sum(2)[:, 0])
        np.testing.assert_array_equal(c, [3., 7., 24.])
        self.assertEqual(c[np.searchsorted(x, 30., side='left') - 1], 3.)
        self.assertEqual(c[np.searchsorted(x, 30., side='right') - 1], 7.)
        for start, stop in zip(result['offsets'][:-1], result['offsets'][1:]):
            self.assertEqual(cumulative[stop - 1], 24.)

    def test_corrupt_precise_minutes_and_weights_fail(self):
        for value in (-1., np.nan, np.inf):
            with self.assertRaises(ValueError):
                encode(np.full((2, 1, 5), value), ['1'], np.array([1, 1]))
        with self.assertRaises(ValueError):
            encode(np.zeros((2, 1, 5)), ['1'], np.array([.5, .5]))


if __name__ == '__main__':
    unittest.main()
