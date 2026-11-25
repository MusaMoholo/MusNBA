"""Independent synthetic boundaries for C02 possession data and probabilities."""
import tempfile
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
from analysis import c02_data as d
from analysis.c01_core import ContractError

class DataBoundaryTests(unittest.TestCase):
    def frame(self,name='who'):
        f=pd.DataFrame({k:np.zeros(10) for k in d.COLS[name]})
        f['y']=[1,0,0,0,0]*2;f['seg_id']=np.repeat([1,2],5);f['date_et']='2025-01-01';return f
    def test_valid_five_and_deliberate_duplicate_label(self):
        f=self.frame();self.assertTrue(d.validate(f,'who',True));f.loc[1,'y']=1
        with self.assertRaisesRegex(ContractError,'exactly one'):d.validate(f,'who',True)
    def test_missing_and_future_features_rejected(self):
        f=self.frame();f.loc[0,'date_et']='2026-01-01'
        with self.assertRaisesRegex(ContractError,'future'):d.validate(f,'who',True)
        with self.assertRaisesRegex(ContractError,'missing'):d.validate(self.frame().drop(columns=d.WHO[0]),'who')
    def test_interleaved_groups_rejected(self):
        f=self.frame();f['seg_id']=[1,2]*5;f['y']=[1,1]+[0]*8
        with self.assertRaisesRegex(ContractError,'contiguous'):d.validate(f,'who')
    def test_source_predicate_excludes_future_and_older_outcomes(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'segments.parquet'
            pd.DataFrame({'game_id':['1','2','3'],'date_et':['2024-01-01','2025-01-01','2026-01-01'],'season_type':[2]*3,'future_truth':[99,1,999]}).to_parquet(p)
            with d.Boundary(['2'],'training').installed():f=pd.read_parquet(p)
            self.assertEqual(f.future_truth.tolist(),[1])
    def test_no_ids_final_totals_or_quotas_in_feature_interface(self):
        for cols in d.COLS.values():
            self.assertFalse(set(cols)&{'game_id','player','team','points','team_points','final_score','remaining_shots','shot_target'})
    def test_invalid_action_and_infinite_input(self):
        f=self.frame('what');f['y']=8
        with self.assertRaisesRegex(ContractError,'action label'):d.validate(f,'what')
        f=self.frame();f.loc[0,d.WHO[0]]=np.inf
        with self.assertRaisesRegex(ContractError,'infinite'):d.validate(f,'who')

if __name__=='__main__':unittest.main()

class ProbabilityTests(unittest.TestCase):
    def test_conditional_softmax_gradient_matches_finite_difference(self):
        from analysis.c02_model import objective
        class DS:
            def get_label(self):return np.array([0,1,0,0,0.])
            def get_weight(self):return None
        z=np.array([-.2,.5,.1,-.1,.2]);g,h=objective(z,DS())
        def loss(q):return np.log(np.exp(q).sum())-q[1]
        numerical=np.array([(loss(z+np.eye(5)[i]*1e-5)-loss(z-np.eye(5)[i]*1e-5))/2e-5 for i in range(5)])
        np.testing.assert_allclose(g,numerical,atol=1e-9);self.assertTrue((h>0).all());self.assertAlmostEqual(g.sum(),0)
    def test_candidate_permutation_and_invalid_probabilities(self):
        from analysis.c02_model import softmax,check_prob
        z=np.array([1.,0.,-1.,.1,.2]);perm=[3,0,4,2,1]
        np.testing.assert_allclose(softmax(z[perm])[0],softmax(z)[0,perm])
        with self.assertRaisesRegex(ContractError,'probability'):check_prob([[.2,.2]])
    def test_future_fit_origin_fails(self):
        from analysis.c02_model import weights
        with self.assertRaisesRegex(ContractError,'future'):
            weights(pd.DataFrame({'date_et':['2025-01-01']}),'2025-01-01')
    def test_profile_action_law_has_hand_checked_shares(self):
        from analysis.c02_model import profile_what
        f=pd.DataFrame({f'actor_mix_{z}':[.2] for z in ('rim','paint','mid','corner3','above3')})
        f['actor_shot_share']=.6;f['actor_tov_share']=.2;f['actor_foul_drawn_share']=.2
        p=profile_what(f,[.125]*8)
        np.testing.assert_allclose(p[0],[.12]*5+[.2,.192,.008]);self.assertAlmostEqual(p.sum(),1)

class RelativeBoundaryFaultTests(unittest.TestCase):
    def test_future_other_lineup_cannot_change_missing_earlier_role(self):
        from scripts import nodes
        def compute(later):
            c=object.__new__(nodes.Chain)
            rows=[{'seg_id':i,'player':str(j),**{k:v for k in ('usage','ast_rate','oreb_pct','shot_share','blk_rate','stl_rate','dreb_pct','pf_rate')}}
                  for i,vs in enumerate(([1.,2.,np.nan,3.,4.],[later]*5)) for j,v in enumerate(vs)]
            c.off=pd.DataFrame(rows);c.dfn=c.off.copy();d.causal_relative(c)
            return c.off.iloc[:5][['usage_share','usage_rank']].to_numpy()
        np.testing.assert_allclose(compute(1.),compute(99999.),equal_nan=True)
        np.testing.assert_allclose(compute(1.)[:,0],[.08,.16,.2,.24,.32])
