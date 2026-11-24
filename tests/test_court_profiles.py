import unittest
import numpy as np
import pandas as pd
from scripts import court_profiles as p,court_zones as z


class CourtProfilesTest(unittest.TestCase):
    def data(self):
        rows=[];roster=[]
        for game,day in [('a','2023-01-01'),('b','2023-01-01'),('c','2023-01-02')]:
            for i in range(10):roster.append(dict(game_id=game,date_et=day,season=2023,player=i+1))
            r=dict(game_id=game,date_et=day,season=2023,actor=1,end_type='shot',value=2,x=25.,y=2.,heave=False,made=1,game_ok=True)
            r.update({f'{side}_{i+1}':j for side,ids in [('off',range(1,6)),('def',range(6,11))] for i,j in enumerate(ids)})
            rows.append(r)
        return pd.DataFrame(rows),pd.DataFrame(roster)

    def test_day_boundary_and_future_outcomes(self):
        s,r=self.data();a,audit=p.build(s,r)
        # Simultaneous games cannot teach one another; next day observes both.
        np.testing.assert_array_equal(a[a.game_id=='a'][p.COLS],a[a.game_id=='b'][p.COLS])
        self.assertGreater(a[(a.game_id=='c') & (a.player==1)].court_fg_0.iloc[0],.5)
        s.loc[s.game_id=='c',['made','x','y']]=[0,47,2]
        b,_=p.build(s,r)
        np.testing.assert_array_equal(a[p.COLS],b[p.COLS])
        self.assertEqual(audit['covered_attempts'],3);self.assertEqual(audit['defender_attempts'],15)

    def test_illegal_lineup_and_unknown_are_explicit(self):
        s,r=self.data();s.loc[0,'def_5']=s.loc[0,'off_1'];s.loc[1,'x']=np.nan
        _,audit=p.build(s,r)
        self.assertEqual(audit['covered_uses'],2)
        self.assertEqual(audit['uncovered_uses'],1)
        self.assertEqual(audit['unknown_attempts'],1)

    def test_zero_actor_uses_age_exposure_and_rate_units(self):
        s,r=self.data()
        s.loc[s.game_id=='b','date_et']='2023-01-02'
        r.loc[r.game_id=='b','date_et']='2023-01-02'
        s.loc[s.game_id=='c','date_et']='2023-01-03'
        r.loc[r.game_id=='c','date_et']='2023-01-03'
        s.loc[s.game_id=='b','actor']=2
        f,_=p.build(s,r)
        row=f[(f.game_id=='c') & (f.player==1)].iloc[0]
        self.assertAlmostEqual(row.court_uses_eff,2**(-1/15),places=6)
        self.assertAlmostEqual(row.court_shots_eff,2**(-1/40),places=6)
        self.assertAlmostEqual(row[[f'court_rate_{i}' for i in range(22)]].sum(),1.,places=6)
        cold=f[(f.game_id=='a') & (f.player==1)].iloc[0]
        self.assertAlmostEqual(cold[[f'court_rate_{i}' for i in range(22)]].sum(),.5,places=6)

    def test_native_geometry_and_value_conflict(self):
        np.testing.assert_array_equal(z.derive([25,3,47,25,np.nan,25],[2,3,3,60,2,2],[2,3,3,3,2,3]),[0,13,14,19,20,21])
        self.assertEqual(z.derive([25],[2],[1])[0],-1)

    def test_layout_conserves_value_and_coarse_parent(self):
        for distance,classes in [(False,27),(True,62)]:
            spec=z.layout(distance);coarse,cell,mask=z.decoder(spec)
            self.assertEqual(len(cell),classes)
            np.testing.assert_array_equal(mask.sum(axis=0),1)
            np.testing.assert_array_equal(z.VALUES[cell],np.where(coarse>=3,3,2))


class CrossSourceJoinTest(unittest.TestCase):
    def test_ambiguous_clocks_are_never_resolved_with_outcomes(self):
        from analysis.c2_source_audit import unique_clock_pairs
        nba=pd.DataFrame({'player':['1','1','2'],'period':[1,1,1],'clock':[100.,101.,200.]})
        espn=pd.DataFrame({'player':['1','1','2'],'period':[1,1,1],'clock':[100.,101.,201.]})
        pairs,audit=unique_clock_pairs(nba,espn)
        self.assertEqual(pairs,[(2,2)])
        self.assertEqual(audit,{'ambiguous_native':2,'ambiguous_espn':2})

    def test_player_and_period_identity_are_required(self):
        from analysis.c2_source_audit import unique_clock_pairs
        a=pd.DataFrame({'player':['1','2',None],'period':[1,2,1],'clock':[100.,100.,100.]})
        b=pd.DataFrame({'player':['2','1'],'period':[1,2],'clock':[100.,100.]})
        self.assertEqual(unique_clock_pairs(a,b)[0],[])

if __name__=='__main__':unittest.main()
