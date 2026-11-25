import unittest
import numpy as np
from analysis.c04_core import COLS,legal,inputs,prior,quantiles
from analysis.c01_core import ContractError
class RoleBoundaryTests(unittest.TestCase):
    def test_projection_constraint_and_optimality(self):
        np.testing.assert_allclose(legal(np.full(10,20.)),24)
        np.testing.assert_allclose(legal([100,0,0,0,0]),48)
        x=np.array([40,35,30,25,20,15,10,5.]);y=legal(x);self.assertAlmostEqual(y.sum(),240)
        free=(y>0)&(y<48);self.assertLess(np.ptp((y-x)[free]),1e-10)
        perm=[3,0,7,1,6,2,5,4];np.testing.assert_allclose(legal(x[perm]),y[perm])
    def test_meaningful_faults(self):
        for a in ([1]*4,[np.nan]*5):
            with self.assertRaises(ContractError):legal(a)
        for dates in (['2026-01-01'],['2026-01-02']):
            with self.assertRaises(ContractError):prior(dates,'2026-01-01')
        c={k:np.ones(3) for k in COLS}
        for label in ('reg','starter','target','current_minutes'):
            with self.assertRaises(ContractError):inputs({**c,label:np.ones(3)})
        with self.assertRaises(ContractError):quantiles(np.full((2,7),np.nan))
