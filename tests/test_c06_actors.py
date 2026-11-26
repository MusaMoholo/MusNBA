import unittest
import numpy as np
from analysis.c06_core import check,softmax,normalise,pack,dates_before
from analysis.c03_choices import CONTEXT,PLAYER
from analysis.c01_core import ContractError

class ActorBoundaryTests(unittest.TestCase):
    def test_known_law_and_permutation(self):
        p=softmax(np.log([[1,2,3,4,5]]));np.testing.assert_allclose(p,[[1/15,2/15,3/15,4/15,5/15]])
        perm=[3,1,4,2,0];np.testing.assert_allclose(softmax(np.log([[1,2,3,4,5]])[:,perm]),p[:,perm]);np.testing.assert_allclose(normalise([[.1,.2,.3,.4,.5]]),p)
    def test_meaningful_illegal_law_and_future_faults(self):
        for a in ([[0,.25,.25,.25,.25]],[[.1]*5],[[np.nan]*5],[[.2]*4]):
            with self.assertRaises(ContractError):check(a)
        for dates in (['2026-01-01'],['2025-12-32'],[None]):
            with self.assertRaises(ContractError):dates_before(dates,'2025-12-31')
        dates_before(['2023-01-01','2025-12-31'],'2025-12-31')
    def test_current_label_input_rejected(self):
        c={k:np.ones(3) for k in CONTEXT};p={k:np.ones((3,5)) for k in PLAYER}
        self.assertEqual(pack(c,p).shape,(15,len(CONTEXT)+len(PLAYER)))
        for k in ('actor','y','current_points','target'):
            with self.assertRaises(ContractError):pack({**c,k:np.ones(3)},p)
