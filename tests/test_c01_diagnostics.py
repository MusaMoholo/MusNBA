"""Synthetic fault boundaries for C01 observed contexts, replay and input oracles."""
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock,patch

import numpy as np
import pandas as pd

from analysis import c01_contexts as c,c01_diagnostics as d
from analysis.c01_core import ContractError


class SourceAndProbabilityTests(unittest.TestCase):
    def test_source_predicate_prevents_reserved_rows_and_unknown_loaders(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"segments.parquet"
            pd.DataFrame({"game_id":["1","2"],"date_et":["2025-01-01","2026-02-01"],"points":[2,999]}).to_parquet(path,index=False)
            boundary=c.SourceBoundary(["1"],"panel")
            with boundary.installed():
                result=pd.read_parquet(path,columns=["points"])
            self.assertEqual(result.points.tolist(),[2])
            with c.SourceBoundary(["1"],"training").installed():
                result=pd.read_parquet(path)
            self.assertEqual(result.game_id.tolist(),["1"])
            with self.assertRaisesRegex(ContractError,"unapproved"):
                boundary.read(Path(directory)/"protected.parquet")
            with patch.object(c,"ORIGINAL_PARQUET",return_value=pd.DataFrame({"game_id":["2"],"points":[999]})):
                with self.assertRaisesRegex(ContractError,"crossed"):
                    boundary.read(path)

    def test_filter_intersection_preserves_both_sides_of_dnf(self):
        existing=[[('a','==',1)],[('a','==',2)]]
        result=c.and_filters(existing,[('game_id','in',['1'])])
        self.assertEqual(result,[[('a','==',1),('game_id','in',['1'])],[('a','==',2),('game_id','in',['1'])]])

    def test_candidate_probability_reference_and_group_guard(self):
        probs=np.array([.1,.2,.3,.15,.25]*2)
        booster=Mock();booster.predict.return_value=np.log(probs)
        e=SimpleNamespace(m=SimpleNamespace(nodes={"who":{"columns":["x"],"temperature":1.}},boosters={"who":booster}))
        data={"X":pd.DataFrame({"x":np.zeros(10)}),"y":np.array([0,0,1,0,0]*2),"group":np.repeat([1,2],5),"kind":"candidate"}
        p,brier,uniform,pick=c.predict_node(e,"who",data)
        np.testing.assert_allclose(p,[.3,.3]);np.testing.assert_allclose(uniform,[np.log(5)]*2)
        self.assertAlmostEqual(brier[0],.1**2+.2**2+(.3-1)**2+.15**2+.25**2)
        data["group"]=np.array([1,2]*5)
        p,_,_,_=c.predict_node(e,"who",data)
        np.testing.assert_allclose(p,[.3,.3])
        data["y"]=np.zeros(10,int)
        with self.assertRaisesRegex(ContractError,"candidate label"):c.predict_node(e,"who",data)

    def test_duration_mixture_has_hand_checked_proper_score_in_seconds(self):
        crps,mae=c.duration_scores([[.25,.75]],[np.array([0.,0.]),np.array([2.,2.])],[1.])
        self.assertEqual(crps.tolist(),[.625]);self.assertEqual(mae.tolist(),[.5])
        with self.assertRaisesRegex(ContractError,"timing probabilities"):
            c.duration_scores([[.2,.2]],[np.array([0.]),np.array([2.])],[1.])


class ReplayAndOracleTests(unittest.TestCase):
    def test_stored_simulated_schedule_identity_and_deliberate_duplicate(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"capture.npz"
            minutes=np.zeros((1,10,5));minutes[:,:,:4]=12
            fives=np.tile(np.arange(10).reshape(1,2,5),(4,1,1))
            data={"trace_phase":np.zeros(4),"trace_period":np.arange(1,5),"trace_world":np.zeros(4),"trace_clock":np.full(4,720.),
                  "trace_lineups":fives,"final_period":np.array([4]),"player_ids":np.array([str(i+1) for i in range(10)]),"side":np.repeat([0,1],5),"minutes":minutes}
            np.savez(path,**data)
            tables,combo,error=c.stored_schedules(path)
            self.assertEqual(tables.shape,(2,2880,5));self.assertEqual(combo.tolist(),[[0,1]]);self.assertEqual(error,0)
            data["trace_lineups"][0,0,0]=1;np.savez(path,**data)
            with self.assertRaisesRegex(ContractError,"illegal stored"):c.stored_schedules(path)

    def test_zone_and_minute_accounting_faults_are_detected(self):
        g=SimpleNamespace(side=np.repeat([0,1],5))
        box={key:np.zeros((1,10,5),int) for key in ('fga','fg3m','ftm')}
        box['fga'][0,0,0]=1
        minutes=np.zeros((1,10,5));minutes[:,:,:4]=12
        pts=np.zeros((1,2,5),int);pts[0,0,0]=2
        st=SimpleNamespace(W=1,done=np.array([True]),period=np.array([4]),clock=np.array([720.]),minutes=minutes,pts=pts,box=box,ingame={"pf_so_far":np.zeros((1,10))})
        observer=c.ZoneObserver();observer.begin(g,st)
        observer.before_segment(g,st,np.array([0]),np.arange(10).reshape(1,2,5))
        observer.after_segment(g,st,np.array([0]),{"shot":np.array([0]),"off":np.array([0]),"zone":np.array([0]),"res":np.array([1])})
        observer.finish(g,st)
        st.minutes[0,0,0]+=1
        with self.assertRaisesRegex(ContractError,"minute identity"):observer.finish(g,st)
        st.minutes[0,0,0]-=1;observer.makes[0,0,0]=0
        with self.assertRaisesRegex(ContractError,"scoring identity"):observer.finish(g,st)

    def test_opportunity_oracle_keeps_integer_bounds_and_rejects_future(self):
        fit={"players":{},"league":[.5,.35,.8],"latest_input":"2025-12-31"}
        a,made=d.opportunity_draws(fit,"1",["11"],[[2,3,4]],"2026-01-01")
        self.assertTrue((made<=[[[2,3,4]]]).all());self.assertTrue((made>=0).all())
        np.testing.assert_array_equal(a['pts'],2*made[:,:,0]+3*made[:,:,1]+made[:,:,2])
        again,_=d.opportunity_draws(fit,"1",["11"],[[2,3,4]],"2026-01-01")
        np.testing.assert_array_equal(a['pts'],again['pts'])
        with self.assertRaisesRegex(ContractError,"future"):
            d.opportunity_draws({**fit,"latest_input":"2026-01-01"},"1",["11"],[[2,3,4]],"2026-01-01")
        with self.assertRaisesRegex(ContractError,"attempts"):
            d.opportunity_draws(fit,"1",["11"],[[2,-3,4]],"2026-01-01")


if __name__=="__main__":unittest.main()
