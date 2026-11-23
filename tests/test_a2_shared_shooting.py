import unittest

import numpy as np
import pandas as pd

from analysis.a2_shared_shooting import terms, evaluate


class SharedShootingTests(unittest.TestCase):
    def test_different_player_pairs_and_bootstrap_recentering(self):
        rows = pd.DataFrame([
            ['F1', '1', 'a', 'x', .3], ['F1', '1', 'a', 'x', -.4],
            ['F1', '1', 'a', 'y', .7], ['F1', '1', 'b', 'z', -.2],
            ['F1', '1', 'b', 'w', .1], ['F1', '2', 'a', 'x', .8],
            ['F1', '2', 'a', 'y', -.1], ['F1', '2', 'b', 'z', .4],
            ['F1', '2', 'b', 'w', -.5]], columns=['fold', 'game_id', 'team', 'player', 'residual'])
        v, counts = terms(rows)
        self.assertEqual(counts['team_games'], 4)
        for weights in ([1, 1], [2, 0], [1, 3]):
            repeated = pd.concat([rows[rows['game_id'].eq(str(i + 1))] for i, k in enumerate(weights) for _ in range(k)])
            centre = repeated['residual'].mean()
            teammate, opponent = [], []
            for i, k in enumerate(weights):
                game = rows[rows['game_id'].eq(str(i + 1))]
                for _ in range(k):
                    for _, team in game.groupby('team'):
                        products = [(a.residual - centre) * (b.residual - centre)
                                    for a in team.itertuples() for b in team.itertuples() if a.player != b.player]
                        teammate.append(np.mean(products))
                    a, b = (g for _, g in game.groupby('team'))
                    opponent.append(np.mean([(x - centre) * (y - centre) for x in a.residual for y in b.residual]))
            actual = evaluate(v, np.array([weights], float))
            self.assertAlmostEqual(actual['teammate'][0], np.mean(teammate))
            self.assertAlmostEqual(actual['opponent'][0], np.mean(opponent))
