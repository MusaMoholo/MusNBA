import unittest
import numpy as np
from analysis.c07_core import weights,crps,record,pool,team_mass,prior_dates
from analysis.c01_core import ContractError

class WeightedBoundaryTests(unittest.TestCase):
    def test_reference_pairwise_and_replication(self):
        x=np.array([0.,2.,7.]);w=np.array([.2,.5,.3]);y=3.
        ref=w@abs(x-y)-.5*np.sum(w[:,None]*w[None,:]*abs(x[:,None]-x[None,:]))
        self.assertAlmostEqual(crps(x,y,w),ref)
        np.testing.assert_allclose(crps(np.repeat(x,2),y,np.repeat(w/2,2)),ref)
        from analysis.c01_metrics import crps as old
        z=np.random.default_rng(1).normal(size=1000);self.assertAlmostEqual(crps(z,.4,np.full(1000,.001)),old(z,.4))
    def test_meaningful_mass_and_future_faults(self):
        for w in ([.4,.4],[-.1,1.1],[np.nan,1]):
            with self.assertRaises(ContractError):weights(w)
        with self.assertRaises(ContractError):prior_dates(['2026-01-22'])
        prior_dates(['2026-01-01','2026-01-21'])
        with self.assertRaises(ContractError):team_mass([1.1,.2])
    def test_pool_preserves_worlds_exact_mass_halves_and_count(self):
        m={str(i):{'player_ids':np.array(['p']),'side':np.array([0]),'pts':np.arange(1000)[:,None]+i*1000} for i in range(4)};p=np.array([.00001,.1,.2,.69999]);a=pool(m,p,'g')
        self.assertEqual(len(a['weight']),1000);self.assertAlmostEqual(a['weight'].sum(),1)
        np.testing.assert_allclose(np.bincount(a['member'],weights=a['weight']),p,atol=1e-12)
        np.testing.assert_array_equal(a['pts'][:,0],a['member_world']+1000*a['member'].astype(int))
        np.testing.assert_array_equal(a['pts'],pool(m,p,'g')['pts'])
        r=record(np.zeros(1000),0,np.full(1000,.001));self.assertEqual(r['crps'],0);self.assertEqual(r['covered80'],1)

    def test_independent_cdf_and_actual_world_fault(self):
        from analysis.c07_audit import reference_crps
        from analysis.c07_score import check_worlds
        x=np.array([0.,1.,4.]);w=np.array([.3,.2,.5]);self.assertAlmostEqual(crps(x,2.,w),reference_crps(x,2.,w))
        a={'player_ids':np.array([str(i) for i in range(10)]),'side':np.repeat([0,1],5),'final_period':np.full(1000,4),'minutes':np.full((1000,10),48.),'team':np.tile([1,0],(1000,1))}
        for key in ('pts','fgm','fga','fg3m','fg3a','ftm','fta','oreb','dreb','ast','pf','reb'):a[key]=np.zeros((1000,10),int)
        a['pts'][:,0]=1;a['ftm'][:,0]=1;a['fta'][:,0]=1;check_worlds(a)
        a['team'][0,0]=2
        with self.assertRaisesRegex(ContractError,'identity'):check_worlds(a)
    def test_future_gate_fit_rejected_before_features(self):
        from analysis.c07_model import Predictor
        from analysis import c07_members as m
        from unittest.mock import patch
        p=Predictor.__new__(Predictor);p.models={'fit_through':'2026-01-21'}
        with patch.dict(m.STATE,{'refs':{'g':{'date_et':'2026-01-21'}}}):
            with self.assertRaisesRegex(ContractError,'future'):p.masses('g','pool')

    def test_current_truth_cannot_enter_gate_features(self):
        import pandas as pd
        from analysis import c07_model as model,c07_members as m
        from unittest.mock import patch
        ids=[str(i) for i in range(10)];raw=pd.DataFrame({'game_id':'g','player':ids,'n_history':10.,'reg':48.});prior=pd.DataFrame({'game_id':'g','player':ids,'usage':.2,'points':5.});ref={'g':{'captured_player_ids':ids,'captured_sides':[0]*5+[1]*5}}
        with patch.dict(m.STATE,{'refs':ref}),patch.dict(m.old.STATE,{'rows':raw}),patch.dict(model.engine.STATE,{'causal':prior}),patch.object(m,'draws',return_value=(np.full((1000,10),48.),np.full((1000,10),48.))):
            a=model.feature_rows('g');raw['reg']=999;prior['points']=999
            b=model.feature_rows('g')
            for x,y in zip(a,b):np.testing.assert_array_equal(x,y)

    def test_artifact_resume_and_empty_shortlist_faults(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from unittest.mock import patch
        import json
        from analysis import c07_members as m,c07_model as model,c07_evaluate as ev
        from basketball_common import sha256_file
        with TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'data.json').write_text('{}');(root/'models.json').write_text('{}');(root/'fit.json').write_text(json.dumps({'code_sha256':sha256_file(Path(model.__file__)),'contract_sha256':sha256_file(model.data.CONTRACT),'data_sha256':sha256_file(root/'data.json'),'models_sha256':'0'*64}))
            with patch.object(model.data,'WORK',root):
                with self.assertRaisesRegex(ContractError,'artifact'):model.Predictor(root)
            folder=root/'members/g/N';folder.mkdir(parents=True);(folder/'receipt.json').write_text(json.dumps({'sources':{'x':'old'}}))
            with patch.object(m.data,'WORK',root),patch.object(m,'signature',return_value={'x':'new'}):
                with self.assertRaisesRegex(ContractError,'artifact/source'):m.load('g','N')
            (root/'fit.json').write_text(json.dumps({'training':{f:{'converged':True} for f in 'ABC'}}));(root/'short_decision.json').write_text(json.dumps({'shortlist':[]}))
            with patch.object(ev.data,'WORK',root),patch.object(ev.data,'verify',return_value={}):
                with self.assertRaisesRegex(ContractError,'expansion forbidden'):ev.run('final',1)

    def test_retained_source_bytes_fault(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from basketball_common import sha256_file
        from analysis.c07_audit import verify_fingerprints
        with TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'inputs').mkdir();p=root/'inputs/source.bin';p.write_bytes(b'original');expected={'nested':{'inputs/source.bin':sha256_file(p)}}
            self.assertEqual(verify_fingerprints(expected,root),1);p.write_bytes(b'changed')
            with self.assertRaisesRegex(ContractError,'source bytes changed'):verify_fingerprints(expected,root)
