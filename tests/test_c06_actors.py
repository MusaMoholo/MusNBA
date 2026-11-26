import unittest
import numpy as np
from analysis.c06_core import check,softmax,normalise,pack,dates_before
from analysis.c03_choices import CONTEXT,PLAYER
from analysis.c01_core import ContractError

class ActorBoundaryTests(unittest.TestCase):
    def test_known_law_and_permutation(self):
        p=softmax(np.log([[1,2,3,4,5]]));np.testing.assert_allclose(p,[[1/15,2/15,3/15,4/15,5/15]])
        perm=[3,1,4,2,0];np.testing.assert_allclose(softmax(np.log([[1,2,3,4,5]])[:,perm]),p[:,perm]);np.testing.assert_allclose(normalise([[.1,.2,.3,.4,.5]]),p)
    def test_meaningful_illegal_law_and_future_faults(self):
        for a in ([[0,.25,.25,.25,.25]],[[.1]*5],[[np.nan]*5],[[.2]*4]):
            with self.assertRaises(ContractError):check(a)
        for dates in (['2026-01-01'],['2025-12-32'],[None]):
            with self.assertRaises(ContractError):dates_before(dates,'2025-12-31')
        dates_before(['2023-01-01','2025-12-31'],'2025-12-31')
    def test_current_label_input_rejected(self):
        c={k:np.ones(3) for k in CONTEXT};p={k:np.ones((3,5)) for k in PLAYER}
        self.assertEqual(pack(c,p).shape,(15,len(CONTEXT)+len(PLAYER)))
        for k in ('actor','y','current_points','target'):
            with self.assertRaises(ContractError):pack({**c,k:np.ones(3)},p)

class RuntimeAndArtifactFaultTests(unittest.TestCase):
    def test_temperature_and_functions_restore_even_on_error(self):
        from types import SimpleNamespace
        from analysis.c06_runtime import attached
        predictor=SimpleNamespace(meta={'training_through':'2025-12-31'})
        old_context=lambda *a:{};old_five=lambda *a:{};old_predict=lambda name,cols,n:np.full(n,4.)
        e=SimpleNamespace(_context=old_context,_five=old_five,m=SimpleNamespace(predict=old_predict,nodes={'who':{'temperature':2.}}))
        with self.assertRaisesRegex(RuntimeError,'deliberate'):
            with attached(e,SimpleNamespace(day='2026-01-01'),None,predictor) as used:
                np.testing.assert_array_equal(e.m.predict('who',{'foul_event':np.ones(10)},10),np.full(10,2.));self.assertEqual(used['who'],0)
                raise RuntimeError('deliberate')
        self.assertIs(e._context,old_context);self.assertIs(e._five,old_five);self.assertIs(e.m.predict,old_predict);self.assertEqual(e.m.nodes['who']['temperature'],2.)
        with self.assertRaisesRegex(ContractError,'future'):
            with attached(e,SimpleNamespace(day='2025-12-31'),None,predictor):pass
    def test_stopping_and_source_resume_fail_closed(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from unittest.mock import patch
        import json
        from analysis import c06_rollout as r
        with TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'events.json').write_text(json.dumps({'shortlist':[]}))
            with patch.object(r.data,'WORK',root),patch.object(r.data,'verify',return_value={'game_ids':['g']}):
                with self.assertRaisesRegex(ContractError,'expansion forbidden'):r.run('short',1)
            (root/'wiring_plan.json').write_text(json.dumps({'sources':{'x':'old'}}))
            with patch.object(r.data,'WORK',root),patch.object(r.data,'verify',return_value={'game_ids':['g']}),patch.object(r,'signature',return_value={'x':'new'}):
                with self.assertRaisesRegex(ContractError,'resume sources changed'):r.run('wiring',1)
            (root/'wiring_plan.json').write_text(json.dumps({'sources':{'x':'new'}}));game=root/'games/g';game.mkdir(parents=True);(game/'A.npz').write_bytes(b'changed');(game/'receipt.json').write_text(json.dumps({'generation_signature':{'x':'new'},'hashes':{'A.npz':'0'*64},'arms':['native','control','A','B','C']}))
            with patch.object(r.data,'WORK',root),patch.object(r.data,'verify',return_value={'game_ids':['g']}),patch.object(r,'signature',return_value={'x':'new'}):
                with self.assertRaisesRegex(ContractError,'completed actor game/source changed'):r.run('wiring',1)

    def test_changed_fit_artifact_rejected(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        import json
        from basketball_common import sha256_file
        from analysis import c06_model as m
        with TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'A').mkdir();(root/'data.json').write_text('{}');(root/'A/model.txt').write_text('tampered')
            (root/'A/fit.json').write_text(json.dumps({'contract_sha256':sha256_file(m.data.CONTRACT),'code_sha256':sha256_file(Path(m.__file__)),'data_sha256':sha256_file(root/'data.json'),'hashes':{'model.txt':'0'*64}}))
            with patch.object(m.data,'WORK',root):
                with self.assertRaisesRegex(ContractError,'artifact'):m.Predictor('A',root)
