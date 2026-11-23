import sys
import unittest
from unittest.mock import patch

import numpy as np

from analysis.a1_matched_penalty_repair import MatchedPenaltyTrace
from analysis.a1_vector_matched_penalty import VectorMatchedPenaltyTrace
from analysis import a1_vector_penalty_backtest
from scripts import engine
from tests.test_a1_lineup_branches import OnePlayerBranchesTests


class MatchedPenaltyRepairTest(unittest.TestCase):
    def test_vector_backtest_rejects_worker_count_outside_budget(self):
        for jobs in ('0', '11'):
            with self.subTest(jobs=jobs), \
                 patch.object(sys, 'argv', ['backtest', '--name', 'test', '--jobs', jobs]), \
                 self.assertRaisesRegex(ValueError, 'between 1 and 10'):
                a1_vector_penalty_backtest.main()

    def test_vector_exhaustion_does_not_change_other_world_lineup_or_score(self):
        game = OnePlayerBranchesTests().game(size=6)
        game.P['ft_pct'] = np.ones(game.n)
        state = engine.Worlds(game, 2, np.random.default_rng(42))
        state.off[:] = 0
        lineups = np.tile(np.array([[[0, 1, 2, 3, 4], [6, 7, 8, 9, 10]]]), (2, 1, 1))
        active = np.array([0, 1])
        state.ingame['pf_so_far'][:, 0] = 5
        state.ingame['pf_so_far'][1, 5] = 6
        policy = VectorMatchedPenaltyTrace()
        policy.begin(game, 2, np.ones((2, game.n), dtype=bool), 42)
        policy.before_segment(game, state, active, lineups)
        state.ingame['pf_so_far'][:, 0] = 6
        offense, defense = lineups[:, 0].copy(), lineups[:, 1].copy()
        np.testing.assert_array_equal(policy.after_fouls(game, state, active, offense, defense), [True, False])
        self.assertIn(5, offense[0])
        self.assertIn(0, offense[1])
        np.testing.assert_array_equal(state.score[:, 1], [0, 1])
        self.assertFalse(policy.repair.exempt[0].any())
        self.assertTrue(policy.repair.exempt[1, 0])
        scheduled = lineups.copy()
        scheduled[1, 0, 0] = 5
        repaired = policy.before_segment(game, state, active, scheduled)
        self.assertIn(0, repaired[1, 0])
        self.assertNotIn(5, repaired[1, 0])

    def test_retains_only_current_foul_out_and_records_technical(self):
        for side in (0, 1):
            with self.subTest(side=side):
                game = OnePlayerBranchesTests().game(size=6)
                game.P['ft_pct'] = np.ones(game.n)
                state = engine.Worlds(game, 1, np.random.default_rng(42))
                state.off[0] = 0
                first = 6 * side
                lineup = np.array([[[0, 1, 2, 3, 4], [6, 7, 8, 9, 10]]])
                state.ingame['pf_so_far'][0, first] = 5
                state.ingame['pf_so_far'][0, first + 5] = 6
                policy = MatchedPenaltyTrace()
                policy.begin(game, 1, np.ones((1, game.n), dtype=bool), 42)
                active = np.array([0])
                policy.before_segment(game, state, active, lineup)
                state.ingame['pf_so_far'][0, first] = 6
                offense, defense = lineup[:, 0].copy(), lineup[:, 1].copy()
                self.assertFalse(policy.after_fouls(game, state, active, offense, defense)[0])
                self.assertEqual(len(policy.technical_events), 1)
                self.assertEqual(state.score[0, 1 - side], 1)
                self.assertTrue(policy.repair.exempt[0, first])
                scheduled = lineup.copy()
                scheduled[0, side, 0] = first + 5
                repaired = policy.before_segment(game, state, active, scheduled)
                self.assertIn(first, repaired[0, side])
                self.assertNotIn(first + 5, repaired[0, side])
                state.ingame['pf_so_far'][0, first] = 7
                offense, defense = repaired[:, 0].copy(), repaired[:, 1].copy()
                policy.after_fouls(game, state, active, offense, defense)
                self.assertEqual(len(policy.technical_events), 2)
                self.assertEqual(state.score[0, 1 - side], 2)

    def test_replaces_when_five_eligible_without_penalty(self):
        game = OnePlayerBranchesTests().game(size=6)
        game.P['ft_pct'] = np.ones(game.n)
        state = engine.Worlds(game, 1, np.random.default_rng(42))
        lineup = np.array([[[0, 1, 2, 3, 4], [6, 7, 8, 9, 10]]])
        active = np.array([0])
        policy = MatchedPenaltyTrace()
        policy.begin(game, 1, np.ones((1, game.n), dtype=bool), 42)
        state.ingame['pf_so_far'][0, 0] = 5
        policy.before_segment(game, state, active, lineup)
        state.ingame['pf_so_far'][0, 0] = 6
        off = int(state.off[0])
        offense, defense = lineup[:, off].copy(), lineup[:, 1 - off].copy()
        self.assertTrue(policy.after_fouls(game, state, active, offense, defense)[0])
        self.assertIn(5, offense[0] if off == 0 else defense[0])
        self.assertEqual(policy.technical_events, [])

    def test_exhaustion_requires_known_opposing_free_throw_probability(self):
        game = OnePlayerBranchesTests().game(size=6)
        game.P['ft_pct'] = np.full(game.n, np.nan)
        state = engine.Worlds(game, 1, np.random.default_rng(42))
        lineup = np.array([[[0, 1, 2, 3, 4], [6, 7, 8, 9, 10]]])
        active = np.array([0])
        policy = MatchedPenaltyTrace()
        policy.begin(game, 1, np.ones((1, game.n), dtype=bool), 42)
        state.ingame['pf_so_far'][0, 0] = 5
        state.ingame['pf_so_far'][0, 5] = 6
        policy.before_segment(game, state, active, lineup)
        state.ingame['pf_so_far'][0, 0] = 6
        off = int(state.off[0])
        with self.assertRaisesRegex(ValueError, 'no opposing on-court player'):
            policy.after_fouls(game, state, active, lineup[:, off].copy(), lineup[:, 1 - off].copy())


if __name__ == '__main__':
    unittest.main()
