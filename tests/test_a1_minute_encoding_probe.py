import unittest

import numpy as np

from analysis.a1_minute_encoding_probe import compare


class MinuteEncodingProbeTests(unittest.TestCase):
    def test_rounding_can_cross_threshold_and_erase_participation(self):
        minutes = np.zeros((3, 1, 5), dtype=np.float64)
        minutes[:, 0, 0] = [29.999, 30.0, 0.001]
        result = compare(minutes)['encodings']
        self.assertEqual(result['float64_minutes']['integer_minute_threshold_disagreements']['30'], 0)
        self.assertEqual(result['rounded_seconds']['integer_minute_threshold_disagreements']['30'], 1)
        self.assertEqual(result['rounded_seconds']['positive_minutes_lost'], 1)

    def test_invalid_minutes_fail_explicitly(self):
        for values in (np.zeros((1, 1, 4)), np.full((1, 1, 5), np.nan),
                       np.full((1, 1, 5), -1.0)):
            with self.subTest(shape=values.shape):
                with self.assertRaises(ValueError):
                    compare(values)


if __name__ == '__main__':
    unittest.main()
