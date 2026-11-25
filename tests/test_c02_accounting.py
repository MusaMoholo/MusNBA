import unittest
from analysis.c02_accounting import reference_crps
from analysis.c01_core import ContractError

class IndependentArithmeticTests(unittest.TestCase):
    def test_hand_computed_probability_score(self):
        self.assertEqual(reference_crps([0,2],1),.5)
        self.assertEqual(reference_crps([0,0,2,2],1),.5)
        self.assertEqual(reference_crps([3,3],3),0)
    def test_invalid_sample_rejected(self):
        with self.assertRaisesRegex(ContractError,'invalid'):reference_crps([],1)
        with self.assertRaisesRegex(ContractError,'invalid'):reference_crps([float('nan')],1)

if __name__=='__main__':unittest.main()
