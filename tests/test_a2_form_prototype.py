import unittest
from unittest.mock import patch

import numpy as np

from scripts import a2_form_prototype as prototype


class SyntheticFormTests(unittest.TestCase):
    def test_symmetric_effect_has_exact_mean_and_valid_boundaries(self):
        p = np.array([0., .1, .5, .9, 1.])
        low = prototype.probability_tilt(p, -np.ones(5))
        high = prototype.probability_tilt(p, np.ones(5))
        np.testing.assert_allclose((low + high) / 2, p, rtol=0, atol=1e-16)
        self.assertTrue(((0 <= low) & (high <= 1)).all())
        np.testing.assert_array_equal(prototype.probability_tilt(p, np.zeros(5)), p)

    def test_namespaced_world_draws_are_stable_across_order_and_partitions(self):
        ids = ['10', '20', '30']
        strength = np.array([.5, 0., 1.])
        first = prototype.player_effects('123', ids, 1000, 42, strength, 'form')
        reordered = prototype.player_effects('123', ['30', '10', '20', '40'], 1000, 42,
                                             np.array([1., .5, 0., .2]), 'form')
        np.testing.assert_array_equal(first, reordered[:, [1, 2, 0]])
        worker_one = prototype.player_effects('123', ids, 1000, 42, strength, 'form')[:400]
        worker_two = prototype.player_effects('123', ids, 1000, 42, strength, 'form')[400:]
        np.testing.assert_array_equal(np.concatenate([worker_one, worker_two]), first)
        self.assertTrue((first[:, 1] == 0).all())
        self.assertTrue((np.abs(first) <= strength).all())
        talent = prototype.player_effects('123', ids, 1000, 42, strength, 'talent')
        self.assertFalse(np.array_equal(first[:, 0], talent[:, 0]))
        with patch.object(prototype.projection, 'rng_for', side_effect=AssertionError('unexpected draw')):
            np.testing.assert_array_equal(prototype.player_effects('123', ids, 2, 42, np.zeros(3), 'form'),
                                          np.zeros((2, 3)))

    def test_bad_ids_strengths_and_probabilities_fail_explicitly(self):
        for ids, strength in [(['1', '1'], [0., 0.]), ([''], [0.]), (['1'], [1.01]), (['1'], [np.nan])]:
            with self.subTest(ids=ids, strength=strength), self.assertRaises(ValueError):
                prototype.player_effects('123', ids, 2, 42, np.array(strength), 'form')
        with self.assertRaisesRegex(ValueError, 'unsupported research factor'):
            prototype.player_effects('123', ['1'], 2, 42, np.array([.5]), 'unknown')
        for p, effect in [(np.array([.5]), np.array([np.nan])), (np.array([1.1]), np.array([0.])),
                          (np.array([.5]), np.array([1.1])), (np.array([.5]), np.zeros(2))]:
            with self.subTest(p=p, effect=effect), self.assertRaises(ValueError):
                prototype.probability_tilt(p, effect)


if __name__ == '__main__':
    unittest.main()
