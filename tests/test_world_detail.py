import unittest
import numpy as np
from tests import test_foul_out as fixtures
from scripts.world_detail import WorldDetail
from scripts import shot_zones

class WorldDetailTests(unittest.TestCase):
 def fixture(self):
  g,st,lineups,_=fixtures.Rule3Tests().fixture(2)
  capture=WorldDetail([0],capture_rotations=False);capture.begin(g,st)
  active=np.array([0,1]);capture.before_segment(g,st,active,lineups)
  before=lineups.copy();offense=lineups[:,0].copy();defense=lineups[:,1].copy();offense[0,0]=5
  for team in [0,1]:st.minutes[0,before[0,team],0]+=10/60
  for five in [offense[0],defense[0]]:st.minutes[0,five,0]+=2/60
  for key,value in [('fga',1),('fgm',1),('pts',2)]:st.box[key][0,0,0]=value
  st.pts[0,0,0]=2;st.score[0,0]=2;st.clock[0]=708
  record={'shot':np.array([0]),'zone':np.array([0,0]),'res':np.array([1,0]),'band':np.array([0,0]),
   'actor':np.array([0,0]),'off':np.array([0,0]),'offense':offense,'defense':defense,
   'lineups':before,'secs':np.array([10.,0.])}
  capture.after_segment(g,st,active,record);st.done[:]=True
  return g,st,capture

 def test_post_foul_gap_uses_new_five_and_reconstructs_boxes(self):
  g,st,capture=self.fixture();capture.finish(g,st)
  event=capture.events[0][0]
  self.assertIn(g.ids[0],event['lineups'][0]);self.assertNotIn(g.ids[0],event['lineups_after'][0])
  seconds=dict(event['seconds']);self.assertAlmostEqual(seconds[g.ids[0]],10);self.assertAlmostEqual(seconds[g.ids[5]],2)
  self.assertTrue(capture.audit[0]['all_box_fields_exact'])
  raw={'minutes':st.minutes,'zone_fga':capture.attempts,'zone_fgm':capture.makes,
       **{'box_'+k:v for k,v in st.box.items()},'player_ids':np.asarray(g.ids),'side':g.side}
  self.assertTrue(shot_zones.validate(raw));encoded=shot_zones.encode(raw)
  self.assertEqual(encoded['zone_schema'],1)
  summary=shot_zones.summaries(raw,np.array([1,3],dtype=np.int64))
  self.assertEqual(summary['home']['attempts'][0],.25)
  self.assertEqual(summary['home']['attempt_probability'][0],.25)

 def test_wrong_zone_totals_and_wrong_rotation_clock_fail(self):
  g,st,capture=self.fixture();capture.attempts[0,0,0,0]+=1
  with self.assertRaisesRegex(ValueError,'totals differ'):capture.finish(g,st)
  g,st,capture=self.fixture();capture.events[0][0]['lineups_after'][0][0]=g.ids[0]
  with self.assertRaisesRegex(ValueError,'lineup/clock'):capture.finish(g,st)

 def test_missing_schema_stays_legacy_and_partial_fails(self):
  self.assertEqual(shot_zones.encode({}),{})
  with self.assertRaisesRegex(ValueError,'incomplete'):shot_zones.validate({'zone_fga':np.zeros(1)})

if __name__=='__main__':unittest.main()
