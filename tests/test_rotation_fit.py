import unittest
import numpy as np

from scripts.engine import Game
from scripts.rotation_fit import independent


class IndependentRotationTests(unittest.TestCase):
    def test_minute_target_noise_is_resolved_within_each_world(self):
        from scripts.minutes import redraw

        class FixedNoise:
            def __init__(self, values):
                self.values = values

            def standard_normal(self, shape):
                self.shape = shape
                if self.values.shape != shape:
                    raise AssertionError('unexpected random-draw dimensions')
                return self.values.copy()

        noise = np.random.default_rng(23).standard_normal((12,8))
        mu, cap, sd = np.full(8,30.), np.full(8,42.), np.full(8,5.)
        reference = np.concatenate([redraw(mu,cap,sd,1,FixedNoise(row[None])) for row in noise])
        np.testing.assert_array_equal(redraw(mu,cap,sd,12,FixedNoise(noise)),reference)
        order = np.random.default_rng(24).permutation(12)
        np.testing.assert_array_equal(redraw(mu,cap,sd,12,FixedNoise(noise[order])),reference[order])

    def test_batch_chunk_and_permutation_match_existing_one_world_reference(self):
        rng = np.random.default_rng(20261123)
        curves = rng.normal(size=(12, 8, 288))
        target = rng.uniform(20, 40, size=(12, 8))
        target *= 240 / target.sum(1, keepdims=True)
        from scripts.engine import ROTATION
        reference = np.concatenate([Game._fit_offsets(curves[i:i+1], target[i:i+1]) for i in range(12)])
        result = independent(curves, target, ROTATION)
        np.testing.assert_array_equal(result, reference)
        for cuts in ([1, 5, 9], [2, 4, 6, 8, 10]):
            chunks = zip(np.split(curves, cuts), np.split(target, cuts))
            np.testing.assert_array_equal(np.concatenate([independent(c, t, ROTATION) for c,t in chunks]), reference)
        order = rng.permutation(12)
        np.testing.assert_array_equal(independent(curves[order], target[order], ROTATION), reference[order])

    def test_other_worlds_cannot_change_a_converged_world(self):
        from scripts.engine import ROTATION
        curves = np.zeros((2, 6, 288))
        curves[:, :5] = 1
        targets = np.array([[48]*5 + [0], [40]*6], float)
        alone = independent(curves[:1], targets[:1], ROTATION)
        together = independent(curves, targets, ROTATION)
        np.testing.assert_array_equal(alone[0], together[0])
        self.assertTrue(np.all(np.diff(np.sort(together, axis=1), axis=1) != 0))


if __name__ == '__main__':
    unittest.main()
