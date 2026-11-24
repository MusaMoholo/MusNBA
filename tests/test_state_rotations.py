import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
from scripts import state_rotations as rotation,engine,lineup_forecast
from scripts.a1_substitution_engine import SelectedTimeoutPolicy
from tests import test_foul_out as foul_fixtures

class FixedModel:
 def __init__(self,incoming=False):self.incoming=incoming;self.inputs=[]
 def predict(self,x,**kwargs):
  self.inputs.append(x.copy())
  return np.zeros(len(x)) if self.incoming else np.where(x[:,2]<0,.8,.1)

class StateRotationTests(unittest.TestCase):
 def fixture(self,kind=rotation.StateRotations):
  g,st,fives,_=foul_fixtures.Rule3Tests().fixture()
  g.game.update(game_id='test',home_id='home',away_id='away')
  features=pd.DataFrame([{'game_id':'test','team':g.game[g.sides[int(g.side[i])]+'_id'],
   'player':pid,'control_mean':20.,'tier':'bench','prior_position':'guard'} for i,pid in enumerate(g.ids)])
  # Use a position in the original frozen model taxonomy.
  from scripts.a1_substitution_engine import POSITIONS
  features['prior_position']=POSITIONS[0]
  p=kind(FixedModel(),FixedModel(True),{'regulation':[[[1,0.]]],'overtime':[[0.]]},features)
  p.begin(g,1,np.ones((1,g.n),bool),42)
  return g,st,fives,p

 def test_ordinary_selected_decisions_exactly_match_original(self):
  g,st,fives,new=self.fixture();_,_,_,old=self.fixture(SelectedTimeoutPolicy)
  active=np.array([0]);st.score[0]=[0,10]
  a=new.before_segment(g,st,active,fives);b=old.before_segment(g,st,active,fives)
  np.testing.assert_array_equal(a,b)
  self.assertEqual(new.counts['timeout_team_windows'],2)
  self.assertGreater(new.counts['timeout_outgoing'],0)
  self.assertEqual(new.rng.bit_generator.state,old.rng.bit_generator.state)
  x=new.outgoing.inputs[0]
  np.testing.assert_array_equal(x[:5,2],-10)
  np.testing.assert_array_equal(x[5:,2],10)

 def test_foul_out_syncs_selected_lineup_and_stint_state(self):
  g,st,fives,p=self.fixture();p.reg_templates=[[]]
  st.ingame['pf_so_far'][0,0]=5
  p.before_segment(g,st,np.array([0]),fives)
  foul_fixtures.Rule3Tests().foul(st,0,True)
  offense,defense=fives[:,0].copy(),fives[:,1].copy()
  changed=p.after_fouls(g,st,np.array([0]),offense,defense)
  self.assertTrue(changed[0]);self.assertNotIn(0,p.current[0,0])
  np.testing.assert_array_equal(p.current[0,0],offense[0])
  self.assertTrue(np.isfinite(p.off_since[0,0]))

 def test_exhaustion_uses_current_rule3_offensive_penalty(self):
  g,st,fives,p=self.fixture();p.reg_templates=[[]]
  st.ingame['pf_so_far'][0,[0,5]]=[5,6]
  p.before_segment(g,st,np.array([0]),fives)
  foul_fixtures.Rule3Tests().foul(st,0,True)
  p.after_fouls(g,st,np.array([0]),fives[:,0].copy(),fives[:,1].copy())
  self.assertEqual(st.tfouls[0,0],1);self.assertEqual(len(p.technical_events),1)
  self.assertIn(0,p._legal_plan(g,st,0,0,fives[0,0]))
  self.assertNotIn(5,p._legal_plan(g,st,0,0,np.array([5,1,2,3,4])))

 def test_publication_capture_delegates_selected_policy(self):
  g,st,fives,p=self.fixture();p.reg_templates=[[]]
  wrapper=lineup_forecast.LegalCapture(p)
  wrapper.begin(g,1,np.ones((1,g.n),bool),42);p.reg_templates=[[]]
  result=wrapper.before_segment(g,st,np.array([0]),fives)
  np.testing.assert_array_equal(result,p.current)
  self.assertEqual(wrapper.checked,2);self.assertTrue((wrapper.opening>=0).all())

 def test_publication_restores_policy_on_failure(self):
  class FailEngine:
   runtime={'foul_policy':'nba-rule3-v1'}
   rotation_policy=object()
   def simulate(self,*args):raise ValueError('intentional')
  eng=FailEngine();previous=eng.rotation_policy
  with self.assertRaisesRegex(ValueError,'intentional'):lineup_forecast.simulate(eng,None,1,42)
  self.assertIs(eng.rotation_policy,previous)

if __name__=='__main__':unittest.main()
