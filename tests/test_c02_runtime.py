from types import SimpleNamespace
import unittest
from unittest.mock import Mock
import numpy as np
from analysis.c02_runtime import attached,validate_worlds
from analysis.c02_data import COLS
from analysis.c02_features import PREFIX
from analysis.c01_core import ContractError

class RuntimeTests(unittest.TestCase):
    def setup_engine(self):
        old=Mock(return_value=np.array([.2,.8]));e=SimpleNamespace(_context=Mock(),_five=Mock(),_actor=Mock(),m=SimpleNamespace(predict=old,nodes={'who':{'temperature':1.189}}))
        p=SimpleNamespace(meta={'training_through':'2025-12-31'},predict=Mock(return_value=np.array([[.125]*8])))
        return e,old,p,SimpleNamespace(day='2026-01-01')
    def test_other_nodes_unchanged_and_restore_after_deliberate_fault(self):
        e,old,p,g=self.setup_engine();original=e._context
        with self.assertRaisesRegex(ContractError,'missing causal'):
            with attached(e,g,Mock(),p):
                np.testing.assert_array_equal(e.m.predict('shot_result',{},1),[.2,.8]);e.m.predict('who',{},5)
        self.assertIs(e.m.predict,old);self.assertIs(e._context,original);self.assertEqual(e.m.nodes['who']['temperature'],1.189)
    def test_future_fit_rejected_before_runtime(self):
        e,_,p,g=self.setup_engine();g.day='2025-12-31'
        with self.assertRaisesRegex(ContractError,'future'):
            with attached(e,g,Mock(),p):pass
    def test_what_probability_boundary_rejects_corrupt_model(self):
        e,_,p,g=self.setup_engine();p.predict.return_value=np.array([[.2]*8])
        cols={PREFIX+k:np.zeros(1) for k in COLS['what']};cols['shot_time']=np.zeros(1)
        with attached(e,g,Mock(),p):
            with self.assertRaisesRegex(ContractError,'probability'):e.m.predict('what',cols,1)
    def test_target_fields_never_enter_predictor(self):
        e,_,p,g=self.setup_engine();cols={PREFIX+k:np.zeros(1) for k in COLS['what']};cols['shot_time']=np.zeros(1);cols['point_target']=999
        with attached(e,g,Mock(),p):e.m.predict('what',cols,1)
        self.assertEqual(set(p.predict.call_args.args[1]),set(COLS['what']))
    def test_independent_world_accounting_and_deliberate_point_corruption(self):
        g=SimpleNamespace(side=np.repeat([0,1],5));box={k:np.zeros((1,10,5),int) for k in ('pts','fgm','fg3m','ftm','fga','fg3a','fta')}
        minutes=np.zeros((1,10,5));minutes[:,:,:4]=12
        st=SimpleNamespace(done=np.array([True]),score=np.zeros((1,2)),pts=np.zeros((1,2,5),int),box=box,minutes=minutes,period=np.array([4]))
        self.assertTrue(validate_worlds(g,st));box['pts'][0,0,0]=2
        with self.assertRaisesRegex(ContractError,'scoring identity'):validate_worlds(g,st)

if __name__=='__main__':unittest.main()
