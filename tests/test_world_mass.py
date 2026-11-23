from fractions import Fraction
import unittest

import numpy as np

from scripts.world_mass import WorldMass, branch_masses


class MassTests(unittest.TestCase):
    def test_original_status_probability_and_full_empirical_mixture(self):
        weights = branch_masses([2, 2], [Fraction(3, 20), Fraction(17, 20)])
        np.testing.assert_array_equal(weights, [3, 3, 17, 17])
        m = WorldMass(4, weights)
        s = m.summary(np.array([10, 20, 0, 0]))
        self.assertEqual(m.total, 40)
        self.assertEqual(sum(s['hist']), 40)
        self.assertEqual(s['mean'], 2.25)
        self.assertEqual(s['q'], [0, 0, 0, 0, 10])
        self.assertEqual(float(m.mean(np.array([1, 1, 0, 0]))), .15)

    def test_conditional_mass_and_multidimensional_means(self):
        m = WorldMass(4, np.array([3, 3, 17, 17]))
        condition = np.array([True, True, False, False])
        sub = m.subset(condition)
        self.assertEqual(sub.total, 6)
        self.assertEqual(float(sub.mean([10, 20])), 15.)
        np.testing.assert_allclose(m.mean(np.array([[2., 3.], [2., 3.], [0., 1.], [0., 1.]])), [.3, 1.3])
        with self.assertRaises(ValueError):
            m.subset(np.zeros(4, bool))

    def test_rejects_corrupt_or_inexact_weights(self):
        for weights in ([.5, .5], [1, 0], [1], [2**53, 1]):
            with self.assertRaises(ValueError):
                WorldMass(2, weights)
        with self.assertRaises(ValueError):
            branch_masses([1, 1], [Fraction(1, 5), Fraction(1, 5)])
        with self.assertRaises(ValueError):
            WorldMass(2).counts(np.array([1., 1.5]))


if __name__ == '__main__':
    unittest.main()
