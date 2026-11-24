import unittest
import numpy as np
from scripts import competition_rules as r

class Rules(unittest.TestCase):
    def test_recursive_partial_tie(self):
        # On the restart, the two-team criterion differs from the first multiway criterion.
        def criteria(t):return [lambda i: {0:2,1:1,2:1}[i]] if len(t)==3 else [lambda i: {1:0,2:1}[i]]
        self.assertEqual(r.break_tie([0,1,2],criteria,[.1,.2,.3]),[0,2,1])
    def test_runner_up_and_regulation_ties(self):
        wins=np.array([3,3,1]);h=np.zeros((3,3),int);n=h.copy();h[0,1]=1;n[0,1]=n[1,0]=1
        self.assertEqual(r.cup_order([0,1,2],wins,h,n,np.array([-5,99,0]),np.ones(3),np.ones(3),[.1,.2,.3]),[0,1,2])
    def test_fillers(self):
        pairs=np.zeros((30,30),int)
        for alt in (False,True):
            slates=r.fillers([list(range(11)),list(range(15,26))],pairs,alt)
            flat=[x for row in slates for x in row]
            self.assertEqual(len(flat),22);self.assertEqual(len({frozenset(x) for x in flat}),22)
            self.assertEqual(sum((h<15)!=(a<15) for h,a in flat),2)
            for t in list(range(11))+list(range(15,26)):
                self.assertEqual(sum(h==t for h,a in flat),1);self.assertEqual(sum(a==t for h,a in flat),1)
            for row in slates:self.assertEqual(len({t for p in row for t in p}),22)
    def test_official_standings_h2h_and_eligible(self):
        wins=np.arange(30,dtype=int);wins[0]=wins[1]=50
        conf=['East']*15+['West']*15;div=[i//5 for i in range(30)]
        n=np.ones((30,30),int)*2;h=n//2;h[0,1]=0;h[1,0]=2
        rank,d=r.standings(wins,h,n,np.arange(30),conf,div,np.arange(30))
        self.assertEqual(rank[1],1);self.assertEqual(rank[0],2);self.assertEqual(len(d),6)
        self.assertEqual(sorted(rank[:15]),list(range(1,16)))

class OfficialTieCases(unittest.TestCase):
    def fixture(self):
        wins=np.arange(30,dtype=int)
        conf=['East']*15+['West']*15;division=[i//5 for i in range(30)]
        n=np.full((30,30),2,int);h=np.ones((30,30),int);np.fill_diagonal(n,0);np.fill_diagonal(h,0)
        return wins,conf,division,n,h

    def test_two_way_head_to_head_precedes_division_winner(self):
        wins,c,d,n,h=self.fixture();wins[0]=wins[5]=50;wins[6]=60
        h[5,0]=2;h[0,5]=0
        rank,division=r.standings(wins,h,n,np.zeros(30,int),c,d,np.arange(30))
        self.assertIn(0,division);self.assertNotIn(5,division);self.assertLess(rank[5],rank[0])

    def test_multiway_division_winner_precedes_head_to_head(self):
        wins,c,d,n,h=self.fixture();wins[[0,5,10]]=50;wins[[6,11]]=60
        h[0,5]=h[0,10]=0;h[5,0]=h[10,0]=2
        rank,division=r.standings(wins,h,n,np.zeros(30,int),c,d,np.arange(30))
        self.assertIn(0,division);self.assertLess(rank[0],rank[5]);self.assertLess(rank[0],rank[10])

    def test_eligible_includes_all_tied_for_tenth(self):
        wins,c,d,n,h=self.fixture();wins[:15]=[10,10,12,11,11,11,11,11,11,8,8,6,5,4,3]
        h[0,10]=2;h[10,0]=0;h[0,11]=0;h[11,0]=2
        h[1,9]=2;h[9,1]=0;h[1,11]=0;h[11,1]=2
        diff=np.zeros(30,int);diff[0]=100
        rank,division=r.standings(wins,h,n,diff,c,d,np.arange(30))
        # Equal conference/division/H2H and eligible records only when BOTH tied10th teams count;
        # point differential then awards0. Dropping team10 would incorrectly award1 earlier.
        self.assertNotIn(0,division);self.assertNotIn(1,division);self.assertLess(rank[0],rank[1])

class Compatibility(unittest.TestCase):
    def test_movers_require_same_calendar_schema(self):
        from pathlib import Path
        from unittest.mock import patch
        from scripts import views
        snaps={'2026-11-23':{'path':Path('/synthetic'),'meta':{'kind':'prospective'}}}
        current={'as_of':'2026-11-24','model':'team-pathway-v1','competition_schema':r.SCHEMA,'teams':{}}
        old={'as_of':'2026-11-23','model':'team-pathway-v1','teams':{}}
        with patch.object(views,'read_json',return_value=old):
            self.assertIsNone(views.season_movers(snaps,'2026-11-24',current,[])['from'])
        old['competition_schema']=r.SCHEMA
        with patch.object(views,'read_json',return_value=old):
            self.assertEqual(views.season_movers(snaps,'2026-11-24',current,[])['from'],'2026-11-23')

    def test_canonical_flags_exclude_final_from_regular_totals(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from scripts import master_fixtures,season_stats
        from basketball_common import MASTER_CSV
        self.assertEqual(master_fixtures.competition_flags('NBA Cup - Group Play')['regular_season'],1)
        self.assertEqual(master_fixtures.competition_flags('NBA Cup - Semifinal')['regular_season'],1)
        self.assertEqual(master_fixtures.competition_flags('NBA Cup - Championship')['regular_season'],0)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'master.csv';path.touch()
            with patch('basketball_common.MASTER_CSV',path),patch.object(master_fixtures,'load',return_value=[{'game_id':'final','regular_season':0}]):
                self.assertEqual(season_stats.regular_rows([{'game_id':'regular'},{'game_id':'final'}]),[{'game_id':'regular'}])

if __name__=='__main__':unittest.main()
