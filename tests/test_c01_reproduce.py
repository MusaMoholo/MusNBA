"""The reproduction boundary rejects changed results, support and semantics."""
import unittest
from analysis.c01_core import ContractError
from analysis.c01_reproduce import compare_numeric


class ReproductionContractTests(unittest.TestCase):
    def test_small_reduction_noise_is_bounded_but_changed_effects_fail(self):
        self.assertLess(compare_numeric({'score':[1.,2.]},{'score':[1.+1e-12,2.]}),1e-10)
        with self.assertRaises(ContractError):compare_numeric({'score':[1.,2.]},{'score':[1.1,2.]})

    def test_missing_support_keys_or_boolean_meaning_never_pass(self):
        for a,b in [({'a':1},{'b':1}),([1,2],[1]),(None,0),(False,0)]:
            with self.assertRaises(ContractError):compare_numeric(a,b)


if __name__=='__main__':unittest.main()
