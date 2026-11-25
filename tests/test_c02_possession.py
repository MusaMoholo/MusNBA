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
