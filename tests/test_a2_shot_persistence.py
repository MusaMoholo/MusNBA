import unittest

import numpy as np
import pandas as pd

from scripts import a2_shot_persistence as screen


class ShotPersistenceTests(unittest.TestCase):
    def test_two_way_weights_recenter_and_exclude_same_game_pairs(self):
        source = pd.DataFrame([
            ('F1', 'g1', 'a', 'star', 2, 1.0), ('F1', 'g2', 'a', 'star', 3, 0.4),
            ('F1', 'g3', 'a', 'star', 2, -0.5), ('F1', 'g1', 'b', 'star', 2, -0.2),
            ('F1', 'g2', 'b', 'star', 2, 0.8), ('F1', 'g2', 'c', 'bench', 2, -0.6),
            ('F1', 'g3', 'c', 'bench', 4, 0.3), ('F1', 'g1', 'd', 'star', 2, 0.3),
        ], columns=['fold', 'game_id', 'player', 'tier', 'shots', 'residual_sum'])
        rows = screen.prepare(source)
        self.assertNotIn('d', set(rows['player']))
        player_weights = np.array([[1, 1, 1], [1, 2, 1], [0, 1, 2]])
        game_weights = np.array([[1, 1, 1], [2, 0, 1], [1, 2, 1]])
        actual = screen.evaluate(rows, {'F1': (player_weights, game_weights)})
        players, games = sorted(rows.player.unique()), sorted(rows.game_id.unique())
        for replicate in range(len(player_weights)):
            for role in ('star', 'bench'):
                data = rows[rows.tier.eq(role)]
                eligible = []
                for player, group in data.groupby('player'):
                    if sum(game_weights[replicate, games.index(g)] > 0 for g in group.game_id) >= 2:
                        eligible.append((player, group))
                weighted_r = weighted_n = 0.0
                for player, group in eligible:
                    wp = player_weights[replicate, players.index(player)]
                    for row in group.itertuples():
                        weight = wp * game_weights[replicate, games.index(row.game_id)]
                        weighted_r += weight * row.residual_sum
                        weighted_n += weight * row.shots
                if not weighted_n:
                    continue
                center = weighted_r / weighted_n
                total = denominator = 0.0
                for player, group in eligible:
                    wp = player_weights[replicate, players.index(player)]
                    pairs = []
                    for a in group.itertuples():
                        for b in group.itertuples():
                            if a.game_id == b.game_id:
                                continue
                            w = (game_weights[replicate, games.index(a.game_id)]
                                 * game_weights[replicate, games.index(b.game_id)])
                            pairs.append((w * (a.residual_sum - center * a.shots)
                                          * (b.residual_sum - center * b.shots), w * a.shots * b.shots))
                    pair_den = sum(pair[1] for pair in pairs)
                    if pair_den:
                        total += wp * sum(pair[0] for pair in pairs) / pair_den
                        denominator += wp
                role_index = screen.ROLES.index(role)
                self.assertAlmostEqual(actual['sums'][replicate, 0, role_index], total)
                self.assertEqual(actual['totals'][replicate, 0, role_index], denominator)

    def test_duplicate_player_games_and_empty_resample_fail(self):
        row = pd.DataFrame([('F1', 'g1', 'a', 'star', 2, 1.0),
                            ('F1', 'g2', 'a', 'star', 2, 0.5)],
                           columns=['fold', 'game_id', 'player', 'tier', 'shots', 'residual_sum'])
        with self.assertRaisesRegex(ValueError, 'duplicated'):
            screen.prepare(pd.concat([row, row.iloc[:1]]))
        result = screen.evaluate(screen.prepare(row), {'F1': (np.array([[1]]), np.array([[2, 0]]))})
        with self.assertRaisesRegex(ValueError, 'no eligible cross-game pairs'):
            screen.cohort_value(result, 'F1', 'star')


if __name__ == '__main__':
    unittest.main()
