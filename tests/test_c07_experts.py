import unittest
import numpy as np
from analysis.c07_core import weights,crps,record,pool,team_mass,prior_dates
from analysis.c01_core import ContractError

class WeightedBoundaryTests(unittest.TestCase):
    def test_reference_pairwise_and_replication(self):
        x=np.array([0.,2.,7.]);w=np.array([.2,.5,.3]);y=3.
        ref=w@abs(x-y)-.5*np.sum(w[:,None]*w[None,:]*abs(x[:,None]-x[None,:]))
        self.assertAlmostEqual(crps(x,y,w),ref)
        np.testing.assert_allclose(crps(np.repeat(x,2),y,np.repeat(w/2,2)),ref)
        from analysis.c01_metrics import crps as old
        z=np.random.default_rng(1).normal(size=1000);self.assertAlmostEqual(crps(z,.4,np.full(1000,.001)),old(z,.4))
    def test_meaningful_mass_and_future_faults(self):
        for w in ([.4,.4],[-.1,1.1],[np.nan,1]):
            with self.assertRaises(ContractError):weights(w)
        with self.assertRaises(ContractError):prior_dates(['2026-01-22'])
        prior_dates(['2026-01-01','2026-01-21'])
        with self.assertRaises(ContractError):team_mass([1.1,.2])
    def test_pool_preserves_worlds_exact_mass_halves_and_count(self):
        m={str(i):{'player_ids':np.array(['p']),'side':np.array([0]),'pts':np.arange(1000)[:,None]+i*1000} for i in range(4)};p=np.array([.00001,.1,.2,.69999]);a=pool(m,p,'g')
        self.assertEqual(len(a['weight']),1000);self.assertAlmostEqual(a['weight'].sum(),1)
        np.testing.assert_allclose(np.bincount(a['member'],weights=a['weight']),p,atol=1e-12)
        np.testing.assert_array_equal(a['pts'][:,0],a['member_world']+1000*a['member'].astype(int))
        np.testing.assert_array_equal(a['pts'],pool(m,p,'g')['pts'])
        r=record(np.zeros(1000),0,np.full(1000,.001));self.assertEqual(r['crps'],0);self.assertEqual(r['covered80'],1)
