from types import SimpleNamespace
import unittest
import numpy as np
import pandas as pd
from scripts import nodes
from analysis.c02_features import View,selected
from analysis.c01_core import ContractError

class FeatureViewTests(unittest.TestCase):
    def setup_view(self):
        ids=[str(i) for i in range(10)]
        g=SimpleNamespace(game={'game_id':'1','home_id':'h','away_id':'a'},ids=ids,day='2026-01-01')
        rows=[]
        for i,p in enumerate(ids):rows.append({'game_id':'1','player':p,'date_et':g.day,'pos':'G',**{k:float(i+1) for k in nodes.PROFILE}})
        teams=pd.DataFrame([{'game_id':'1','team':t,'date_et':g.day,'rest_days':2,'season_day':60,**{f'{s}_{k}':.1 for s in ('off','def') for k in ('pace','three','rim','tov','foul','oreb')}} for t in ('h','a')])
        v=View(g,pd.DataFrame(rows),teams)
        st=SimpleNamespace(off=np.array([0]),period=np.array([1]),clock=np.array([710.]),score=np.array([[2.,0.]]),tfouls=np.zeros((1,2)),start=np.array([0]),ingame={k:np.zeros((1,10),np.float32) for k in nodes.IN_GAME})
        return g,v,st
    def test_hand_reconciled_context_and_shares(self):
        g,v,st=self.setup_view();A=np.array([0]);lo=np.arange(5)[None,:];ld=np.arange(5,10)[None,:]
        c=v.context(g,st,A,lo,ld);f=v.five(st,A,lo)
        self.assertEqual(c['margin'][0],2);self.assertEqual(c['sec_left_game'][0],2870);self.assertEqual(c['off_usage_sum'][0],15)
        np.testing.assert_allclose(f['usage_share'],[[1/15,2/15,3/15,4/15,5/15]])
        self.assertEqual(v.actor(f,np.array([3]))['actor_usage'][0],4)
    def test_player_permutation_reorders_probabilistic_inputs(self):
        _,v,st=self.setup_view();A=np.array([0]);lo=np.arange(5)[None,:];perm=[3,1,4,0,2]
        a=v.five(st,A,lo);b=v.five(st,A,lo[:,perm])
        for k in ('usage','usage_share','usage_rank'):np.testing.assert_allclose(a[k][:,perm],b[k])
    def test_future_game_targets_cannot_change_event_features(self):
        g,v,st=self.setup_view();A=np.array([0]);lo=np.arange(5)[None,:];ld=lo+5
        before=v.context(g,st,A,lo,ld);g.team_point_target=9999;g.shot_target=9999
        after=v.context(g,st,A,lo,ld)
        for k in before:np.testing.assert_array_equal(before[k],after[k])
    def test_missing_runtime_feature_fails_closed(self):
        with self.assertRaisesRegex(ContractError,'missing causal'):selected('who',{})
    def test_history_is_current_state_only(self):
        _,v,st=self.setup_view();st.ingame['uses_so_far'][0,1]=3
        f=v.five(st,np.array([0]),np.arange(5)[None,:]);self.assertEqual(f['uses_so_far'][0,1],3)

if __name__=='__main__':unittest.main()
