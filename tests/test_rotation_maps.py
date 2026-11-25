import unittest
import numpy as np
from scripts.world_detail import WorldDetail
from scripts.rotation_maps import summarise,validate
from tests.test_foul_out import Rule3Tests

class RotationTests(unittest.TestCase):
 def capture(self):
  g,st,lineups,_=Rule3Tests().fixture(2);detail=WorldDetail();detail.begin(g,st);active=np.arange(2)
  after=lineups.copy();after[0,0,0]=5
  for period in range(1,6):
   st.period[:]=period;st.clock[:]=720 if period<5 else 300
   detail.before_segment(g,st,active,lineups)
   st.clock[:]=0
   record={'lineups':lineups,'offense':after[:,0],'defense':after[:,1],'off':np.zeros(2,int),'secs':np.array([30.,720. if period<5 else 300.]),'shot':np.array([],int),'res':np.zeros(2,int),'zone':np.zeros(2,int),'actor':np.zeros(2,int)}
   detail.after_segment(g,st,active,record)
  st.done[:]=True;detail.finish(g,st)
  return {'rotation_presence':detail.rotation_presence,'side':g.side,'available':np.ones((2,g.n),bool),'player_ids':np.asarray(g.ids)}
 def test_exact_boundary_repaired_gap_ot_excluded_and_weighted(self):
  raw=self.capture();self.assertTrue(validate(raw));p=raw['rotation_presence']
  self.assertTrue((p[0,0]==0).all());self.assertTrue((p[0,5]==1).all());self.assertTrue((p[1,0]==1).all())
  s=summarise(raw,np.array([1,3],np.int64));pid=str(raw['player_ids'][0]);self.assertEqual(s['worlds'],2);self.assertEqual(s['probability_mass'],4)
  self.assertEqual(s['players'][pid]['probability'],[.75]*48);self.assertEqual(s['players'][pid]['on_court_mass'],[3]*48)
 def test_missing_is_legacy_and_invalid_fives_unavailable_fail(self):
  self.assertIsNone(summarise({}));raw=self.capture();raw['available'][0,5]=False
  with self.assertRaisesRegex(ValueError,'unavailable'):validate(raw)
  raw=self.capture();raw['rotation_presence'][0,0,0]=1
  with self.assertRaisesRegex(ValueError,'five'):validate(raw)
 def test_incomplete_clock_capture_fails(self):
  g,st,L,_=Rule3Tests().fixture(1);d=WorldDetail();d.begin(g,st);st.done[:]=True
  with self.assertRaisesRegex(ValueError,'missing regulation'):d.finish(g,st)
 def test_fractional_boundary_uses_canonical_event_clock_without_duplicate(self):
  g,st,L,_=Rule3Tests().fixture(1);d=WorldDetail();d.begin(g,st);active=np.array([0]);after=L.copy();after[0,0,0]=5
  st.clock[:]=690.3;d.before_segment(g,st,active,L);st.clock[:]=690.
  record={'lineups':L,'offense':after[:,0],'defense':after[:,1],'off':np.array([0]),'secs':np.array([.3]),'shot':np.array([],int),'res':np.array([0]),'zone':np.array([0]),'actor':np.array([0])}
  d.after_segment(g,st,active,record);self.assertFalse(d.rotation_seen[0,0])
  d.before_segment(g,st,active,after);st.clock[:]=630.;record.update(lineups=after,secs=np.array([60.]))
  d.after_segment(g,st,active,record);self.assertEqual(d.rotation_presence[0,0,0],0);self.assertEqual(d.rotation_presence[0,5,0],1)

if __name__=='__main__':unittest.main()
