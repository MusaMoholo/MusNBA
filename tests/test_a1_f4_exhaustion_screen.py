import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from analysis import a1_f4_exhaustion_screen as screen
from analysis import a1_f4_six_roster_audit as stress_audit
from analysis import a1_f4_six_roster_stress as stress
from scripts.a1_branch_foul_out import ExhaustedEligiblePlayers


class ExhaustionScreenTests(unittest.TestCase):
    def setUp(self):
        self.game = SimpleNamespace(
            day='2026-02-01', side=np.array([0] * 6 + [1] * 6),
            expected=np.array([30.] * 12), ids=[str(i + 1) for i in range(12)],
            game={'home_id': '1'}, avail=np.ones(12),
            players={'home': [{'availability': 1.0} for _ in range(6)]},
        )
        self.engine = SimpleNamespace(rotation_policy=None, last=None)
        screen._WORKER['engine'] = self.engine

    def test_typed_world_failure_is_recorded_but_unknown_error_propagates(self):
        calls = 0

        def simulate(_game, _worlds, _seed):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise ExhaustedEligiblePlayers('fewer than five eligible players')

        self.engine.simulate = simulate
        policy = SimpleNamespace(capture=lambda _g, _st: {'value': np.array([1])})
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(screen.backtest, 'run_game', side_effect=lambda _gid: self.engine.simulate(self.game, 1, 0)), \
             patch.object(screen.a1_lineup_branches, 'one_player', return_value=self.game), \
             patch.object(screen.a1_branch_world_probe, 'RepairedTrace', return_value=policy), \
             patch.object(screen.a1_substitution_world_audit, 'audit_worlds', return_value={'worlds': 1}):
            result = screen.screen_game('123', tmp)
            attempts = [a for branch in result['branches'] for a in branch['attempts']]
            self.assertEqual(len(attempts), 10)
            self.assertEqual([a['status'] for a in attempts].count('exhausted'), 1)
            self.assertIsNone(self.engine.rotation_policy)
            self.assertTrue((Path(tmp) / '123.json').is_file())

        self.engine.simulate = lambda *_args: (_ for _ in ()).throw(RuntimeError('unknown'))
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(screen.backtest, 'run_game', side_effect=lambda _gid: self.engine.simulate(self.game, 1, 0)), \
             patch.object(screen.a1_lineup_branches, 'one_player', return_value=self.game), \
             patch.object(screen.a1_branch_world_probe, 'RepairedTrace', return_value=policy):
            with self.assertRaisesRegex(RuntimeError, 'unknown'):
                screen.screen_game('123', tmp)
            self.assertFalse((Path(tmp) / '123.json').exists())
            self.assertIsNone(self.engine.rotation_policy)

    def test_invalid_initial_allocation_is_not_retried(self):
        self.engine.simulate = lambda *_args: self.fail('invalid branch must not simulate')
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(screen.backtest, 'run_game', side_effect=lambda _gid: self.engine.simulate(self.game, 1, 0)), \
             patch.object(screen.a1_lineup_branches, 'one_player',
                          side_effect=ValueError('home D29 targets do not form a legal 240-minute allocation')):
            result = screen.screen_game('123', tmp)
            self.assertTrue(all(b['status'] == 'invalid initial roster or allocation' and not b['attempts']
                                for b in result['branches']))

    def test_six_player_stress_rejects_only_explicit_world_failure(self):
        stress._WORKER.update(engine=self.engine, branch=self.game,
                              simulate=lambda *_args: (_ for _ in ()).throw(
                                  ExhaustedEligiblePlayers('fewer than five eligible players')))
        policy = SimpleNamespace()
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(stress.a1_branch_world_probe, 'RepairedTrace', return_value=policy):
            self.assertEqual(stress.attempt(0, tmp)['status'], 'exhausted')
            self.assertEqual(list(Path(tmp).iterdir()), [])
            stress._WORKER['simulate'] = lambda *_args: (_ for _ in ()).throw(RuntimeError('unknown'))
            with self.assertRaisesRegex(RuntimeError, 'unknown'):
                stress.attempt(1, tmp)

    def test_six_player_audit_rejects_changed_manifest_without_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            detail = root / 'manifest.json'
            detail.write_text('{}')
            summary = root / 'summary.json'
            summary.write_text(json.dumps({'details': str(detail), 'details_sha256': 'wrong'}))
            output = root / 'audit.json'
            with patch.object(stress_audit.sys, 'argv', ['audit', str(summary), '--output', str(output)]):
                with self.assertRaisesRegex(ValueError, 'detailed manifest differs'):
                    stress_audit.main()
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
