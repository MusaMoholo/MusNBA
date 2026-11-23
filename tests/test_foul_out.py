import copy
import unittest

import numpy as np

from scripts import engine
from scripts.foul_out import Rule3Policy
from tests import test_a1_lineup_branches as fixtures


class Rule3Tests(unittest.TestCase):
    def fixture(self, worlds=1):
        game = fixtures.OnePlayerBranchesTests().game(size=6)
        game.P['ft_pct'] = np.ones(game.n)
        state = engine.Worlds(game, worlds, np.random.default_rng(42))
        state.off[:] = 0
        lineups = np.tile(np.array([[[0, 1, 2, 3, 4], [6, 7, 8, 9, 10]]]), (worlds, 1, 1))
        policy = Rule3Policy(capture_events=True)
        policy.begin(game, worlds, np.ones((worlds, game.n), dtype=bool), 42)
        return game, state, lineups, policy

    def foul(self, state, player, offensive):
        state.box['pf'][0, player, 0] = state.ingame['pf_so_far'][0, player] + 1
        state.ingame['pf_so_far'][0, player] += 1
        if not offensive:
            state.tfouls[0, 1] += 1

    def test_sixth_foul_replaces_when_a_legal_bench_player_exists(self):
        for fouler in (0, 6):
            game, state, lineups, policy = self.fixture()
            state.ingame['pf_so_far'][0, fouler] = 5
            policy.before_segment(game, state, np.array([0]), lineups)
            self.foul(state, fouler, fouler == 0)
            offense, defense = lineups[:, 0].copy(), lineups[:, 1].copy()
            mask = policy.after_fouls(game, state, np.array([0]), offense, defense)
            self.assertTrue(mask[0])
            self.assertNotIn(fouler, offense[0] if fouler == 0 else defense[0])
            self.assertEqual(policy.counts['technical_attempts'], 0)
            self.assertEqual(state.tfouls[0, fouler // 6], int(fouler != 0))

    def test_retained_offensive_fouls_count_team_foul_and_technical_each_time(self):
        game, state, lineups, policy = self.fixture()
        state.ingame['pf_so_far'][0, [0, 5]] = [5, 6]
        for n in (1, 2):
            lineups = policy.before_segment(game, state, np.array([0]), lineups)
            self.foul(state, 0, True)
            offense, defense = lineups[:, 0].copy(), lineups[:, 1].copy()
            policy.after_fouls(game, state, np.array([0]), offense, defense)
            self.assertIn(0, offense[0])
            self.assertEqual(state.tfouls[0, 0], n)
            self.assertEqual(state.score[0, 1], n)
            self.assertEqual(state.box['fta'][0].sum(), n)
            self.assertEqual(state.box['ftm'][0].sum(), n)
            self.assertEqual(state.box['pts'][0].sum(), state.pts[0].sum())
        self.assertEqual(policy.counts['retained_offensive_team_fouls'], 2)

    def test_retained_defensive_foul_does_not_double_count_team_foul(self):
        game, state, lineups, policy = self.fixture()
        state.ingame['pf_so_far'][0, [6, 11]] = [5, 6]
        policy.before_segment(game, state, np.array([0]), lineups)
        self.foul(state, 6, False)
        policy.after_fouls(game, state, np.array([0]), lineups[:, 0].copy(), lineups[:, 1].copy())
        self.assertEqual(state.tfouls[0, 1], 1)
        self.assertEqual(policy.counts['technical_attempts'], 1)
        self.assertEqual(policy.counts['retained_offensive_team_fouls'], 0)

    def test_exhaustion_changes_only_its_world_and_never_revives_removed_player(self):
        game, state, lineups, policy = self.fixture(2)
        state.ingame['pf_so_far'][:, 0] = 5
        state.ingame['pf_so_far'][1, 5] = 6
        policy.before_segment(game, state, np.array([0, 1]), lineups)
        state.ingame['pf_so_far'][:, 0] += 1
        offense, defense = lineups[:, 0].copy(), lineups[:, 1].copy()
        mask = policy.after_fouls(game, state, np.array([0, 1]), offense, defense)
        np.testing.assert_array_equal(mask, [True, False])
        np.testing.assert_array_equal(state.score[:, 1], [0, 1])
        np.testing.assert_array_equal(state.tfouls[:, 0], [0, 1])
        lineups[1, 0, 0] = 5
        repaired = policy.before_segment(game, state, np.array([0, 1]), lineups)
        self.assertIn(0, repaired[1, 0])
        self.assertNotIn(5, repaired[1, 0])

    def test_missing_technical_shooter_profile_fails_without_inventing_a_probability(self):
        game, state, lineups, policy = self.fixture()
        game.P['ft_pct'][:] = np.nan
        state.ingame['pf_so_far'][0, [0, 5]] = [5, 6]
        policy.before_segment(game, state, np.array([0]), lineups)
        self.foul(state, 0, True)
        with self.assertRaisesRegex(ValueError, 'known opposing on-court'):
            policy.after_fouls(game, state, np.array([0]), lineups[:, 0].copy(), lineups[:, 1].copy())

    def test_invalid_initial_roster_is_not_repaired_by_activating_anyone(self):
        game, _, _, _ = self.fixture()
        available = np.ones((1, game.n), dtype=bool)
        available[0, :2] = False
        with self.assertRaisesRegex(ValueError, 'invalid initial roster'):
            Rule3Policy().begin(game, 1, available, 42)

    def test_unaffected_states_leave_lineups_and_boxes_identical(self):
        game, state, lineups, policy = self.fixture()
        saved = copy.deepcopy(state)
        np.testing.assert_array_equal(policy.before_segment(game, state, np.array([0]), lineups), lineups)
        mask = policy.after_fouls(game, state, np.array([0]), lineups[:, 0].copy(), lineups[:, 1].copy())
        self.assertFalse(mask.any())
        for key in state.box:
            np.testing.assert_array_equal(state.box[key], saved.box[key])
        np.testing.assert_array_equal(state.score, saved.score)
        np.testing.assert_array_equal(state.tfouls, saved.tfouls)


if __name__ == '__main__':
    unittest.main()
