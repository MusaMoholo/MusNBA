import unittest
import numpy as np
from analysis.c03_choices import CONTEXT,PLAYER,law,decode,validate_inputs,long_features,check
from analysis.c01_core import ContractError

class ChoiceTests(unittest.TestCase):
    def setUp(self):
        self.c={k:np.zeros(2) for k in CONTEXT};self.p={k:np.zeros((2,5)) for k in PLAYER}
    def test_independent_marginal_arithmetic(self):
        p=np.tile(np.arange(1,44,dtype=float), (2,1));p/=p.sum(1,keepdims=True)
        e,w,a=decode(p)
        self.assertAlmostEqual(e[0,0],sum(range(1,41))/sum(range(1,44)))
        self.assertAlmostEqual(w[0,0],sum(range(1,9))/sum(range(1,41)))
        self.assertAlmostEqual(a[0,0,0],1/sum(range(1,9)))
        np.testing.assert_allclose((e[:,0,None,None]*w[:,:,None]*a).reshape(2,40),p[:,:40])
    def test_fault_boundary(self):
        for p in (np.full((2,43),np.nan),np.ones((2,43)),np.zeros((2,43))):
            with self.assertRaises(ContractError):check(p)
        with self.assertRaises(ContractError):validate_inputs(self.c,self.p,['2026-01-01']*2,True)
        for key in ('y','foul_event','current_action','legal_mask'):
            with self.assertRaises(ContractError):long_features({**self.c,key:np.ones(2)},self.p)
    def test_alternatives_do_not_depend_on_labels(self):
        x,cols=long_features(self.c,self.p);self.assertEqual(x.shape,(86,len(cols)))
        np.testing.assert_array_equal(x[:43,-1],np.r_[np.tile(np.arange(8),5),8,9,10])
        check(law(np.zeros((2,43))))

class RuntimeTests(unittest.TestCase):
    def test_adapter_conditionals_and_fixed_foul_resolver(self):
        from types import SimpleNamespace
        from analysis.c03_runtime import attached
        base=np.arange(1,44,dtype=float);base/=base.sum();p=np.tile(base,(2,1))
        class Predictor:
            meta={'training_through':'2025-12-31'}
            def predict(self,c,f):return p.copy()
        class View:
            def context(self,*args):return {k:np.zeros(2) for k in CONTEXT if k!='shot_time'}
            def five(self,*args):return {k:np.zeros((2,5)) for k in PLAYER}
        old=lambda name,cols,n:np.ones(n)*4
        e=SimpleNamespace(_context=lambda *a:{},_five=lambda *a:{},_actor=lambda *a:{},m=SimpleNamespace(predict=old,nodes={'who':{'temperature':2.}}))
        g=SimpleNamespace(day='2026-01-01');idx=np.arange(2);lo=np.zeros((2,5),int)
        with attached(e,g,View(),Predictor()) as counts:
            ctx=e._context(g,None,idx,lo,lo);ctx['shot_time']=np.ones(2)
            ev=e.m.predict('event',ctx,2);np.testing.assert_allclose(ev[:,0],base[:40].sum())
            five=e._five(g,None,idx,lo,());actor=e._actor(five,np.array([1,3]));what=e.m.predict('what',{**ctx,**actor},2)
            np.testing.assert_allclose(what[0],base[8:16]/base[8:16].sum())
            who=e.m.predict('who',{'c03_row':np.repeat(idx,5),'foul_event':np.zeros(10)},10)
            np.testing.assert_allclose(np.exp(who.reshape(2,5))[0],base[:40].reshape(5,8).sum(1)/base[:40].sum())
            np.testing.assert_array_equal(e.m.predict('who',{'foul_event':np.ones(5)},5),np.ones(5)*2)
        self.assertIs(e.m.predict,old);self.assertEqual(e.m.nodes['who']['temperature'],2.)

    def test_real_boundary_fault_saved_counts(self):
        from analysis.c02_accounting import reference_crps
        self.assertAlmostEqual(reference_crps([0,2],1),.5)
        with self.assertRaises(ContractError):reference_crps([np.nan],0)

class LearningTests(unittest.TestCase):
    def test_shared_loss_gradient_against_finite_difference(self):
        from analysis.c03_model import objective
        z=np.linspace(-.7,.6,86);y=np.zeros(86);y[7]=1;y[64]=1
        class Dataset:
            def get_label(self):return y
        gradient,hessian=objective(43)(z,Dataset())
        def loss(x):
            a=x.reshape(2,43);return float(np.sum(np.log(np.exp(a).sum(1))-np.sum(y.reshape(2,43)*a,1)))
        for k in (0,7,42,64,85):
            plus=z.copy();minus=z.copy();plus[k]+=1e-6;minus[k]-=1e-6
            self.assertAlmostEqual(gradient[k],(loss(plus)-loss(minus))/2e-6,places=8)
        self.assertTrue((hessian>0).all())
    def test_label_mask_fault_and_actor_permutation(self):
        from analysis.c03_choices import long_features,law
        c={k:np.zeros(1) for k in CONTEXT};p={k:np.arange(5,dtype=float)[None,:] for k in PLAYER}
        x,_=long_features(c,p);perm=[2,0,4,1,3];other,_=long_features(c,{k:v[:,perm] for k,v in p.items()})
        np.testing.assert_array_equal(other[:40],x[:40].reshape(5,8,-1)[perm].reshape(40,-1))
        np.testing.assert_array_equal(other[40:],x[40:])
        with self.assertRaises(ContractError):long_features({**c,'actor_observed':np.zeros(1)},p)

class MechanicalFaultTests(unittest.TestCase):
    def test_observer_rejects_duplicate_and_invalid_clock(self):
        from types import SimpleNamespace
        from analysis.c01_contexts import ZoneObserver
        g=SimpleNamespace(side=np.repeat([0,1],5));L=np.arange(10).reshape(1,2,5)
        st=SimpleNamespace(clock=np.array([700.]),period=np.array([1]),ingame={'pf_so_far':np.zeros((1,10))})
        observer=ZoneObserver();observer.before_segment(g,st,np.array([0]),L)
        bad=L.copy();bad[0,0,1]=bad[0,0,0]
        with self.assertRaises(ContractError):observer.before_segment(g,st,np.array([0]),bad)
        st.clock[0]=-1
        with self.assertRaises(ContractError):observer.before_segment(g,st,np.array([0]),L)
        g2=SimpleNamespace(side=np.r_[np.zeros(6,int),np.ones(5,int)])
        st2=SimpleNamespace(clock=np.array([700.]),period=np.array([1]),ingame={'pf_so_far':np.zeros((1,11))})
        st2.ingame['pf_so_far'][0,0]=6
        with self.assertRaises(ContractError):observer.before_segment(g2,st2,np.array([0]),np.array([[[0,1,2,3,4],[6,7,8,9,10]]]))
    def test_fitted_probability_artifact_tampering_fails(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from analysis.c03_model import Predictor
        from analysis.c03_data import CONTRACT
        from basketball_common import sha256_file
        import json
        with TemporaryDirectory() as folder:
            root=Path(folder);(root/'A').mkdir();(root/'A'/'event.json').write_text('{}')
            meta={'contract_sha256':sha256_file(CONTRACT),'hashes':{'event.json':'0'*64}}
            (root/'A'/'fit.json').write_text(json.dumps(meta))
            with self.assertRaises(ContractError):Predictor('A',root)

class ResumeFaultTests(unittest.TestCase):
    def test_resume_refuses_changed_source_and_changed_completed_game(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from unittest.mock import patch
        from analysis import c03_rollout as run
        import json
        with TemporaryDirectory() as folder:
            root=Path(folder);(root/'data.json').write_text(json.dumps({'game_ids':['g']}))
            (root/'mvp_plan.json').write_text(json.dumps({'sources':{'x':'old'}}))
            with patch.object(run.data,'WORK',root),patch.object(run.data,'verify',return_value={}),patch.object(run,'signature',return_value={'x':'new'}):
                with self.assertRaisesRegex(ContractError,'resume source changed'):run.run('mvp',1)
            (root/'mvp_plan.json').write_text(json.dumps({'sources':{'x':'new'}}));game=root/'rollout/g';game.mkdir(parents=True)
            (game/'A.npz').write_bytes(b'modified artifact');(game/'receipt.json').write_text(json.dumps({'hashes':{'A.npz':'0'*64}}))
            with patch.object(run.data,'WORK',root),patch.object(run.data,'verify',return_value={}),patch.object(run,'signature',return_value={'x':'new'}):
                with self.assertRaisesRegex(ContractError,'completed game changed'):run.run('mvp',1)

    def test_no_finalist_expansion_after_negative_search(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from unittest.mock import patch
        from analysis import c03_rollout as run
        import json
        with TemporaryDirectory() as folder:
            root=Path(folder);(root/'data.json').write_text(json.dumps({'game_ids':['g']}));(root/'mvp.json').write_text(json.dumps({'shortlist':[]}))
            with patch.object(run.data,'WORK',root),patch.object(run.data,'verify',return_value={}),patch.object(run,'signature',return_value={}):
                with self.assertRaisesRegex(ContractError,'expansion forbidden'):run.run('finalists',1)
