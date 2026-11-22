import copy
import unittest

from scripts import smoke


class ShootingAccountingTests(unittest.TestCase):
    def test_histograms_account_for_no_attempt_worlds(self):
        counts = {'min': 0, 'hist': [1, 0, 2]}
        percentage = {'min': 0, 'hist': [1, 0, 1], 'defined': 2, 'total': 3}
        zero = {'min': 0, 'hist': [3]}
        stats = {'fga': counts, 'fg3a': zero, 'fta': zero, 'fgpct': percentage}
        self.assertEqual(smoke.player_hist_problems(stats, 3, True), [])
        broken = copy.deepcopy(stats)
        broken['fgpct']['defined'] = 3
        self.assertIn('fgpct conditional histogram count', smoke.player_hist_problems(broken, 3, True))
        del broken['fgpct']
        self.assertIn('fgpct conditional histogram count', smoke.player_hist_problems(broken, 3, True))
        broken['fgpct'] = {'min': 101, 'hist': [2], 'defined': 2, 'total': 3}
        self.assertIn('fgpct conditional histogram count', smoke.player_hist_problems(broken, 3, True))

    def test_legacy_replay_ignores_only_new_fields(self):
        stats = {'pts': {'hist': [1], 'min': 0}, 'fga': {'hist': [1], 'min': 0},
                 'fgpct': {'hist': [1], 'min': 0, 'defined': 1, 'total': 1}}
        replay = {'shooting_distribution_schema': 1, 'home': {'players': [{'periods': {
            'fg': {'stats': copy.deepcopy(stats)}, 'q1': {'stats': copy.deepcopy(stats)}}}]}, 'away': {'players': []}}
        current = copy.deepcopy(replay)
        smoke.align_legacy_shooting_schema({'shooting_distribution_schema': 1}, current)
        self.assertEqual(current, replay)
        smoke.align_legacy_shooting_schema({}, replay)
        self.assertNotIn('shooting_distribution_schema', replay)
        self.assertEqual(set(replay['home']['players'][0]['periods']['fg']['stats']), {'pts', 'fga'})
        self.assertEqual(set(replay['home']['players'][0]['periods']['q1']['stats']), {'pts'})


if __name__ == '__main__':
    unittest.main()
