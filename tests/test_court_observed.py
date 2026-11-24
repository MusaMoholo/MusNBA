import unittest
from unittest.mock import patch
import pandas as pd
import numpy as np
from scripts import court_observed

class ObservedWindowsTests(unittest.TestCase):
 def test_subjects_use_their_own_team_window_and_preserve_unknown_support(self):
  def shot(gid,day,offense,defense,actor='1',made=1,legal=True):
   return {'game_id':gid,'date_et':day,'season':2027,'offense':offense,'defense':defense,'actor':actor,'made':made,'x':25.,'y':1.,'value':2,'heave':None,'game_ok':legal,
    **{f'off_{i}':str(i) for i in range(1,6)},**{f'def_{i}':str(i+5) for i in range(1,6)}}
  rows=[shot('old','2026-10-01','h','a')]+[shot('h'+str(i),f'2026-11-{i:02d}','h','x') for i in range(1,11)]
  rows.extend([shot('a','2026-11-11','a','x',made=np.nan),shot('unknown','2026-11-12','x','h',legal=False)])
  frame=pd.DataFrame(rows)
  game={'date':'2026-11-23','home':{'id':'h'},'away':{'id':'a'}}
  with patch.object(court_observed,'rows',return_value=frame):result=court_observed.build(game,{'home':[{'id':'1'},{'id':'6'}],'away':[{'id':'9'}]})
  shots=result['shots'];subjects=result['subjects']
  self.assertNotIn('old',[shots[i]['game'] for i in subjects['t:home']['offense']])
  self.assertIn('old',[shots[i]['game'] for i in subjects['t:away']['defense']])
  self.assertNotIn('old',[shots[i]['game'] for i in subjects['p:1']['offense']])
  self.assertEqual(subjects['p:6']['unassigned_defense_attempts'],1)
  self.assertNotIn('unknown',[shots[i]['game'] for i in subjects['p:6']['defense']])
  self.assertIsNone(next(p for p in shots if p['game']=='a')['made'])
  self.assertTrue(all(p['flagged_heave'] is None for p in shots))
if __name__=='__main__':unittest.main()
