import base64
import unittest

import numpy as np

from analysis.a1_minute_payload_probe import encode


class MinutePayloadProbeTests(unittest.TestCase):
    def test_world_periods_and_sorted_marginals_preserve_values(self):
        minutes = np.array([[[0.001, 2, 0, 0, 0]], [[0, 3, 0, 0, 0]], [[30, 0, 0, 0, 1]]])
        worlds, marginal = encode(minutes, False), encode(minutes, True)
        restored = np.frombuffer(base64.b64decode(worlds['minutes_f64_le']), '<f8').reshape(worlds['shape'])
        np.testing.assert_array_equal(restored, minutes)
        restored_marginal = np.frombuffer(base64.b64decode(marginal['minutes_f64_le']), '<f8').reshape(marginal['shape'])
        np.testing.assert_array_equal(restored_marginal[:, 0, 0], np.sort(minutes[:, 0, 0]))
        np.testing.assert_array_equal(restored_marginal[:, 0, -1], np.sort(minutes[:, 0, :].sum(axis=1)))

    def test_invalid_values_rejected(self):
        for values in (np.zeros((1, 1, 4)), np.full((1, 1, 5), np.inf), np.full((1, 1, 5), -1.0)):
            with self.subTest(shape=values.shape):
                with self.assertRaises(ValueError):
                    encode(values, False)


if __name__ == '__main__':
    unittest.main()
