import unittest
import numpy as np
from analysis.c03_choices import CONTEXT,PLAYER,law,decode,validate_inputs,long_features,check
from analysis.c01_core import ContractError

class ChoiceTests(unittest.TestCase):
    def setUp(self):
        self.c={k:np.zeros(2) for k in CONTEXT};self.p={k:np.zeros((2,5)) for k in PLAYER}
    def test_independent_marginal_arithmetic(self):
        p=np.tile(np.arange(1,44,dtype=float), (2,1));p/=p.sum(1,keepdims=True)
        e,w,a=decode(p)
        self.assertAlmostEqual(e[0,0],sum(range(1,41))/sum(range(1,44)))
        self.assertAlmostEqual(w[0,0],sum(range(1,9))/sum(range(1,41)))
        self.assertAlmostEqual(a[0,0,0],1/sum(range(1,9)))
        np.testing.assert_allclose((e[:,0,None,None]*w[:,:,None]*a).reshape(2,40),p[:,:40])
    def test_fault_boundary(self):
        for p in (np.full((2,43),np.nan),np.ones((2,43)),np.zeros((2,43))):
            with self.assertRaises(ContractError):check(p)
        with self.assertRaises(ContractError):validate_inputs(self.c,self.p,['2026-01-01']*2,True)
        for key in ('y','foul_event','current_action','legal_mask'):
            with self.assertRaises(ContractError):long_features({**self.c,key:np.ones(2)},self.p)
    def test_alternatives_do_not_depend_on_labels(self):
        x,cols=long_features(self.c,self.p);self.assertEqual(x.shape,(86,len(cols)))
        np.testing.assert_array_equal(x[:43,-1],np.r_[np.tile(np.arange(8),5),8,9,10])
        check(law(np.zeros((2,43))))
