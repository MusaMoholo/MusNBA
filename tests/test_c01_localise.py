"""Independent uncertainty/accounting checks for connected localisation."""
import unittest
from pathlib import Path
import tempfile
import numpy as np
import pandas as pd
from analysis import c01_localise as local
from analysis.c01_core import ContractError


class LocalisationUncertaintyTests(unittest.TestCase):
    def test_completed_derived_tables_resume_identically_but_cannot_be_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'evidence.parquet';frame=pd.DataFrame({'value':[1.]})
            local.create_table(path,frame);original=path.read_bytes()
            local.create_table(path,frame)
            self.assertEqual(path.read_bytes(),original)
            with self.assertRaises(ContractError):local.create_table(path,pd.DataFrame({'value':[2.]}))
            self.assertEqual(path.read_bytes(),original)

    def test_independent_start_history_uses_only_preceding_events(self):
        ids=[str(i) for i in range(11,16)]+[str(i) for i in range(21,26)]
        common={**{f'off_{j}':str(10+j) for j in range(1,6)},**{f'def_{j}':str(20+j) for j in range(1,6)}}
        rows=[{**common,'duration':10.,'actor':'11','end_type':'shot','made':True,'points':3,'fouler':'21','assister':'12'},
              {**common,'duration':5.,'actor':'21','end_type':'turnover','made':False,'points':0,'fouler':None,'assister':None}]
        history=local.start_histories(pd.DataFrame(rows),ids)
        self.assertTrue(all((v[0]==0).all() for v in history.values()))
        np.testing.assert_array_equal(history['sec_so_far'][1],np.full(10,10.))
        self.assertEqual(history['uses_so_far'][1,0],1);self.assertEqual(history['fga_so_far'][1,0],1)
        self.assertEqual(history['made_so_far'][1,0],1);self.assertEqual(history['pts_so_far'][1,0],3)
        self.assertEqual(history['pf_so_far'][1,5],1);self.assertEqual(history['ast_so_far'][1,1],1)
        self.assertEqual(history['uses_so_far'][1,5],0)

    def test_location_reference_conditions_on_known_zone_not_all21_bands(self):
        rows=[]
        for i,zone in enumerate(('rim','corner3')):
            rows.append({'game_id':'1','actor':'11','end_type':'shot','heave':False,'zone':zone,'x':25.,'y':1.,'start_clock':100.,'period':1,
                         **{f'off_{j}':str(10+j) for j in range(1,6)}})
        r=local.location_reference(pd.DataFrame(rows))
        self.assertEqual(r[('1','zone','rim')][0],1)
        self.assertAlmostEqual(r[('1','zone','rim')][1],np.log(4))
        self.assertAlmostEqual(r[('1','zone','corner3')][1],np.log(3))
        self.assertNotAlmostEqual(r[('1','all','all')][1],2*np.log(21))

    def test_equal_ratios_have_exact_zero_game_and_calendar_intervals(self):
        frame=pd.DataFrame({'game_id':['1','1','2','2'],'date_et':['2026-01-01']*2+['2026-01-10']*2,
                            'a':[1.,3.,2.,6.],'n':[2.,6.,4.,12.],'b':[3.,9.,1.,3.],'m':[6.,18.,2.,6.]})
        r=local.ratio_change(frame,'a','n','b','m')
        self.assertEqual(r['mean'],0);self.assertEqual(r['ci95_game'],[0,0]);self.assertEqual(r['ci95_calendar_week'],[0,0])

    def test_response_coefficient_and_paired_uncertainty_match_known_equations(self):
        rng=np.random.default_rng(6);n=240
        frame=pd.DataFrame({'game_id':np.repeat([str(i) for i in range(n//2)],2),'date_et':np.repeat(pd.date_range('2026-01-01',periods=n//2).strftime('%Y-%m-%d'),2),
                            'off_rating':rng.normal(size=n),'opp_def_rating':rng.normal(size=n),'home_flag':np.tile([1.,0.],n//2),'rest':rng.integers(1,5,n)})
        frame['actual']=100+2*frame.off_rating+.8*frame.opp_def_rating+frame.home_flag-.3*frame.rest
        frame['predicted']=100+2*frame.off_rating+.4*frame.opp_def_rating+frame.home_flag-.3*frame.rest
        r=local.regression(frame,'actual','predicted')
        self.assertAlmostEqual(r['observed_opponent_coefficient'],.8,places=10)
        self.assertAlmostEqual(r['predicted_opponent_coefficient'],.4,places=10)
        np.testing.assert_allclose(r['ci95_game']['difference'],[-.4,-.4],atol=1e-9)


if __name__=='__main__':unittest.main()
