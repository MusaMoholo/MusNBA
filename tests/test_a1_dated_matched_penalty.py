import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from analysis import a1_dated_matched_penalty as run
from analysis import a1_dated_matched_penalty_audit as audit
from analysis.a1_parallel_world_probe import capture_digest
from basketball_common import sha256_file


class DatedMatchedPenaltyTest(unittest.TestCase):
    def test_metrics_use_only_available_home_players_and_preserve_fractional_minutes(self):
        data = {
            'player_ids': np.array([str(i) for i in range(10)]),
            'side': np.array([0] * 8 + [1] * 2),
            'available': np.array([[True] * 7 + [False] + [True] * 2]),
            'final_score': np.array([[103, 99]]),
            'player_points': np.ones((1, 10, 5)),
            'minutes': np.full((1, 10, 5), 1 / 60),
        }
        labels, values = audit.metrics(data)
        self.assertEqual(labels[:4], ['home_points', 'away_points', 'total_points', 'home_margin'])
        np.testing.assert_allclose(values[:4], [103, 99, 202, 4])
        self.assertNotIn('home_player_7_minutes', labels)
        self.assertAlmostEqual(values[labels.index('home_player_0_minutes')], 5 / 60)
        data['available'][0, 0] = False
        with self.assertRaisesRegex(ValueError, 'seven available'):
            audit.metrics(data)

    def test_generation_rejects_mismatched_failure_state(self):
        spec = {'fold': 'F1', 'game': {'game': '123'}, 'branch': {'attempts': [
            {'draw': 0, 'seed': '7', 'status': 'exhausted', 'reason': 'exhausted'}]}}
        original_failure = {'reason': 'exhausted', 'clock': 1}
        policy = SimpleNamespace(first_exhaustion={0: {'reason': 'exhausted', 'clock': 2}},
                                 capture=lambda *_args: {'value': np.array([1])})
        worker = {'engine': SimpleNamespace(last=None), 'branch': object(),
                  'simulate': lambda *_args: None}
        with tempfile.TemporaryDirectory() as tmp, \
             patch.dict(run._WORKER, worker, clear=True), \
             patch.object(run, 'simulate_original', return_value=('7', 'exhausted', original_failure, None)), \
             patch.object(run.repair, 'MatchedPenaltyTrace', return_value=policy):
            with self.assertRaisesRegex(ValueError, 'first-exhaustion state differs'):
                run.attempt(0, spec, tmp)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_audit_rejects_survivor_changed_after_original_replay(self):
        spec = {'fold': 'F1', 'game': {'game': '123'}}
        original = {'game_id': np.array('123'), 'value': np.array([1])}
        changed = {'game_id': np.array('123'), 'value': np.array([2])}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = Path('captures')
            (root / directory).mkdir()
            path = root / directory / 'world-0005.npz'
            np.savez_compressed(path, **changed)
            record = {'draw': 5, 'seed': '7', 'status': 'complete', 'failure': None,
                      'original_world_sha256': capture_digest(original),
                      'capture': str(directory / path.name), 'capture_sha256': sha256_file(path),
                      'audit': {'worlds': 1}}
            with patch.object(audit, 'ROOT', root), \
                 patch.object(run, 'simulate_original', return_value=('7', 'complete', None, original)), \
                 patch.object(audit.a1_substitution_world_audit, 'audit_worlds', return_value={'worlds': 1}):
                with self.assertRaisesRegex(ValueError, 'survivor trajectory differs'):
                    audit.check(record, spec, directory)


if __name__ == '__main__':
    unittest.main()
