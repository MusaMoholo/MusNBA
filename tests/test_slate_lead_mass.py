import tempfile
import unittest
from pathlib import Path
import numpy as np
from scripts import views

class SlateLeadMass(unittest.TestCase):
    def setUp(self):views._LINES_CACHE.clear()

    def lines(self,n=2):
        lines=np.zeros((n,2,len(views.WORLD_STATS)),np.uint8)
        lines[0,0,views.WORLD_STATS.index('pts')]=10
        lines[1:,1,views.WORLD_STATS.index('pts')]=10
        return lines

    def test_early_raw_cache_reloads_after_season_coupling_appears(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            np.savez(root/'engine_players.npz',g__lines=self.lines(),g__ids=np.array(['a','b']))
            self.assertEqual(views.lead_chances(root,['g'],'pts',['a','b']),{'a':.5,'b':.5})
            np.savez(root/'season_player_indices.npz',g=np.array([0,0,1,1]),weights=np.array([1,2,3,4]))
            self.assertEqual(views.lead_chances(root,['g'],'pts',['a','b']),{'a':.3,'b':.7})

    def test_single_game_uses_original_branch_mass_without_coupling(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            np.savez(root/'engine_players.npz',g__lines=self.lines(),g__ids=np.array(['a','b']),g__weights=np.array([1,3]))
            self.assertEqual(views.lead_chances(root,['g'],'pts',['a','b']),{'a':.25,'b':.75})

    def test_different_layouts_and_masses_stay_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            np.savez(root/'engine_players.npz',g__lines=self.lines(),g__ids=np.array(['a','b']),g__weights=np.array([1,3]),
                     h__lines=self.lines(),h__ids=np.array(['c','d']),h__weights=np.array([3,1]))
            self.assertEqual(views.lead_chances(root,['g','h'],'pts',['a']),{})
            np.savez(root/'engine_players.npz',g__lines=self.lines(),g__ids=np.array(['a','b']),
                     h__lines=self.lines(3),h__ids=np.array(['c','d']))
            self.assertEqual(views.lead_chances(root,['g','h'],'pts',['a']),{})

if __name__=='__main__':unittest.main()
