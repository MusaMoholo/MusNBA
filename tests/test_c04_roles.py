import unittest
import numpy as np
from analysis.c04_core import COLS,legal,inputs,prior,quantiles
from analysis.c01_core import ContractError
class RoleBoundaryTests(unittest.TestCase):
    def test_projection_constraint_and_optimality(self):
        np.testing.assert_allclose(legal(np.full(10,20.)),24)
        np.testing.assert_allclose(legal([100,0,0,0,0]),48)
        x=np.array([40,35,30,25,20,15,10,5.]);y=legal(x);self.assertAlmostEqual(y.sum(),240)
        free=(y>0)&(y<48);self.assertLess(np.ptp((y-x)[free]),1e-10)
        perm=[3,0,7,1,6,2,5,4];np.testing.assert_allclose(legal(x[perm]),y[perm])
    def test_meaningful_faults(self):
        for a in ([1]*4,[np.nan]*5):
            with self.assertRaises(ContractError):legal(a)
        for dates in (['2026-01-01'],['2026-01-02']):
            with self.assertRaises(ContractError):prior(dates,'2026-01-01')
        c={k:np.ones(3) for k in COLS}
        for label in ('reg','starter','target','current_minutes'):
            with self.assertRaises(ContractError):inputs({**c,label:np.ones(3)})
        with self.assertRaises(ContractError):quantiles(np.full((2,7),np.nan))

class CausalRoleTests(unittest.TestCase):
    def test_actual_feature_builder_ignores_current_and_future_outcomes(self):
        import pandas as pd
        from analysis.c04_data import features
        rows=[]
        for j,day in enumerate(['2025-01-01','2025-01-03','2025-01-05']):
            for i in range(6):rows.append(dict(game_id=str(j),player=str(i),team='t',date_et=day,season=2025,reg=40.,sec=2400.,starter=i<5))
        f=pd.DataFrame(rows);a=features(f);bad=f.copy();bad.loc[bad.date_et.ge('2025-01-03'),'reg']=10.;bad.loc[bad.date_et.ge('2025-01-03'),'starter']=False;b=features(bad)
        np.testing.assert_array_equal(a[a.date_et.eq('2025-01-03')][COLS],b[b.date_et.eq('2025-01-03')][COLS])
    def test_forecast_team_vector_has_exact_bounded_time(self):
        from analysis.c04_core import legal
        x=np.random.default_rng(4).normal(20,15,(100,11));a=legal(x)
        self.assertTrue(((a>=0)&(a<=48)).all());np.testing.assert_allclose(a.sum(1),240,atol=1e-9)

class InferenceAndResumeFaultTests(unittest.TestCase):
    def test_current_targets_cannot_change_forecast(self):
        import pandas as pd
        from analysis.c04_models import Predictor
        p=Predictor.__new__(Predictor);p.family='A';p.meta={'training_through':'2025-12-31'};p.model={'normalisation':{'mean':[0.]*len(COLS),'sd':[1.]*len(COLS)},'coef':[0.]*(len(COLS)+1)};p.noise=[[0.]*6,[1.,-1.,1.,-1.,0.,0.]]
        f=pd.DataFrame({k:np.zeros(6) for k in COLS});f['alloc']=40.;f['player']=[str(i) for i in range(6)];f['date_et']='2026-01-01';f['reg']=40.
        a=p.draw(f,40,np.random.default_rng(3));f['reg']=np.arange(6)*100;f['starter']=True
        np.testing.assert_array_equal(a,p.draw(f,40,np.random.default_rng(3)))
        f['date_et']='2025-12-31'
        with self.assertRaises(ContractError):p.draw(f,40,np.random.default_rng(3))
    def test_negative_screen_forbids_expansion(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from unittest.mock import patch
        from analysis import c04_rollout as r
        import json
        with TemporaryDirectory() as folder:
            root=Path(folder);(root/'data.json').write_text(json.dumps({'game_ids':['g']}));(root/'minute_screen.json').write_text(json.dumps({'shortlist':[]}))
            with patch.object(r.data,'WORK',root),patch.object(r.data,'verify',return_value={}),patch.object(r,'signature',return_value={}):
                with self.assertRaisesRegex(ContractError,'expansion forbidden'):r.run('short',1)
    def test_changed_role_fit_rejected(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        import json
        from basketball_common import sha256_file
        from analysis.c04_models import Predictor
        from analysis.c04_data import CONTRACT
        with TemporaryDirectory() as folder:
            root=Path(folder);(root/'A').mkdir();(root/'A/ridge.json').write_text('{}');(root/'A/fit.json').write_text(json.dumps({'contract_sha256':sha256_file(CONTRACT),'hashes':{'ridge.json':'0'*64}}))
            with self.assertRaises(ContractError):Predictor('A',root)

    def test_resume_refuses_modified_sources_and_game(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from unittest.mock import patch
        from analysis import c04_rollout as r
        import json
        with TemporaryDirectory() as folder:
            root=Path(folder);(root/'data.json').write_text(json.dumps({'game_ids':['g']}));(root/'minute_screen.json').write_text(json.dumps({'shortlist':[]}));(root/'wiring_plan.json').write_text(json.dumps({'sources':{'x':'old'}}))
            with patch.object(r.data,'WORK',root),patch.object(r.data,'verify',return_value={}),patch.object(r,'signature',return_value={'x':'new'}):
                with self.assertRaisesRegex(ContractError,'resume sources changed'):r.run('wiring',1)
            (root/'wiring_plan.json').write_text(json.dumps({'sources':{'x':'new'}}));game=root/'games/g';game.mkdir(parents=True);(game/'A.npz').write_bytes(b'modified');(game/'receipt.json').write_text(json.dumps({'arms':['native','bridge','A','B','C'],'hashes':{'A.npz':'0'*64}}))
            with patch.object(r.data,'WORK',root),patch.object(r.data,'verify',return_value={}),patch.object(r,'signature',return_value={'x':'new'}):
                with self.assertRaisesRegex(ContractError,'completed role game changed'):r.run('wiring',1)
