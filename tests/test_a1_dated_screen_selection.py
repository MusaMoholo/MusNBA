import tempfile
import unittest
from pathlib import Path

import numpy as np

from analysis.a1_dated_screen_selection import compare, load_capture
from basketball_common import sha256_file


class DatedScreenSelectionTest(unittest.TestCase):
    def test_comparison_resamples_whole_games_and_retains_failed_mass(self):
        survivors = np.array([[10., 4., 14., 6.], [14., 6., 20., 8.]])
        continued = np.array([[30., 10., 40., 20.], [14., 6., 20., 8.]])
        counts = np.array([1, 1])
        all_counts = np.array([2, 1])
        draws = np.array([[0, 0], [1, 1], [0, 1]])
        result = compare(survivors, counts, continued, all_counts, draws)
        self.assertAlmostEqual(result['total_points']['difference'], 17 - 20)
        np.testing.assert_allclose(result['total_points']['ci_95'],
                                   np.quantile([14 - 20, 0, 17 - 20], [0.025, 0.975]))
        with self.assertRaisesRegex(ValueError, 'dimensions'):
            compare(survivors, counts, continued, all_counts, np.array([[0]]))

    def test_capture_requires_matching_hash_game_and_player_score(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'world.npz'
            np.savez_compressed(path, game_id=np.array('123'), final_score=np.array([[2, 1]]),
                                team_points=np.array([[[2], [1]]]),
                                side=np.array([0, 0, 1]), available=np.array([[True, False, True]]),
                                player_ids=np.array(['a', 'b', 'c']),
                                player_points=np.array([[[2], [0], [1]]]),
                                minutes=np.array([[[1 / 60], [0], [1]]]))
            digest = sha256_file(path)
            score, players = load_capture(path, digest, '123')
            np.testing.assert_array_equal(score, [2, 1, 3, 1])
            self.assertEqual(players, {'a': [2, 1 / 60]})
            with self.assertRaisesRegex(ValueError, 'hash differs'):
                load_capture(path, 'bad', '123')
            with self.assertRaisesRegex(ValueError, 'game differs'):
                load_capture(path, digest, '456')


if __name__ == '__main__':
    unittest.main()
