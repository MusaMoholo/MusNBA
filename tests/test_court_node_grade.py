import unittest
import numpy as np
from analysis.c2_node_grade import pair,bootstrap


class CourtNodeGradeTest(unittest.TestCase):
    def test_duplicate_game_metadata_does_not_mask_swapped_decisions(self):
        a={'game':np.array(['a','a','b']),'date':np.array(['d','d','d']),
           'source_seg_id':np.array([4,5,7]),'cell':np.array([0,0,1]),'loss':np.array([.5,.4,.6])}
        b={k:v.copy() for k,v in a.items()};b['source_seg_id'][:2]=[5,4]
        with self.assertRaises(AssertionError):pair(a,b)

    def test_nonzero_constant_cluster_difference_keeps_its_direction(self):
        games=np.array(['a','a','b','c','c','c'])
        for value in [-.01,.01]:
            result=bootstrap([(games,np.full(len(games),value))],repeats=1000)
            self.assertAlmostEqual(result['pooled_delta'],value)
            self.assertAlmostEqual(result['benefit_upper_bonferroni3'],value)

    def test_independent_fold_clusters_reproduce(self):
        parts=[(np.array(['a','a','b']),np.array([-.1,.1,-.2])),
               (np.array(['c','d','d']),np.array([.1,-.3,.4]))]
        self.assertEqual(bootstrap(parts,repeats=1000),bootstrap(parts,repeats=1000))

if __name__=='__main__':unittest.main()
