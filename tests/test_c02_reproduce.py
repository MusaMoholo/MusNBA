import unittest
import numpy as np
import pandas as pd
from analysis.c02_reproduce import compare_worlds,independent_rows
from analysis.c01_core import ContractError

class ReproductionTests(unittest.TestCase):
    def test_worker_array_and_key_corruption_fail(self):
        a={'points':np.array([[0,2]]),'ids':np.array(['a','b'])}
        self.assertTrue(compare_worlds(a,{k:v.copy() for k,v in a.items()}))
        with self.assertRaisesRegex(ContractError,'array keys'):compare_worlds(a,{'points':a['points']})
        with self.assertRaisesRegex(ContractError,'replay differs'):compare_worlds(a,{**a,'points':np.array([[2,0]])})
    def test_independent_action_brier_has_hand_checked_value(self):
        f=pd.DataFrame({'y':[1],'seg_id':[1],'game_id':['1'],'date_et':['2026-01-01']})
        p=np.array([[.1,.3,.1,.1,.1,.1,.1,.1]])
        r=independent_rows('what',f,p,'candidate')
        self.assertAlmostEqual(r.brier.iloc[0],.56);self.assertAlmostEqual(r.loss.iloc[0],-np.log(.3))
    def test_independent_actor_law_selects_the_labelled_candidate(self):
        f=pd.DataFrame({'y':[0,0,1,0,0],'seg_id':[1]*5,'game_id':['1']*5,'date_et':['2026-01-01']*5})
        p=np.array([[.1,.2,.4,.2,.1]])
        r=independent_rows('who',f,p,'candidate')
        self.assertAlmostEqual(r.brier.iloc[0],.46);self.assertEqual(len(r),1)

if __name__=='__main__':unittest.main()
