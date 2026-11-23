import tempfile
import unittest
from pathlib import Path

import numpy as np

from scripts import views


class WeightedViewsTests(unittest.TestCase):
    def test_advanced_rates_match_independent_integer_replication(self):
        weights = np.array([3, 3, 17, 17], np.int64)
        box = {k: np.array(v) for k, v in {'pts':[0,12,20,30], 'fgm':[0,5,8,12], 'fga':[0,10,15,22],
               'fg3m':[0,2,3,4], 'fg3a':[0,4,6,8], 'fta':[0,0,4,5], 'ast':[0,3,5,8],
               'tov':[0,1,2,4], 'oreb':[0,1,2,3], 'dreb':[0,3,5,6], 'stl':[0,1,2,3]}.items()}
        opponent = {k: a[::-1] for k, a in box.items()}
        repeated = lambda data: {k: np.repeat(a, weights) for k, a in data.items()}
        weighted = views.advanced_world_summaries(box, opponent, weights)
        replicated = views.advanced_world_summaries(repeated(box), repeated(opponent))
        for key, value in weighted.items():
            self.assertEqual(value['worlds'], 4)
            self.assertEqual(value['total'], 40)
            self.assertTrue(value['weighted'])
            self.assertEqual({k: v for k, v in value.items() if k not in ('worlds', 'defined_worlds', 'weighted')},
                             {k: v for k, v in replicated[key].items() if k not in ('worlds', 'defined_worlds', 'weighted')})

    def test_slate_leaders_use_the_same_exact_coupling_as_seasons(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            a, b = np.zeros((2, 2, 15), np.uint8), np.zeros((2, 2, 15), np.uint8)
            a[0, 0, 1] = 10
            b[:, 0, 1] = 5
            np.savez(folder / 'engine_players.npz', a__lines=a, a__ids=['1','2'], b__lines=b, b__ids=['3','4'])
            np.savez(folder / 'season_player_indices.npz', a=[0,0,0,1], b=[0,1,0,1], weights=np.ones(4, np.int64))
            self.assertEqual(views.lead_chances(folder, ['a','b'], 'pts', ['1','3']), {'1': .75, '3': .25})

    def test_duel_and_lead_probabilities_use_mass_and_empirical_quantiles(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            lines = np.zeros((2,2,15), np.uint8)
            lines[:, :, 1] = [[10,0],[0,5]]
            points = np.zeros((2,2,5), np.int16)
            points[:, :, 0] = lines[:,:,1]
            np.savez(folder / 'engine_players.npz', g__lines=lines, g__ids=['1','2'], g__weights=np.array([3,1]))
            np.savez(folder / 'engine_worlds.npz', g=points)
            duel = views.scorer_duel(folder, 'g', '1', '2')
            self.assertEqual((duel['p_a'],duel['p_b'],duel['worlds']),(.75,.25,2))
            fan = views.lead_fan(folder, 'g')
            self.assertEqual(fan['p_lead'], [.75]*4)
            self.assertEqual(fan['q'], [[-5,-5,10,10,10]]*4)


if __name__ == '__main__':
    unittest.main()
