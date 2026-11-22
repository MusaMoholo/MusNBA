import json
import unittest
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

import numpy as np

from scripts import a1_branch_foul_out, a1_branch_world_probe, a1_foul_out_probe, a1_lineup_branches, engine, minutes, projection


class OnePlayerBranchesTests(unittest.TestCase):
    def game(self, size=7):
        game = object.__new__(engine.Game)
        game.game = {'game_id': '123', 'home_id': '1', 'away_id': '2'}
        game.sides = ('home', 'away')
        game.side = np.repeat([0, 1], size)
        game.ids = [str(100 + i) for i in range(size)] + [str(200 + i) for i in range(size)]
        game.avail = np.ones(2 * size)
        game.avail[0] = 0.5
        game.expected = np.full(2 * size, 20.0)
        game.mstate = []
        game.players = {}
        for side in game.sides:
            players = []
            offset = 0 if side == 'home' else size
            for i in range(size):
                healthy = 36.0 if i == 0 else 28.0 - i
                state = {'healthy': healthy, 'cap': 40.0, 'ramp': 1.0, 'rotation': 1.0,
                         'priority': healthy, 'start_share': 1.0 if i < 5 else 0.0,
                         'sd_table': {'edges': [0, 10, 20, 30, 40, 50], 'sd': {}}}
                game.mstate.append(state)
                players.append({'id': game.ids[offset + i], 'pos': 'G', 'minutes': state,
                                'availability': game.avail[offset + i], 'starter': i < 5,
                                'projected_starter': i < 5})
            game.players[side] = players
        game.lineup = {0: list(range(5)), 1: list(range(5))}
        game.templates = {0: [], 1: []}
        game.strict_minute_targets = False
        n = len(game.ids)
        game.n = n
        game.P = {'grp_code': np.zeros(n), 'min_avg': np.full(n, 25.0),
                  'height_in': np.full(n, 78.0), 'weight_lb': np.full(n, 210.0),
                  'm_fg_rim': np.full(n, 0.2)}
        game.P['m_fg_rim'][0] = 0.9
        return game

    def selection_inputs(self):
        game = self.game()
        game.day, game.input_before = '2026-01-02', '2026-01-01'
        game.P['usage'] = np.full(game.n, 0.1)
        registry, latest, inputs = {}, {}, {}
        for side in game.sides:
            team_id = str(game.game[f'{side}_id'])
            for player in game.players[side]:
                player['status'], player['availability_basis'] = 'Questionable', 'status'
                registry[player['id']] = {'team': team_id, 'on_roster': True,
                                           'status': 'Questionable', 'status_source': 'report'}
                latest[player['id']] = {'games': 1, 'last_date': '2025-12-30'}
                inputs[player['id']] = {'healthy_role': game.mstate[game.ids.index(player['id'])]['healthy'],
                                        'value': 1.0, 'availability': player['availability'], 'status': player['status'],
                                        'availability_basis': player['availability_basis']}
        return game, registry, latest, inputs

    def test_selects_only_highest_ranked_uncertainty_per_team(self):
        game, registry, latest, inputs = self.selection_inputs()
        for index in (1, 3, 7, 8):
            game.avail[index] = 0.5
            side = 'home' if index < 7 else 'away'
            player = game.players[side][index % 7]
            player['availability'] = inputs[player['id']]['availability'] = 0.5
        selected, ranking = a1_lineup_branches.select_uncertain(game, registry, latest, inputs)
        self.assertEqual([p.player_id for p in selected], ['100', '200'])
        self.assertEqual([p.impact_rank for p in selected], [1, 1])
        self.assertEqual(len(ranking), 14)
        self.assertEqual(selected[0].status_source, 'report')
        self.assertEqual(selected[0].probability, 0.5)

    def test_selection_rejects_stale_rosters_and_future_or_invalid_criteria(self):
        game, registry, latest, inputs = self.selection_inputs()
        registry['100']['team'] = '2'
        with self.assertRaisesRegex(ValueError, 'roster'):
            a1_lineup_branches.select_uncertain(game, registry, latest, inputs)
        registry['100']['team'] = '1'
        latest['100']['last_date'] = game.input_before
        with self.assertRaisesRegex(ValueError, 'before'):
            a1_lineup_branches.select_uncertain(game, registry, latest, inputs)
        latest['100']['last_date'] = '2025-12-30'
        game.P['usage'][0] = 1.5
        with self.assertRaisesRegex(ValueError, 'usage'):
            a1_lineup_branches.select_uncertain(game, registry, latest, inputs)
        game.P['usage'][0] = 0.1
        inputs['100']['value'] = 1e308
        with self.assertRaisesRegex(ValueError, 'impact score'):
            a1_lineup_branches.select_uncertain(game, registry, latest, inputs)

    def test_out_players_rank_and_uncertainty_outside_top_three_is_excluded(self):
        game, registry, latest, inputs = self.selection_inputs()
        registry['999'] = {'team': '1', 'on_roster': True, 'status': 'Out'}
        inputs['999'] = {'healthy_role': 40, 'value': 2, 'availability': 0, 'status': 'Out'}
        latest['999'] = {'games': 1, 'last_date': '2025-12-30'}
        game.avail[0] = game.players['home'][0]['availability'] = inputs['100']['availability'] = 1
        game.avail[2] = game.players['home'][2]['availability'] = inputs['102']['availability'] = 0.5
        selected, ranking = a1_lineup_branches.select_uncertain(game, registry, latest, inputs)
        self.assertEqual(selected, ())
        self.assertEqual(next(r['rank'] for r in ranking if r['player_id'] == '102'), 4)
        game.avail[1] = game.players['home'][1]['availability'] = inputs['101']['availability'] = 0.5
        latest.pop('101')
        game.P['usage'][1] = np.nan
        selected, _ = a1_lineup_branches.select_uncertain(game, registry, latest, inputs)
        self.assertEqual([p.player_id for p in selected], ['101'])
        self.assertEqual(selected[0].missing, ('observed_role', 'usage'))
        self.assertEqual(selected[0].impact_rank, 3)

    def test_tied_impact_uses_player_id_and_requires_full_roster(self):
        game, registry, latest, inputs = self.selection_inputs()
        game.avail[1] = game.players['home'][1]['availability'] = inputs['101']['availability'] = 0.5
        inputs['101']['value'] = inputs['100']['healthy_role'] / inputs['101']['healthy_role']
        selected, _ = a1_lineup_branches.select_uncertain(game, registry, latest, inputs)
        self.assertEqual(selected[0].player_id, '100')
        del inputs['106']
        with self.assertRaisesRegex(ValueError, 'entire origin roster'):
            a1_lineup_branches.select_uncertain(game, registry, latest, inputs)

    def test_exact_joint_branches_are_order_independent_and_reallocate_together(self):
        game = self.game()
        game.avail[1:3] = [0.3, 0.4]
        game.players['home'][1]['availability'] = 0.3
        game.players['home'][2]['availability'] = 0.4
        selection = [('1', '101'), ('1', '100')]
        branches = a1_lineup_branches.enumerate_branches(game, selection)
        self.assertEqual(branches, a1_lineup_branches.enumerate_branches(game, selection[::-1]))
        self.assertEqual(len(branches), 4)
        self.assertTrue(all(b.weight is not None for b in branches))
        self.assertEqual(sum(b.weight for b in branches if b.weight is not None), 1)
        self.assertEqual({b.branch_id: b.weight for b in branches}, {
            'lineup-v1:1/100=plays,1/101=plays': Fraction(3, 20),
            'lineup-v1:1/100=plays,1/101=sits': Fraction(7, 20),
            'lineup-v1:1/100=sits,1/101=plays': Fraction(3, 20),
            'lineup-v1:1/100=sits,1/101=sits': Fraction(7, 20),
        })
        both_out = a1_lineup_branches.prepare_branch(game, branches[-1].assignments)
        self.assertEqual(both_out.avail[:2].tolist(), [0, 0])
        self.assertEqual(both_out.avail[2], 0.4)
        self.assertEqual(both_out.players['home'][2]['availability'], 0.4)
        self.assertEqual(both_out.expected[:2].tolist(), [0, 0])
        self.assertAlmostEqual(sum(both_out.expected[:7]), 240)
        self.assertEqual(game.avail[:2].tolist(), [0.5, 0.3])

    def test_long_decimal_weights_and_branch_seeds_are_exact_and_reproducible(self):
        game = self.game()
        game.avail[:2] = [0.12345678901234566, 0.9876543210987654]
        selected = [('1', '101'), ('1', '100')]
        branches = a1_lineup_branches.enumerate_branches(game, selected)
        p, q = (Fraction(str(x)) for x in game.avail[:2])
        self.assertEqual(branches[0].weight, p * q)
        self.assertEqual(sum(b.weight for b in branches if b.weight is not None), 1)
        seeds = [projection.seed_for('lineup-v1', 'engine', '2026-01-01', '2026-01-02', '123', b.branch_id)
                 for b in branches]
        again = a1_lineup_branches.enumerate_branches(game, selected[::-1])
        self.assertEqual(seeds, [projection.seed_for('lineup-v1', 'engine', '2026-01-01',
                                                     '2026-01-02', '123', b.branch_id) for b in again])
        self.assertEqual(len(set(seeds)), 4)

    def test_one_player_weights_and_cross_team_assignments(self):
        game = self.game()
        self.assertEqual([b.weight for b in a1_lineup_branches.enumerate_branches(game, [('1', '100')])],
                         [Fraction(1, 2), Fraction(1, 2)])
        game.avail[7] = 0.8
        game.players['away'][0]['availability'] = 0.8
        branches = a1_lineup_branches.enumerate_branches(game, [('2', '200'), ('1', '100')])
        self.assertEqual([b.weight for b in branches], [Fraction(2, 5), Fraction(1, 10),
                                                       Fraction(2, 5), Fraction(1, 10)])
        prepared = a1_lineup_branches.prepare_branch(game, branches[-1].assignments)
        self.assertEqual([prepared.avail[0], prepared.avail[7]], [0, 0])
        self.assertAlmostEqual(sum(prepared.expected[:7]), 240)
        self.assertAlmostEqual(sum(prepared.expected[7:]), 240)

    def test_more_than_two_are_unweighted_non_exhaustive_sensitivities(self):
        game = self.game()
        game.avail[1:3] = [0.3, 0.7]
        branches = a1_lineup_branches.enumerate_branches(game, [('1', '102'), ('1', '100'), ('1', '101')])
        self.assertEqual(len(branches), 4)
        self.assertTrue(all(b.weight is None for b in branches))
        self.assertEqual([[plays for _, _, plays in b.assignments] for b in branches],
                         [[True, True, True], [False, True, True], [True, False, True], [True, True, False]])
        for branch in branches:
            prepared = a1_lineup_branches.prepare_branch(game, branch.assignments)
            self.assertEqual(prepared.avail[:3].tolist(), [float(x[2]) for x in branch.assignments])

    def test_branch_enumeration_rejects_missing_invalid_or_duplicate_selections(self):
        game = self.game()
        for selection in ([], [('1', '100'), ('1', '100')], [('2', '100')],
                          [('1', 'missing')], [('1', '101')], [('', '100')]):
            with self.subTest(selection=selection), self.assertRaises(ValueError):
                a1_lineup_branches.enumerate_branches(game, selection)
        game.mstate = None
        with self.assertRaisesRegex(ValueError, 'D29'):
            a1_lineup_branches.enumerate_branches(game, [('1', '100')])
        game = self.game()
        game.ids[1] = '100'
        with self.assertRaisesRegex(ValueError, 'duplicate player'):
            a1_lineup_branches.enumerate_branches(game, [('1', '100')])
        game = self.game()
        with self.assertRaisesRegex(ValueError, 'boolean'):
            a1_lineup_branches.prepare_branch(game, (('1', '100', 1),))  # type: ignore[arg-type]
        for probability in (float('nan'), float('inf'), -0.1, 1.1, 0.0, 1.0):
            game.avail[0] = probability
            with self.subTest(probability=probability), self.assertRaises(ValueError):
                a1_lineup_branches.enumerate_branches(game, [('1', '100')])

    def test_two_out_fails_explicitly_when_not_enough_players_remain(self):
        game = self.game(size=6)
        game.avail[1] = 0.3
        with self.assertRaisesRegex(ValueError, 'fewer than five'):
            a1_lineup_branches.prepare_branch(game, (('1', '100', False), ('1', '101', False)))

    def test_branches_reallocate_and_form_eligible_defending_fives(self):
        original = self.game()
        branches = [a1_lineup_branches.one_player(original, '1', '100', plays) for plays in (True, False)]
        self.assertEqual(original.avail[0], 0.5)
        self.assertEqual(original.lineup[0], list(range(5)))
        self.assertEqual(branches[0].avail[0], 1)
        self.assertEqual(branches[1].avail[0], 0)
        self.assertEqual(branches[1].expected[0], 0)
        self.assertAlmostEqual(sum(branches[1].expected[:7]), 240)
        self.assertGreater(branches[1].expected[5:].sum(), branches[0].expected[5:].sum())

        theta_path = Path(__file__).resolve().parents[1] / 'models' / 'matchup_2025-12-31.json'
        model = object.__new__(engine.Models)
        model.theta = json.loads(theta_path.read_text())
        eng = object.__new__(engine.Engine)
        eng.m = model
        values = []
        for branch in branches:
            available = np.broadcast_to(branch.avail > 0, (1, len(branch.ids)))
            tables, combos = branch.lineup_tables(available, np.random.default_rng(42))
            for side in range(2):
                lineup = tables[combos[0, side]]
                self.assertTrue(available[0, lineup].all())
                self.assertTrue((np.sort(lineup, axis=1)[:, 1:] != np.sort(lineup, axis=1)[:, :-1]).all())
            defence = tables[combos[0, 0], 0][None, :]
            values.append(eng._mu(branch, defence, np.array([7]), np.array([0]))['mu_fg_rim'][0])
        self.assertGreater(values[0], values[1])

    def test_short_rosters_and_invalid_overrides_fail(self):
        with self.assertRaisesRegex(ValueError, 'fewer than five'):
            a1_lineup_branches.one_player(self.game(size=5), '1', '100', False)
        for team, player, plays in (('2', '100', False), ('1', '101', False)):
            with self.subTest(team=team, player=player, plays=plays), self.assertRaises(ValueError):
                a1_lineup_branches.one_player(self.game(), team, player, plays)
        with self.assertRaisesRegex(ValueError, 'boolean'):
            a1_lineup_branches.one_player(self.game(), '1', '100', 1)  # type: ignore[arg-type]
        with patch.object(minutes, 'game_targets', return_value=np.zeros(6)):
            with self.assertRaisesRegex(ValueError, 'legal 240-minute allocation'):
                a1_lineup_branches.one_player(self.game(), '1', '100', False)

    def test_trace_observes_without_changing_the_scheduled_lineup(self):
        game = self.game()
        state = engine.Worlds(game, 1, np.random.default_rng(42))
        lineup = np.array([[[0, 1, 2, 3, 4], [7, 8, 9, 10, 11]]])
        available = np.ones((1, game.n), dtype=bool)
        policy = a1_branch_world_probe.TracePolicy()
        policy.begin(game, 1, available, 42)
        before = lineup.copy()
        self.assertIs(policy.before_segment(game, state, np.array([0]), lineup), lineup)
        np.testing.assert_array_equal(lineup, before)
        self.assertFalse(policy.after_fouls(game, state, np.array([0]), lineup[:, 0], lineup[:, 1]))
        state.done[:] = True
        policy.finish(game, state)
        saved = policy.capture(game, state)
        lineup[0, 0, 0] = 5
        self.assertEqual(saved['trace_lineups'][0, 0, 0], 0)

    def test_branch_guard_rejects_sixth_foul_without_changing_legal_lineups(self):
        game = self.game()
        state = engine.Worlds(game, 1, np.random.default_rng(42))
        lineup = np.array([[[0, 1, 2, 3, 4], [7, 8, 9, 10, 11]]])
        available = np.ones((1, game.n), dtype=bool)
        guard = a1_lineup_branches.BranchLegalityGuard()
        guard.begin(game, 1, available, 42)
        self.assertIs(guard.before_segment(game, state, np.array([0]), lineup), lineup)
        for off in (0, 1):
            state.off[0] = off
            state.ingame['pf_so_far'][0, 0] = 0
            self.assertFalse(guard.after_fouls(game, state, np.array([0]), lineup[:, off], lineup[:, 1 - off]))
            state.ingame['pf_so_far'][0, 0] = 6
            with self.assertRaisesRegex(ValueError, 'world 0 side 0.*unsupported sixth foul for player 100'):
                guard.after_fouls(game, state, np.array([0]), lineup[:, off], lineup[:, 1 - off])
        available[0, 0] = False
        guard.begin(game, 1, available, 42)
        with self.assertRaisesRegex(ValueError, 'invalid five'):
            guard.before_segment(game, state, np.array([0]), lineup)

    def test_guard_stops_the_known_engine_foul_out_defect(self):
        game = a1_foul_out_probe.ProbeGame()
        game.game = {'game_id': '123'}
        game.ids = [str(i) for i in range(game.n)]
        eng = a1_foul_out_probe.ProbeEngine()
        eng.rotation_policy = a1_lineup_branches.BranchLegalityGuard()

        class FouledWorlds(engine.Worlds):
            def __init__(self, g, worlds, rng):
                super().__init__(g, worlds, rng)
                self.ingame['pf_so_far'][0, 0] = 6

        with patch.object(engine, 'Worlds', FouledWorlds):
            with self.assertRaisesRegex(ValueError, 'unsupported sixth foul for player 0'):
                eng.simulate(game, 1, 20261122)

    def test_guarded_trace_surfaces_the_same_explicit_failure(self):
        game = self.game()
        state = engine.Worlds(game, 1, np.random.default_rng(42))
        lineup = np.array([[[0, 1, 2, 3, 4], [7, 8, 9, 10, 11]]])
        trace = a1_branch_world_probe.GuardedTrace()
        trace.begin(game, 1, np.ones((1, game.n), dtype=bool), 42)
        trace.before_segment(game, state, np.array([0]), lineup)
        state.ingame['pf_so_far'][0, 0] = 6
        off = int(state.off[0])
        with self.assertRaises(a1_lineup_branches.BranchLegalityError):
            trace.after_fouls(game, state, np.array([0]), lineup[:, off], lineup[:, 1 - off])

    def test_isolated_foul_out_repairs_only_affected_worlds_and_sides(self):
        game = self.game()
        state = engine.Worlds(game, 3, np.random.default_rng(42))
        state.off[:] = [0, 1, 0]
        state.ingame['pf_so_far'][0, 0] = 6
        state.ingame['pf_so_far'][2, 7] = 6
        lineup = np.tile(np.array([[[0, 1, 2, 3, 4], [7, 8, 9, 10, 11]]]), (3, 1, 1))
        original = lineup.copy()
        active = np.arange(3)
        policy = a1_branch_foul_out.BranchFoulOutPolicy()
        policy.begin(game, 3, np.ones((3, game.n), dtype=bool), 42)
        offense = lineup[active, state.off].copy()
        defense = lineup[active, 1 - state.off].copy()
        changed = policy.after_fouls(game, state, active, offense, defense)
        np.testing.assert_array_equal(changed, [True, False, True])
        np.testing.assert_array_equal(offense[1], original[1, 1])
        np.testing.assert_array_equal(defense[1], original[1, 0])
        self.assertEqual(offense[0, 0], 5)
        self.assertEqual(defense[2, 0], 12)
        np.testing.assert_array_equal(lineup, original)
        repaired = policy.before_segment(game, state, active, lineup)
        self.assertEqual(repaired[0, 0, 0], 5)
        self.assertEqual(repaired[2, 1, 0], 12)
        self.assertEqual(policy.counts, {'scheduled_replacements': 2, 'foul_out_replacements': 2})

    def test_repaired_trace_records_only_changed_post_foul_worlds(self):
        game = self.game()
        state = engine.Worlds(game, 2, np.random.default_rng(42))
        state.off[:] = [0, 1]
        lineup = np.tile(np.array([[[0, 1, 2, 3, 4], [7, 8, 9, 10, 11]]]), (2, 1, 1))
        active = np.arange(2)
        policy = a1_branch_world_probe.RepairedTrace()
        policy.begin(game, 2, np.ones((2, game.n), dtype=bool), 42)
        policy.before_segment(game, state, active, lineup)
        state.ingame['pf_so_far'][0, 7] = 6
        offense = lineup[active, state.off].copy()
        defense = lineup[active, 1 - state.off].copy()
        np.testing.assert_array_equal(policy.after_fouls(game, state, active, offense, defense), [True, False])
        post = policy.trace[-1]
        np.testing.assert_array_equal(post['world'], [0])
        np.testing.assert_array_equal(post['phase'], [1])
        self.assertEqual(post['lineups'][0, 1, 0], 12)
        self.assertFalse((post['fouls'] >= 6).any())

    def test_isolated_foul_out_handles_multiple_replacements_and_fails_short(self):
        game = self.game()
        state = engine.Worlds(game, 1, np.random.default_rng(42))
        lineup = np.array([[[0, 1, 2, 3, 4], [7, 8, 9, 10, 11]]])
        available = np.ones((1, game.n), dtype=bool)
        policy = a1_branch_foul_out.BranchFoulOutPolicy()
        policy.begin(game, 1, available, 42)
        state.ingame['pf_so_far'][0, :2] = 6
        repaired = policy.before_segment(game, state, np.array([0]), lineup)
        np.testing.assert_array_equal(repaired[0, 0], [5, 6, 2, 3, 4])
        available[0, 6] = False
        policy.begin(game, 1, available, 42)
        with self.assertRaisesRegex(a1_lineup_branches.BranchLegalityError, 'fewer than five eligible'):
            policy.before_segment(game, state, np.array([0]), lineup)
        lineup[0, 0, 1] = 0
        with self.assertRaisesRegex(a1_lineup_branches.BranchLegalityError, 'invalid scheduled five'):
            policy.before_segment(game, state, np.array([0]), lineup)

    def test_isolated_replacement_respects_availability_and_active_world_indices(self):
        game = self.game()
        state = engine.Worlds(game, 3, np.random.default_rng(42))
        lineup = np.tile(np.array([[[0, 1, 2, 3, 4], [7, 8, 9, 10, 11]]]), (2, 1, 1))
        available = np.ones((3, game.n), dtype=bool)
        available[2, 0] = False
        available[2, 5] = False
        state.ingame['pf_so_far'][2, 7] = 6
        policy = a1_branch_foul_out.BranchFoulOutPolicy()
        policy.begin(game, 3, available, 42)
        result = policy.before_segment(game, state, np.array([0, 2]), lineup)
        np.testing.assert_array_equal(result[0], lineup[0])
        self.assertEqual(result[1, 0, 0], 6)
        self.assertEqual(result[1, 1, 0], 12)
        self.assertEqual(policy.counts['scheduled_replacements'], 2)


if __name__ == '__main__':
    unittest.main()
