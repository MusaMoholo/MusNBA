import unittest
import numpy as np
from analysis.b2_grade import histogram_crps
from scripts.aggregate import crps_samples


class HistogramScoreTests(unittest.TestCase):
    def test_exact_integer_cdf_matches_independent_sample_formula_including_outside_support(self):
        samples=np.array([[2,0],[4,8],[4,8],[7,13]])
        hist=np.stack([np.bincount(samples[:,i],minlength=14) for i in range(2)])
        for truth in [np.array([3.,5.]),np.array([20.,1.]),np.array([0.,30.])]:
            np.testing.assert_allclose(histogram_crps(hist,truth),crps_samples(samples,truth),rtol=0,atol=1e-12)

    def test_missing_support_is_not_filled(self):
        with self.assertRaises(ValueError):histogram_crps(np.zeros((2,4),int),np.array([2,3]))


if __name__=='__main__':unittest.main()
