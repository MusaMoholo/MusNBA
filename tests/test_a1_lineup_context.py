import unittest
from unittest.mock import patch

import numpy as np

from scripts import a1_foul_out_probe, engine


LINEUP_COLUMNS = ('off_usage_sum', 'off_usage_max', 'off_ast_sum', 'off_three_sum', 'off_oreb_sum',
                  'off_bigs', 'off_min_mean', 'def_blk_sum', 'def_blk_max', 'def_stl_sum', 'def_dreb_sum',
                  'def_pf_sum', 'def_bigs', 'def_min_mean')


class CapturedPenalty(Exception):
    def __init__(self, world_cols, five_cols):
        self.world_columns = {key: value.copy() for key, value in world_cols.items()}
        self.five_columns = {key: value.copy() for key, value in five_cols.items()}


class TwoWorldGame(a1_foul_out_probe.ProbeGame):
    def lineup_tables(self, avail_world, rng):
        tables, _ = super().lineup_tables(avail_world, rng)
        return tables, np.tile([0, 1], (len(avail_world), 1))


class ControlledModels:
    dated_candidate = False
    who_mm: list[str] = []
    mu = ()
    optional_lineup = ('optional_lineup_probe',)
    bin_secs = [np.array([1.0])]
    penalty = np.ones(20)

    def predict(self, node, columns, size):
        if node == 'duration':
            return np.ones((size, 1))
        if node == 'event':
            result = np.zeros((size, 4))
            result[:, 1] = 1
            return result
        raise AssertionError(f'unexpected node {node}')


class ControlledEngine(engine.Engine):
    def __init__(self):
        self.m = ControlledModels()
        self.diag = self.rotation_diag = None
        self.rotation_policy = None
        self.context_calls = []
        self.five_calls = []
        self.penalty_columns: dict[str, np.ndarray] | None = None
        self.penalty_five: dict[str, np.ndarray] | None = None

    def _context(self, g, st, A, L_off, L_def):
        self.context_calls.append(A.copy())
        marker = 100 * len(self.context_calls) + L_def[:, 0]
        return {**{key: marker.astype(float) for key in (*LINEUP_COLUMNS, *self.m.optional_lineup)},
                'fouls_def': np.zeros(len(A))}

    def _five(self, g, st, A, L, rel):
        self.five_calls.append(A.copy())
        return {'marker': np.repeat(L[:, :1], 5, axis=1)}

    def _actor(self, five_cols, slot):
        return {}

    def _mu(self, g, L_def, actor_glob, rows, L_off=None, actor_slot=None):
        return {}

    def _fouler(self, g, st, A, idx, shooting, ctx, def_five, L_def, pidx, rng):
        pass

    @staticmethod
    def _flat(world_cols, five_cols, keep=None):
        raise CapturedPenalty(world_cols, five_cols)


class Policy:
    def __init__(self, changed: bool | np.bool_ | np.ndarray, side='defense'):
        self.changed = changed
        self.side = side
        self.counts = {}

    def begin(self, g, worlds, available, seed):
        pass

    def before_segment(self, g, st, active, scheduled):
        return scheduled

    def after_fouls(self, g, st, active, offense, defense) -> bool | np.bool_ | np.ndarray:
        if isinstance(self.changed, np.ndarray) and self.changed.size and self.changed[0]:
            lineup = offense if self.side == 'offense' else defense
            lineup[0, 0] = 5 if lineup[0, 0] < 6 else 11
        return self.changed

    def finish(self, g, st):
        pass


class LineupContextTests(unittest.TestCase):
    def run_until_penalty(self, policy):
        simulation = ControlledEngine()
        simulation.rotation_policy = policy
        with self.assertRaises(CapturedPenalty) as capture:
            simulation.simulate(TwoWorldGame(), 2, 42)
        simulation.penalty_columns = capture.exception.world_columns
        simulation.penalty_five = capture.exception.five_columns
        return simulation

    def test_mask_refreshes_only_changed_worlds(self):
        for side in ('offense', 'defense'):
            with self.subTest(side=side):
                simulation = self.run_until_penalty(Policy(np.array([True, False]), side))
                self.assertEqual([x.tolist() for x in simulation.context_calls], [[0, 1], [0]])
                self.assertEqual([x.tolist() for x in simulation.five_calls], [[0, 1], [0, 1], [0], [0]])
                assert simulation.penalty_columns is not None
                for key in ('def_blk_sum', 'optional_lineup_probe'):
                    markers = simulation.penalty_columns[key]
                    self.assertGreater(markers[0], 200)
                    self.assertLess(markers[1], 200)

    def test_legacy_boolean_and_no_policy_paths(self):
        results = []
        for policy, expected in ((None, [[0, 1]]), (Policy(False), [[0, 1]]),
                                 (Policy(np.bool_(False)), [[0, 1]]),
                                 (Policy(True), [[0, 1], [0, 1]])):
            with self.subTest(policy=policy):
                simulation = self.run_until_penalty(policy)
                self.assertEqual([x.tolist() for x in simulation.context_calls], expected)
                results.append(simulation)
        assert results[0].penalty_columns is not None and results[1].penalty_columns is not None
        for key in results[0].penalty_columns:
            np.testing.assert_array_equal(results[0].penalty_columns[key], results[1].penalty_columns[key])

    def test_empty_change_mask_does_not_refresh_context(self):
        simulation = self.run_until_penalty(Policy(np.array([False, False])))
        self.assertEqual([x.tolist() for x in simulation.context_calls], [[0, 1]])

    def test_bad_mask_fails_explicitly(self):
        for invalid in (np.array([True]), np.array([1, 0])):
            with self.subTest(mask=invalid):
                simulation = ControlledEngine()
                simulation.rotation_policy = Policy(invalid)
                with self.assertRaisesRegex(ValueError, 'mask'):
                    simulation.simulate(TwoWorldGame(), 2, 42)

    def test_mask_must_not_omit_a_changed_lineup(self):
        class IncorrectPolicy(Policy):
            def after_fouls(self, g, st, active, offense, defense):
                defense[0, 0] = 5 if defense[0, 0] < 6 else 11
                return np.array([False, False])

        simulation = ControlledEngine()
        simulation.rotation_policy = IncorrectPolicy(False)
        with self.assertRaisesRegex(ValueError, 'mask omitted'):
            simulation.simulate(TwoWorldGame(), 2, 42)

    def test_changed_mismatch_features_fail_explicitly(self):
        simulation = ControlledEngine()
        simulation.m.who_mm = ['cand_edge']
        simulation.rotation_policy = Policy(np.array([True, False]))
        game = TwoWorldGame()
        game.P = {key: np.zeros(game.n) for fields in engine.nodes.MIX_ZONE.values() for key in fields}
        with patch.object(engine.nodes, 'mismatch_edges', return_value=np.zeros((2, 5))):
            with self.assertRaisesRegex(ValueError, 'mismatch'):
                simulation.simulate(game, 2, 42)


if __name__ == '__main__':
    unittest.main()
