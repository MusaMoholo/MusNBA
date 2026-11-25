import unittest
import numpy as np
from analysis import b2_runner
from analysis.b2_paths import HistoricalPaths


class HistoricalPathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        b2_runner.init_worker()

    def model(self,frame=None):
        s=b2_runner.STATE;day='2023-11-20';year=2024
        return HistoricalPaths(s['frames'][year] if frame is None else frame,s['calendar'][str(year)],day,
            s['starts']['origins'][day]['reference'],s['teams'],s['periods'][year],s['previous'][year],
            8,19,{'scale':1.,'n_cap':20})

    def test_future_results_and_unresolved_cup_assignments_cannot_change_paths(self):
        base=self.model();expected,_=base.capture()
        frame=b2_runner.STATE['frames'][2024].copy()
        future=frame.date.ge('2023-11-20')
        frame.loc[future,['pts','opp_pts']]=99999
        cup=frame.date.between('2023-12-04','2023-12-09')
        frame.loc[cup,'team']='27';frame.loc[cup,'opp']='29'
        actual,_=self.model(frame).capture()
        for key in expected:np.testing.assert_array_equal(actual[key],expected[key])

    def test_historical_neutral_bracket_and_source_reconciliation(self):
        model=self.model();_,audit=model.capture()
        self.assertEqual(audit['games_per_team'],82)
        self.assertEqual(audit['wins_per_world'],1230)
        sf=[e for e in model.events if e['stage']=='cup_sf']
        self.assertEqual(len(sf),2)
        self.assertTrue(all(e['neutral'] and e['date']=='2023-12-07' for e in sf))
        final=[e for e in model.events if e['stage']=='cup_final']
        self.assertEqual(len(final),1)
        self.assertFalse(final[0]['regular'])
        self.assertEqual(model.prep['past']['401584717']['reg'],[113,106])


if __name__=='__main__':unittest.main()
