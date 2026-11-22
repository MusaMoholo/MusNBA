import unittest
from unittest.mock import Mock, patch

import lightgbm as lgb
import numpy as np
import pandas as pd

from scripts import a1_substitution_engine as candidate, engine


class FixtureGame(engine.Game):
    def __init__(self):
        self.n = 14
        self.sides = ('home', 'away')
        self.ids = [str(i) for i in range(self.n)]
        self.side = np.array([0] * 7 + [1] * 7)
        self.game = {'game_id': '1', 'home_id': '10', 'away_id': '20'}
        self.expected = np.arange(self.n, dtype=float) + 1
        self.avail = np.ones(self.n)

    def lineup_tables(self, avail_world, rng):
        _ = avail_world, rng
        tables = np.stack([np.tile(np.arange(5), (2880, 1)), np.tile(np.arange(7, 12), (2880, 1))])
        return tables, np.array([[0, 1]])


def fixture_policy(game, probability=0.9, regulation=None, overtime=None, capture_trace=False):
    rows = pd.DataFrame([{'game_id': '1', 'team': '10' if i < 7 else '20', 'player': str(i),
                          'control_mean': 20., 'tier': 'bench', 'prior_position': 'G'}
                         for i in range(game.n)])
    outgoing, incoming = Mock(spec=lgb.Booster), Mock(spec=lgb.Booster)
    outgoing.predict.side_effect = lambda X, **_kwargs: np.full(len(X), probability)
    incoming.predict.side_effect = lambda X, **_kwargs: np.arange(len(X), dtype=float) / 100
    timing = {'regulation': regulation if regulation is not None else [[[1, 120.]]],
              'overtime': overtime if overtime is not None else [[40.]]}
    return candidate.SelectedTimeoutPolicy(outgoing, incoming, timing, rows, capture_trace=capture_trace)


def schedule(worlds):
    return np.tile(np.array([[0, 1, 2, 3, 4], [7, 8, 9, 10, 11]]), (worlds, 1, 1))


class RotationPolicyTests(unittest.TestCase):
    def test_candidate_features_match_pre_window_state_and_leave_overtime_deficit_missing(self):
        game = FixtureGame()
        state = engine.Worlds(game, 1, np.random.default_rng(1))
        policy = fixture_policy(game, regulation=[[]])
        policy.begin(game, 1, np.ones((1, game.n), bool), 1)
        policy.before_segment(game, state, np.array([0]), schedule(1))
        state.period[0], state.clock[0], state.score[0] = 2, 300, [80, 75]
        state.ingame['pf_so_far'][0, 0] = 2
        state.ingame['sec_so_far'][0, 0] = 600
        policy.on_since[0, 0] = 940
        w, side, player = np.array([0]), np.array([0]), np.array([0])
        now = candidate.elapsed(state.period[w], state.clock[w])
        actual = np.array([column[0] for column in policy._numeric(state, w, side, player, now, rest=False)])
        expected = np.array([2, 300, 5, 2, 600, 200, 20, 20 * 1140 / 2880 - 10])
        np.testing.assert_allclose(actual, expected)
        state.period[0], state.clock[0] = 5, 200
        now = candidate.elapsed(state.period[w], state.clock[w])
        self.assertTrue(np.isnan(policy._numeric(state, w, side, player, now, rest=False)[-1][0]))
        unseen = np.array([5])
        self.assertTrue(np.isnan(policy._numeric(state, w, side, unseen, now, rest=True)[5][0]))

    def test_conditional_outgoing_draw_respects_bench_and_rejects_impossible_mass(self):
        rng = np.random.default_rng(42)
        probabilities = np.full((300, 5), 0.9)
        capacity = np.tile([0, 1, 2], 100)
        exits = candidate.conditional_exits(probabilities, capacity, rng)
        self.assertTrue((exits.sum(axis=1) <= capacity).all())
        self.assertTrue((exits[capacity == 0].sum(axis=1) == 0).all())
        with self.assertRaisesRegex(ValueError, 'no legal probability mass'):
            candidate.conditional_exits(np.ones((1, 5)), np.array([4]), rng)
        with self.assertRaisesRegex(ValueError, 'invalid outgoing'):
            candidate.conditional_exits(np.full((1, 5), np.nan), np.array([5]), rng)

    def test_simultaneous_timeout_changes_persist_until_a_legal_plan_change(self):
        game, worlds = FixtureGame(), 40
        state = engine.Worlds(game, worlds, np.random.default_rng(1))
        policy = fixture_policy(game)
        policy.begin(game, worlds, np.ones((worlds, game.n), bool), 1)
        original = schedule(worlds)
        self.assertTrue(np.array_equal(policy.before_segment(game, state, np.arange(worlds), original), original))
        state.clock[:] = 600
        state.start[:] = engine.S['made_fg']
        state.ingame['sec_so_far'][:, :5] = 120
        state.ingame['sec_so_far'][:, 7:12] = 120
        changed = policy.before_segment(game, state, np.arange(worlds), original)
        self.assertEqual(policy.counts['timeout_worlds'], worlds)
        self.assertGreater(policy.counts['timeout_outgoing'], worlds)
        for world in changed:
            for side in world:
                self.assertEqual(len(set(side)), 5)
        different_plan = np.tile(np.array([[2, 3, 4, 5, 6], [9, 10, 11, 12, 13]]), (worlds, 1, 1))
        state.clock[:] = 590
        state.start[:] = engine.S['oreb']
        self.assertTrue(np.array_equal(policy.before_segment(game, state, np.arange(worlds), different_plan), changed))
        state.start[:] = engine.S['made_fg']
        reset = policy.before_segment(game, state, np.arange(worlds), different_plan)
        self.assertTrue(np.array_equal(reset, different_plan))

    def test_timeout_policy_repeats_identically_for_the_same_seed(self):
        game, worlds = FixtureGame(), 20
        states = [engine.Worlds(game, worlds, np.random.default_rng(1)) for _ in range(2)]
        policies = [fixture_policy(game) for _ in range(2)]
        results = []
        for policy, state in zip(policies, states):
            policy.begin(game, worlds, np.ones((worlds, game.n), bool), 123)
            policy.before_segment(game, state, np.arange(worlds), schedule(worlds))
            state.clock[:] = 600
            state.start[:] = engine.S['made_fg']
            results.append(policy.before_segment(game, state, np.arange(worlds), schedule(worlds)))
        self.assertTrue(np.array_equal(results[0], results[1]))
        self.assertEqual(policies[0].counts, policies[1].counts)

    def test_trace_capture_preserves_draws_and_records_the_lineup_used_after_a_foul(self):
        game, worlds = FixtureGame(), 20
        states = [engine.Worlds(game, worlds, np.random.default_rng(1)) for _ in range(2)]
        policies = [fixture_policy(game, capture_trace=enabled) for enabled in (False, True)]
        results = []
        for policy, state in zip(policies, states):
            policy.begin(game, worlds, np.ones((worlds, game.n), bool), 123)
            policy.before_segment(game, state, np.arange(worlds), schedule(worlds))
            state.clock[:] = 600
            state.start[:] = engine.S['made_fg']
            lineups = policy.before_segment(game, state, np.arange(worlds), schedule(worlds))
            state.off[:] = 0
            offense, defense = lineups[:, 0].copy(), lineups[:, 1].copy()
            state.ingame['pf_so_far'][0, defense[0, 0]] = 6
            policy.after_fouls(game, state, np.arange(worlds), offense, defense)
            results.append((offense, defense))
        np.testing.assert_array_equal(results[0][0], results[1][0])
        np.testing.assert_array_equal(results[0][1], results[1][1])
        self.assertEqual(policies[0].counts, policies[1].counts)
        self.assertEqual(len(policies[0].trace), 0)
        trace = policies[1].trace[-1]
        self.assertEqual(trace['phase'].tolist(), [1])
        np.testing.assert_array_equal(trace['lineups'][0, 0], results[1][0][0])
        np.testing.assert_array_equal(trace['lineups'][0, 1], results[1][1][0])
        self.assertTrue((trace['fouls'] < 6).all())

    def test_initial_short_roster_fails_and_exactly_five_never_activates_a_bench_player(self):
        game = FixtureGame()
        state = engine.Worlds(game, 1, np.random.default_rng(1))
        policy = fixture_policy(game)
        available = np.ones((1, game.n), bool)
        available[0, 4:7] = False
        with self.assertRaisesRegex(ValueError, 'fewer than five explicitly available'):
            policy.begin(game, 1, available, 1)
        available[0, 4] = True
        policy.begin(game, 1, available, 1)
        initial = policy.before_segment(game, state, np.array([0]), schedule(1))
        state.clock[0], state.start[0] = 600, engine.S['made_fg']
        after = policy.before_segment(game, state, np.array([0]), schedule(1))
        np.testing.assert_array_equal(after[0, 0], initial[0, 0])
        state.ingame['pf_so_far'][0, 0] = 6
        with self.assertRaisesRegex(ValueError, 'fewer than five eligible'):
            policy.after_fouls(game, state, np.array([0]), after[:, 0].copy(), after[:, 1].copy())

    def test_foul_out_uses_only_available_bench_and_short_roster_fails(self):
        game = FixtureGame()
        state = engine.Worlds(game, 1, np.random.default_rng(1))
        policy = fixture_policy(game, regulation=[[]])
        available = np.ones((1, game.n), bool)
        available[0, 6] = False
        policy.begin(game, 1, available, 1)
        current = policy.before_segment(game, state, np.array([0]), schedule(1))
        state.off[0] = 0
        offense, defense = current[:, 0].copy(), current[:, 1].copy()
        state.ingame['pf_so_far'][0, 0] = 6
        self.assertTrue(policy.after_fouls(game, state, np.array([0]), offense, defense))
        self.assertNotIn(0, offense[0])
        self.assertIn(5, offense[0])
        self.assertNotIn(6, offense[0])
        self.assertEqual(policy.counts['foul_out_replacements'], 1)
        state.ingame['pf_so_far'][0, 1] = 6
        with self.assertRaisesRegex(ValueError, 'fewer than five eligible'):
            policy.after_fouls(game, state, np.array([0]), offense, defense)

    def test_timeout_clocks_coalesce_expire_and_overtime_uses_its_own_template(self):
        game = FixtureGame()
        state = engine.Worlds(game, 1, np.random.default_rng(1))
        policy = fixture_policy(game, probability=0, regulation=[[[1, 10.], [1, 15.], [2, 1.]]],
                                overtime=[[40.]])
        policy.begin(game, 1, np.ones((1, game.n), bool), 3)
        policy.before_segment(game, state, np.array([0]), schedule(1))
        state.clock[0], state.start[0] = 700, engine.S['made_fg']
        policy.before_segment(game, state, np.array([0]), schedule(1))
        self.assertEqual(policy.counts['coalesced_timeout_clocks'], 1)
        state.period[0], state.clock[0], state.start[0] = 3, 720, engine.S['period_start']
        policy.before_segment(game, state, np.array([0]), schedule(1))
        self.assertEqual(policy.counts['expired_timeout_clocks'], 1)
        state.period[0], state.clock[0], state.start[0] = 5, 300, engine.S['period_start']
        policy.before_segment(game, state, np.array([0]), schedule(1))
        state.clock[0], state.start[0] = 250, engine.S['made_fg']
        policy.before_segment(game, state, np.array([0]), schedule(1))
        self.assertEqual(policy.counts['overtime_timeout_worlds'], 1)

    def test_finish_checks_regulation_and_overtime_accounting(self):
        game = FixtureGame()
        state = engine.Worlds(game, 2, np.random.default_rng(1))
        policy = fixture_policy(game, regulation=[[]], overtime=[[]])
        policy.begin(game, 2, np.ones((2, game.n), bool), 1)
        state.done[:] = True
        state.period[:] = [4, 5]
        for side in (np.arange(5), np.arange(7, 12)):
            state.minutes[:, side, 0] = 48
            state.minutes[1, side, 4] = 5
        policy.finish(game, state)
        state.minutes[0, 0, 0] -= 1
        with self.assertRaisesRegex(ValueError, 'five-player game time'):
            policy.finish(game, state)


class CapturedRebound(Exception):
    def __init__(self, defense):
        self.defense = defense


class FoulReboundModel:
    dated_candidate = False
    who_mm = []
    mu = []
    optional_lineup = []
    bin_secs = [np.array([1.])] * 13
    foul_gap = np.array([0.])
    band_d = np.array([0.])
    band_l = np.array([0.])

    def predict(self, node, cols, n):
        _ = cols
        if node == 'duration':
            return np.tile(np.eye(13)[0], (n, 1))
        if node == 'event':
            return np.tile([1., 0., 0., 0.], (n, 1))
        if node == 'what':
            return np.tile([0., 0., 0., 0., 0., 0., 1., 0.], (n, 1))
        if node == 'free_throw':
            return np.zeros(n)
        raise ValueError(f'unexpected node {node}')


class FoulReboundEngine(engine.Engine):
    def __init__(self, policy):
        self.m = FoulReboundModel()
        self.diag = self.rotation_diag = None
        self.rotation_policy = policy

    def _context(self, g, st, A, L_off, L_def):
        _ = g, st, L_off, L_def
        keys = ('off_usage_sum', 'off_usage_max', 'off_ast_sum', 'off_three_sum', 'off_oreb_sum',
                'off_bigs', 'off_min_mean', 'def_blk_sum', 'def_blk_max', 'def_stl_sum', 'def_dreb_sum',
                'def_pf_sum', 'def_bigs', 'def_min_mean')
        return {key: np.zeros(len(A)) for key in keys}

    def _five(self, g, st, A, L, rel):
        _ = g, st, A, L, rel
        return {}

    def _actor(self, five_cols, slot):
        _ = five_cols, slot
        return {}

    def _choose(self, node, rows, k, rng, n_groups):
        _ = node, rows, k, rng
        return np.zeros(n_groups, dtype=int)

    def _rebound(self, g, st, A, idx, extra, ctx, off_five, def_five,
                 L_off, L_def, shooter_slot, pidx, nxt_off, nxt_start, off, rng):
        _ = g, st, A, idx, extra, ctx, off_five, def_five, L_off, shooter_slot, pidx, nxt_off, nxt_start, off, rng
        raise CapturedRebound(L_def.copy())


class EngineFoulOutHookTests(unittest.TestCase):
    def test_sixth_foul_is_replaced_before_a_missed_free_throw_rebound(self):
        game = FixtureGame()
        policy = fixture_policy(game, regulation=[[]])

        class InjectedWorlds(engine.Worlds):
            def __init__(self, game, worlds, rng):
                super().__init__(game, worlds, rng)
                self.first[:] = self.off[:] = 0
                self.ingame['pf_so_far'][0, 7] = 5
                self.box['pf'][0, 7, 0] = 5

        with patch.object(engine, 'Worlds', InjectedWorlds):
            with self.assertRaises(CapturedRebound) as caught:
                FoulReboundEngine(policy).simulate(game, 1, 4)
        self.assertNotIn(7, caught.exception.defense[0])
        self.assertIn(13, caught.exception.defense[0])
        self.assertEqual(policy.counts['foul_out_replacements'], 1)


if __name__ == '__main__':
    unittest.main()
