import unittest

import numpy as np
import pandas as pd

from scripts import a2_residual_dependence as screen


class ResidualDependenceTests(unittest.TestCase):
    def test_pair_covariances_recenter_roles_for_each_game_resample(self):
        rows = pd.DataFrame([
            ('1', 'a', 'star', 2., 4.), ('1', 'a', 'bench', 4., 1.),
            ('1', 'a', 'bench', 7., 8.), ('1', 'b', 'star', -1., 3.),
            ('1', 'b', 'starter', 3., 9.), ('2', 'c', 'star', 9., 7.),
            ('2', 'c', 'starter', 2., 4.), ('2', 'd', 'star', 8., -3.),
            ('2', 'd', 'bench', -2., 2.),
        ], columns=['game_id', 'team', 'tier', 'minutes', 'points_per_36'])
        terms, counts = screen.build_terms(rows, ['1', '2'])
        weights = np.array([[1, 1], [2, 0], [1, 2]])
        result = screen.evaluate(terms, weights)
        self.assertEqual((counts['team_games'], counts['teammate_ordered_pairs'], counts['opponent_pairs']),
                         (4, 12, 10))
        for index, (first, second) in enumerate(weights):
            sample = pd.concat([rows[rows['game_id'].eq('1')]] * first
                               + [rows[rows['game_id'].eq('2')]] * second)
            for metric_index, metric in enumerate(screen.METRICS):
                means = sample.groupby('tier')[metric].mean()
                teammate, opponent = [], []
                for gid in ['1'] * first + ['2'] * second:
                    game = rows[rows['game_id'].eq(gid)]
                    teams = [side for _, side in game.groupby('team', sort=True)]
                    for side in teams:
                        values = [row[metric] - means[row['tier']] for _, row in side.iterrows()]
                        teammate.append(np.mean([x * y for i, x in enumerate(values)
                                                 for j, y in enumerate(values) if i != j]))
                    left = [row[metric] - means[row['tier']] for _, row in teams[0].iterrows()]
                    right = [row[metric] - means[row['tier']] for _, row in teams[1].iterrows()]
                    opponent.append(np.mean([x * y for x in left for y in right]))
                self.assertAlmostEqual(result['teammate'][index, metric_index], np.mean(teammate))
                self.assertAlmostEqual(result['opponent'][index, metric_index], np.mean(opponent))
                self.assertAlmostEqual(result['difference'][index, metric_index],
                                       np.mean(teammate) - np.mean(opponent))

    def test_missing_role_and_small_minutes_are_not_replaced(self):
        control = pd.DataFrame({'game_id': ['1'] * 4, 'player': list('abcd'),
                                'min_actual': [10, 10, 7, 10], 'min_sim': [10] * 4,
                                'pts_actual': [5] * 4, 'pts_sim': [5] * 4})
        roles = pd.DataFrame({'game_id': ['1'] * 3, 'player': list('abc'),
                              'team': ['t'] * 3, 'tier': ['star', 'unknown', 'bench']})
        rows, counts = screen.prepare(control, roles)
        self.assertEqual(rows['player'].tolist(), ['a'])
        self.assertEqual((counts['unmatched'], counts['matched_unknown_role'],
                          counts['matched_known_role_below_minutes_threshold']), (1, 1, 1))
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            screen.prepare(pd.concat([control, control.iloc[:1]]), roles)


if __name__ == '__main__':
    unittest.main()
