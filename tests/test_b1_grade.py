import unittest
import numpy as np
import pandas as pd
from analysis.b1_grade import team_metrics


def frames():
    control=pd.DataFrame({'game_id':[str(i) for i in range(200)],'real_home':100.,'real_away':100.,
                          'home_sim':102.,'away_sim':102.,'home_crps':6.,'away_crps':6.})
    candidate=control.assign(home_sim=101.,away_sim=101.,home_crps=5.8,away_crps=5.8)
    return control,candidate


class TeamScoreGateTests(unittest.TestCase):
    def test_bias_reduction_and_paired_benefit_are_separate_requirements(self):
        control,candidate=frames()
        result,primary=team_metrics(control,candidate)
        self.assertTrue(all(result['checks'].values()))
        self.assertTrue(result['control_bias_detectable'])
        self.assertAlmostEqual(primary['change'],-.2)
        # Removing average bias by making half the forecasts much worse cannot pass MAE/RMSE.
        candidate.loc[:99,['home_sim','away_sim']]=110.
        candidate.loc[100:,['home_sim','away_sim']]=90.
        result,_=team_metrics(control,candidate)
        self.assertTrue(result['checks']['owner_bias_target'])
        self.assertFalse(result['checks']['mae_not_increased'])
        self.assertFalse(result['checks']['rmse_not_increased'])

    def test_zero_baseline_bias_uses_fixed_tolerance_and_mismatched_truth_fails(self):
        control,candidate=frames()
        control[['home_sim','away_sim']]=100.
        candidate[['home_sim','away_sim']]=101.1
        result,_=team_metrics(control,candidate)
        self.assertFalse(result['control_bias_detectable'])
        self.assertFalse(result['checks']['owner_bias_target'])
        candidate.loc[0,'real_home']=101.
        with self.assertRaises(ValueError):team_metrics(control,candidate)

    def test_game_pairing_is_order_invariant(self):
        control,candidate=frames()
        a,_=team_metrics(control,candidate)
        b,_=team_metrics(control.sample(frac=1,random_state=1),candidate.sample(frac=1,random_state=2))
        self.assertEqual(a,b)


if __name__=='__main__':unittest.main()
