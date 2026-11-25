"""Small independent numerical/cutoff/ordering tests for frozen C01 challengers."""
from copy import deepcopy
import unittest

import numpy as np
import pandas as pd

from analysis import c01_baselines as b, c01_metrics as m
from analysis.c01_core import ContractError


def games(n=320):
    rng=np.random.default_rng(44)
    rows=[]
    for i,day in enumerate(pd.date_range("2023-01-01",periods=n)):
        rows.append({"game_id":str(1000+i),"date_et":day.date().isoformat(),"home":str(i%4+1),"away":str((i+1)%4+1),
                     "home_points":float(100+rng.integers(0,20)),"away_points":float(98+rng.integers(0,20)),"home_poss":100,"away_poss":99})
    return pd.DataFrame(rows)


class BaselineBoundaryTests(unittest.TestCase):
    def test_team_priors_do_not_use_same_day_or_future_outcomes(self):
        original=games(12)
        first,state=b.team_features(original)
        changed=original.copy()
        changed.loc[10:,"home_points"]+=50
        later,_=b.team_features(changed)
        pd.testing.assert_frame_equal(first.loc[first.game_id.lt("1010"),list(b.XCOLS)].reset_index(drop=True),later.loc[later.game_id.lt("1010"),list(b.XCOLS)].reset_index(drop=True))
        same=original.iloc[0].copy();same.game_id="9999";same.home="3";same.away="4"
        extended=pd.concat([original,pd.DataFrame([same])],ignore_index=True)
        a,_=b.team_features(extended)
        reverse=pd.concat([pd.DataFrame([same]),original],ignore_index=True)
        z,_=b.team_features(reverse)
        pd.testing.assert_frame_equal(a.set_index("game_id").sort_index()[list(b.XCOLS)],z.set_index("game_id").sort_index()[list(b.XCOLS)])

    def test_ridge_matches_closed_form_normalised_one_predictor(self):
        n=220;x=np.linspace(-3,3,n)
        f=pd.DataFrame({key:np.zeros(n) for key in b.XCOLS})
        f["home_off"]=x;f["home_points"]=3+2*x;f["away_points"]=4-x;f["date_et"]="2025-01-01"
        fit=b.ridge_fit(f,"2025-01-02")
        coef=np.asarray(fit["coef"])
        np.testing.assert_allclose(coef[0],[3,4],atol=1e-12)
        np.testing.assert_allclose(coef[1],np.array([2,-1])*x.std()*n/(n+10),atol=1e-12)
        pred=b.ridge_predict(fit,f)
        np.testing.assert_allclose(pred[:,0],3+2*x*n/(n+10),atol=1e-12)
        with self.assertRaisesRegex(ContractError,"future"):
            b.ridge_fit(f.assign(date_et="2026-01-01"),b.CUTOFF)

    def test_player_prior_and_shared_minutes_reproduce_under_player_order(self):
        f=pd.DataFrame({"player":["11","12"],"date_et":["2025-12-01"]*2,"minutes":[20.,10.],
                        **{s:[3.,2.] for s in b.RATE_STATS}})
        fit=b.player_fit(f)
        minutes=np.column_stack([np.full(1000,30.),np.full(1000,10.)])
        a,missing=b.draw_players(fit,"1",["11","12"],minutes,"2026-01-01")
        z,_=b.draw_players(fit,"1",["12","11"],minutes[:,::-1],"2026-01-01")
        for key in a:np.testing.assert_array_equal(a[key],z[key][:,::-1])
        np.testing.assert_array_equal(a["pts"],2*a["fg2m"]+3*a["fg3m"]+a["ftm"])
        self.assertEqual(missing,[])
        _,missing=b.draw_players(fit,"1",["11","999"],minutes,"2026-01-01")
        self.assertEqual(missing,["999"])
        with self.assertRaisesRegex(ContractError,"future"):
            b.player_fit(f.assign(date_et="2026-01-01"))
        with self.assertRaisesRegex(ContractError,"future"):
            b.draw_players({**fit,"cutoff":"2026-01-01"},"1",["11","12"],minutes,"2026-01-01")

    def test_residual_state_fit_and_normalisation_cutoff_faults(self):
        f,state=b.team_features(games())
        fit=b.team_fit(f,state)
        x,_=b.draw_teams(fit,"1","1","2","2026-01-01",{"1":1,"2":2})
        self.assertEqual(x.shape,(1000,2))
        self.assertGreaterEqual(len(fit["residuals"]),100)
        for kind in ("top","fit","state","residual"):
            bad=deepcopy(fit)
            if kind=="top":bad["latest_input"]="2026-01-01"
            elif kind=="fit":bad["fit"]["latest_input"]="2026-01-01"
            elif kind=="state":bad["state"]["latest_input"]="2026-01-01"
            else:bad["residual_dates"][-1]="2026-01-01"
            with self.assertRaisesRegex(ContractError,"future"):
                b.draw_teams(bad,"1","1","2","2026-01-01",{"1":1,"2":2})
        with self.assertRaisesRegex(ContractError,"future"):
            b.team_features(games().assign(date_et="2026-01-01"))


class CommonScoringTests(unittest.TestCase):
    def test_joint_energy_agrees_with_full_pair_reference(self):
        x=np.array([[0,1],[2,3],[5,4]],float);y=np.array([2,2],float)
        self.assertAlmostEqual(m.energy(x,y,range(len(x))),m.energy_reference(x,y),places=12)
        self.assertEqual(m.energy(np.tile(y,(3,1)),y),0)
        self.assertGreater(m.energy(x+100,y),m.energy(x,y))

    def test_two_team_sides_are_distinct_and_pairing_detects_bad_truth(self):
        f=pd.DataFrame({"game_id":["1","1"],"entity":"team","stat":"points","player":"","side":["home","away"],
                        "date_et":"2026-01-01","truth":[100.,110.],"crps":[4.,5.]})
        p=m.paired_frame(f,f.sample(frac=1,random_state=1))
        self.assertEqual(p.change.tolist(),[0,0])
        bad=f.copy();bad.loc[0,"truth"]+=1
        with self.assertRaisesRegex(ContractError,"truth differ"):m.paired_frame(f,bad)
        with self.assertRaisesRegex(ContractError,"support/truth differ"):m.paired_frame(f,f.iloc[:1])
        with self.assertRaisesRegex(ContractError,"duplicate"):m.paired_frame(f,pd.concat([f,f]))

    def test_game_uncertainty_keeps_home_away_together(self):
        f=pd.DataFrame({"game_id":["1","1","2","2"],"date_et":["2026-01-01"]*2+["2026-01-10"]*2,"change":[1.,-1.,5.,-5.]})
        result=m.bootstrap_change(f)
        self.assertEqual(result["change"],0)
        self.assertEqual(result["ci95_game"],[0,0])
        self.assertEqual(result["ci95_calendar_week"],[0,0])

    def test_infinite_loss_is_explicit_and_not_silently_clipped(self):
        r=m.joint_record(np.tile([0.,1.],(1000,1)),[2.,0.])
        self.assertIsNone(r["win_log_loss"])
        self.assertTrue(r["win_log_loss_infinite"])
        self.assertTrue(np.isfinite(r["win_log_loss_smoothed"]))


if __name__=="__main__":unittest.main()
