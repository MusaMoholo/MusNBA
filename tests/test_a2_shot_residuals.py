import unittest

import numpy as np
import pandas as pd

from scripts import a2_shot_residuals as screen


class ShotResidualTests(unittest.TestCase):
    def test_player_pair_estimator_and_equal_game_weight(self):
        shots = pd.DataFrame({
            'fold': ['F1'] * 6, 'game_id': ['a', 'a', 'a', 'b', 'b', 'b'],
            'player': ['1', '1', '2', '3', '3', '3'], 'tier': ['star'] * 6,
            'residual': [.8, -.2, .5, .5, .5, .5],
        })
        games = screen.player_games(shots)
        self.assertEqual(len(games), 2)
        self.assertAlmostEqual(games.iloc[0]['pair_mean'], -.16)
        self.assertAlmostEqual(games.iloc[1]['pair_mean'], .25)
        self.assertEqual(games['ordered_pairs'].sum(), 8)
        many = pd.concat([games.assign(game_id=str(i)) for i in range(50)], ignore_index=True)
        result = screen.summarize(many)
        self.assertEqual(result['status'], 'supported')
        self.assertAlmostEqual(result['estimate'], .045)
        self.assertEqual(screen.summarize(games)['status'], 'insufficient')

    def test_missing_and_wrong_team_roles_and_unrecorded_actors_are_excluded(self):
        shots = pd.DataFrame({
            'fold': ['F1'] * 4, 'game_id': ['a'] * 4, 'actor': ['1', '2', '3', '4'],
            'offense': ['t'] * 4, 'made': [1, 0, 1, 0], 'probability': [.4] * 4,
            'off_1': ['1'] * 4, 'off_2': ['2'] * 4, 'off_3': ['3'] * 4,
            'off_4': ['5'] * 4, 'off_5': ['6'] * 4,
        })
        roles = pd.DataFrame({'game_id': ['a', 'a'], 'player': ['1', '2'],
                              'team': ['t', 'other'], 'tier': ['star', 'bench']})
        rows, counts = screen.attach_roles(shots, roles)
        self.assertEqual(rows['player'].tolist(), ['1'])
        self.assertTrue(np.allclose(rows['residual'], [.6]))
        self.assertEqual(counts, {'shots': 4, 'actor_outside_recorded_five': 1,
                                  'missing_wrong_team_or_unknown_role': 2, 'eligible_shots': 1})


if __name__ == '__main__':
    unittest.main()
