import unittest
import numpy as np
from analysis.c05_core import seconds,schedule,validate
from analysis.c04_core import legal
from analysis.c01_core import ContractError

class ExactDecoderTests(unittest.TestCase):
    def test_random_boundary_and_independent_count(self):
        rng=np.random.default_rng(9)
        for n in (5,6,9,12,15):
            for j in range(8):
                x=legal(rng.normal(20,30,n));tab=schedule(x,rng.random((n,2880)))
                self.assertTrue(all(len(set(row))==5 for row in tab))
                actual=np.array([(tab==i).sum()/60 for i in range(n)])
                self.assertLessEqual(np.max(abs(actual-x)),1/60+1e-9)
                np.testing.assert_array_equal(tab,schedule(x,rng.random((n,2880))) if n==5 else tab)
    def test_illegal_law_and_schedule_faults(self):
        for x in ([48]*4,[49,47,48,48,48],[np.nan]*5,[40]*6+[1]):
            with self.assertRaises(ContractError):seconds(x)
        x=np.full(8,30.);tab=schedule(x);tab[0,0]=tab[0,1]
        with self.assertRaisesRegex(ContractError,'five'):validate(tab,x)
        tab=schedule(x);tab[0,0]=next(i for i in range(8) if i not in tab[0])
        with self.assertRaisesRegex(ContractError,'target-to-schedule'):validate(tab,x)

class LawBoundaryTests(unittest.TestCase):
    def test_latent_constraints_and_current_future_fault(self):
        import pandas as pd
        from analysis.c05_models import latent,Predictor
        from analysis.c04_core import COLS
        x=latent(np.random.default_rng(1).normal(0,3,(100,11)))
        np.testing.assert_allclose(x.sum(1),240,atol=1e-8)
        self.assertTrue(((x>=0)&(x<=48)).all())
        f=pd.DataFrame({k:np.zeros(6) for k in COLS});f['alloc']=40.;f['player']=[str(i) for i in range(6)];f['date_et']='2026-01-01';f['reg']=40.
        mean={'normalisation':{'mean':[0.]*len(COLS),'sd':[1.]*len(COLS)},'coef':[0.]*(len(COLS)+1)}
        lib={'empirical':[[0.]*6,[2.,-2.,0.,0.,0.,0.]]}
        p=Predictor('A',model=mean,library=lib,weight=1)
        a=p.draw(f,100,np.random.default_rng(2));f['reg']=999;f['starter']=True
        np.testing.assert_array_equal(a,p.draw(f,100,np.random.default_rng(2)))
        f['date_et']='2025-12-31'
        with self.assertRaisesRegex(ContractError,'future'):p.draw(f,100,np.random.default_rng(2))

    def test_artifact_and_expansion_faults(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        import json
        from analysis.c05_models import Predictor,CONTRACT
        from basketball_common import sha256_file
        from analysis import c05_rollout as r
        import analysis.c05_models as m
        with TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'fit.json').write_text(json.dumps({'contract_sha256':sha256_file(CONTRACT),'code_sha256':sha256_file(Path(m.__file__)),'hashes':{'model.json':'0'*64}}));(root/'model.json').write_text('{}')
            with self.assertRaisesRegex(ContractError,'artifact'):Predictor('A',root)
            (root/'minute_screen.json').write_text(json.dumps({'shortlist':[]}))
            with patch.object(r.data,'WORK',root),patch.object(r.data,'verify',return_value={'game_ids':['g']}),patch.object(r,'signature',return_value={}):
                with self.assertRaisesRegex(ContractError,'expansion forbidden'):r.run('short',1)

    def test_legacy_band_includes_48_boundary(self):
        import pandas as pd
        from analysis.c05_models import make_library
        groups=[]
        for k in range(3):
            g=pd.DataFrame({'reg':[48.,48.,48.,48.,48.],'alloc':[48.]*5})
            groups.append((g,np.full(5,48.)))
        lib=make_library(groups)
        self.assertEqual(len(lib['sd']),14)
        self.assertEqual(lib['sd'][13],0)

    def test_resume_rejects_changed_source_and_completed_world(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        import json
        from analysis import c05_rollout as r
        with TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'minute_screen.json').write_text(json.dumps({'shortlist':[]}));(root/'wiring_plan.json').write_text(json.dumps({'sources':{'x':'old'}}))
            with patch.object(r.data,'WORK',root),patch.object(r.data,'verify',return_value={'game_ids':['g']}),patch.object(r,'signature',return_value={'x':'new'}):
                with self.assertRaisesRegex(ContractError,'resume sources changed'):r.run('wiring',1)
            (root/'wiring_plan.json').write_text(json.dumps({'sources':{'x':'new'}}));game=root/'games/g';game.mkdir(parents=True);(game/'A.npz').write_bytes(b'changed');(game/'receipt.json').write_text(json.dumps({'hashes':{'A.npz':'0'*64},'arms':['bridge','A','B','C']}))
            with patch.object(r.data,'WORK',root),patch.object(r.data,'verify',return_value={'game_ids':['g']}),patch.object(r,'signature',return_value={'x':'new'}):
                with self.assertRaisesRegex(ContractError,'completed role game changed'):r.run('wiring',1)
