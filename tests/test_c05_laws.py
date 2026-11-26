import unittest
import numpy as np
from analysis.c05_core import seconds,schedule,validate
from analysis.c04_core import legal
from analysis.c01_core import ContractError

class ExactDecoderTests(unittest.TestCase):
    def test_random_boundary_and_independent_count(self):
        rng=np.random.default_rng(9)
        for n in (5,6,9,12,15):
            for j in range(8):
                x=legal(rng.normal(20,30,n));tab=schedule(x,rng.random((n,2880)))
                self.assertTrue(all(len(set(row))==5 for row in tab))
                actual=np.array([(tab==i).sum()/60 for i in range(n)])
                self.assertLessEqual(np.max(abs(actual-x)),1/60+1e-9)
                np.testing.assert_array_equal(tab,schedule(x,rng.random((n,2880))) if n==5 else tab)
    def test_illegal_law_and_schedule_faults(self):
        for x in ([48]*4,[49,47,48,48,48],[np.nan]*5,[40]*6+[1]):
            with self.assertRaises(ContractError):seconds(x)
        x=np.full(8,30.);tab=schedule(x);tab[0,0]=tab[0,1]
        with self.assertRaisesRegex(ContractError,'five'):validate(tab,x)
        tab=schedule(x);tab[0,0]=next(i for i in range(8) if i not in tab[0])
        with self.assertRaisesRegex(ContractError,'target-to-schedule'):validate(tab,x)
