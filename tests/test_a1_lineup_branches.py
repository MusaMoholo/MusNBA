import json
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np

from scripts import a1_lineup_branches, engine, minutes


class OnePlayerBranchesTests(unittest.TestCase):
    def game(self, size=7):
        game = object.__new__(engine.Game)
        game.game = {'home_id': '1', 'away_id': '2'}
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
        game.P = {'grp_code': np.zeros(n), 'min_avg': np.full(n, 25.0),
                  'height_in': np.full(n, 78.0), 'weight_lb': np.full(n, 210.0),
                  'm_fg_rim': np.full(n, 0.2)}
        game.P['m_fg_rim'][0] = 0.9
        return game

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


if __name__ == '__main__':
    unittest.main()
