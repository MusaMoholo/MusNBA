import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from analysis import a1_real_retry_paired as run
from analysis import a1_real_retry_paired_audit as audit
from basketball_common import read_json, write_json
from scripts import a1_branch_foul_out, a1_world_retry


class RealRetryPairedTest(unittest.TestCase):
    def test_only_original_typed_exhaustion_is_retryable(self):
        failure = {'reason': 'fewer than five', 'state_sha256': 'abc'}
        original = SimpleNamespace(failure=failure)
        continuation = SimpleNamespace(first_exhaustion={0: failure},
                                       capture=lambda *_args: {'value': np.array([1])})
        engine = SimpleNamespace(last=None, rotation_policy=None)

        def simulate(*_args):
            if engine.rotation_policy is original:
                raise a1_branch_foul_out.ExhaustedEligiblePlayers('fewer than five')

        worker = {'engine': engine, 'branch': object(), 'simulate': simulate}
        with tempfile.TemporaryDirectory() as tmp, patch.dict(run.stress._WORKER, worker, clear=True), \
             patch.object(run.matched, 'FailureTrace', return_value=original), \
             patch.object(run.repair, 'MatchedPenaltyTrace', return_value=continuation), \
             patch.object(run.a1_substitution_world_audit, 'audit_worlds', return_value={'worlds': 1}):
            with self.assertRaisesRegex(a1_world_retry.RecoverableWorldError, 'fewer than five'):
                run.attempt(0, 0, 7, batch=0, directory=tmp)
            saved = read_json(Path(tmp) / 'first-0000.json')
            self.assertEqual(saved['failure'], failure)
            self.assertTrue(Path(saved['capture']['path']).is_file())

    def test_unclassified_or_continuation_failure_is_not_retried(self):
        original = SimpleNamespace(failure={'reason': 'fewer than five'})
        continuation = SimpleNamespace()
        engine = SimpleNamespace(last=None, rotation_policy=None)
        worker = {'engine': engine, 'branch': object(),
                  'simulate': lambda *_args: (_ for _ in ()).throw(a1_world_retry.RecoverableWorldError('unknown'))}
        with tempfile.TemporaryDirectory() as tmp, patch.dict(run.stress._WORKER, worker, clear=True), \
             patch.object(run.matched, 'FailureTrace', return_value=original), \
             patch.object(run.repair, 'MatchedPenaltyTrace', return_value=continuation):
            with self.assertRaisesRegex(ValueError, 'unclassified recoverable'):
                run.attempt(0, 0, 7, batch=0, directory=tmp)

            def failing_continuation(*_args):
                if engine.rotation_policy is original:
                    raise a1_branch_foul_out.ExhaustedEligiblePlayers('fewer than five')
                raise a1_branch_foul_out.ExhaustedEligiblePlayers('continuation failure')

            run.stress._WORKER['simulate'] = failing_continuation
            with self.assertRaisesRegex(ValueError, 'continuation failed'):
                run.attempt(0, 0, 7, batch=0, directory=tmp)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_audit_rejects_seed_mismatch_before_replay(self):
        first = {'slot': 0, 'seed': '1'}
        accepted = {'slot': 0, 'attempt': 0, 'seed': '1'}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_json(root / 'first-0000.json', first, pretty=True)
            with patch.object(audit, 'ROOT', root), self.assertRaisesRegex(ValueError, 'seed or ordering'):
                audit.check(first, accepted, [], Path('.'), 20261123)


if __name__ == '__main__':
    unittest.main()
